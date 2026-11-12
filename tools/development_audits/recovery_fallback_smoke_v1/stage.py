"""Stage thirty matched fault-conditioned 14B fallback requests; no inference."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path

import ledger

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = Path("artifacts/local_development_audits")
OUTPUT = ROOT / "recovery_matched_fallback_smoke_preparation_v1"
PARENT_SHA = "dd91a73f5f565269f83d70773fd25fd64c82785029e3d96b139682c072b59595"
PARENT_MANIFEST = "3b747531cb19eb6e11a5fd74cdf338382f47e22ac0b5c9f596c84f08006d105c"
POLICY_SHA = "b41dcac018c2ceb9d7b27e36f4b787ae4ca9f13f19d16e3cc142efc5ac99b3ac"


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def checked(path, expected, inputs):
    raw = ledger.regular(path)
    if ledger.sha(raw) != expected:
        raise ValueError("Original input fingerprint differs: " + path.name)
    inputs[path] = expected
    return raw


def matched_requests(parent_requests, parent_episodes, parent_records, full_data, roles):
    """Select every parent episode by identity only, preserving the exact messages."""
    if len(parent_requests) != 30 or len(parent_episodes) != 30 or len(parent_records) != 30:
        raise ValueError("All thirty parent episodes and known responses required")
    full_episodes = {e["episode_key"]: e for e in full_data["episodes.json"]}
    records = {r["request_id"]: r for r in parent_records}
    eps = {e["episode_key"]: e for e in parent_episodes}
    if len(records) != 30 or len(eps) != 30:
        raise ValueError("Duplicate parent identities")
    result, receipts = [], []
    for small in parent_requests:
        key = small["episode_key"]
        if (
            small != roles["postfault_small"][key]
            or eps[key] != full_episodes[key]
            or eps[key]["injection_eligible"] is not True
        ):
            raise ValueError("Parent differs from the original full recovery plan")
        saved = records[small["request_id"]]
        if (
            saved["episode_key"] != key
            or saved["context_messages_sha256"] != small["context_messages_sha256"]
            or saved["ledger_state"] != "injected_response_saved"
            or saved["transition_injected"] is not True
            or saved["http_status"] != 200
        ):
            raise ValueError("Known parent small response and observed submission required")
        fallback = deepcopy(roles["postfault_fallback"][key])
        if fallback["context_messages_sha256"] != small["context_messages_sha256"] or {
            n: v for n, v in fallback["request"].items() if n != "model"
        } != {n: v for n, v in small["request"].items() if n != "model"}:
            raise ValueError("Fallback must use the same original fault history")
        fallback["paired_small_request_id"] = small["request_id"]
        result.append(fallback)
        receipts.append(
            {
                "episode_key": key,
                "request_id": small["request_id"],
                "context_messages_sha256": small["context_messages_sha256"],
                "request_sha256": small["request_sha256"],
                "http_status": saved["http_status"],
                "transition_injected": True,
                "evidence_status": saved["validation"]["status"],
                "parser_status": saved["validation"]["parser_status"],
                "usage": saved["usage"],
                "elapsed_seconds": saved["elapsed_seconds"],
            }
        )
    ledger.checked_rows(result)
    if len({r["episode_key"] for r in result}) != 30:
        raise ValueError("Fallback subset/duplicates are not allowed")
    return result, receipts


def context_checks(requests, preflight, settings):
    if (
        preflight["requests"] != 750
        or preflight["overflow_requests"] != 0
        or preflight["model_id"] != settings["model_id"]
        or preflight["tokenizer_revision"] != settings["tokenizer_revision"]
        or preflight["context_limit"] != 8192
    ):
        raise ValueError("Completed pinned 14B context preflight required")
    rows = {r["request_id"]: r for r in preflight["per_request"]}
    if len(rows) != 750 or len(preflight["per_request"]) != 750:
        raise ValueError("Full fallback context coverage differs")
    selected = []
    for request in requests:
        row = rows[request["request_id"]]
        if (
            any(
                row[n] != request[n]
                for n in ("episode_key", "request_sha256", "context_messages_sha256")
            )
            or row["within_limit"] is not True
            or type(row["prompt_tokens"]) is not int
            or row["prompt_tokens"] < 1
            or row["completion_allowance"] != 1024
            or row["prompt_tokens"] + 1024 > 8192
        ):
            raise ValueError("Selected fallback context token evidence differs")
        selected.append(row)
    return selected


def review_checks(review_summary, review_records, review_provenance, scored_records, scored_raw):
    if (
        review_provenance["reference_scoring_recomputed_exactly"] is not True
        or any(
            review_provenance["original_scoring_sha256"][n] != ledger.sha(raw)
            for n, raw in scored_raw.items()
        )
        or len(review_records) != 30
    ):
        raise ValueError("Completed owner review and unchanged reference scores required")
    original = {r["request_id"]: r for r in scored_records}
    if set(original) != {r["request_id"] for r in review_records}:
        raise ValueError("Review cohort must retain all thirty scored episodes")
    for r in review_records:
        before = original[r["request_id"]]
        if any(
            r[n] != before[n]
            for n in (
                "episode_key",
                "canonical_base_id",
                "benchmark",
                "fault_type",
                "panel",
                "initial_reference_match",
                "postfault_reference_match",
            )
        ):
            raise ValueError("Review altered an original score or identity")
    if review_summary["rows"] != 30 or review_summary["groups"] != 5:
        raise ValueError("Complete five-group owner review required")


def stage(repo):
    prior = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        return _stage(repo.resolve())
    finally:
        sys.dont_write_bytecode = prior


def _stage(repo):
    output = repo / OUTPUT
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Fresh matched fallback staging required; preserve existing outputs")
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(OUTPUT / "summary.json")], cwd=repo
    ).returncode:
        raise ValueError("Private fallback plan must stay ignored")
    policy_raw = ledger.regular(HERE / "policy.json").replace(b"\r\n", b"\n")
    if ledger.sha(policy_raw) != POLICY_SHA:
        raise ValueError("Matched fallback policy fingerprint differs")
    policy = json.loads(policy_raw)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", policy["baseline_commit"], "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    for name, expected in policy["source_sha256_lf"].items():
        if ledger.sha(ledger.regular(repo / name).replace(b"\r\n", b"\n")) != expected:
            raise ValueError("Pinned staging dependency differs: " + name)
    inputs = {}
    root = repo / ROOT
    preflight = module(
        "_matched_fallback_preflight",
        repo / "tools/development_audits/recovery_context_preflight_v1/preflight.py",
    )
    config_path = repo / "docs/config/task1_single_sample_v1.json"
    config_raw = ledger.regular(config_path)
    if ledger.sha(config_raw.replace(b"\r\n", b"\n")) != preflight.CONFIG_SHA:
        raise ValueError("Frozen model configuration differs")
    inputs[config_path] = ledger.sha(config_raw)
    config = preflight.loads(config_raw)
    a, m, eligible, _ = preflight.TRANSFERS["qwen15b"]
    path = root / "recovery_development_preparation_v1/qwen15b_recovery_development_transfer_v1.zip"
    full = preflight.read_archive(path, a, m)
    inputs[path] = a
    manifest, roles = preflight.validate_plan(full, "qwen15b", config, eligible)
    owner = root / "recovery_smoke_qwen15b_import_dd91a73f"
    evidence = owner / "evidence"
    importer = module(
        "_matched_fallback_import",
        repo / "tools/development_audits/recovery_smoke_import_v1/import_smoke.py",
    )
    policy_path = repo / "tools/development_audits/recovery_smoke_scoring_v1/policy.json"
    source_policy = json.loads(ledger.regular(policy_path))
    index = checked(
        evidence / "metadata/export_file_hashes.json",
        source_policy["smoke_export_manifest_sha256"],
        inputs,
    )
    payloads = {
        name: checked(evidence / name, fingerprint, inputs)
        for name, fingerprint in json.loads(index).items()
    }
    payloads["metadata/export_file_hashes.json"] = index
    importer.verify_members(payloads)
    importer.check_runtime_evidence(payloads)
    client = module("_matched_parent_client", evidence / "metadata/client.py")
    parent_plan, parent_requests, _, parent_ledger, support, workflow = client.load_plan(
        owner / "reproduced/repo", evidence / "prepared"
    )
    if ledger.sha(payloads["prepared/manifest.json"]) != PARENT_MANIFEST:
        raise ValueError("Parent smoke manifest differs")
    state = parent_ledger.replay(
        parent_requests,
        evidence / "run",
        client.binding_for(evidence, parent_plan, parent_requests, support, workflow),
    )
    if state["saved_responses"] != 30 or state["unknown_slots"] or state["known_http_errors"]:
        raise ValueError("No fallback may follow an unknown parent outcome")
    episodes = json.loads(payloads["prepared/episodes.json"])
    parent_records = json.loads(payloads["replay/records.json"])
    requests, receipts = matched_requests(parent_requests, episodes, parent_records, full, roles)
    review = module(
        "_matched_owner_review",
        repo / "tools/development_audits/recovery_smoke_review_v1/review.py",
    )
    review_root = root / "recovery_smoke_behaviour_review_v1"
    scored_root = root / "recovery_smoke_reference_scoring_v1"
    scored_raw = {
        n: ledger.regular(scored_root / n)
        for n in ("records.json", "summary.json", "provenance.json")
    }
    review_raw = {
        n: ledger.regular(review_root / n)
        for n in ("records.json", "summary.json", "provenance.json")
    }
    for folder, collection in ((scored_root, scored_raw), (review_root, review_raw)):
        inputs.update({folder / n: ledger.sha(raw) for n, raw in collection.items()})
    review_summary, review_records, provenance = (
        json.loads(review_raw[n]) for n in ("summary.json", "records.json", "provenance.json")
    )
    if (
        provenance["policy_sha256_lf"] != review.POLICY_SHA
        or review.summarize(review_records) != review_summary
    ):
        raise ValueError("Owner structural review binding differs")
    review_checks(
        review_summary,
        review_records,
        provenance,
        json.loads(scored_raw["records.json"]),
        scored_raw,
    )
    frozen = support.methods(owner / "reproduced/repo")
    reviewed = {r["request_id"]: r for r in review_records}
    for parent in parent_requests:
        ep = next(e for e in episodes if e["episode_key"] == parent["episode_key"])
        before = frozen["parse"](parent["request"]["messages"][-2]["content"], ep["benchmark"])
        body = json.loads(payloads["run/cases/" + parent["request_id"] + "/http_response.bin"])
        after = frozen["parse"](body["choices"][0]["message"]["content"], ep["benchmark"])
        if reviewed[parent["request_id"]]["behaviour"] != review.behaviour(
            before, after, ep["benchmark"]
        ):
            raise ValueError("Owner structural observations differ from preserved text")
    context_path = root / "recovery_context_preflight_v1/report.json"
    context_raw = ledger.regular(context_path)
    inputs[context_path] = ledger.sha(context_raw)
    context = context_checks(
        requests,
        json.loads(context_raw)["models"]["qwen15b"]["postfault_fallback"],
        manifest["model_settings"]["fallback"],
    )
    files = {
        "requests.json": (ledger.canonical(requests) + "\n").encode(),
        "episodes.json": (ledger.canonical(episodes) + "\n").encode(),
        "paired_small_records.json": (ledger.canonical(receipts) + "\n").encode(),
        "ledger.py": ledger.regular(HERE / "ledger.py").replace(b"\r\n", b"\n"),
    }
    prepared = {
        "version": "uqroute-matched-recovery-fallback-smoke-1.0.0",
        "purpose": "qwen14b-postfault-fallback-matched-smoke",
        "collection_mode": "all_matched_smoke_episodes_no_threshold",
        "initial_model_key": "qwen15b",
        "model_settings": manifest["model_settings"]["fallback"],
        "server_settings": manifest["server_settings"],
        "request_count": 30,
        "maximum_new_requests": 30,
        "fresh_small_requests": 0,
        "parent_smoke_archive_sha256": PARENT_SHA,
        "parent_prepared_manifest_sha256": PARENT_MANIFEST,
        "full_recovery_archive_sha256": a,
        "known_parent_small_slots": 30,
        "payload_sha256": {n: ledger.sha(b) for n, b in files.items()},
        "automatic_retries": 0,
        "dispatch_authorized": False,
        "static_dispatcher_compatible": False,
        "runtime_validation": "pending",
        "held_out_access_enabled": False,
        "main_experiment_ready": False,
        "final_threshold": "not_selected",
        "labels_used_for_selection": False,
        "scope": (
            "Thirty matched fault histories; no static fallback reuse or later answer appended"
        ),
    }
    files["manifest.json"] = (ledger.canonical(prepared) + "\n").encode()
    with tempfile.TemporaryDirectory(dir=root, prefix="matched-fallback-stage-") as folder:
        dest = Path(folder)
        archive = dest / "qwen14b_matched_recovery_fallback_smoke_v1.zip"
        with zipfile.ZipFile(archive, "x", zipfile.ZIP_STORED) as zipped:
            for name, raw in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o600 << 16
                zipped.writestr(info, raw)
        with zipfile.ZipFile(archive) as zipped:
            if (
                zipped.testzip() is not None
                or set(zipped.namelist()) != set(files)
                or any(zipped.read(n) != raw for n, raw in files.items())
            ):
                raise ValueError("Fallback transfer verification differs")
        summary = {
            "version": prepared["version"],
            "matched_episodes": 30,
            "canonical_groups": len({e["canonical_base_id"] for e in episodes}),
            "benchmarks": sorted({e["benchmark"] for e in episodes}),
            "planned_new_fallback_requests": 30,
            "planned_new_small_requests": 0,
            "known_parent_small_responses": 30,
            "parent_no_parsed_call_rows_retained": review_summary["buckets"][
                "no_parsed_postfault_call"
            ],
            "initial_control_name_rows_retained": review_summary["initial_first_control_name_rows"],
            "selected_prompt_tokens_max": max(r["prompt_tokens"] for r in context),
            "context_overflows": 0,
            "model_id": prepared["model_settings"]["model_id"],
            "model_revision": prepared["model_settings"]["model_revision"],
            "archive": archive.name,
            "archive_sha256": ledger.sha(archive.read_bytes()),
            "manifest_sha256": ledger.sha(files["manifest.json"]),
            "generation_requests_sent": 0,
            "dispatch_authorized": False,
            "runtime_validation": "pending",
            "labels_used_for_selection": False,
            "held_out_access_enabled": False,
            "main_experiment_ready": False,
        }
        for name, value in (
            ("summary.json", summary),
            (
                "provenance.json",
                {
                    "input_sha256": {p.relative_to(repo).as_posix(): h for p, h in inputs.items()},
                    "policy_sha256_lf": POLICY_SHA,
                    "source_sha256_lf": {
                        p.name: ledger.sha(ledger.regular(p).replace(b"\r\n", b"\n"))
                        for p in (HERE / "stage.py", HERE / "ledger.py")
                    },
                },
            ),
        ):
            (dest / name).write_text(ledger.canonical(value) + "\n", encoding="utf-8", newline="\n")
        for path, wanted in inputs.items():
            if ledger.sha(ledger.regular(path)) != wanted:
                raise ValueError("Original evidence/review changed during preparation")
        publisher = module(
            "_matched_fallback_publish",
            repo
            / "tools/development_audits"
            / "fallback_full_development_scoring_v1/score_fallback_full.py",
        )
        publisher.publish_directory(dest, output)
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
        summary = stage(REPO)
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as exc:
        raise SystemExit(
            "Matched fallback staging stopped: " + str(exc) + ". Preserve evidence; no model calls."
        ) from None
    print(json.dumps(summary, indent=2))
    print("Prepared:", OUTPUT)
    print("CPU only; no downloads, generation, scoring, exclusions or dispatch authorization.")


if __name__ == "__main__":
    main()
