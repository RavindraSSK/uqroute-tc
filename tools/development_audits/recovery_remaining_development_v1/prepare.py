"""Package remaining original recovery development slots; CPU only, no dispatcher."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = Path("artifacts/local_development_audits")
OUTPUT = ROOT / "recovery_remaining_development_preparation_v1"
POLICY_SHA = "5e17b743dcace3601177ba610169d715da19417768f67864c02cab2427b78d85"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def canonical(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")
    )


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Regular preparation input required")
    return path.read_bytes()


def check_closed_review(records, summary, provenance, paired, paired_raw, reviewer):
    if (
        summary["rows"] != 30
        or summary["groups"] != 5
        or summary != reviewer.summarize(records)
        or summary["initial_control_name_rows"] != 6
        or provenance["paired_scoring_recomputed_exactly"] is not True
        or provenance["policy_sha256_lf"] != reviewer.POLICY_SHA
        or provenance["original_paired_scoring_sha256"]
        != {n: sha(raw) for n, raw in paired_raw.items()}
    ):
        raise ValueError("Completed unchanged paired smoke review required")
    expected = {r["request_id"]: r for r in paired}
    if (
        len(records) != 30
        or len(expected) != 30
        or set(expected) != {r["request_id"] for r in records}
    ):
        raise ValueError("All thirty scored/reviewed pairs required")
    fields = (
        "episode_key",
        "paired_small_request_id",
        "canonical_base_id",
        "benchmark",
        "fault_type",
        "panel",
        "initial_reference_match",
        "small_reference_match",
        "fallback_reference_match",
        "small_parser_status",
        "fallback_parser_status",
    )
    for r in records:
        if any(r[n] != expected[r["request_id"]][n] for n in fields):
            raise ValueError("Review changed an original paired identity/outcome")


def context_check(roles, report, settings):
    for role, rows in roles.items():
        value = report[role]
        model = settings["small" if role == "postfault_small" else "fallback"]
        indexed = {r["request_id"]: r for r in value["per_request"]}
        if (
            len(indexed) != len(rows)
            or len(value["per_request"]) != len(rows)
            or value["requests"] != len(rows)
            or value["overflow_requests"] != 0
            or value["model_id"] != model["model_id"]
            or value["tokenizer_revision"] != model["tokenizer_revision"]
            or value["context_limit"] != 8192
            or set(indexed) != {r["request_id"] for r in rows.values()}
        ):
            raise ValueError("Complete pinned full-role tokenizer evidence required")
        for row in rows.values():
            token = indexed[row["request_id"]]
            if (
                any(
                    token[n] != row[n]
                    for n in ("episode_key", "request_sha256", "context_messages_sha256")
                )
                or token["within_limit"] is not True
                or token["completion_allowance"] != 1024
                or type(token["prompt_tokens"]) is not int
                or token["prompt_tokens"] < 1
                or token["prompt_tokens"] + 1024 > 8192
            ):
                raise ValueError("Role/request/context token binding differs")


def remaining_plan(episodes, roles, completed):
    """Inventory only: completed response IDs, never labels, determine reuse."""
    if set(roles) != {"postfault_small", "postfault_fallback"} or set(completed) - set(roles):
        raise ValueError("Both original roles required")
    small_done = {r["episode_key"] for r in completed.get("postfault_small", {}).values()}
    if any(
        r["episode_key"] not in small_done for r in completed.get("postfault_fallback", {}).values()
    ):
        raise ValueError("Completed fallback requires a known completed small parent")
    indexed = {e["episode_key"]: e for e in episodes}
    eligible = {k for k, e in indexed.items() if e["injection_eligible"] is True}
    if len(indexed) != len(episodes) or any(set(rows) != eligible for rows in roles.values()):
        raise ValueError("Complete original eligible episode coverage required")
    ordered = sorted(
        eligible,
        key=lambda k: (
            indexed[k]["benchmark"],
            indexed[k]["canonical_base_id"],
            indexed[k]["fault_type"],
            k,
        ),
    )
    pending, batches, reused = {}, {}, {}
    for role, rows in roles.items():
        known = completed.get(role, {})
        originals = {r["request_id"]: r for r in rows.values()}
        if any(key not in originals or row != originals[key] for key, row in known.items()):
            raise ValueError("Known smoke slot differs from original full role plan")
        reused[role] = len(known)
        selected = [deepcopy(rows[k]) for k in ordered if rows[k]["request_id"] not in known]
        pending[role] = selected
        batches[role] = [
            {
                "batch_index": i // 30,
                "request_ids": [r["request_id"] for r in selected[i : i + 30]],
                "maximum_new_requests": len(selected[i : i + 30]),
                "parent_small_response_required_before_dispatch": role == "postfault_fallback",
            }
            for i in range(0, len(selected), 30)
        ]
        if len(selected) + len(known) != len(rows):
            raise ValueError("Pending/completed partition differs")
    # A fallback pending slot must wait for an observed known small response,
    # including when that response is a refusal/no-call. Unknowns are never retried.
    return pending, batches, reused


def prepare(repo):
    prior = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        return _prepare(repo.resolve())
    finally:
        sys.dont_write_bytecode = prior


def _prepare(repo):
    output = repo / OUTPUT
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Fresh remaining-development preparation required")
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(OUTPUT / "summary.json")], cwd=repo
    ).returncode:
        raise ValueError("Prepared private inputs must stay ignored")
    raw = regular(HERE / "policy.json").replace(b"\r\n", b"\n")
    if sha(raw) != POLICY_SHA:
        raise ValueError("Remaining-development policy differs")
    policy = json.loads(raw)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", policy["baseline_commit"], "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    for n, h in policy["source_sha256_lf"].items():
        if sha(regular(repo / n).replace(b"\r\n", b"\n")) != h:
            raise ValueError("Pinned preparation dependency differs: " + n)
    root, inputs = repo / ROOT, {}

    def read(path):
        raw = regular(path)
        inputs[path] = sha(raw)
        return raw

    scorer = module(
        "_remaining_pair_scorer",
        repo / "tools/development_audits/recovery_fallback_smoke_scoring_v1/score_pairs.py",
    )
    original = module(
        "_remaining_original_scorer",
        repo / "tools/development_audits/recovery_smoke_scoring_v1/score_smoke.py",
    )
    paired_policy = json.loads(
        read(repo / "tools/development_audits/recovery_fallback_smoke_scoring_v1/policy.json")
    )
    with scorer.workflow_modules():
        _payloads, saved_fallback, _ = scorer.verified_payloads(
            repo, paired_policy, original, inputs
        )
    reviewer = module(
        "_remaining_closed_review",
        repo / "tools/development_audits/recovery_matched_smoke_review_v1/review_pairs.py",
    )
    review_root = root / "recovery_matched_smoke_behaviour_review_v1"
    review = {
        n: json.loads(read(review_root / n))
        for n in ("records.json", "summary.json", "provenance.json")
    }
    paired_root = root / "recovery_matched_smoke_paired_reference_scoring_v1"
    paired_raw = {
        n: read(paired_root / n) for n in ("records.json", "summary.json", "provenance.json")
    }
    check_closed_review(
        review["records.json"],
        review["summary.json"],
        review["provenance.json"],
        json.loads(paired_raw["records.json"]),
        paired_raw,
        reviewer,
    )
    for n, h in review["provenance.json"]["input_sha256"].items():
        inputs[repo / n] = h
    known_small = json.loads(
        read(root / "recovery_smoke_qwen15b_import_dd91a73f/evidence/prepared/requests.json")
    )
    completed = {
        "postfault_small": {r["request_id"]: r for r in known_small},
        "postfault_fallback": {
            r["request_id"]: {k: v for k, v in r.items() if k != "paired_small_request_id"}
            for r in saved_fallback
        },
    }
    preflight = module(
        "_remaining_preflight",
        repo / "tools/development_audits/recovery_context_preflight_v1/preflight.py",
    )
    config = json.loads(read(repo / "docs/config/task1_single_sample_v1.json"))
    context = json.loads(read(root / "recovery_context_preflight_v1/report.json"))
    summary = {
        "version": policy["version"],
        "models": {},
        "generation_requests_sent": 0,
        "dispatch_authorized": False,
        "executor_implemented": False,
        "runtime_quota_validation": "pending",
        "held_out_access_enabled": False,
        "main_experiment_ready": False,
        "labels_used_for_selection": False,
    }
    with tempfile.TemporaryDirectory(dir=root, prefix="remaining-recovery-") as folder:
        stage = Path(folder)
        for key, (archive_sha, manifest_sha, eligible, _) in preflight.TRANSFERS.items():
            path = (
                root
                / "recovery_development_preparation_v1"
                / (key + "_recovery_development_transfer_v1.zip")
            )
            data = preflight.read_archive(path, archive_sha, manifest_sha)
            inputs[path] = archive_sha
            manifest, roles = preflight.validate_plan(data, key, config, eligible)
            context_check(roles, context["models"][key], manifest["model_settings"])
            pending, batches, reused = remaining_plan(
                data["episodes.json"], roles, completed if key == "qwen15b" else {}
            )
            counts = {role: len(rows) for role, rows in pending.items()}
            if counts != policy["expected_pending"][key]:
                raise ValueError("Original pending inventory differs")
            files = {
                "episodes.json": (canonical(data["episodes.json"]) + "\n").encode(),
                "pending_requests.json": (canonical(pending) + "\n").encode(),
                "batch_inventory.json": (canonical(batches) + "\n").encode(),
            }
            transfer = {
                "version": policy["version"],
                "small_model_key": key,
                "purpose": "remaining-original-development-pair-collection",
                "model_settings": manifest["model_settings"],
                "server_settings": manifest["server_settings"],
                "original_archive_sha256": archive_sha,
                "reused_complete_slots": reused,
                "pending_roles": counts,
                "maximum_batch_requests": 30,
                "fallback_parent_rule": (
                    "Known saved small response required; "
                    "unknown/HTTP-failure slots stop execution; no automatic retries"
                ),
                "dispatch_authorized": False,
                "executor_implemented": False,
                "static_dispatcher_compatible": False,
                "labels_used_for_selection": False,
                "held_out_access_enabled": False,
                "main_experiment_ready": False,
                "payload_sha256": {n: sha(b) for n, b in files.items()},
            }
            files["manifest.json"] = (canonical(transfer) + "\n").encode()
            archive = stage / (key + "_remaining_recovery_development_v1.zip")
            with zipfile.ZipFile(archive, "x", zipfile.ZIP_STORED) as zipped:
                for n, raw in sorted(files.items()):
                    info = zipfile.ZipInfo(n, date_time=(1980, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = 0o600 << 16
                    info.compress_type = zipfile.ZIP_STORED
                    zipped.writestr(info, raw)
            with zipfile.ZipFile(archive) as zipped:
                if zipped.testzip() is not None or any(
                    zipped.read(n) != raw for n, raw in files.items()
                ):
                    raise ValueError("Remaining transfer differs")
            summary["models"][key] = {
                "eligible_episodes": eligible,
                "terminal_no_injection": len(data["episodes.json"]) - eligible,
                "reused_complete_slots": reused,
                "pending_roles": counts,
                "batches": {role: len(value) for role, value in batches.items()},
                "maximum_potential_new_calls": sum(counts.values()),
                "archive": archive.name,
                "archive_sha256": sha(archive.read_bytes()),
                "manifest_sha256": sha(files["manifest.json"]),
            }
        summary["maximum_potential_new_calls"] = sum(
            m["maximum_potential_new_calls"] for m in summary["models"].values()
        )
        for n, value in (
            ("summary.json", summary),
            (
                "provenance.json",
                {
                    "policy_sha256_lf": POLICY_SHA,
                    "input_sha256": {p.relative_to(repo).as_posix(): h for p, h in inputs.items()},
                },
            ),
        ):
            (stage / n).write_text(canonical(value) + "\n", encoding="utf-8", newline="\n")
        for path, h in inputs.items():
            if sha(regular(path)) != h:
                raise ValueError("Prior source/evidence changed during preparation")
        publisher = module(
            "_remaining_publish",
            repo
            / "tools/development_audits"
            / "fallback_full_development_scoring_v1/score_fallback_full.py",
        )
        publisher.publish_directory(stage, output)
    return summary


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    if Path.cwd().resolve() != REPO:
        raise SystemExit("Run from the uqroute-tc repository root")
    try:
        subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(HERE), "-p", "test_*.py"],
            cwd=REPO,
            check=True,
        )
        result = prepare(REPO)
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as exc:
        raise SystemExit(
            "Remaining recovery preparation stopped: "
            + str(exc)
            + ". Preserve prior evidence; no generation."
        ) from None
    print(json.dumps(result, indent=2))
    print("Prepared:", OUTPUT)
    print("CPU only. No downloads, generation, scoring, runtime authorization or held-out access.")


if __name__ == "__main__":
    main()
