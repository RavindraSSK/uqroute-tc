"""Write-once post-fault small-stage smoke ledger; no fallback, scoring or retries."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import time
from pathlib import Path
from urllib.parse import urlsplit

SUBMISSION_OBSERVATION = "local HTTP request write returned; server execution unconfirmed"


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Expected regular ledger file")
    return path.read_bytes()


def write_once(path, raw):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Symlink ledger path")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as file:
        file.write(raw)
        file.flush()
        os.fsync(file.fileno())


def json_once(path, value):
    write_once(path, (canonical(value) + "\n").encode())


def checked_rows(rows):
    ids = set()
    episodes = set()
    if not rows or len(rows) > 30:
        raise ValueError("Smoke requires one to thirty fixed small-stage requests")
    for row in rows:
        body = row["request"]
        expected_body = {
            "model": "Qwen/Qwen2.5-1.5B-Instruct",
            "messages": body["messages"],
            "temperature": 0.001,
            "max_tokens": 1024,
            "logprobs": True,
            "top_logprobs": 5,
            "stream": False,
        }
        if (
            row["stage"] != "postfault_small"
            or row["request_id"] in ids
            or row["episode_key"] in episodes
            or row["request_id"] != sha(canonical([row["episode_key"], row["stage"]]).encode())
            or row["request_sha256"] != sha(canonical(body).encode())
            or row["context_messages_sha256"] != sha(canonical(body["messages"]).encode())
            or body != expected_body
            or body.get("stream") is not False
        ):
            raise ValueError("Smoke request/stage binding differs")
        ids.add(row["request_id"])
        episodes.add(row["episode_key"])


def intent_for(row, binding_sha):
    return {
        "request_id": row["request_id"],
        "episode_key": row["episode_key"],
        "stage": row["stage"],
        "request_sha256": row["request_sha256"],
        "context_messages_sha256": row["context_messages_sha256"],
        "run_binding_sha256": binding_sha,
    }


def inspect_slot(folder, intent):
    """Never equate an occupied intent with a submitted request."""
    if not folder.exists():
        return "pending_not_attempted"
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("Invalid smoke slot directory")
    allowed = {
        "intent.json",
        "submission.json",
        "http_response.bin",
        "response_metadata.json",
        "transport_error.json",
    }
    if any(p.name not in allowed or p.is_symlink() or not p.is_file() for p in folder.iterdir()):
        raise ValueError("Unexpected smoke slot files")
    if json.loads(regular(folder / "intent.json")) != intent:
        raise ValueError("Prior smoke intent differs")
    submission = folder / "submission.json"
    if not submission.exists():
        if any((folder / n).exists() for n in ("http_response.bin", "response_metadata.json")):
            raise ValueError("Response without submission evidence")
        return "injection_unknown_no_resubmit"
    expected = intent | {
        "transition_injected": True,
        "observation": SUBMISSION_OBSERVATION,
    }
    if json.loads(regular(submission)) != expected:
        raise ValueError("Prior submission binding differs")
    raw_path, meta_path = folder / "http_response.bin", folder / "response_metadata.json"
    if not raw_path.exists() or not meta_path.exists():
        return "injected_response_unknown_no_resubmit"
    raw = regular(raw_path)
    meta = json.loads(regular(meta_path))
    if (
        meta["request_id"] != intent["request_id"]
        or meta["body_sha256"] != sha(raw)
        or type(meta["http_status"]) is not int
        or type(meta["elapsed_seconds"]) not in (int, float)
        or not 100 <= meta["http_status"] <= 599
        or not 0 <= meta["elapsed_seconds"] < float("inf")
    ):
        raise ValueError("Prior response binding differs")
    if (folder / "transport_error.json").exists():
        raise ValueError("Contradictory response and transport failure")
    return "injected_response_saved"


def replay(rows, output, binding):
    checked_rows(rows)
    if json.loads(regular(output / "run_manifest.json")) != binding:
        raise ValueError("Smoke run binding differs")
    allowed = {"run_manifest.json", "cases", ".writer.lock"}
    if any(p.name not in allowed or p.is_symlink() for p in output.iterdir()):
        raise ValueError("Unexpected smoke run entries")
    cases = output / "cases"
    expected = {r["request_id"] for r in rows}
    if cases.exists() and (
        cases.is_symlink()
        or not cases.is_dir()
        or any(p.name not in expected for p in cases.iterdir())
    ):
        raise ValueError("Unexpected smoke request slot")
    digest = sha(canonical(binding).encode())
    states = {
        r["request_id"]: inspect_slot(cases / r["request_id"], intent_for(r, digest)) for r in rows
    }
    http_errors = sum(
        json.loads(regular(cases / request_id / "response_metadata.json"))["http_status"] != 200
        for request_id, state in states.items()
        if state == "injected_response_saved"
    )
    return {
        "requests": len(rows),
        "states": states,
        "known_http_errors": http_errors,
        "pending": sum(s == "pending_not_attempted" for s in states.values()),
        "observed_injected": sum(s.startswith("injected_") for s in states.values()),
        "saved_responses": sum(s == "injected_response_saved" for s in states.values()),
        "unknown_slots": sum(s.endswith("no_resubmit") for s in states.values()),
        "official_scoring": "not_performed",
        "rq3_outcomes": "not_evaluated",
    }


def dispatch(rows, output, binding, caller, *, execute_development=False):
    """Caller must attest HTTP write completion via mark_submitted; never retry."""
    if execute_development is not True:
        raise ValueError("Explicit development execution required")
    checked_rows(rows)
    if (
        binding["purpose"] != "qwen15b-postfault-small-resource-smoke"
        or binding["request_inventory_sha256"] != sha(canonical(rows).encode())
        or binding["automatic_retries"] != 0
        or binding["held_out_access_enabled"] is not False
        or binding["main_experiment_ready"] is not False
    ):
        raise ValueError("Smoke execution binding differs")
    output = Path(output)
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Symlink smoke output")
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".writer.lock"
    # An abandoned lock is evidence to review, not permission to retry requests.
    write_once(lock, b"single writer; preserve on interrupted process\n")
    try:
        manifest = output / "run_manifest.json"
        if not manifest.exists():
            if set(p.name for p in output.iterdir()) != {".writer.lock"}:
                raise ValueError("Occupied smoke output without manifest")
            json_once(manifest, binding)
        prior = replay(rows, output, binding)
        if prior["unknown_slots"] or prior["known_http_errors"]:
            raise ValueError("Unresolved smoke slot; no automatic resubmission or continuation")
        digest = sha(canonical(binding).encode())
        for row in rows:
            folder = output / "cases" / row["request_id"]
            intent = intent_for(row, digest)
            if prior["states"][row["request_id"]] == "injected_response_saved":
                continue
            json_once(folder / "intent.json", intent)

            def mark_submitted(folder=folder, intent=intent):
                json_once(
                    folder / "submission.json",
                    intent
                    | {
                        "transition_injected": True,
                        "observation": SUBMISSION_OBSERVATION,
                    },
                )

            start = time.perf_counter()
            try:
                status, raw = caller(row["request"], mark_submitted)
            except Exception as exc:
                json_once(
                    folder / "transport_error.json",
                    {
                        "exception_type": type(exc).__name__,
                        "elapsed_seconds": time.perf_counter() - start,
                        "outcome": "unknown response; no automatic retry",
                    },
                )
                break
            if not (folder / "submission.json").exists():
                raise ValueError("Caller returned without durable submission evidence")
            if type(status) is not int or not 100 <= status <= 599 or not isinstance(raw, bytes):
                raise ValueError("Unexpected transport result; preserve occupied slot")
            write_once(folder / "http_response.bin", raw)
            json_once(
                folder / "response_metadata.json",
                {
                    "request_id": row["request_id"],
                    "http_status": status,
                    "body_sha256": sha(raw),
                    "elapsed_seconds": time.perf_counter() - start,
                },
            )
            # Known HTTP failures also stop the smoke; saved status/body are retained.
            if status != 200:
                break
        return replay(rows, output, binding)
    finally:
        lock.unlink()


def local_caller(endpoint, timeout=300):
    """One direct loopback HTTP write; no proxy, redirect or request retry."""
    url = urlsplit(endpoint)
    if (
        url.scheme != "http"
        or url.hostname not in {"127.0.0.1", "localhost", "::1"}
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path.rstrip("/") != "/v1"
    ):
        raise ValueError("Only local HTTP /v1 smoke serving is supported")

    def call(body, mark_submitted):
        connection = http.client.HTTPConnection(url.hostname, url.port or 80, timeout=timeout)
        try:
            connection.request(
                "POST",
                "/v1/chat/completions",
                canonical(body).encode(),
                {"Content-Type": "application/json"},
            )
            mark_submitted()
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    return call
