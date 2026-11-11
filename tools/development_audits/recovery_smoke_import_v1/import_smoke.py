"""Import and independently replay the completed owner recovery smoke on CPU."""

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
ARCHIVE_SHA = "dd91a73f5f565269f83d70773fd25fd64c82785029e3d96b139682c072b59595"
CODE = "fbe1e3ed1892cfa4b71fb69559af8235107ad0dc"
MANIFEST_SHA = "3b747531cb19eb6e11a5fd74cdf338382f47e22ac0b5c9f596c84f08006d105c"
OUTPUT = Path("artifacts/local_development_audits/recovery_smoke_qwen15b_import_dd91a73f")
SOURCES = {
    "metadata/client.py": (
        "tools/development_audits/recovery_gpu_smoke_v1/client.py",
        "3207177606a4261e7a974df7ade02a27cfbce506cce9596b586cef90bccb58b3",
    ),
    "metadata/runner.py": (
        "tools/development_audits/recovery_gpu_smoke_v1/runner.py",
        "02b0e7fb20c9f2e281188ac9a13c35966ba5731603f7f8af3be8af656cb0c518",
    ),
    "prepared/ledger.py": (
        "tools/development_audits/recovery_smoke_v1/ledger.py",
        "98c162c520b568adc2f67d3a3fa6900c41cf8159dbb0bc939baf1d5af0496813",
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
        len(index) != 152
        or len(payloads) != 153
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
            len(infos) != 153
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
            "repetition_penalty": 1.1,
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


def find_archive():
    folder = Path.home() / "Downloads"
    for path in sorted(folder.glob("*recovery_smoke*.zip")):
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
        selected.add("tools/development_audits/recovery_smoke_v1/ledger.py")
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
            "version": "uqroute-recovery-smoke-import-1.0.0",
            "archive_sha256": ARCHIVE_SHA,
            "verified_export_files": 152,
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
            "fallback_requests": 0,
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
