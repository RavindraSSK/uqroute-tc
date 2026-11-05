"""Prepare a matched corrected 14B-AWQ primary-development plan; no model requests."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path("artifacts/local_development_audits")
OUTPUT = ROOT / "fallback_primary_development_preparation_v1"
CANDIDATES = "177b0409bb6f2f0e116fa6b924e46807c9c30a3305a5fd6e15bfa30cf0f3d060"
DENOMINATORS = "14a59d3da30d715675271dd05ad6384c3f6c7421db52e86630b828e8651c44f6"
PREVIOUS = ROOT / "corrected_qwen15b_full_development_import_8517fd5d/prepared"
PREVIOUS_MANIFEST = "310daceecaedb4c5de38046fcab33222f7dd81bb54568192dca54f12be8d1aa0"
ENGINE = {
    "workflow.py": "01a881a67e9b80c81f09268e878502b48bb640398c9729f5eed1ffc47b843831",
    "support.py": "4aac9f16ed6a03fa833ab3fbaf321127c3043194273c91f79c4f2bda167dbc47",
}
MODEL = "Qwen/Qwen2.5-14B-Instruct-AWQ"
REVISION = "539535859b135b0244c91f3e59816150c8056698"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError("Expected a regular input without symlink ancestors")
    return path.read_bytes()


def validate_matching_requests(current, previous):
    """Full shared requests must differ only in their request model field."""
    for rows in (current, previous):
        if len(rows) != 1728 or len({r["case_key"] for r in rows}) != 1728:
            raise ValueError("Expected 1728 unique development cases per model")
    if [r["case_key"] for r in current] != [r["case_key"] for r in previous]:
        raise ValueError("Case selection or order differs")
    for new, old in zip(current, previous, strict=True):
        if any(new[k] != old[k] for k in ("benchmark", "source_file", "canonical_base_id")):
            raise ValueError("Case lineage differs")
        if new["request"]["model"] != MODEL:
            raise ValueError("Unexpected fallback model")
        a = {k: v for k, v in new["request"].items() if k != "model"}
        b = {k: v for k, v in old["request"].items() if k != "model"}
        if a != b:
            raise ValueError("Prompt or generation settings differ")


def load_workflow(repo):
    folder = repo / "tools/development_audits/corrected_generation_v1"
    for name, expected in ENGINE.items():
        if sha(regular(folder / name).replace(b"\r\n", b"\n")) != expected:
            raise ValueError("Frozen generation source differs")
    sys.path.insert(0, str(folder))
    try:
        workflow = importlib.import_module("workflow")
        for name in ("workflow", "support"):
            if Path(sys.modules[name].__file__).resolve().parent != folder.resolve():
                raise ValueError("Conflicting generation module")
        return workflow
    finally:
        sys.path.pop(0)


def run(repo):
    repo = repo.resolve()
    output = repo / OUTPUT
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Output exists or has a symlink ancestor; preserve it")
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(OUTPUT / "summary.json")], cwd=repo
    ).returncode:
        raise ValueError("Preparation artifacts must be ignored by Git")
    workflow = load_workflow(repo)
    # Validate the preserved small-model plan before preparing the matched fallback.
    _, previous = workflow.load_plan(repo, repo / PREVIOUS, PREVIOUS_MANIFEST)
    audit = repo / ROOT / "full_primary_audit_v1"
    denominators = repo / ROOT / "population_plan_v1/denominators.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix="fallback-preparation-") as tmp:
        stage = Path(tmp) / "package"
        stage.mkdir()
        plan = stage / "prepared"
        prepared = workflow.prepare(
            repo,
            audit,
            denominators,
            CANDIDATES,
            DENOMINATORS,
            "qwen14b_awq",
            "full-development",
            plan,
        )
        manifest, requests = workflow.load_plan(repo, plan, prepared["manifest_sha256"])
        model = manifest["model_settings"]
        if (
            model["role"] != "fallback"
            or model["model_id"] != MODEL
            or model["model_revision"] != REVISION
            or model["tokenizer_revision"] != REVISION
            or model["dtype"] != "float16"
            or model["quantization"] != "AWQ 4-bit checkpoint"
        ):
            raise ValueError("Frozen fallback settings differ")
        validate_matching_requests(requests, previous)
        archive = stage / "qwen14b_awq_full_development_transfer_v1.zip"
        with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as z:
            for name in ("manifest.json", "requests.json"):
                z.writestr(name, regular(plan / name))
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:
                raise ValueError("Transfer ZIP integrity failed")
        # Recheck the comparison source after packaging; preserve source bytes.
        workflow.load_plan(repo, repo / PREVIOUS, PREVIOUS_MANIFEST)
        summary = {
            "version": "uqroute-fallback-development-preparation-1.0.0",
            "model": MODEL,
            "requests": len(requests),
            "scope": "primary-development-only",
            "matched_small_manifest_sha256": PREVIOUS_MANIFEST,
            "manifest_sha256": prepared["manifest_sha256"],
            "transfer_file": archive.name,
            "transfer_sha256": sha(regular(archive)),
            "held_out_access_enabled": False,
            "main_experiment_ready": False,
            "generation_requests_sent": 0,
            "official_scoring": "not_performed",
            "dispatch_authorized_by_preparation": False,
            "pending": [
                "Pinned-tokenizer context preflight on every request",
                "Available GPU/quota and runtime attestation",
                "Separate development dispatch and preserved response evidence",
                "CPU replay/scoring and prompt-matched fallback join",
                "Grouped development objective and threshold selection",
            ],
        }
        (stage / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        # copytree atomically claims a fresh directory; a partial interrupted copy
        # remains evidence to inspect, never permission to overwrite or dispatch.
        shutil.copytree(stage, output)
    return summary


if __name__ == "__main__":
    repo_root = Path.cwd()
    try:
        test_env = dict(os.environ)
        test_env["PYTHONPATH"] = (
            str(repo_root / "src") + os.pathsep + test_env.get("PYTHONPATH", "")
        )
        print("Running routing and frozen generation CPU checks...", flush=True)
        for folder, pattern in (
            ("tests/unit", "test_routing_development.py"),
            ("tools/development_audits/routing_development_v1", "test_*.py"),
            ("tools/development_audits/corrected_generation_v1", "test_*.py"),
        ):
            subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", folder, "-p", pattern],
                cwd=repo_root,
                env=test_env,
                check=True,
            )
        result = run(repo_root)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exc:
        message = str(exc) if type(exc) is ValueError else "Preparation input/source check failed"
        raise SystemExit(message) from None
    print(json.dumps(result, indent=2))
    print("Prepared:", OUTPUT)
    print("No inference or scoring. Run tokenizer/context preflight before any dispatch.")
