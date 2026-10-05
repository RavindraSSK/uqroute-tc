"""Audit four saved five-case development pilots without model inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from uqroute_tc.inference.pilot import _atomic_json, _record_path
from uqroute_tc.parsing.canonical import parse_prediction
from uqroute_tc.uncertainty.single import single_sample_scores

PILOT_FOLDERS = {
    "Qwen/Qwen2.5-1.5B-Instruct": "qwen25-15b-dev-five-v1",
    "meta-llama/Llama-3.2-3B-Instruct": "llama32-3b-dev-five-v1",
    "Qwen/Qwen2.5-7B-Instruct": "qwen25-7b-dev-five-v1",
    "Qwen/Qwen2.5-14B-Instruct-AWQ": "qwen25-14b-awq-feasibility-five-v1",
}


def audit_pilots(
    pilot_root: Path,
    config: dict[str, Any],
    split: dict[str, Any],
    reference_parser: Callable[[str, str], list[dict[str, Any]]],
) -> dict[str, Any]:
    """Reparse saved outputs and revalidate evidence; retain per-case failures."""
    models = {model["model_id"]: model for model in config["models"]}
    assignments = split["assignments"]
    entries = []
    expected_ids: list[str] | None = None
    for model_id, folder in PILOT_FOLDERS.items():
        location = pilot_root / folder
        manifest = json.loads((location / "manifest.json").read_text(encoding="utf-8"))
        pinned = models[model_id]
        for field in ("model_revision", "tokenizer_revision", "dtype"):
            if manifest[field] != pinned[field]:
                raise ValueError(f"{model_id} {field} differs from the frozen Task 1 config")
        if manifest["model_id"] != model_id:
            raise ValueError(f"{folder} contains a different model")
        if manifest["benchmark_revision"] != config["benchmark"]["revision"]:
            raise ValueError(f"{folder} benchmark revision differs")
        ids = manifest["case_ids"]
        if len(ids) != 5 or len(set(ids)) != 5:
            raise ValueError(f"{folder} does not have five unique case IDs")
        if expected_ids is None:
            expected_ids = ids
        elif ids != expected_ids:
            raise ValueError(f"{folder} does not contain the same ordered case IDs")
        for row_id in ids:
            group = assignments.get(row_id) or {}
            if group.get("split") != "development" or group.get("population") != "primary":
                raise ValueError(f"case outside primary development groups: {row_id}")
            record = json.loads(_record_path(location, row_id).read_text(encoding="utf-8"))
            if record["id"] != row_id:
                raise ValueError(f"wrong record ID in {folder}: {row_id}")
            raw = record["prediction"]["raw_output"]
            outcome = parse_prediction(raw, record["benchmark"], reference_parser)
            saved_calls = record["prediction"]["tool_calls"]
            matches = list(outcome.calls) == saved_calls
            try:
                scores = single_sample_scores(record)
                score_error = None
            except ValueError as exc:
                scores = None
                score_error = str(exc)
            entries.append({
                "model_id": model_id,
                "case_id": row_id,
                "saved_status": record["uqroute"]["status"],
                "parser_status": outcome.status,
                "canonical_key": outcome.key,
                "saved_call_count": len(saved_calls),
                "reparsed_call_count": len(outcome.calls),
                "parser_matches_saved": matches,
                "parser_error": outcome.error,
                "single_sample_scores": vars(scores) if scores else None,
                "score_error": score_error,
                "raw_preview": raw[:240],
            })
    return {
        "scope": "same five clean development BFCL cases across four saved pilots",
        "benchmark_revision": config["benchmark"]["revision"],
        "case_ids": expected_ids,
        "total": len(entries),
        "parser_status_counts": dict(Counter(e["parser_status"] for e in entries)),
        "saved_status_counts": dict(Counter(e["saved_status"] for e in entries)),
        "parser_matches_saved": sum(e["parser_matches_saved"] for e in entries),
        "valid_single_sample_scores": sum(e["single_sample_scores"] is not None for e in entries),
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    project = args.project_root
    config = json.loads((project / "docs/config/task1_single_sample_v1.json").read_text())
    split_path = project / config["benchmark"]["split_manifest"]
    if hashlib.sha256(split_path.read_bytes()).hexdigest() != config["benchmark"]["split_sha256"]:
        parser.error("split manifest differs from the frozen Task 1 config")
    split = json.loads(split_path.read_text())
    revision = subprocess.check_output(
        ["git", "-C", str(args.benchmark_root), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != config["benchmark"]["revision"]:
        parser.error("benchmark clone is not at the frozen revision")
    sys.path.insert(0, str(args.benchmark_root / "scripts"))
    from run_eval import parse_tool_calls  # noqa: PLC0415

    report = audit_pilots(args.pilot_root, config, split, parse_tool_calls)
    report["code_revision"] = subprocess.check_output(
        ["git", "-C", str(project), "rev-parse", "HEAD"], text=True
    ).strip()
    _atomic_json(args.output, report)
    print("Saved:", args.output)
    for key in ("total", "parser_status_counts", "saved_status_counts",
                "parser_matches_saved", "valid_single_sample_scores"):
        print(f"{key}: {report[key]}")
    for entry in report["entries"]:
        if not entry["parser_matches_saved"] or entry["score_error"]:
            print("Review:", entry["model_id"], entry["case_id"], entry["score_error"])


if __name__ == "__main__":
    main()
