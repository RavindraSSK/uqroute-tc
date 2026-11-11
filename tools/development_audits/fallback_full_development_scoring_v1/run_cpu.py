"""Verify/import/replay the completed fallback archive, then score local development references."""

from __future__ import annotations

import argparse
import io
import json
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

import score_fallback_full as scoring

ROOT = Path("artifacts/local_development_audits")
IMPORTED = ROOT / "corrected_qwen14b_awq_full_development_import_e21e0f54"
REPLAY = ROOT / "corrected_qwen14b_awq_full_development_local_replay_v1"
SCORED = ROOT / "corrected_qwen14b_awq_full_development_official_scoring_v1"
ARCHIVE = "uqroute_qwen14b_awq_full_development_e21e0f54.zip"
RUNNER_SHA = "1d343f7e229773a728bac44619fcd4c644d94bd636ccddd8b42bd6e7d2dc649c"
STATUS_COUNTS = {"complete": 1558, "invalid_evidence": 128, "truncated": 42}


def safe_payloads(raw):
    """Only bounded regular evidence files; reject Windows aliases and traversal."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if (
            len({name.casefold() for name in names}) != len(names)
            or sum(entry.file_size for entry in entries) > 250_000_000
            or archive.testzip() is not None
        ):
            raise ValueError("Archive inventory, size or integrity differs")
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (
                entry.is_dir()
                or path.is_absolute()
                or not path.parts
                or any(part in {"", ".", ".."} for part in entry.filename.split("/"))
                or "\\" in entry.filename
                or ":" in entry.filename
                or path.parts[0] not in {"prepared", "metadata", "run", "replay"}
                or stat.S_ISLNK(entry.external_attr >> 16)
                or any(part.endswith((" ", ".")) for part in path.parts)
            ):
                raise ValueError("Unsafe or unsupported archive member")
        return {entry.filename: archive.read(entry) for entry in entries}


def validate_archive(path, rules):
    raw = scoring.regular(path)
    if scoring.sha(raw) != rules["archive_sha256"]:
        raise ValueError("Fallback ZIP SHA256 differs from the notebook-verified export")
    payloads = safe_payloads(raw)
    if set(payloads) != set(rules["evidence_file_sha256"]):
        raise ValueError("Archive file set differs from the bound policy")
    for name, expected in rules["evidence_file_sha256"].items():
        if scoring.sha(payloads[name]) != expected:
            raise ValueError("Bound evidence fingerprint differs")
    hashes = scoring.loads(payloads["metadata/export_file_hashes.json"])
    if len(hashes) != 6942 or set(hashes) != set(payloads) - {"metadata/export_file_hashes.json"}:
        raise ValueError("Expected 6942 fingerprinted evidence members")
    if any(scoring.sha(payloads[name]) != wanted for name, wanted in hashes.items()):
        raise ValueError("Export inventory fingerprint differs")
    if scoring.sha(payloads["metadata/execution_source.py"]) != RUNNER_SHA:
        raise ValueError("Reviewed notebook execution source differs")
    preflight = scoring.loads(payloads["metadata/tokenizer_preflight.json"])
    shutdown = scoring.loads(payloads["metadata/shutdown.json"])
    status = scoring.loads(payloads["metadata/execution_status.json"])
    if (
        preflight["requests"] != 1728
        or preflight["overflow_cases"] != []
        or preflight["held_out_access_enabled"] is not False
        or shutdown["server_stopped"] is not True
        or status["status"] != "generation_and_replay_finished"
        or status["held_out_access_enabled"] is not False
    ):
        raise ValueError("Preflight, completion or shutdown binding differs")
    return payloads


def exact_existing(folder, payloads):
    if any(p.is_symlink() for p in (folder, *folder.parents)):
        raise ValueError("Symlink output rejected")
    paths = [p for p in folder.rglob("*") if p.is_file() or p.is_symlink()]
    if {p.relative_to(folder).as_posix() for p in paths} != set(payloads):
        raise ValueError("Existing output inventory differs; preserve it")
    for path in paths:
        if scoring.regular(path) != payloads[path.relative_to(folder).as_posix()]:
            raise ValueError("Existing output bytes differ; preserve them")


def import_and_replay(repo, archive):
    rules = scoring.policy()
    payloads = validate_archive(archive, rules)
    root = repo / ROOT
    target, replay = repo / IMPORTED, repo / REPLAY
    for folder in (target, replay):
        if any(p.is_symlink() for p in (folder, *folder.parents)):
            raise ValueError("Symlink output rejected")
        if subprocess.run(
            ["git", "check-ignore", "-q", "--", str(folder.relative_to(repo) / "summary.json")],
            cwd=repo,
        ).returncode:
            raise ValueError("All generated evidence must remain ignored by Git")
    workflow, _, _, _ = scoring.load_dependencies(repo, rules)
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root, prefix="fallback-import-check-") as temp:
        stage = Path(temp)
        candidate = target if target.exists() else stage / "evidence"
        if target.exists():
            exact_existing(target, payloads)
        else:
            candidate.mkdir()
            for name, raw in payloads.items():
                path = candidate.joinpath(*PurePosixPath(name).parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("xb") as stream:
                    stream.write(raw)
        manifest, records = workflow.load_plan(
            repo, candidate / "prepared", rules["prepared_manifest_sha256"]
        )
        if (
            manifest["model_settings"]["role"] != "fallback"
            or manifest["model_settings"]["model_id"] != rules["model_id"]
            or len(records) != 1728
            or manifest["selection"] != "full-development"
        ):
            raise ValueError("Not the reviewed fallback full-development plan")
        runtime = scoring.loads(payloads["metadata/runtime.json"])
        workflow.check_runtime(runtime, manifest)
        binding = scoring.loads(payloads["run/run_manifest.json"])
        if (
            binding["runtime_attestation"] != runtime
            or binding["runtime_attestation_sha256"]
            != scoring.sha(payloads["metadata/runtime.json"])
            or runtime["launch_command_sha256"]
            != scoring.sha(payloads["metadata/launch_argv.json"])
            or runtime["server_log_sha256"]
            != scoring.sha(payloads["metadata/server_before_generation.log"])
        ):
            raise ValueError("Runtime/source snapshots differ from the durable run binding")
        # Replay validates the durable intent/request/body hashes and frozen methods.
        checked = stage / "replay"
        workflow.replay(
            repo,
            candidate / "prepared",
            rules["prepared_manifest_sha256"],
            candidate / "run",
            checked,
        )
        generated = {
            name: scoring.regular(checked / name) for name in ("summary.json", "records.json")
        }
        for name, raw in generated.items():
            if scoring.loads(raw) != scoring.loads(payloads["replay/" + name]):
                raise ValueError("Full local replay differs from exported " + name)
        summary = scoring.loads(generated["summary.json"])
        if (
            summary["status_counts"] != STATUS_COUNTS
            or summary["rows"] != 1728
            or summary["attempted_slots"] != 1728
            or summary["unfinished_sessions"] != 0
            or summary["whole_output_eligible"] != 1558
            or summary["meaningful_token_eligible"] != 631
            or summary["held_out_access_enabled"] is not False
        ):
            raise ValueError("Reviewed replay counts differ")
        exact_existing(candidate, payloads)
        if not target.exists():
            scoring.publish_directory(candidate, target)
        if replay.exists():
            exact_existing(replay, generated)
        else:
            scoring.publish_directory(checked, replay)
    return summary


def run(repo, archive, replay_only=False):
    repo = repo.resolve()
    summary = import_and_replay(repo, archive)
    print("ZIP, 6942 member hashes, runtime and full local replay: VERIFIED", flush=True)
    if replay_only:
        return {
            "stage": "import_and_replay_verified",
            "official_scoring": "not_performed",
            **{
                k: summary[k]
                for k in (
                    "rows",
                    "status_counts",
                    "whole_output_eligible",
                    "meaningful_token_eligible",
                    "held_out_access_enabled",
                )
            },
        }
    bundle = repo / ROOT / "full_primary_export_v1"
    audit = repo / ROOT / "full_primary_audit_v1"
    required = [
        bundle / name for name in ("attestation.json", "membership.json", "references.jsonl")
    ]
    required.append(audit / "inventory.json")
    if any(not p.is_file() for p in required):
        raise ValueError(
            "Replay verified. Scoring needs the preserved full_primary_export_v1 "
            "sidecars and full_primary_audit_v1/inventory.json; do not regenerate or bypass hashes"
        )
    return scoring.score(repo, repo / IMPORTED, bundle, audit, repo / SCORED)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path.home() / "Downloads" / ARCHIVE)
    parser.add_argument("--replay-only", action="store_true")
    args = parser.parse_args()
    repo = Path.cwd()
    if not (repo / ".git").exists() or not (repo / "docs/PROJECT_TASKS.md").is_file():
        raise SystemExit("Run from the uqroute-tc repository root")
    try:
        for folder in (
            "tools/development_audits/fallback_full_development_scoring_v1",
            "tools/development_audits/corrected_generation_v1",
        ):
            subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", folder, "-p", "test_*.py"],
                cwd=repo,
                check=True,
            )
        summary = run(repo, args.archive, args.replay_only)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        message = str(exc) if type(exc) is ValueError else "CPU input/source validation failed"
        raise SystemExit(
            message + ". Preserve existing evidence; never retry model requests"
        ) from None
    print(json.dumps(summary, indent=2))
    print("No inference, held-out access, label changes or Git writes performed.")


if __name__ == "__main__":
    main()
