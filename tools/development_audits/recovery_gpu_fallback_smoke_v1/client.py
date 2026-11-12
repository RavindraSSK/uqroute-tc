"""Pinned matched 30-request 14B fallback smoke; no fresh small calls or retries."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

CODE = "c3cbf9f44334547a747585c613afe34d381bd070"
ZIP_SHA = "2e2bc38f6104c06d9a6084344a5d89b1dfcd2ddb7b3ec53791a7d9d65c3abc61"
MANIFEST_SHA = "3bc0762f233ebfcad69f55bc20285235a8962b6a93417b73fab96d24094d816d"
MODEL = "Qwen/Qwen2.5-14B-Instruct-AWQ"
REV = "539535859b135b0244c91f3e59816150c8056698"
PARENT_SHA = "dd91a73f5f565269f83d70773fd25fd64c82785029e3d96b139682c072b59595"
MEMBERS = {
    "manifest.json",
    "requests.json",
    "episodes.json",
    "paired_small_records.json",
    "ledger.py",
}


def quantization_check(config):
    quant = config.get("quantization_config", {})
    if quant.get("quant_method", "").lower() != "awq" or quant.get("bits") != 4:
        raise ValueError("Pinned model must describe a four-bit AWQ checkpoint")
    return {
        "model_id": MODEL,
        "revision": REV,
        "dtype": "float16",
        "checkpoint_quantization": quant,
        "backend": "Automatic selection by pinned vLLM; inspect server log",
    }


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
        manifest["version"] != "uqroute-matched-recovery-fallback-smoke-1.0.0"
        or manifest["purpose"] != "qwen14b-postfault-fallback-matched-smoke"
        or manifest["model_settings"] != config["models"][3]
        or manifest["server_settings"] != config["single_sample"]["server"]
        or manifest["request_count"] != 30
        or manifest["maximum_new_requests"] != 30
        or manifest["fresh_small_requests"] != 0
        or manifest["known_parent_small_slots"] != 30
        or manifest["parent_smoke_archive_sha256"] != PARENT_SHA
        or manifest["collection_mode"] != "all_matched_smoke_episodes_no_threshold"
        or manifest["labels_used_for_selection"] is not False
        or manifest["static_dispatcher_compatible"] is not False
        or manifest["automatic_retries"] != 0
        or any(
            manifest[n] is not False
            for n in ("dispatch_authorized", "held_out_access_enabled", "main_experiment_ready")
        )
    ):
        raise ValueError("Bounded smoke scope/settings differ")
    expected_ledger = support.read(
        repo / "tools/development_audits/recovery_fallback_smoke_v1/ledger.py"
    )
    if payloads["ledger.py"] != expected_ledger.replace(b"\r\n", b"\n"):
        raise ValueError("Packaged ledger differs from pinned repository")
    ledger = module("_recovery_gpu_ledger", prepared / "ledger.py")
    rows, episodes = (
        support.loads(payloads["requests.json"]),
        support.loads(payloads["episodes.json"]),
    )
    ledger.checked_rows(rows)
    if len(rows) != 30:
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
    receipts = support.loads(payloads["paired_small_records.json"])
    paired = {r["request_id"]: r for r in receipts}
    if (
        len(receipts) != 30
        or len(paired) != 30
        or set(paired) != {row["paired_small_request_id"] for row in rows}
    ):
        raise ValueError("Complete known parent receipt inventory required")
    for row in rows:
        parent = paired[row["paired_small_request_id"]]
        if (
            parent["episode_key"] != row["episode_key"]
            or parent["context_messages_sha256"] != row["context_messages_sha256"]
            or parent["http_status"] != 200
            or parent["transition_injected"] is not True
            or parent["evidence_status"] != "complete"
        ):
            raise ValueError("Known matching parent response receipt required")
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
            len(zipped.namelist()) != 5
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


def ledger_canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


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
    local_rows = {r["request_id"]: r for r in local["per_request"]}
    server_rows = {r["request_id"]: r for r in server["per_request"]}
    expected = {r["request_id"] for r in rows}
    if (
        set(local_rows) != expected
        or set(server_rows) != expected
        or len(local["per_request"]) != len(rows)
        or len(server["per_request"]) != len(rows)
        or local["tokenizer_revision"] != REV
        or local["context_limit"] != 8192
        or local["output_allowance"] != 1024
    ):
        raise ValueError("Runtime tokenizer identity/coverage differs")
    for row in rows:
        before, after = local_rows[row["request_id"]], server_rows[row["request_id"]]
        if (
            type(before["prompt_tokens"]) is not int
            or before["prompt_tokens"] < 1
            or before["prompt_tokens"] + 1024 > 8192
            or any(before[k] != after[k] for k in ("prompt_tokens", "token_ids_sha256"))
        ):
            raise ValueError("Runtime tokenizer evidence differs")
    return {
        "purpose": manifest["purpose"],
        "request_inventory_sha256": support.sha(ledger_canonical(rows).encode()),
        "parent_smoke_archive_sha256": PARENT_SHA,
        "known_parent_small_slots": manifest["known_parent_small_slots"],
        "collection_mode": manifest["collection_mode"],
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
            "paired_small_request_id": row["paired_small_request_id"],
            "stage": "postfault_fallback",
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
        fallback_requests=states["observed_injected"],
        maximum_fallback_requests=30,
        fresh_small_requests=0,
        collection_mode="all_matched_smoke_episodes_no_threshold",
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
