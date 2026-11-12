"""Colab L4 supervisor for one pinned 30-request matched fallback smoke."""

from __future__ import annotations

import http.client
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
import zipfile
from importlib import metadata
from pathlib import Path

import client


def export_evidence(task):
    """Export completed or partial evidence, excluding environment/cache/credentials."""
    contents = {}
    for prefix in ("prepared", "metadata", "run", "replay"):
        folder = task / prefix
        if folder.is_symlink():
            raise ValueError("Symlink evidence directory")
        if folder.is_dir():
            for path in sorted(folder.rglob("*")):
                if path.is_symlink():
                    raise ValueError("Symlink evidence file")
                if path.is_file():
                    contents[prefix + "/" + path.relative_to(folder).as_posix()] = path.read_bytes()
    import hashlib

    hashes = {name: hashlib.sha256(raw).hexdigest() for name, raw in contents.items()}
    archive = task.parent / (
        "uqroute_qwen14b_matched_recovery_fallback_smoke_" + uuid.uuid4().hex[:8] + ".zip"
    )
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED) as zipped:
        for name, raw in contents.items():
            zipped.writestr(name, raw)
        zipped.writestr(
            "metadata/export_file_hashes.json", json.dumps(hashes, sort_keys=True) + "\n"
        )
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None or any(
            hashlib.sha256(zipped.read(n)).hexdigest() != h for n, h in hashes.items()
        ):
            raise ValueError("Evidence export verification failed")
    with (task / "export_path.txt").open("x", encoding="utf-8") as file:
        file.write(str(archive))
    return {
        "archive": str(archive),
        "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "evidence_files": len(hashes),
    }


def main(task):
    task = task.resolve()
    meta = task / "metadata"
    meta.mkdir(exist_ok=False)
    server, generation, failure = None, None, None
    started = time.monotonic()

    def write(name, value):
        with (meta / name).open("x", encoding="utf-8") as file:
            json.dump(value, file, indent=2, allow_nan=False)
            file.write("\n")

    def stop(process):
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=10)

    def command(args, **kwargs):
        return subprocess.run(args, check=True, **kwargs)

    def post_tokenize(body):
        connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=30)
        try:
            connection.request(
                "POST", "/tokenize", json.dumps(body).encode(), {"Content-Type": "application/json"}
            )
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def interrupted(signum, frame):
        raise KeyboardInterrupt("Supervisor interrupted; preserve request states")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)

    try:
        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA and the frozen FP16 AWQ model required")
        device = torch.cuda.get_device_properties(0)
        if "L4" not in device.name:
            raise RuntimeError("Select the L4 GPU for this pinned notebook")
        if metadata.version("vllm") != "0.30.0" or metadata.version("transformers") != "5.20.2":
            raise RuntimeError("Pinned dependency versions differ")
        quota = (task / "quota_note.txt").read_text().strip()
        if not quota:
            raise RuntimeError(
                "Record current provider quota or explicitly note it is not displayed"
            )
        write(
            "environment.json",
            {
                "python": sys.version,
                "torch": metadata.version("torch"),
                "vllm": metadata.version("vllm"),
                "transformers": metadata.version("transformers"),
                "torch_cuda_build": torch.version.cuda,
                "gpu_name": device.name,
                "gpu_memory_mib": device.total_memory // 1024**2,
                "quota_note": quota,
            },
        )
        ninja = shutil.which("ninja")
        if not ninja:
            raise RuntimeError("Ninja absent from isolated PATH")
        write(
            "ninja_check.json",
            {
                "path": ninja,
                "version": command(
                    [ninja, "--version"], capture_output=True, text=True
                ).stdout.strip(),
            },
        )
        client.unpack(task)
        repo = task / "repo"
        command(
            [
                "git",
                "clone",
                "--no-checkout",
                "https://github.com/RavindraSSK/uqroute-tc.git",
                str(repo),
            ],
            capture_output=True,
            text=True,
        )
        command(
            ["git", "-C", str(repo), "checkout", "--detach", client.CODE],
            capture_output=True,
            text=True,
        )
        if (
            command(
                ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True
            ).stdout.strip()
            != client.CODE
            or command(
                ["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True
            ).stdout
        ):
            raise RuntimeError("Pinned repository checkout differs")
        manifest, rows, _, ledger, support, workflow = client.load_plan(repo, task / "prepared")
        write(
            "repository_validation.json",
            {
                "revision": client.CODE,
                "manifest_sha256": client.MANIFEST_SHA,
                "zip_sha256": client.ZIP_SHA,
                "requests": len(rows),
            },
        )
        from huggingface_hub import hf_hub_download
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            client.MODEL, revision=client.REV, trust_remote_code=False
        )
        counts = []
        for row in rows:
            ids = tokenizer.apply_chat_template(
                row["request"]["messages"],
                tokenize=True,
                add_generation_prompt=True,
                return_dict=False,
            )
            if not isinstance(ids, list) or not ids or any(type(t) is not int for t in ids):
                raise RuntimeError("Unexpected tokenizer IDs")
            counts.append(
                {
                    "request_id": row["request_id"],
                    "prompt_tokens": len(ids),
                    "token_ids_sha256": ledger.sha(json.dumps(ids, separators=(",", ":")).encode()),
                }
            )
        preflight = {
            "requests": len(counts),
            "prompt_tokens_max": max(r["prompt_tokens"] for r in counts),
            "overflow_requests": sum(r["prompt_tokens"] + 1024 > 8192 for r in counts),
            "output_allowance": 1024,
            "context_limit": 8192,
            "tokenizer_revision": client.REV,
            "per_request": counts,
        }
        write("tokenizer_preflight.json", preflight)
        if preflight["overflow_requests"]:
            raise RuntimeError("Context overflow; no trimming/dropping allowed")
        config_raw = Path(
            hf_hub_download(client.MODEL, "config.json", revision=client.REV)
        ).read_bytes()
        quantization = client.quantization_check(json.loads(config_raw))
        with (meta / "model_config.json").open("xb") as file:
            file.write(config_raw)
        write("quantization_check.json", quantization)
        generation_raw = Path(
            hf_hub_download(client.MODEL, "generation_config.json", revision=client.REV)
        ).read_bytes()
        with (meta / "model_generation_config.json").open("xb") as file:
            file.write(generation_raw)
        from vllm.entrypoints.openai.chat_completion.protocol import ChatCompletionRequest

        observed = set()
        for row in rows:
            params = ChatCompletionRequest(**row["request"]).to_sampling_params(
                max_tokens=1024, default_sampling_params=json.loads(generation_raw)
            )
            observed.add(
                (
                    params.temperature,
                    params.top_p,
                    params.top_k,
                    params.repetition_penalty,
                    params.max_tokens,
                    params.n,
                    params.seed,
                )
            )
        if len(observed) != 1:
            raise RuntimeError("Nonuniform installed sampling constructor")
        temperature, top_p, top_k, penalty, output_cap, n, seed = next(iter(observed))
        if temperature != 0.01 or output_cap != 1024 or n != 1 or seed is not None:
            raise RuntimeError("Installed sampling differs from recorded static-run behavior")
        write(
            "sampling_constructor_check.json",
            {
                "requested_temperature": 0.001,
                "constructed_temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "repetition_penalty": penalty,
                "max_tokens": output_cap,
                "n": n,
                "seed": seed,
                "scope": ("Installed local constructor; server sampler not independently observed"),
            },
        )
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", 8000)) == 0:
                raise RuntimeError("Port 8000 occupied; preserve existing server")
        argv = [
            sys.executable,
            "-m",
            "vllm.entrypoints.openai.api_server",
            "--model",
            client.MODEL,
            "--revision",
            client.REV,
            "--tokenizer-revision",
            client.REV,
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
        write("launch_argv.json", argv)
        print("Loading the pinned Qwen 14B AWQ model on L4.", flush=True)
        with (meta / "server.log").open("xb") as log:
            server = subprocess.Popen(
                argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
            )
        startup = time.monotonic()
        last = 0
        while True:
            if server.poll() is not None or time.monotonic() - startup > 1200:
                raise RuntimeError("Server failed/startup deadline exceeded; preserve logs")
            try:
                status, raw = workflow.transport("http://127.0.0.1:8000/v1", "/models", timeout=5)
                if status != 200 or client.MODEL not in {
                    m["id"] for m in support.loads(raw)["data"]
                }:
                    raise RuntimeError("Unexpected local model server")
                break
            except (OSError, TimeoutError):
                if time.monotonic() - last >= 30:
                    print("Server loading/compiling; waiting.", flush=True)
                    last = time.monotonic()
                time.sleep(2)
        snapshot = (meta / "server.log").read_bytes()
        with (meta / "server_before_generation.log").open("xb") as file:
            file.write(snapshot)
        server_check = client.server_context_check(rows, preflight, post_tokenize)
        write("server_tokenizer_preflight.json", server_check)
        runtime = {
            k: manifest["model_settings"][k]
            for k in ("model_id", "model_revision", "tokenizer_revision", "dtype", "quantization")
        }
        runtime.update(
            vllm_version=metadata.version("vllm"),
            max_model_len=8192,
            gpu_memory_utilization=0.88,
            chat_template=manifest["server_settings"]["chat_template"],
            effective_temperature=temperature,
            gpu_name=device.name,
            gpu_memory_mib=device.total_memory // 1024**2,
            platform="Google Colab L4",
            quota_note=quota,
            launch_command_sha256=ledger.sha((meta / "launch_argv.json").read_bytes()),
            server_log_sha256=ledger.sha(snapshot),
        )
        workflow.check_runtime(runtime, manifest)
        write("runtime.json", runtime)
        write(
            "runtime_limits.json",
            {
                "sampling": "Local constructor observation, not per-request server sampler proof",
                "model_identity": (
                    "Pinned launch arguments; model ID endpoint does not verify weights"
                ),
                "quota": "Operator note; available GPU minutes and completion are not guaranteed",
                "batch_wall_limit_seconds": 900,
                "per_request_timeout_seconds": 300,
                "tokenizer_requests": 30,
                "maximum_generation_requests": 30,
            },
        )
        write(
            "execution_authorization.json",
            {
                "scope": "User-run notebook authorizes exactly this 30-request development smoke",
                "preparation_dispatch_authorized": False,
                "maximum_fallback_requests": 30,
                "fresh_small_requests": 0,
                "parent_smoke_archive_sha256": client.PARENT_SHA,
                "held_out_access_enabled": False,
                "main_experiment_ready": False,
            },
        )
        print(
            "All 30 server/local token sequences match. Generating the 30 smoke responses once.",
            flush=True,
        )
        generation_start = time.monotonic()
        with (
            (meta / "generation_stdout.log").open("xb") as out,
            (meta / "generation_stderr.log").open("xb") as err,
        ):
            generation = subprocess.Popen(
                [
                    sys.executable,
                    str(task / "client.py"),
                    "run",
                    "--task",
                    str(task),
                    "--execute-development",
                ],
                stdout=out,
                stderr=err,
                start_new_session=True,
            )
            last = 0
            while generation.poll() is None:
                if time.monotonic() - generation_start > 900:
                    stop(generation)
                    raise RuntimeError("900-second generation wall limit; preserve unknown slots")
                if time.monotonic() - last >= 30:
                    slots = task / "run/cases"
                    occupied = len(list(slots.glob("*/intent.json")))
                    saved = len(list(slots.glob("*/response_metadata.json")))
                    print(
                        f"Smoke progress: {occupied}/30 intents, {saved}/30 saved responses.",
                        flush=True,
                    )
                    last = time.monotonic()
                time.sleep(2)
        write(
            "generation_exit.json",
            {
                "returncode": generation.returncode,
                "wall_seconds": time.monotonic() - generation_start,
            },
        )
        replay = subprocess.run(
            [sys.executable, str(task / "client.py"), "replay", "--task", str(task)],
            capture_output=True,
            text=True,
        )
        write(
            "replay_command.json",
            {"returncode": replay.returncode, "stdout": replay.stdout, "stderr": replay.stderr},
        )
        print(replay.stdout, flush=True)
        if generation.returncode or replay.returncode:
            raise RuntimeError("Smoke dispatch/replay incomplete; preserve evidence, do not retry")
        write(
            "execution_status.json",
            {
                "status": "smoke_generation_and_replay_finished",
                "official_scoring": "not_performed",
                "rq3_outcomes": "not_evaluated",
                "held_out_access_enabled": False,
                "main_experiment_ready": False,
            },
        )
    except BaseException as exc:
        failure = type(exc).__name__ + ": " + str(exc)
        write(
            "execution_error.json",
            {"error": failure, "action": "Preserve evidence; no request retries"},
        )
        print("STOPPED:", failure, flush=True)
    finally:
        for name, process in (("generation", generation), ("server", server)):
            try:
                stop(process)
            except Exception as exc:
                write(name + "_shutdown_error.json", {"exception_type": type(exc).__name__})
        write(
            "shutdown.json",
            {
                "server_stopped": server is None or server.poll() is not None,
                "generation_stopped": generation is None or generation.poll() is not None,
                "supervisor_wall_seconds": time.monotonic() - started,
                "scope": "Supervisor wall time; not all GPU allocation or billing",
            },
        )
        for name in ("runner.py", "client.py", "environment_install.log", "dependency_check.log"):
            if (task / name).is_file():
                shutil.copyfile(task / name, meta / name)
        exported = export_evidence(task)
        print(json.dumps(exported, indent=2), flush=True)
        print(
            "Server shutdown attempted. Download evidence before deleting the runtime.", flush=True
        )
    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
