"""Stage a bounded Qwen 1.5B recovery resource smoke; CPU only, no dispatch."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import ledger

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OUTPUT = Path("artifacts/local_development_audits/recovery_resource_smoke_preparation_v1")
PREFLIGHT = Path("artifacts/local_development_audits/recovery_context_preflight_v1")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_preflight(summary, report, plans, pins, config_sha):
    if (
        summary["version"] != "uqroute-recovery-context-preflight-1.0.0"
        or summary["all_contexts_fit"] is not True
        or summary["generation_requests_sent"] != 0
        or summary["observed_fault_conditioned_dispatches"] != 0
        or summary["dispatch_authorized"] is not False
        or summary["held_out_access_enabled"] is not False
        or summary["main_experiment_ready"] is not False
        or summary["prompts_truncated"] is not False
        or summary["requests_dropped"] != 0
        or report["task1_settings_sha256_lf"] != config_sha
        or report["input_archive_sha256"]
        != {key + "_recovery_development_transfer_v1.zip": value[0] for key, value in pins.items()}
        or set(summary["models"]) != set(plans)
        or set(report["models"]) != set(plans)
    ):
        raise ValueError("Completed owner context preflight required")
    for key, (manifest, roles) in plans.items():
        if set(report["models"][key]) != set(roles) or set(summary["models"][key]) != set(roles):
            raise ValueError("Preflight role inventory differs")
        for role, rows in roles.items():
            result = report["models"][key][role]
            if summary["models"][key][role] != {
                n: v for n, v in result.items() if n != "per_request"
            }:
                raise ValueError("Preflight report and summary differ")
            indexed = {r["request_id"]: r for r in result["per_request"]}
            limit = manifest["server_settings"]["max_model_len"]
            settings = manifest["model_settings"][
                "small" if role == "postfault_small" else "fallback"
            ]
            if (
                len(indexed) != len(result["per_request"])
                or set(indexed) != set(r["request_id"] for r in rows.values())
                or result["requests"] != len(rows)
                or result["overflow_requests"] != 0
                or result["context_limit"] != limit
                or result["model_id"] != settings["model_id"]
                or result["tokenizer_revision"] != settings["tokenizer_revision"]
            ):
                raise ValueError("Preflight request/tokenizer coverage differs")
            counts = []
            for row in rows.values():
                saved = indexed[row["request_id"]]
                n = saved["prompt_tokens"]
                if (
                    any(
                        saved[field] != row[field]
                        for field in ("episode_key", "request_sha256", "context_messages_sha256")
                    )
                    or type(n) is not int
                    or n < 1
                    or saved["within_limit"] is not True
                    or saved["completion_allowance"] != row["request"]["max_tokens"]
                    or n + saved["completion_allowance"] > limit
                ):
                    raise ValueError("Per-request context evidence differs")
                counts.append(n)
            if (
                sum(counts) != result["prompt_tokens_total"]
                or min(counts) != result["prompt_tokens_min"]
                or max(counts) != result["prompt_tokens_max"]
            ):
                raise ValueError("Preflight token aggregates differ")


def select_smoke(episodes, roles):
    """One label-independent eligible clean group per available benchmark; all six faults."""
    groups = {}
    for row in episodes:
        if row["injection_eligible"] is True:
            groups.setdefault((row["benchmark"], row["canonical_base_id"]), []).append(row)
    benchmarks = sorted({e["benchmark"] for e in episodes})
    chosen, missing = [], []
    faults = {
        "timeout",
        "rate_limit",
        "auth_error",
        "server_error",
        "malformed_response",
        "schema_drift",
    }
    for benchmark in benchmarks:
        eligible = [(group, rows) for (b, group), rows in groups.items() if b == benchmark]
        if not eligible:
            missing.append(benchmark)
            continue
        _, rows = min(
            eligible, key=lambda pair: ledger.sha(ledger.canonical([benchmark, pair[0]]).encode())
        )
        if len(rows) != 6 or set(r["fault_type"] for r in rows) != faults:
            raise ValueError("Selected clean group lacks all six eligible faults")
        chosen.extend(sorted(rows, key=lambda r: r["fault_type"]))
    selected = [roles["postfault_small"][e["episode_key"]] for e in chosen]
    ledger.checked_rows(selected)
    return chosen, selected, missing


def stage(repo):
    output = repo / OUTPUT
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Fresh smoke preparation required; preserve occupied outputs")
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(OUTPUT / "summary.json")], cwd=repo
    ).returncode:
        raise ValueError("Smoke transfer must remain ignored")
    preflight = load_module(
        "_recovery_smoke_preflight",
        repo / "tools/development_audits/recovery_context_preflight_v1/preflight.py",
    )
    config_path = repo / "docs/config/task1_single_sample_v1.json"
    config_raw = preflight.regular(config_path)
    if ledger.sha(config_raw.replace(b"\r\n", b"\n")) != preflight.CONFIG_SHA:
        raise ValueError("Frozen Task 1 configuration differs")
    config = preflight.loads(config_raw)
    inputs, plans, payloads = {config_path: ledger.sha(config_raw)}, {}, {}
    for key, (archive_sha, manifest_sha, count, _) in preflight.TRANSFERS.items():
        path = repo / preflight.PREPARATION / (key + "_recovery_development_transfer_v1.zip")
        payloads[key] = preflight.read_archive(path, archive_sha, manifest_sha)
        plans[key] = preflight.validate_plan(payloads[key], key, config, count)
        inputs[path] = archive_sha
    loaded = {}
    for name in ("summary.json", "report.json"):
        path = repo / PREFLIGHT / name
        raw = preflight.regular(path)
        loaded[name] = preflight.loads(raw)
        inputs[path] = ledger.sha(raw)
    verify_preflight(
        loaded["summary.json"],
        loaded["report.json"],
        plans,
        preflight.TRANSFERS,
        preflight.CONFIG_SHA,
    )
    manifest, roles = plans["qwen15b"]
    episodes, requests, missing = select_smoke(payloads["qwen15b"]["episodes.json"], roles)
    ledger_raw = preflight.regular(HERE / "ledger.py").replace(b"\r\n", b"\n")
    files = {
        "requests.json": (ledger.canonical(requests) + "\n").encode(),
        "episodes.json": (ledger.canonical(episodes) + "\n").encode(),
        "ledger.py": ledger_raw,
    }
    smoke = {
        "version": "uqroute-recovery-resource-smoke-1.0.0",
        "purpose": "qwen15b-postfault-small-resource-smoke",
        "selection": "SHA-ranked eligible clean group per available benchmark; all six faults",
        "model_settings": manifest["model_settings"]["small"],
        "server_settings": manifest["server_settings"],
        "request_count": len(requests),
        "maximum_new_requests": len(requests),
        "request_inventory_sha256": ledger.sha(ledger.canonical(requests).encode()),
        "payload_sha256": {n: ledger.sha(b) for n, b in files.items()},
        "source_archive_sha256": preflight.TRANSFERS["qwen15b"][0],
        "owner_preflight_sha256": {
            p.name: h for p, h in inputs.items() if p.parent == repo / PREFLIGHT
        },
        "automatic_retries": 0,
        "fallback_requests": 0,
        "dispatch_authorized": False,
        "runtime_validation": "pending",
        "held_out_access_enabled": False,
        "main_experiment_ready": False,
        "threshold": "not_selected",
        "official_scoring": "not_performed",
        "rq3_outcomes": "not_evaluated",
    }
    files["manifest.json"] = (ledger.canonical(smoke) + "\n").encode()
    root = output.parent
    with tempfile.TemporaryDirectory(dir=root, prefix="recovery-smoke-") as folder:
        destination = Path(folder)
        archive = destination / "qwen15b_recovery_resource_smoke_v1.zip"
        with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as zipped:
            for name, raw in files.items():
                zipped.writestr(name, raw)
        with zipfile.ZipFile(archive) as zipped:
            if zipped.testzip() is not None or any(
                zipped.read(n) != raw for n, raw in files.items()
            ):
                raise ValueError("Smoke archive validation differs")
        summary = {
            "version": smoke["version"],
            "model": "qwen15b",
            "selected_benchmarks": sorted({e["benchmark"] for e in episodes}),
            "benchmarks_without_eligible_group": missing,
            "selected_groups": len(episodes) // 6,
            "planned_postfault_small": len(requests),
            "planned_fallback_requests": 0,
            "maximum_new_requests": len(requests),
            "archive": archive.name,
            "archive_sha256": ledger.sha(archive.read_bytes()),
            "manifest_sha256": ledger.sha(files["manifest.json"]),
            "generation_requests_sent": 0,
            "observed_fault_conditioned_dispatches": 0,
            "dispatch_authorized": False,
            "held_out_access_enabled": False,
            "main_experiment_ready": False,
            "runtime_validation": "pending",
            "official_scoring": "not_performed",
            "rq3_outcomes": "not_evaluated",
        }
        for name, value in (
            ("summary.json", summary),
            (
                "provenance.json",
                {
                    "input_sha256": {p.relative_to(repo).as_posix(): h for p, h in inputs.items()},
                    "new_source_sha256_lf": {
                        p.name: ledger.sha(preflight.regular(p).replace(b"\r\n", b"\n"))
                        for p in (HERE / "stage.py", HERE / "ledger.py")
                    },
                },
            ),
        ):
            (destination / name).write_text(
                ledger.canonical(value) + "\n", encoding="utf-8", newline="\n"
            )
        for path, expected in inputs.items():
            if ledger.sha(preflight.regular(path)) != expected:
                raise ValueError("Original preparation/preflight input changed")
        publisher = load_module(
            "_recovery_smoke_publish",
            repo
            / "tools/development_audits"
            / "fallback_full_development_scoring_v1/score_fallback_full.py",
        )
        publisher.publish_directory(destination, output)
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
            "Recovery smoke preparation stopped: "
            + str(exc)
            + ". Preserve existing evidence; no generation performed."
        ) from None
    print(json.dumps(summary, indent=2))
    print("Prepared:", OUTPUT)
    print("CPU only; no downloads, inference, injection, scoring or dispatch authorization.")


if __name__ == "__main__":
    main()
