"""Build the reviewed Colab L4 notebook with exact tested client/supervisor sources."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
NOTEBOOK = REPO / "notebooks/UQRoute_TC_Qwen14B_Matched_Recovery_Fallback_Smoke_v1.ipynb"
ZIP_SHA = "2e2bc38f6104c06d9a6084344a5d89b1dfcd2ddb7b3ec53791a7d9d65c3abc61"


def cell(kind, source):
    result = {"cell_type": kind, "metadata": {}, "source": source.splitlines(keepends=True)}
    if kind == "code":
        result.update(execution_count=None, outputs=[])
    return result


def build():
    intro = """# Qwen 14B AWQ matched recovery fallback smoke — 30 requests

1. In Colab, choose **Runtime → Change runtime type → L4 GPU**.
2. Upload the INPUT `qwen14b_matched_recovery_fallback_smoke_v1.zip` from
   `artifacts/local_development_audits/recovery_matched_fallback_smoke_preparation_v1/`.
3. Run the execution cell **once**. Enter the current quota/compute-unit note,
   or explicitly `not displayed` if the provider does not show remaining quota.
4. Run DOWNLOAD after execution finishes, including a recorded failure.
   Save the OUTPUT `uqroute_qwen14b_matched_recovery_fallback_smoke_*.zip` and attach it in chat.
5. After saving the output, **disconnect and delete the GPU runtime**.

This user-run execution cell authorizes at most **30 new fallback responses**
for this development engineering smoke only: five eligible clean groups, all six
fault-feedback types per group. Initial outputs are reused, not regenerated.
No new small generation, reference scoring, final threshold or held-out evaluation.
All 30 prior fault contexts are retained without correctness/uncertainty filtering.
No later small answer is appended; this collects pairs, not a gated policy.
Preparation authorization/readiness flags remain false and unchanged.

The notebook installs isolated vLLM 0.30.0, Transformers 5.20.2 and Ninja, then
checks every local/server token sequence before generation. It retains the
requested temperature 0.001 and records the observed constructor clamp to 0.01,
inherited model defaults, FP16 AWQ, context 8192 and output cap 1024. No seed is added.
The public Qwen tokenizer/model needs no user authentication token.

Repository: `c3cbf9f44334547a747585c613afe34d381bd070`.
INPUT ZIP SHA256: `2e2bc38f6104c06d9a6084344a5d89b1dfcd2ddb7b3ec53791a7d9d65c3abc61`.
Manifest SHA256: `3bc0762f233ebfcad69f55bc20285235a8962b6a93417b73fab96d24094d816d`.

There are **zero automatic generation retries**. An existing execution folder
is refused; interrupted/unknown requests remain occupied. Do not reset and resend
this batch after an interruption. Download partial evidence for review first.
Setup/model compilation can take several minutes; the startup deadline is 20
minutes and the generation wall deadline is 15 minutes, with 300 seconds per
request. These are stopping limits, not estimates or a quota guarantee. The
quota note records operator information, not measured GPU minutes or money.

The server `/tokenize` checks do not generate model outputs. A recorded local
HTTP write establishes a submitted fault-feedback attempt, not server execution
or an actual external tool failure. Smoke status/usage/token alignment do not
measure recovery correctness. Dependent faults share only five canonical groups.
Raw prompts and model outputs stay in the private evidence ZIP. Credentials,
environment variables, dependency caches and model weights are not exported.
Partial export is best effort after a software interruption; forced runtime
deletion can lose evidence. Downloading the output again does not rerun inference.
"""
    upload = f"""from pathlib import Path
import hashlib
from google.colab import files

expected = {ZIP_SHA!r}
target = Path('/content/qwen14b_matched_recovery_fallback_smoke_v1.zip')
if target.is_symlink():
    raise RuntimeError('Symlink INPUT path; preserve it.')
if target.exists():
    if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Occupied INPUT path differs; preserve it for review.')
    print('Approved INPUT already available; no upload needed.')
else:
    uploaded = files.upload()
    if len(uploaded) != 1:
        raise RuntimeError('Select one INPUT transfer ZIP.')
    raw = next(iter(uploaded.values()))
    if hashlib.sha256(raw).hexdigest() != expected:
        raise RuntimeError('Wrong INPUT: select qwen14b_matched_recovery_fallback_smoke_v1.zip.')
    if not target.exists():
        with target.open('xb') as file:
            file.write(raw)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected:
        raise RuntimeError('Canonical INPUT differs; preserve it.')
    print('INPUT verified. Run execution once.')
"""
    setup = """from pathlib import Path
import hashlib
import importlib.util
import os
import shutil
import signal
import subprocess
import sys
import time

TASK = Path('/content/uqroute_qwen14b_matched_recovery_fallback_smoke_execution_v1')
if TASK.exists():
    raise RuntimeError('Execution folder exists. Preserve it; do not repeat generation.')
source = Path('/content/qwen14b_matched_recovery_fallback_smoke_v1.zip')
raw = source.read_bytes()
expected = '2e2bc38f6104c06d9a6084344a5d89b1dfcd2ddb7b3ec53791a7d9d65c3abc61'
if hashlib.sha256(raw).hexdigest() != expected:
    raise RuntimeError('INPUT fingerprint differs; nothing started.')
gpu = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                     capture_output=True, text=True, check=True)
print('Allocated GPU:', gpu.stdout.strip(), flush=True)
if 'L4' not in gpu.stdout:
    raise RuntimeError('Choose an L4 GPU before starting.')
quota_note = input("Enter current Colab quota/compute units, or 'not displayed': ").strip()
if not quota_note:
    raise RuntimeError('A quota note is required; nothing started.')
TASK.mkdir(exist_ok=False)
(TASK / 'transfer.zip').write_bytes(raw)
(TASK / 'quota_note.txt').write_text(quota_note, encoding='utf-8')
"""
    setup += "\nCLIENT_SOURCE = " + repr((HERE / "client.py").read_text()) + "\n"
    setup += "RUNNER_SOURCE = " + repr((HERE / "runner.py").read_text()) + "\n"
    setup += """(TASK / 'client.py').write_text(CLIENT_SOURCE, encoding='utf-8')
(TASK / 'runner.py').write_text(RUNNER_SOURCE, encoding='utf-8')
execution, install = None, None
try:
    ENV = TASK / 'venv'
    PYTHON = ENV / 'bin/python'
    subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(ENV)], check=True)
    print('Installing the isolated environment; model loading follows setup.', flush=True)
    with (TASK / 'environment_install.log').open('xb') as log:
        install = subprocess.Popen([sys.executable, '-m', 'pip', '--python', str(PYTHON), 'install',
                                    'pip', 'vllm==0.30.0', 'transformers==5.20.2', 'ninja'],
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        last = 0
        while install.poll() is None:
            if time.monotonic() - last >= 30:
                print('Dependency installation is running.', flush=True)
                last = time.monotonic()
            time.sleep(2)
    if install.returncode:
        raise RuntimeError('Dependency install failed; preserve the installation log.')
    env = os.environ.copy()
    env['PATH'] = str(PYTHON.parent) + os.pathsep + env.get('PATH', '')
    env['VIRTUAL_ENV'] = str(ENV)
    env.pop('PYTHONPATH', None)
    with (TASK / 'dependency_check.log').open('xb') as log:
        subprocess.run([str(PYTHON), '-m', 'pip', 'check'], env=env, stdout=log,
                       stderr=subprocess.STDOUT, check=True)
    print('Starting runtime validation and the bounded smoke.', flush=True)
    execution = subprocess.Popen([str(PYTHON), str(TASK / 'runner.py'), str(TASK)],
                                 env=env, start_new_session=True)
    execution.wait()
    print('Execution exit code:', execution.returncode, flush=True)
except BaseException as exc:
    if install is not None and install.poll() is None:
        os.killpg(install.pid, signal.SIGTERM)
        try:
            install.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(install.pid, signal.SIGKILL)
            install.wait(timeout=10)
    if execution is not None and execution.poll() is None:
        os.killpg(execution.pid, signal.SIGINT)
        try:
            execution.wait(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(execution.pid, signal.SIGKILL)
            execution.wait(timeout=10)
    print('Execution stopped:', type(exc).__name__, str(exc), flush=True)
finally:
    if not (TASK / 'export_path.txt').is_file():
        # Salvage setup/partial artifacts without executing the supervisor main.
        meta = TASK / 'metadata'
        meta.mkdir(exist_ok=True)
        for name in ('client.py', 'runner.py', 'environment_install.log', 'dependency_check.log'):
            if (TASK / name).is_file() and not (meta / name).exists():
                shutil.copyfile(TASK / name, meta / name)
        (meta / 'outer_salvage.txt').write_text(
            'Partial/setup evidence only. '
            'Server shutdown and dispatch completion may be unknown.\\n',
            encoding='utf-8')
        sys.path.insert(0, str(TASK))
        spec = importlib.util.spec_from_file_location('_smoke_export_only', TASK / 'runner.py')
        exporter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exporter)
        print(exporter.export_evidence(TASK), flush=True)
    print('Download the OUTPUT evidence ZIP now; do not rerun this execution cell.', flush=True)
"""
    download = """from pathlib import Path
from google.colab import files
task = Path('/content/uqroute_qwen14b_matched_recovery_fallback_smoke_execution_v1')
marker = task / 'export_path.txt'
if not marker.is_file():
    raise RuntimeError('No export marker. Preserve runtime/logs; do not rerun generation.')
output = Path(marker.read_text().strip())
if not output.is_file():
    raise RuntimeError('OUTPUT export missing; preserve runtime.')
print('Downloading OUTPUT:', output.name)
files.download(str(output))
"""
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"gpuType": "L4"},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        },
        "cells": [
            cell("markdown", intro),
            cell("markdown", "## 1. Upload INPUT\n"),
            cell("code", upload),
            cell("markdown", "## 2. Execute once\n"),
            cell("code", setup),
            cell("markdown", "## 3. Download OUTPUT\n"),
            cell("code", download),
        ],
    }
    for index, item in enumerate(notebook["cells"]):
        item["id"] = "recovery-smoke-" + str(index)
    NOTEBOOK.write_text(
        json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return notebook


if __name__ == "__main__":
    build()
    print(NOTEBOOK)
