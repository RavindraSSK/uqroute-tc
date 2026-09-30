"""Resumable, single-sample pilot using the pinned benchmark's prompt and parser."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from uqroute_tc.data.split import BENCHMARK_REVISION


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def token_evidence(choice: dict[str, Any]) -> dict[str, Any]:
    """Align chosen-token bytes with visible output; report any failure explicitly."""
    raw = (choice.get("message") or {}).get("content") or ""
    tokens = (choice.get("logprobs") or {}).get("content") or []
    result: dict[str, Any] = {
        "valid": False,
        "reason": None,
        "excluded_trailing_token": None,
        "visible_token_spans": [],
    }
    if not tokens:
        result["reason"] = "missing chosen-token log-probabilities"
        return result
    if any(
        not isinstance(token.get("bytes"), list)
        or any(not isinstance(byte, int) or not 0 <= byte <= 255 for byte in token["bytes"])
        for token in tokens
    ):
        result["reason"] = "missing or malformed token bytes"
        return result

    visible = tokens
    output = raw.encode("utf-8")
    rebuilt = b"".join(bytes(token["bytes"]) for token in visible)
    if rebuilt != output and tokens[-1].get("token") in {"<|im_end|>", "<|eot_id|>"}:
        visible = tokens[:-1]
        rebuilt = b"".join(bytes(token["bytes"]) for token in visible)
        if rebuilt == output:
            result["excluded_trailing_token"] = tokens[-1]["token"]
    if rebuilt != output:
        result["reason"] = "chosen-token bytes do not match visible UTF-8 output"
        return result
    if not visible:
        result["reason"] = "no visible tokens"
        return result
    if any(
        not isinstance(token.get("logprob"), (int, float))
        or not math.isfinite(token["logprob"])
        for token in visible
    ):
        result["reason"] = "missing or nonfinite chosen-token log-probability"
        return result

    position = 0
    surprisals = []
    for token in visible:
        end = position + len(token["bytes"])
        result["visible_token_spans"].append([position, end])
        position = end
        surprisals.append(-token["logprob"])
    result.update(
        valid=True,
        visible_token_count=len(visible),
        sequence_nll=sum(surprisals),
        mean_token_nll=sum(surprisals) / len(visible),
        max_token_surprisal=max(surprisals),
    )
    return result


def select_clean_development_cases(
    samples: list[dict[str, Any]], split: dict[str, Any], limit: int
) -> list[dict[str, Any]]:
    """Pilot only on clean development groups; preserve the released row order."""
    if limit < 1:
        raise ValueError("limit must be positive")
    assignments = split["assignments"]
    selected = []
    seen = set()
    for sample in samples:
        row_id = str(sample["id"])
        if row_id in seen:
            raise ValueError(f"Duplicate clean case: {row_id}")
        seen.add(row_id)
        group = assignments.get(row_id)
        if group is None or group["population"] != "primary":
            raise ValueError(f"Clean case missing from primary split: {row_id}")
        if group["split"] == "development":
            selected.append(sample)
        if len(selected) == limit:
            break
    if len(selected) != limit:
        raise ValueError(f"Only {len(selected)} development cases available")
    return selected


def _record_path(output_dir: Path, row_id: str) -> Path:
    return output_dir / "records" / (hashlib.sha256(row_id.encode()).hexdigest() + ".json")


def run_cases(
    samples: list[dict[str, Any]],
    client: Any,
    build_messages: Any,
    parse_tool_calls: Any,
    output_dir: Path,
    config: dict[str, Any],
) -> tuple[int, int, int]:
    """Save each case atomically, retry failed cases, and export scorer-compatible rows."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = output_dir / "manifest.json"
    if manifest.exists():
        if json.loads(manifest.read_text(encoding="utf-8")) != config:
            raise ValueError("Existing pilot manifest differs; choose another output directory")
    else:
        if any(output_dir.iterdir()):
            raise ValueError("Output directory has files but no manifest")
        _atomic_json(manifest, config)

    processed = resumed = failed = 0
    for sample in samples:
        row_id = str(sample["id"])
        path = _record_path(output_dir, row_id)
        retry_count = 0
        if path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            if old["id"] != row_id:
                raise ValueError(f"Record hash collision for {row_id}")
            if old["uqroute"]["status"] == "complete":
                resumed += 1
                continue
            retry_count = old["uqroute"].get("retry_count", 0) + 1
        started = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=config["model_id"],
                messages=build_messages(sample),
                temperature=config["temperature"],
                max_tokens=config["max_tokens"],
                logprobs=True,
                top_logprobs=config["top_logprobs"],
            )
            response_data = response.model_dump(mode="json")
            choice = response_data["choices"][0]
            raw = choice["message"].get("content") or ""
            evidence = token_evidence(choice)
            prediction = {
                "raw_output": raw,
                "tool_calls": parse_tool_calls(raw, sample["benchmark"]),
                "error": None,
            }
            status = "complete" if evidence["valid"] else "invalid_evidence"
            error = evidence["reason"]
            if choice.get("finish_reason") == "length":
                status = "truncated"
                error = "generation reached max_tokens"
        except Exception as exc:
            response_data = None
            choice = {}
            evidence = {"valid": False, "reason": "request error"}
            prediction = {
                "raw_output": "",
                "tool_calls": [],
                "error": f"{type(exc).__name__}: {exc}",
            }
            status = "request_error"
            error = prediction["error"]

        record = {
            "id": row_id,
            "benchmark": sample["benchmark"],
            "category": sample.get("category"),
            "perturbation": sample.get("perturbation"),
            "eval_config": sample.get("eval_config"),
            "golden_answers": sample["golden_answers"],
            "prediction": prediction,
            "uqroute": {
                "status": status,
                "error": error,
                "retry_count": retry_count,
                "elapsed_seconds": time.perf_counter() - started,
                "finish_reason": choice.get("finish_reason"),
                "parse_status": "calls" if prediction["tool_calls"] else "no_calls",
                "usage": response_data.get("usage") if response_data else None,
                "evidence": evidence,
                "response": response_data,
            },
        }
        _atomic_json(path, record)
        processed += 1
        failed += status != "complete"
        print(f"{row_id}: {status}", flush=True)

    predictions = output_dir / "pilot.predictions.jsonl"
    temporary = predictions.with_name(predictions.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        for sample in samples:
            record = json.loads(_record_path(output_dir, str(sample["id"])).read_text())
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, predictions)
    return processed, resumed, failed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a five-case clean development pilot.")
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--tokenizer-revision", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--temperature", type=float, default=0.001)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--top-logprobs", type=int, default=5)
    parser.add_argument("--engine-version", required=True)
    parser.add_argument("--dtype", required=True)
    parser.add_argument("--max-model-len", type=int, required=True)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    benchmark_root = args.benchmark_root.resolve()
    revision = subprocess.check_output(
        ["git", "-C", str(benchmark_root), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != BENCHMARK_REVISION:
        parser.error(f"Expected benchmark revision {BENCHMARK_REVISION}, got {revision}")
    data_dir = benchmark_root / "hf_data" / "datasets" / "api_eval"
    dirty_data = subprocess.check_output(
        ["git", "-C", str(benchmark_root), "status", "--porcelain", "--", str(data_dir)],
        text=True,
    )
    if dirty_data:
        parser.error("Benchmark evaluation data has local changes")
    split = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    if split["benchmark_revision"] != revision:
        parser.error("Split manifest benchmark revision differs")

    # Import the pinned release's message builder and parser without copying its rules.
    sys.path.insert(0, str(benchmark_root / "scripts"))
    from run_eval import build_messages, load_samples, parse_tool_calls  # noqa: PLC0415
    from openai import OpenAI  # noqa: PLC0415

    selected = select_clean_development_cases(
        load_samples(data_dir / "clean.jsonl"), split, args.limit
    )
    code_root = Path(__file__).resolve().parents[3]
    code_revision = subprocess.check_output(
        ["git", "-C", str(code_root), "rev-parse", "HEAD"], text=True
    ).strip()
    config = {
        "benchmark_revision": revision,
        "split_sha256": _sha256(args.split_manifest),
        "code_revision": code_revision,
        "model_id": args.model_id,
        "model_revision": args.model_revision,
        "tokenizer_revision": args.tokenizer_revision,
        "endpoint": args.endpoint,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "top_logprobs": args.top_logprobs,
        "engine_version": args.engine_version,
        "dtype": args.dtype,
        "max_model_len": args.max_model_len,
        "mode": "single_prompt_tool_calling",
        "case_ids": [str(sample["id"]) for sample in selected],
    }
    client = OpenAI(base_url=args.endpoint, api_key="EMPTY", timeout=60, max_retries=0)
    processed, resumed, failed = run_cases(
        selected, client, build_messages, parse_tool_calls, args.output_dir, config
    )
    print(f"Pilot: processed={processed} resumed={resumed} failed={failed}")
    if failed:
        raise SystemExit("Some cases failed; inspect saved records and rerun the same command")


if __name__ == "__main__":
    main()
