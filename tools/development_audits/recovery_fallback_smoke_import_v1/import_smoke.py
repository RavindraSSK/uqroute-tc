"""Import and independently replay the completed matched 14B fallback smoke on CPU."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import stat
import subprocess
import sys
import tempfile
import types
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ARCHIVE_SHA = "f85c1c51bb4a3cc19bda831ee87e64b0235af08d8a8f3868a0334415acce14b9"
CODE = "c3cbf9f44334547a747585c613afe34d381bd070"
MANIFEST_SHA = "3bc0762f233ebfcad69f55bc20285235a8962b6a93417b73fab96d24094d816d"
OUTPUT = Path("artifacts/local_development_audits/recovery_fallback_smoke_import_f85c1c51")
SOURCES = {
    "metadata/client.py": (
        "tools/development_audits/recovery_gpu_fallback_smoke_v1/client.py",
        "71a2324de6ad8ba6d4580c20f8c57076df40dbb4f96805187abdba84bb704b16",
    ),
    "metadata/runner.py": (
        "tools/development_audits/recovery_gpu_fallback_smoke_v1/runner.py",
        "0b7ca8ccac6c31834ce785ab75013799559e8415448e56d371309553048e23fd",
    ),
    "prepared/ledger.py": (
        "tools/development_audits/recovery_fallback_smoke_v1/ledger.py",
        "03f316935e64aa8b4570f40b05d6a15810e8d939bbe5bebabce2d208f4e59082",
    ),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("Expected regular input without symlink ancestors")
    return path.read_bytes()


def safe_member(name):
    path = PurePosixPath(name)
    return (
        not path.is_absolute()
        and path.as_posix() == name
        and ".." not in path.parts
        and "\\" not in name
        and ":" not in name
        and path.parts
        and path.parts[0] in {"prepared", "metadata", "run", "replay"}
    )


def verify_members(payloads):
    index = json.loads(payloads["metadata/export_file_hashes.json"])
    if (
        len(index) != 155
        or len(payloads) != 156
        or set(payloads) != set(index) | {"metadata/export_file_hashes.json"}
        or any(not safe_member(name) for name in payloads)
        or any(sha(payloads[name]) != expected for name, expected in index.items())
    ):
        raise ValueError("Smoke export inventory/file hashes differ")
    for name, (_, expected) in SOURCES.items():
        if sha(payloads[name]) != expected:
            raise ValueError("Exported execution source differs: " + name)
    if sha(payloads["prepared/manifest.json"]) != MANIFEST_SHA:
        raise ValueError("Owner preparation manifest differs")


def read_archive(path):
    raw = regular(path)
    if sha(raw) != ARCHIVE_SHA:
        raise ValueError("Expected the completed owner smoke evidence ZIP fingerprint")
    with zipfile.ZipFile(path) as zipped:
        infos = zipped.infolist()
        if (
            len(infos) != 156
            or len({i.filename for i in infos}) != len(infos)
            or sum(i.file_size for i in infos) > 256 * 1024**2
            or any(
                not safe_member(i.filename) or stat.S_ISLNK(i.external_attr >> 16) for i in infos
            )
            or zipped.testzip() is not None
        ):
            raise ValueError("Invalid smoke ZIP paths/inventory")
        payloads = {i.filename: zipped.read(i.filename) for i in infos}
    verify_members(payloads)
    return payloads


def check_runtime_evidence(payloads):
    def load(name):
        return json.loads(payloads[name])

    runtime = load("metadata/runtime.json")
    shutdown = load("metadata/shutdown.json")
    status = load("metadata/execution_status.json")
    generation = load("metadata/generation_exit.json")
    if (
        status["status"] != "smoke_generation_and_replay_finished"
        or shutdown["server_stopped"] is not True
        or shutdown["generation_stopped"] is not True
        or generation["returncode"] != 0
        or load("metadata/replay_command.json")["returncode"] != 0
        or runtime["launch_command_sha256"] != sha(payloads["metadata/launch_argv.json"])
        or runtime["server_log_sha256"] != sha(payloads["metadata/server_before_generation.log"])
        or any(status[k] is not False for k in ("held_out_access_enabled", "main_experiment_ready"))
        or status["official_scoring"] != "not_performed"
        or status["rq3_outcomes"] != "not_evaluated"
    ):
        raise ValueError("Completed smoke runtime/shutdown evidence differs")
    params = load("metadata/sampling_constructor_check.json")
    if any(
        params[n] != expected
        for n, expected in {
            "requested_temperature": 0.001,
            "constructed_temperature": 0.01,
            "top_p": 0.8,
            "top_k": 20,
            "repetition_penalty": 1.05,
            "max_tokens": 1024,
            "n": 1,
            "seed": None,
        }.items()
    ):
        raise ValueError("Saved smoke sampling observation differs")
    local = load("metadata/tokenizer_preflight.json")
    server = load("metadata/server_tokenizer_preflight.json")
    left = {r["request_id"]: r for r in local["per_request"]}
    right = {r["request_id"]: r for r in server["per_request"]}
    rows = load("prepared/requests.json")
    if (
        len(left) != 30
        or len(right) != 30
        or set(left) != set(right)
        or set(left) != {r["request_id"] for r in rows}
        or local["overflow_requests"] != 0
        or server["all_match"] is not True
    ):
        raise ValueError("Thirty matching local/server tokenizer checks required")
    for row in rows:
        key = row["request_id"]
        a, b = left[key], right[key]
        response = load("run/cases/" + key + "/http_response.bin")
        if (
            a["prompt_tokens"] != b["prompt_tokens"]
            or a["token_ids_sha256"] != b["token_ids_sha256"]
            or a["prompt_tokens"] != response["usage"]["prompt_tokens"]
            or a["prompt_tokens"] + row["request"]["max_tokens"] > 8192
        ):
            raise ValueError("Tokenizer/server/returned prompt-token evidence differs")
    return runtime, generation, shutdown


def pair_checks(payloads, parent):
    """Require all original histories and known parent receipts without score selection."""
    rows = json.loads(payloads["prepared/requests.json"])
    small = json.loads(parent["prepared/requests.json"])
    records = {r["request_id"]: r for r in json.loads(parent["replay/records.json"])}
    receipts = json.loads(payloads["prepared/paired_small_records.json"])
    if (
        len(rows) != 30
        or len(small) != 30
        or len(receipts) != 30
        or json.loads(payloads["prepared/episodes.json"])
        != json.loads(parent["prepared/episodes.json"])
        or len({r["request_id"] for r in small}) != 30
    ):
        raise ValueError("All thirty original episodes and known small responses required")
    for row, before, receipt in zip(rows, small, receipts, strict=True):
        saved = records[before["request_id"]]
        expected = {
            "episode_key": before["episode_key"],
            "request_id": before["request_id"],
            "context_messages_sha256": before["context_messages_sha256"],
            "request_sha256": before["request_sha256"],
            "http_status": saved["http_status"],
            "transition_injected": True,
            "evidence_status": saved["validation"]["status"],
            "parser_status": saved["validation"]["parser_status"],
            "usage": saved["usage"],
            "elapsed_seconds": saved["elapsed_seconds"],
        }
        if (
            row["paired_small_request_id"] != before["request_id"]
            or row["episode_key"] != before["episode_key"]
            or row["context_messages_sha256"] != before["context_messages_sha256"]
            or {n: v for n, v in row["request"].items() if n != "model"}
            != {n: v for n, v in before["request"].items() if n != "model"}
            or saved["ledger_state"] != "injected_response_saved"
            or saved["http_status"] != 200
            or saved["transition_injected"] is not True
            or receipt != expected
        ):
            raise ValueError("Fallback history/receipt differs from the known parent")


def paired_parent_check(repo, payloads):
    folder = (
        repo / "artifacts/local_development_audits/recovery_smoke_qwen15b_import_dd91a73f/evidence"
    )
    raw = regular(folder / "metadata/export_file_hashes.json")
    if sha(raw) != "8d642e8e15bfd18c043d5edf3e13a046ee0d978e468070785f2ae323a7920d1f":
        raise ValueError("Completed parent smoke export index differs")
    index = json.loads(raw)
    if any(not safe_member(n) for n in index):
        raise ValueError("Unsafe parent evidence name")
    parent = {n: regular(folder / n) for n in index}
    parent["metadata/export_file_hashes.json"] = raw
    spec = importlib.util.spec_from_file_location(
        "_matched_parent_import",
        repo / "tools/development_audits/recovery_smoke_import_v1/import_smoke.py",
    )
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    original.verify_members(parent)
    original.check_runtime_evidence(parent)
    pair_checks(payloads, parent)
    if any(regular(folder / n) != value for n, value in parent.items()):
        raise ValueError("Original parent evidence changed")


def check_fallback_runtime(payloads):
    def load(n):
        return json.loads(payloads["metadata/" + n])

    runtime, environment = load("runtime.json"), load("environment.json")
    argv = load("launch_argv.json")
    expected = [
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        "Qwen/Qwen2.5-14B-Instruct-AWQ",
        "--revision",
        "539535859b135b0244c91f3e59816150c8056698",
        "--tokenizer-revision",
        "539535859b135b0244c91f3e59816150c8056698",
        "--dtype",
        "float16",
        "--max-model-len",
        "8192",
        "--gpu-memory-utilization",
        "0.88",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    quant = load("model_config.json")["quantization_config"]
    defaults = load("model_generation_config.json")
    params = load("sampling_constructor_check.json")
    auth = load("execution_authorization.json")
    if (
        argv[1:] != expected
        or "L4" not in runtime["gpu_name"]
        or runtime["dtype"] != "float16"
        or runtime["quantization"] != "AWQ 4-bit checkpoint"
        or environment["vllm"] != "0.30.0"
        or environment["transformers"] != "5.20.2"
        or quant.get("bits") != 4
        or quant.get("quant_method") != "awq"
        or load("quantization_check.json")["checkpoint_quantization"] != quant
        or any(defaults[n] != params[n] for n in ("top_p", "top_k", "repetition_penalty"))
        or auth["maximum_fallback_requests"] != 30
        or auth["fresh_small_requests"] != 0
        or auth["parent_smoke_archive_sha256"]
        != "dd91a73f5f565269f83d70773fd25fd64c82785029e3d96b139682c072b59595"
    ):
        raise ValueError("Frozen FP16 AWQ launch/defaults or matched-only scope differs")


def find_archive():
    folder = Path.home() / "Downloads"
    for path in sorted(folder.glob("*matched_recovery_fallback_smoke*.zip")):
        if path.is_file() and not path.is_symlink() and sha(regular(path)) == ARCHIVE_SHA:
            return path
    raise ValueError("Verified smoke evidence ZIP not found in Downloads; supply --archive PATH")


def import_smoke(repo, archive):
    repo = repo.resolve()
    output = repo / OUTPUT
    if output.exists() or any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("Fresh import output required; preserve existing verified evidence")
    if subprocess.run(
        ["git", "check-ignore", "-q", "--", str(OUTPUT / "summary.json")], cwd=repo
    ).returncode:
        raise ValueError("Imported private evidence must remain ignored")
    payloads = read_archive(archive)
    runtime, generation, shutdown = check_runtime_evidence(payloads)
    check_fallback_runtime(payloads)
    paired_parent_check(repo, payloads)
    for _, (name, expected) in SOURCES.items():
        if sha(regular(repo / name).replace(b"\r\n", b"\n")) != expected:
            raise ValueError("Local execution source differs; preserve frozen implementation")
    root = output.parent
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=root, prefix="recovery-smoke-import-") as folder:
        stage = Path(folder)
        evidence, task = stage / "evidence", stage / "reproduced"
        for name, raw in payloads.items():
            path = evidence / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            if PurePosixPath(name).parts[0] in {"prepared", "metadata", "run"}:
                path = task / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
        subprocess.run(
            ["git", "clone", "--quiet", "--shared", "--no-checkout", str(repo), str(task / "repo")],
            check=True,
            capture_output=True,
        )
        # Check out only the frozen replay sources; keep Windows paths short.
        source_root = "tools/development_audits/corrected_generation_v1/"
        sources = json.loads(regular(repo / source_root / "source_manifest.json"))["source_files"]
        selected = set(sources) | {
            source_root + name
            for name in (
                "support.py",
                "workflow.py",
                "workflow_config.json",
                "source_manifest.json",
            )
        }
        selected.add("tools/development_audits/recovery_fallback_smoke_v1/ledger.py")
        subprocess.run(
            ["git", "-C", str(task / "repo"), "sparse-checkout", "set", "--no-cone", "--stdin"],
            input="".join("/" + p + "\n" for p in sorted(selected)),
            text=True,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(task / "repo"), "checkout", "--quiet", "--detach", CODE],
            check=True,
            capture_output=True,
        )
        head = subprocess.check_output(
            ["git", "-C", str(task / "repo"), "rev-parse", "HEAD"], text=True
        ).strip()
        if head != CODE:
            raise ValueError("Independent replay checkout differs")
        # Execute only the source whose bytes matched the published client above.
        replay_client = types.ModuleType("_verified_owner_smoke_client")
        replay_client.__file__ = str(evidence / "metadata/client.py")
        original_bytecode = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            exec(
                compile(payloads["metadata/client.py"], replay_client.__file__, "exec"),
                replay_client.__dict__,
            )
            replayed = replay_client.replay(task)
        finally:
            sys.dont_write_bytecode = original_bytecode
        for name in ("summary.json", "records.json"):
            if regular(task / "replay" / name) != payloads["replay/" + name]:
                raise ValueError("Independent frozen replay differs: " + name)
        if any(regular(evidence / n) != raw for n, raw in payloads.items()):
            raise ValueError("Original imported evidence changed")
        records = json.loads(payloads["replay/records.json"])
        eligible = sum(
            r["validation"]["parser_status"] == "calls"
            and math.isfinite(r["validation"]["whole_output_scores"]["mean_token_nll"])
            for r in records
        )
        summary = {
            "version": "uqroute-matched-recovery-fallback-smoke-import-1.0.0",
            "archive_sha256": ARCHIVE_SHA,
            "verified_export_files": 155,
            "independent_replay_matches": True,
            "requests": replayed["requests"],
            "observed_injected": replayed["observed_injected"],
            "saved_responses": replayed["saved_responses"],
            "unknown_slots": replayed["unknown_slots"],
            "known_http_errors": replayed["known_http_errors"],
            "validation_status_counts": replayed["validation_status_counts"],
            "parser_status_counts": dict(
                Counter(r["validation"]["parser_status"] for r in records)
            ),
            "eligible_parsed_finite_nll_candidates": eligible,
            "benchmarks": dict(Counter(r["benchmark"] for r in records)),
            "fault_types": dict(Counter(r["fault_type"] for r in records)),
            "usage_totals": replayed["usage_totals"],
            "missing_usage_slots": replayed["missing_usage_slots"],
            "request_elapsed_seconds_sum": sum(r["elapsed_seconds"] for r in records),
            "dispatch_wall_seconds": generation["wall_seconds"],
            "supervisor_wall_seconds": shutdown["supervisor_wall_seconds"],
            "gpu_name": runtime["gpu_name"],
            "fallback_requests": replayed["fallback_requests"],
            "new_small_requests": 0,
            "paired_parent_responses": 30,
            "collection_mode": "all_matched_smoke_episodes_no_threshold",
            "parent_pairing_matches": True,
            "effective_sampling_constructor": json.loads(
                payloads["metadata/sampling_constructor_check.json"]
            ),
            "server_stopped": shutdown["server_stopped"],
            "new_generation_requests_sent_by_import": 0,
            "official_scoring": "not_performed",
            "rq3_outcomes": "not_evaluated",
            "held_out_access_enabled": False,
            "main_experiment_ready": False,
        }
        (stage / "summary.json").write_text(
            json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        if sha(regular(archive)) != ARCHIVE_SHA:
            raise ValueError("Original owner ZIP changed during import")
        spec = importlib.util.spec_from_file_location(
            "_smoke_import_publish",
            repo
            / "tools/development_audits"
            / "fallback_full_development_scoring_v1/score_fallback_full.py",
        )
        publisher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(publisher)
        publisher.publish_directory(stage, output)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    args = parser.parse_args()
    if Path.cwd().resolve() != REPO:
        raise SystemExit("Run from the uqroute-tc repository root")
    try:
        archive = args.archive or find_archive()
        subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(HERE), "-p", "test_*.py"],
            cwd=REPO,
            check=True,
        )
        summary = import_smoke(REPO, archive)
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as exc:
        raise SystemExit(
            "Smoke import stopped: "
            + str(exc)
            + ". Preserve the evidence; no generation performed."
        ) from None
    print(json.dumps(summary, indent=2))
    print("Verified:", OUTPUT)
    print("CPU only; no model requests, scoring, held-out access or original evidence changes.")


if __name__ == "__main__":
    main()
