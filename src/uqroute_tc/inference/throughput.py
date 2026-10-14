"""Development-only, coverage-stratified timing with durable attempt history.

No changes to the frozen pilot/parser/uncertainty implementations. Run only one
process per output directory. Sequential timings are not concurrent-serving capacity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from uqroute_tc.data.identity import canonical_base_id, is_multi_turn
from uqroute_tc.data.split import BENCHMARK_REVISION
from uqroute_tc.inference.pilot import _atomic_json, _sha256, token_evidence


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def select_timing_cases(
    data_dir: Path, split: dict[str, Any], per_stratum: int = 1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Hash-select within benchmark x static source file, using identities only.

    One row per nonempty development stratum by default. This is a coverage
    diagnostic, not a population-weighted or length-balanced runtime estimate.
    """
    if per_stratum < 1:
        raise ValueError("per_stratum must be positive")
    if split.get("benchmark_revision") != BENCHMARK_REVISION:
        raise ValueError("Unexpected split benchmark revision")
    clean = [json.loads(line) for line in (data_dir / "clean.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    clean_ids = {str(row["id"]) for row in clean}
    if len(clean_ids) != len(clean):
        raise ValueError("Duplicate clean ID")
    selected, coverage = [], []
    for path in sorted(data_dir.glob("*.jsonl")):
        strata: dict[str, list[dict[str, Any]]] = defaultdict(list)
        seen: set[str] = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if is_multi_turn(row):
                continue
            row_id = str(row["id"])
            if row_id in seen:
                raise ValueError(f"Duplicate ID in {path.name}: {row_id}")
            seen.add(row_id)
            base = canonical_base_id(row_id, clean_ids)
            assignment = split["assignments"].get(base)
            if assignment is None or assignment["benchmark"] != row["benchmark"]:
                raise ValueError(f"Missing or conflicting assignment: {row_id}")
            if assignment["population"] != "primary" or assignment["split"] != "development":
                continue
            strata[str(row["benchmark"])].append({
                "id": row_id, "base_id": base, "benchmark": str(row["benchmark"]),
                "source_file": path.name, "case_key": f"{path.name}:{row_id}",
            })
        for benchmark, rows in sorted(strata.items()):
            ranked = sorted(rows, key=lambda row: (
                hashlib.sha256(f"uqroute-tc/throughput-v1/1729/{row['case_key']}".encode())
                .hexdigest(), row["case_key"],
            ))
            chosen = ranked[:per_stratum]
            selected.extend(chosen)
            coverage.append({"benchmark": benchmark, "source_file": path.name,
                             "eligible_rows": len(rows), "selected_rows": len(chosen)})
    if not selected:
        raise ValueError("No eligible development cases")
    return selected, coverage


def _path(output: Path, key: str) -> Path:
    return output / "cases" / hashlib.sha256(key.encode()).hexdigest()


def _load_attempts(output: Path) -> list[dict[str, Any]]:
    return [json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((output / "cases").glob("*/attempts/*.json"))]


def summarize(output: Path) -> dict[str, Any]:
    """Account for every persisted attempt, including failed/interrupted ones."""
    attempts = _load_attempts(output)
    sessions = [json.loads(path.read_text(encoding="utf-8"))
                for path in sorted((output / "sessions").glob("*.json"))]
    tokens = {name: 0 for name in ("prompt_tokens", "completion_tokens", "total_tokens")}
    missing = {name: 0 for name in tokens}
    for attempt in attempts:
        usage = attempt.get("usage") or {}
        for name in tokens:
            value = usage.get(name)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                tokens[name] += value
            else:
                missing[name] += 1
    elapsed = sum(a.get("elapsed_seconds", 0) or 0 for a in attempts)
    batch_wall = sum(s.get("batch_wall_seconds", 0) or 0 for s in sessions)
    complete = sum(a["status"] == "complete" for a in attempts)
    return {
        "attempt_count": len(attempts), "status_counts": dict(Counter(
            a["status"] for a in attempts)), "session_count": len(sessions),
        "unfinished_sessions": sum(s["status"] != "finished" for s in sessions),
        "measured_attempt_seconds": elapsed, "measured_batch_wall_seconds": batch_wall,
        "known_token_totals": tokens, "missing_usage_attempts": missing,
        "completed_attempts_per_batch_second": complete / batch_wall if batch_wall else None,
        "completion_tokens_per_batch_second": (
            tokens["completion_tokens"] / batch_wall
            if batch_wall and not missing["completion_tokens"] else None),
        "single_gpu_batch_allocation_hours_proxy": batch_wall / 3600,
        "limitations": [
            "Sequential client timings include prompt building, parsing and saving overhead.",
            "Batch wall time is not GPU kernel-active time or total allocated runtime.",
            "Setup, downloads, warm-up and idle GPU allocation are recorded separately in Colab.",
            "Interrupted attempts have unknown elapsed time and possibly unknown billed tokens.",
            "Coverage-stratified subset is not population-weighted; no accuracy/routing claim.",
        ],
    }


def run_timing(
    cases: list[dict[str, Any]], client: Any, build_messages: Any, parse_calls: Any,
    output: Path, config: dict[str, Any], *, retry_errors: bool = False,
) -> dict[str, Any]:
    """Persist intent before requests; keep old attempts and skip recorded outcomes.

    Only request_error/interrupted slots are retried when explicitly requested.
    Truncation and invalid evidence are diagnostic outcomes, not auto-retries.
    """
    if [case["case_key"] for case in cases] != config["case_keys"]:
        raise ValueError("Cases do not match manifest")
    if len(set(config["case_keys"])) != len(cases):
        raise ValueError("Duplicate case key")
    output.mkdir(parents=True, exist_ok=True)
    manifest = output / "manifest.json"
    if manifest.exists():
        if json.loads(manifest.read_text(encoding="utf-8")) != config:
            raise ValueError("Existing manifest differs; use a new output directory")
    else:
        if any(output.iterdir()):
            raise ValueError("Output directory has files but no manifest")
        _atomic_json(manifest, config)
    session_id = uuid.uuid4().hex
    session_path = output / "sessions" / f"{session_id}.json"
    session = {"id": session_id, "started_utc": _now(), "status": "running",
               "processed": 0, "resumed": 0}
    _atomic_json(session_path, session)
    batch_started = time.perf_counter()
    for case in cases:
        folder = _path(output, case["case_key"])
        previous = sorted((folder / "attempts").glob("*.json"))
        if previous:
            old = json.loads(previous[-1].read_text(encoding="utf-8"))
            if old["case_key"] != case["case_key"]:
                raise ValueError("Case hash collision")
            if old["status"] == "started":
                old.update(status="interrupted", error="Prior request outcome unknown")
                _atomic_json(previous[-1], old)
            if not retry_errors or old["status"] not in {"interrupted", "request_error"}:
                session["resumed"] += 1
                continue
        attempt_path = folder / "attempts" / f"{len(previous) + 1:06d}.json"
        attempt = {key: case[key] for key in (
            "case_key", "source_file", "base_id", "id", "benchmark")}
        attempt.update(session_id=session_id, started_utc=_now(), status="started",
                       elapsed_seconds=None, usage=None, response=None, prediction=None)
        _atomic_json(attempt_path, attempt)
        started = time.perf_counter()
        sample = case["sample"]
        response_data = None
        try:
            response = client.chat.completions.create(
                model=config["model_id"], messages=build_messages(sample),
                temperature=config["temperature"], max_tokens=config["max_tokens"],
                logprobs=True, top_logprobs=config["top_logprobs"],
            )
            response_data = response.model_dump(mode="json")
            choice = response_data["choices"][0]
            raw = choice["message"].get("content") or ""
            evidence = token_evidence(choice)
            prediction = {"raw_output": raw, "tool_calls": parse_calls(raw, sample["benchmark"]),
                          "error": None}
            status = "complete" if evidence["valid"] else "invalid_evidence"
            if choice.get("finish_reason") == "length":
                status = "truncated"
            attempt.update(status=status, evidence=evidence, prediction=prediction,
                           finish_reason=choice.get("finish_reason"))
        except Exception as exc:
            attempt.update(status="request_error", error=f"{type(exc).__name__}: {exc}")
        attempt.update(elapsed_seconds=time.perf_counter() - started, finished_utc=_now(),
                       response=response_data,
                       usage=response_data.get("usage") if response_data else None)
        _atomic_json(attempt_path, attempt)
        session["processed"] += 1
        print(f"{case['case_key']}: {attempt['status']}", flush=True)
    session.update(status="finished", finished_utc=_now(),
                   batch_wall_seconds=time.perf_counter() - batch_started)
    _atomic_json(session_path, session)
    report = summarize(output)
    _atomic_json(output / "summary.json", report)
    return {"session": session, "summary": report}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--per-stratum", type=int, default=1)
    parser.add_argument("--request-timeout", type=float, default=300)
    parser.add_argument("--retry-errors", action="store_true")
    parser.add_argument("--select-only", action="store_true")
    args = parser.parse_args()
    if not math.isfinite(args.request_timeout) or args.request_timeout <= 0:
        parser.error("request-timeout must be finite and positive")
    project, benchmark = args.project_root.resolve(), args.benchmark_root.resolve()
    revision = subprocess.check_output(
        ["git", "-C", str(benchmark), "rev-parse", "HEAD"], text=True).strip()
    if revision != BENCHMARK_REVISION:
        parser.error("Benchmark revision differs")
    dirty = subprocess.check_output([
        "git", "-C", str(benchmark), "status", "--porcelain", "--",
        "hf_data/datasets/api_eval", "scripts/run_eval.py",
    ], text=True)
    if dirty:
        parser.error("Benchmark data or official runner has local changes")
    freeze_path = project / "docs/config/task1_single_sample_v1.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    split_path = project / freeze["benchmark"]["split_manifest"]
    if _sha256(split_path) != freeze["benchmark"]["split_sha256"]:
        parser.error("Split fingerprint differs from frozen settings")
    split = json.loads(split_path.read_text(encoding="utf-8"))
    model = next((m for m in freeze["models"] if m["model_id"] == args.model_id), None)
    if model is None:
        parser.error("Model not present in frozen settings")
    data_dir = benchmark / freeze["benchmark"]["data_directory"]
    selected, coverage = select_timing_cases(data_dir, split, args.per_stratum)
    if args.select_only:
        print(json.dumps({"case_count": len(selected), "coverage": coverage,
                          "cases": selected}, indent=2))
        return
    sys.path.insert(0, str(benchmark / "scripts"))
    from importlib.metadata import version  # noqa: PLC0415

    from openai import OpenAI  # noqa: PLC0415
    from run_eval import build_messages, load_samples, parse_tool_calls  # noqa: PLC0415

    if version("vllm") != freeze["single_sample"]["server"]["version"]:
        parser.error("Installed vLLM differs from frozen version")
    by_file = {name: {str(row["id"]): row for row in load_samples(data_dir / name)}
               for name in sorted({row["source_file"] for row in selected})}
    cases = [{**row, "sample": by_file[row["source_file"]][row["id"]]} for row in selected]
    config = {
        "scope": "development-only coverage-stratified sequential throughput-v1",
        "benchmark_revision": revision, "split_sha256": _sha256(split_path),
        "freeze_sha256": _sha256(freeze_path), "model_id": model["model_id"],
        "model_settings": model, "server_settings": freeze["single_sample"]["server"],
        "temperature": freeze["single_sample"]["temperature"],
        "max_tokens": freeze["single_sample"]["max_tokens"],
        "top_logprobs": freeze["single_sample"]["top_logprobs"],
        "endpoint": args.endpoint, "request_timeout": args.request_timeout,
        "request_seed": None, "concurrency": 1, "automatic_retries": 0,
        "runtime_versions": {"python": sys.version, "vllm": version("vllm"),
                             "torch": version("torch"), "openai": version("openai")},
        "selection_seed": 1729, "per_stratum": args.per_stratum,
        "coverage": coverage, "case_keys": [row["case_key"] for row in selected],
        "source_hashes": {path.name: _sha256(path) for path in sorted(data_dir.glob("*.jsonl"))},
        "runner_sha256": _sha256(Path(__file__)),
        "pilot_sha256": _sha256(project / "src/uqroute_tc/inference/pilot.py"),
        "official_runner_sha256": _sha256(benchmark / "scripts/run_eval.py"),
        "code_revision": subprocess.check_output(
            ["git", "-C", str(project), "rev-parse", "HEAD"], text=True).strip(),
    }
    client = OpenAI(base_url=args.endpoint, api_key="EMPTY",
                    timeout=args.request_timeout, max_retries=0)
    result = run_timing(cases, client, build_messages, parse_tool_calls,
                        args.output_dir, config, retry_errors=args.retry_errors)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
