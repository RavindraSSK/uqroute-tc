"""Pinned 30-request recovery resource smoke; no fallback, references or retries."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

CODE = "fbe1e3ed1892cfa4b71fb69559af8235107ad0dc"
ZIP_SHA = "ecd1e39441ddffdd4623d699cd6112dc791c322bfcec9336390f71d1cde2f453"
MANIFEST_SHA = "3b747531cb19eb6e11a5fd74cdf338382f47e22ac0b5c9f596c84f08006d105c"
MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
REV = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"
MEMBERS = {"manifest.json", "requests.json", "episodes.json", "ledger.py"}


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def dependencies(repo):
    support = module(
        "_recovery_gpu_support",
        repo / "tools/development_audits/corrected_generation_v1/support.py",
    )
    # workflow imports its neighboring support module by its historical name.
    sys.modules["support"] = support
    workflow = module(
        "_recovery_gpu_workflow",
        repo / "tools/development_audits/corrected_generation_v1/workflow.py",
    )
    support.verify_baseline(repo)
    return support, workflow


def load_plan(repo, prepared):
    support, workflow = dependencies(repo)
    payloads = {n: support.read(prepared / n) for n in MEMBERS}
    if support.sha(payloads["manifest.json"]) != MANIFEST_SHA:
        raise ValueError("Owner smoke manifest fingerprint differs")
    manifest = support.loads(payloads["manifest.json"])
    if manifest["payload_sha256"] != {
        n: support.sha(b) for n, b in payloads.items() if n != "manifest.json"
    }:
        raise ValueError("Smoke payload inventory differs")
    config = support.loads(support.source_bytes(repo)["docs/config/task1_single_sample_v1.json"])
    if (
        manifest["version"] != "uqroute-recovery-resource-smoke-1.0.0"
        or manifest["purpose"] != "qwen15b-postfault-small-resource-smoke"
        or manifest["model_settings"] != config["models"][0]
        or manifest["server_settings"] != config["single_sample"]["server"]
        or manifest["request_count"] != 30
        or manifest["maximum_new_requests"] != 30
        or manifest["fallback_requests"] != 0
        or manifest["automatic_retries"] != 0
        or any(
            manifest[n] is not False
            for n in ("dispatch_authorized", "held_out_access_enabled", "main_experiment_ready")
        )
    ):
        raise ValueError("Bounded smoke scope/settings differ")
    expected_ledger = support.read(repo / "tools/development_audits/recovery_smoke_v1/ledger.py")
    if payloads["ledger.py"] != expected_ledger.replace(b"\r\n", b"\n"):
        raise ValueError("Packaged ledger differs from pinned repository")
    ledger = module("_recovery_gpu_ledger", prepared / "ledger.py")
    rows, episodes = (
        support.loads(payloads["requests.json"]),
        support.loads(payloads["episodes.json"]),
    )
    ledger.checked_rows(rows)
    if (
        len(rows) != 30
        or ledger.sha(ledger.canonical(rows).encode()) != manifest["request_inventory_sha256"]
    ):
        raise ValueError("Smoke request inventory differs")
    indexed = {e["episode_key"]: e for e in episodes}
    if len(indexed) != len(episodes) or len(episodes) != 30:
        raise ValueError("Episode inventory differs")
    groups = {}
    for row in rows:
        episode = indexed[row["episode_key"]]
        if (
            episode["split"] != "development"
            or episode["population"] != "primary"
            or episode["source_file"] != "clean.jsonl"
            or episode["injection_eligible"] is not True
            or episode["transition_injected"] is not None
            or episode["context_messages_sha256"] != row["context_messages_sha256"]
        ):
            raise ValueError("Episode/context binding differs")
        groups.setdefault((episode["benchmark"], episode["canonical_base_id"]), []).append(
            episode["fault_type"]
        )
    faults = {
        "timeout",
        "rate_limit",
        "auth_error",
        "server_error",
        "malformed_response",
        "schema_drift",
    }
    if (
        len(groups) != 5
        or {b for b, _ in groups} != {"apibank", "bfcl_v3", "rotbench", "toolalpaca", "tooleyes"}
        or any(len(v) != 6 or set(v) != faults for v in groups.values())
    ):
        raise ValueError("Five benchmark groups and all six faults required")
    return manifest, rows, indexed, ledger, support, workflow


def unpack(task):
    import hashlib

    raw = (task / "transfer.zip").read_bytes()
    if hashlib.sha256(raw).hexdigest() != ZIP_SHA:
        raise ValueError("Owner smoke ZIP fingerprint differs")
    prepared = task / "prepared"
    if prepared.exists():
        raise ValueError("Prepared execution input already exists")
    with zipfile.ZipFile(task / "transfer.zip") as zipped:
        if (
            len(zipped.namelist()) != 4
            or set(zipped.namelist()) != MEMBERS
            or zipped.testzip() is not None
        ):
            raise ValueError("Smoke ZIP member inventory differs")
        payloads = {n: zipped.read(n) for n in MEMBERS}
    if hashlib.sha256(payloads["manifest.json"]).hexdigest() != MANIFEST_SHA:
        raise ValueError("Owner smoke manifest fingerprint differs")
    prepared.mkdir()
    for name, content in payloads.items():
        with (prepared / name).open("xb") as file:
            file.write(content)


def server_context_check(rows, local_report, post):
    indexed = {r["request_id"]: r for r in local_report["per_request"]}
    if len(indexed) != len(rows) or set(indexed) != {r["request_id"] for r in rows}:
        raise ValueError("Local tokenizer coverage differs")
    import hashlib

    result = []
    for row in rows:
        saved = indexed[row["request_id"]]
        status, raw = post(
            {
                "model": MODEL,
                "messages": row["request"]["messages"],
                "add_generation_prompt": True,
                "add_special_tokens": False,
            }
        )
        reply = json.loads(raw)
        tokens = reply.get("tokens")
        if (
            status != 200
            or not isinstance(tokens, list)
            or not tokens
            or any(type(t) is not int for t in tokens)
            or reply["count"] != len(tokens)
            or len(tokens) != saved["prompt_tokens"]
            or hashlib.sha256(json.dumps(tokens, separators=(",", ":")).encode()).hexdigest()
            != saved["token_ids_sha256"]
            or len(tokens) + row["request"]["max_tokens"] > 8192
        ):
            raise ValueError("Server/local tokenization mismatch; no generation allowed")
        result.append(
            {
                "request_id": row["request_id"],
                "prompt_tokens": len(tokens),
                "token_ids_sha256": saved["token_ids_sha256"],
                "response_sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return {
        "requests": len(result),
        "all_match": True,
        "generation_requests_sent": 0,
        "scope": "Server tokenizer endpoint only; not model generation",
        "per_request": result,
    }


def binding_for(task, manifest, rows, support, workflow):
    runtime_raw = support.read(task / "metadata/runtime.json")
    runtime = support.loads(runtime_raw)
    workflow.check_runtime(runtime, manifest)
    local = support.loads(support.read(task / "metadata/tokenizer_preflight.json"))
    server = support.loads(support.read(task / "metadata/server_tokenizer_preflight.json"))
    if (
        server["all_match"] is not True
        or server["requests"] != len(rows)
        or local["overflow_requests"] != 0
        or local["requests"] != len(rows)
    ):
        raise ValueError("Complete matching runtime context checks required")
    return {
        "purpose": manifest["purpose"],
        "request_inventory_sha256": manifest["request_inventory_sha256"],
        "prepared_manifest_sha256": MANIFEST_SHA,
        "source_archive_sha256": ZIP_SHA,
        "runtime_attestation": runtime,
        "runtime_attestation_sha256": support.sha(runtime_raw),
        "context_preflight_sha256": {
            name: support.sha(support.read(task / "metadata" / name))
            for name in ("tokenizer_preflight.json", "server_tokenizer_preflight.json")
        },
        "client_source_sha256": support.sha(Path(__file__).read_bytes()),
        "automatic_retries": 0,
        "held_out_access_enabled": False,
        "main_experiment_ready": False,
        "endpoint": "http://127.0.0.1:8000/v1",
        "authorization": "Explicit user-run notebook for 30 smoke requests only",
    }


def run(task, execute=False):
    if execute is not True:
        raise ValueError("Explicit --execute-development required")
    manifest, rows, _, ledger, support, workflow = load_plan(task / "repo", task / "prepared")
    binding = binding_for(task, manifest, rows, support, workflow)
    if (task / "run").exists():
        raise ValueError("Existing execution run; preserve it, do not repeat smoke requests")
    status, raw = workflow.transport(binding["endpoint"], "/models", timeout=30)
    if status != 200 or MODEL not in {m["id"] for m in support.loads(raw)["data"]}:
        raise ValueError("Wrong local model server")
    result = ledger.dispatch(
        rows,
        task / "run",
        binding,
        ledger.local_caller(binding["endpoint"]),
        execute_development=True,
    )
    ledger.json_once(task / "metadata/dispatch_summary.json", result)
    print(json.dumps({n: v for n, v in result.items() if n != "states"}, indent=2), flush=True)
    if result["saved_responses"] != 30 or result["known_http_errors"] or result["unknown_slots"]:
        raise ValueError("Incomplete smoke; preserve all slots and do not retry")


def replay(task):
    manifest, rows, episodes, ledger, support, workflow = load_plan(
        task / "repo", task / "prepared"
    )
    binding = binding_for(task, manifest, rows, support, workflow)
    states = ledger.replay(rows, task / "run", binding)
    frozen = support.methods(task / "repo")
    records = []
    sums, missing = {"prompt_tokens": 0, "completion_tokens": 0}, 0
    for row in rows:
        state = states["states"][row["request_id"]]
        record = {
            "request_id": row["request_id"],
            "episode_key": row["episode_key"],
            "context_messages_sha256": row["context_messages_sha256"],
            "benchmark": episodes[row["episode_key"]]["benchmark"],
            "canonical_base_id": episodes[row["episode_key"]]["canonical_base_id"],
            "fault_type": episodes[row["episode_key"]]["fault_type"],
            "ledger_state": state,
            "transition_injected": True if state.startswith("injected_") else None,
            "official_correctness": None,
            "validation": None,
            "usage": None,
            "initial_usage": episodes[row["episode_key"]].get("initial_usage"),
        }
        folder = task / "run/cases" / row["request_id"]
        if state == "injected_response_saved":
            meta = support.loads(support.read(folder / "response_metadata.json"))
            record["http_status"] = meta["http_status"]
            record["elapsed_seconds"] = meta["elapsed_seconds"]
            raw = support.read(folder / "http_response.bin")
            try:
                response = support.loads(raw)
                record["usage"] = response.get("usage") if isinstance(response, dict) else None
                record["validation"] = (
                    workflow.evaluate(response, record["benchmark"], frozen)
                    if meta["http_status"] == 200
                    else {"status": "http_error"}
                )
            except (ValueError, KeyError, TypeError, OverflowError, AttributeError) as exc:
                record["validation"] = {
                    "status": "validation_error",
                    "exception_type": type(exc).__name__,
                }
        usage = record["usage"]
        if isinstance(usage, dict) and all(
            type(usage.get(n)) is int and usage[n] >= 0 for n in sums
        ):
            for name in sums:
                sums[name] += usage[name]
        else:
            missing += 1
        records.append(record)
    output = task / "replay"
    if output.exists():
        raise ValueError("Replay output already exists; preserve it")
    output.mkdir()
    summary = {n: v for n, v in states.items() if n != "states"}
    summary.update(
        validation_status_counts=dict(
            Counter((r["validation"] or {}).get("status", "no_saved_response") for r in records)
        ),
        known_usage_sums=sums,
        missing_usage_slots=missing,
        usage_totals=None if missing else sums,
        fallback_requests=0,
        initial_generation="reused source evidence, not new calls",
        held_out_access_enabled=False,
        main_experiment_ready=False,
    )
    ledger.json_once(output / "records.json", records)
    ledger.json_once(output / "summary.json", summary)
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("run", "replay"))
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--execute-development", action="store_true")
    args = parser.parse_args()
    if args.mode == "run":
        run(args.task.resolve(), args.execute_development)
    else:
        replay(args.task.resolve())


if __name__ == "__main__":
    main()
