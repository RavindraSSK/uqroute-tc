"""CPU-only production-plan, runtime-binding, replay, export and notebook checks."""

import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import types
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import build_notebook
import client
import runner

REPO = Path(__file__).resolve().parents[3]
CONTEXT = REPO / "tools/development_audits/recovery_context_preflight_v1"
with patch.object(sys, "path", [str(CONTEXT), *sys.path]):
    spec = importlib.util.spec_from_file_location(
        "_gpu_production_fixtures", CONTEXT / "test_preflight.py"
    )
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)


def synthetic_plan(prepared):
    config, _ = fixtures.fixture()
    rows, episodes = [], []
    errors = fixtures.preparer.released_templates(
        (REPO / "tools/development_audits/full_development_v1/official_runner.py").read_text()
    )
    for benchmark in ("apibank", "bfcl_v3", "rotbench", "toolalpaca", "tooleyes"):
        group = "synthetic_" + benchmark
        messages = [
            {"role": "system", "content": "synthetic tools"},
            {"role": "user", "content": "synthetic task"},
        ]
        candidate = {
            "case_key": "clean.jsonl:" + group,
            "canonical_base_id": group,
            "benchmark": benchmark,
            "messages": messages,
            "tools": [],
            "messages_sha256": fixtures.recovery.messages_sha256(messages),
        }
        initial = fixtures.workflow.make_requests(
            [candidate],
            {candidate["case_key"]: {"source_file": "clean.jsonl"}},
            config["models"][0],
            config["single_sample"],
        )[0]
        for fault in errors:
            episode, roles = fixtures.preparer.episode(
                initial,
                "api()",
                [{"name": "api"}],
                "qwen15b",
                fault,
                errors,
                config["models"][3]["model_id"],
                fixtures.recovery,
            )
            episode["initial_usage"] = {"prompt_tokens": 10, "completion_tokens": 1}
            episodes.append(episode)
            rows.append(roles["postfault_small"])
    payloads = {
        "episodes.json": (fixtures.p.canonical(episodes) + "\n").encode(),
        "requests.json": (fixtures.p.canonical(rows) + "\n").encode(),
        "ledger.py": (REPO / "tools/development_audits/recovery_smoke_v1/ledger.py")
        .read_bytes()
        .replace(b"\r\n", b"\n"),
    }
    manifest = {
        "version": "uqroute-recovery-resource-smoke-1.0.0",
        "purpose": "qwen15b-postfault-small-resource-smoke",
        "model_settings": config["models"][0],
        "server_settings": config["single_sample"]["server"],
        "request_count": 30,
        "maximum_new_requests": 30,
        "fallback_requests": 0,
        "automatic_retries": 0,
        "dispatch_authorized": False,
        "held_out_access_enabled": False,
        "main_experiment_ready": False,
        "request_inventory_sha256": fixtures.p.sha(fixtures.p.canonical(rows).encode()),
        "payload_sha256": {n: fixtures.p.sha(b) for n, b in payloads.items()},
    }
    payloads["manifest.json"] = (fixtures.p.canonical(manifest) + "\n").encode()
    prepared.mkdir()
    for name, raw in payloads.items():
        (prepared / name).write_bytes(raw)
    return fixtures.p.sha(payloads["manifest.json"]), manifest, rows, episodes


def runtime_files(task, manifest):
    meta = task / "metadata"
    meta.mkdir()
    runtime = {
        n: manifest["model_settings"][n]
        for n in ("model_id", "model_revision", "tokenizer_revision", "dtype", "quantization")
    }
    runtime.update(
        vllm_version="0.30.0",
        max_model_len=8192,
        gpu_memory_utilization=0.88,
        chat_template=manifest["server_settings"]["chat_template"],
        effective_temperature=0.01,
        gpu_name="synthetic L4",
        gpu_memory_mib=24000,
        platform="synthetic test",
        quota_note="synthetic quota note",
        launch_command_sha256="a" * 64,
        server_log_sha256="b" * 64,
    )
    for name, value in (
        ("runtime.json", runtime),
        ("tokenizer_preflight.json", {"requests": 30, "overflow_requests": 0}),
        ("server_tokenizer_preflight.json", {"requests": 30, "all_match": True}),
    ):
        (meta / name).write_text(json.dumps(value))


def response(usage=True):
    raw = "api()"
    return json.dumps(
        {
            "choices": [
                {
                    "message": {"content": raw},
                    "finish_reason": "stop",
                    "logprobs": {
                        "content": [
                            {
                                "token": raw,
                                "bytes": list(raw.encode()),
                                "logprob": -0.25,
                                "top_logprobs": [],
                            }
                        ]
                    },
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11}
            if usage
            else None,
        }
    ).encode()


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.task = Path(self.tmp.name)
        self.manifest_sha, self.manifest, self.rows, self.episodes = synthetic_plan(
            self.task / "prepared"
        )
        self.pin = patch.object(client, "MANIFEST_SHA", self.manifest_sha)
        self.pin.start()
        self.addCleanup(self.pin.stop)

    def load(self):
        return client.load_plan(REPO, self.task / "prepared")

    def rewrite(self, name, value):
        raw = (fixtures.p.canonical(value) + "\n").encode()
        (self.task / "prepared" / name).write_bytes(raw)
        self.manifest["payload_sha256"][name] = fixtures.p.sha(raw)
        raw = (fixtures.p.canonical(self.manifest) + "\n").encode()
        (self.task / "prepared/manifest.json").write_bytes(raw)
        client.MANIFEST_SHA = fixtures.p.sha(raw)

    def test_real_producer_plan_passes_all_five_benchmarks(self):
        manifest, rows, episodes, _, _, _ = self.load()
        self.assertEqual(len(rows), 30)
        self.assertEqual(len(episodes), 30)
        self.assertFalse(manifest["dispatch_authorized"])

    def test_wrong_manifest_fingerprint_rejected(self):
        client.MANIFEST_SHA = "bad"
        with self.assertRaises(ValueError):
            self.load()

    def test_wrong_payload_fingerprint_rejected(self):
        (self.task / "prepared/requests.json").write_text("[]")
        with self.assertRaises(ValueError):
            self.load()

    def test_held_out_or_already_injected_episode_rejected(self):
        for field, value in (("split", "test"), ("transition_injected", True)):
            episodes = deepcopy(self.episodes)
            episodes[0][field] = value
            self.rewrite("episodes.json", episodes)
            with self.assertRaises(ValueError):
                self.load()

    def test_altered_ledger_rejected_even_with_updated_payload_hash(self):
        self.rewrite("ledger.py", "not executable ledger")
        with self.assertRaises(ValueError):
            self.load()

    def test_missing_fault_rejected(self):
        episodes = deepcopy(self.episodes)
        episodes[0]["fault_type"] = episodes[1]["fault_type"]
        self.rewrite("episodes.json", episodes)
        with self.assertRaises(ValueError):
            self.load()

    def test_explicit_dispatch_flag_required(self):
        with self.assertRaises(ValueError):
            client.run(self.task)
        self.assertFalse((self.task / "run").exists())

    def generate_synthetic(self, fail=False, missing_usage=False):
        subprocess.run(
            ["git", "clone", "--quiet", "--shared", str(REPO), str(self.task / "repo")],
            check=True,
            capture_output=True,
        )
        loaded = self.load()
        manifest, _, _, ledger, support, workflow = loaded
        runtime_files(self.task, manifest)
        count = []

        def caller(body, submitted):
            count.append(body)
            if fail:
                raise TimeoutError("synthetic unknown write")
            submitted()
            return 200, response(not missing_usage or len(count) != 1)

        with (
            patch.object(client, "load_plan", return_value=loaded),
            patch.object(
                workflow,
                "transport",
                return_value=(200, json.dumps({"data": [{"id": client.MODEL}]}).encode()),
            ),
            patch.object(ledger, "local_caller", return_value=caller),
        ):
            if fail:
                with self.assertRaises(ValueError):
                    client.run(self.task, execute=True)
            else:
                client.run(self.task, execute=True)
        return count

    def test_synthetic_dispatch_and_frozen_replay_preserve_all_thirty(self):
        count = self.generate_synthetic()
        summary = client.replay(self.task)
        self.assertEqual(len(count), 30)
        self.assertEqual(summary["saved_responses"], 30)
        self.assertEqual(summary["observed_injected"], 30)
        self.assertEqual(summary["usage_totals"], {"prompt_tokens": 300, "completion_tokens": 30})
        records = json.loads((self.task / "replay/records.json").read_text())
        self.assertTrue(all(r["official_correctness"] is None for r in records))
        self.assertTrue(all(r["validation"] is not None for r in records))
        with self.assertRaises(ValueError):
            client.replay(self.task)

    def test_missing_usage_withholds_totals(self):
        self.generate_synthetic(missing_usage=True)
        summary = client.replay(self.task)
        self.assertIsNone(summary["usage_totals"])
        self.assertEqual(summary["missing_usage_slots"], 1)
        self.assertEqual(summary["known_usage_sums"]["prompt_tokens"], 290)

    def test_unknown_intent_never_becomes_false_injection(self):
        count = self.generate_synthetic(fail=True)
        summary = client.replay(self.task)
        self.assertEqual(len(count), 1)
        self.assertEqual(summary["unknown_slots"], 1)
        self.assertEqual(summary["observed_injected"], 0)
        records = json.loads((self.task / "replay/records.json").read_text())
        self.assertTrue(all(r["transition_injected"] is None for r in records))

    def test_bad_runtime_revision_blocks_binding(self):
        manifest, rows, _, _, support, workflow = self.load()
        runtime_files(self.task, manifest)
        path = self.task / "metadata/runtime.json"
        value = json.loads(path.read_text())
        value["model_revision"] = "bad"
        path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            client.binding_for(self.task, manifest, rows, support, workflow)

    def test_unpack_is_hash_bound_and_never_overwrites(self):
        archive = self.task / "transfer.zip"
        with zipfile.ZipFile(archive, "x") as zipped:
            for path in (self.task / "prepared").iterdir():
                zipped.writestr(path.name, path.read_bytes())
        raw = archive.read_bytes()
        other = self.task / "fresh"
        other.mkdir()
        (other / "transfer.zip").write_bytes(raw)
        with patch.object(client, "ZIP_SHA", hashlib.sha256(raw).hexdigest()):
            client.unpack(other)
            with self.assertRaises(ValueError):
                client.unpack(other)


class ServerAndNotebookTests(unittest.TestCase):
    def server_fixture(self):
        tokens = [10, 20, 30]
        rows = [
            {
                "request_id": "synthetic",
                "request": {"messages": [{"role": "user", "content": "x"}], "max_tokens": 1024},
            }
        ]
        report = {
            "per_request": [
                {
                    "request_id": "synthetic",
                    "prompt_tokens": 3,
                    "token_ids_sha256": hashlib.sha256(
                        json.dumps(tokens, separators=(",", ":")).encode()
                    ).hexdigest(),
                }
            ]
        }
        return rows, report, tokens

    def test_server_local_token_sequences_must_match(self):
        rows, report, tokens = self.server_fixture()
        result = client.server_context_check(
            rows, report, lambda body: (200, json.dumps({"count": 3, "tokens": tokens}).encode())
        )
        self.assertTrue(result["all_match"])
        self.assertEqual(result["generation_requests_sent"], 0)

    def test_equal_length_different_tokens_rejected(self):
        rows, report, _ = self.server_fixture()
        with self.assertRaises(ValueError):
            client.server_context_check(
                rows, report, lambda body: (200, b'{"count":3,"tokens":[10,20,31]}')
            )

    def test_missing_tokenizer_coverage_rejected(self):
        rows, report, _ = self.server_fixture()
        report["per_request"] = []
        with self.assertRaises(ValueError):
            client.server_context_check(rows, report, lambda body: None)

    def test_export_preserves_partial_evidence_and_excludes_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            task = Path(folder) / "task"
            (task / "metadata").mkdir(parents=True)
            (task / "metadata/partial.json").write_text('{"status":"partial"}')
            (task / "venv").mkdir()
            (task / "venv/private.txt").write_text("synthetic excluded environment")
            (task / "quota_note.txt").write_text("synthetic unexported task root")
            result = runner.export_evidence(task)
            with zipfile.ZipFile(result["archive"]) as zipped:
                self.assertEqual(
                    set(zipped.namelist()),
                    {"metadata/partial.json", "metadata/export_file_hashes.json"},
                )
            self.assertTrue((task / "export_path.txt").is_file())

    def test_supervisor_exports_setup_failure_without_dispatch(self):
        with tempfile.TemporaryDirectory() as folder:
            task = Path(folder)
            fake = types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False))
            with patch.dict(sys.modules, {"torch": fake}), patch.object(runner.signal, "signal"):
                self.assertEqual(runner.main(task), 1)
            self.assertTrue((task / "export_path.txt").is_file())
            self.assertFalse((task / "run").exists())

    def test_notebook_embeds_tested_sources_and_all_cells_compile(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "smoke.ipynb"
            with patch.object(build_notebook, "NOTEBOOK", path):
                notebook = build_notebook.build()
            code = "".join(notebook["cells"][4]["source"])
            assignments = {
                n.targets[0].id: ast.literal_eval(n.value)
                for n in ast.parse(code).body
                if isinstance(n, ast.Assign)
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id in {"CLIENT_SOURCE", "RUNNER_SOURCE"}
            }
            self.assertEqual(
                assignments["CLIENT_SOURCE"], (build_notebook.HERE / "client.py").read_text()
            )
            self.assertEqual(
                assignments["RUNNER_SOURCE"], (build_notebook.HERE / "runner.py").read_text()
            )
            for cell in notebook["cells"]:
                if cell["cell_type"] == "code":
                    compile("".join(cell["source"]), "notebook-cell", "exec")
                    self.assertEqual(cell["outputs"], [])
            self.assertIn("TASK.exists()", code)
            self.assertIn("not displayed", code)


if __name__ == "__main__":
    unittest.main()
