"""Synthetic integrity, eligibility and CPU context checks; no tokenizer downloads."""

import importlib.util
import json
import sys
import tempfile
import types
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import preflight as p


def load_source(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Exercise the real producers, rather than duplicating their request schema.
support = load_source(
    "_context_fixture_support",
    p.REPO / "tools/development_audits/corrected_generation_v1/support.py",
)
with patch.dict(sys.modules, {"support": support}):
    workflow = load_source(
        "_context_fixture_workflow",
        p.REPO / "tools/development_audits/corrected_generation_v1/workflow.py",
    )
preparer = load_source(
    "_context_fixture_preparer",
    p.REPO / "tools/development_audits/recovery_development_v1/prepare.py",
)
with patch.object(sys, "path", [str(p.REPO / "src"), *sys.path]):
    from uqroute_tc.routing import recovery


class Tokenizer:
    chat_template = "synthetic-template"
    is_fast = True
    backend_tokenizer = types.SimpleNamespace(to_str=lambda: "synthetic-backend")

    def apply_chat_template(self, messages, **kwargs):
        assert kwargs == {"tokenize": True, "add_generation_prompt": True, "return_dict": False}
        return [1] * len(messages[-1]["content"])


def fixture(key="qwen15b"):
    config = json.loads((p.REPO / "docs/config/task1_single_sample_v1.json").read_text())
    errors = preparer.released_templates(
        (p.REPO / "tools/development_audits/full_development_v1/official_runner.py").read_text()
    )
    manifest = {
        "version": "uqroute-recovery-development-preparation-1.0.0",
        "small_model_key": key,
        "dispatch_authorized": False,
        "held_out_access_enabled": False,
        "main_experiment_ready": False,
        "static_dispatcher_compatible": False,
        "model_settings": deepcopy(
            {"small": config["models"][p.TRANSFERS[key][3]], "fallback": config["models"][3]}
        ),
        "server_settings": config["single_sample"]["server"],
    }
    data = {
        "manifest.json": manifest,
        "episodes.json": [],
        "small_requests.json": [],
        "fallback_requests.json": [],
    }
    messages = [{"role": "system", "content": "tools"}, {"role": "user", "content": "task"}]
    candidate = {
        "case_key": "clean.jsonl:synthetic",
        "canonical_base_id": "synthetic",
        "benchmark": "bfcl_v3",
        "messages": messages,
        "messages_sha256": recovery.messages_sha256(messages),
        "tools": [],
    }
    initial = workflow.make_requests(
        [candidate],
        {candidate["case_key"]: {"source_file": "clean.jsonl"}},
        manifest["model_settings"]["small"],
        config["single_sample"],
    )[0]
    for fault in errors:
        episode, roles = preparer.episode(
            initial,
            "api()",
            [{"name": "api", "parameters": {}}],
            key,
            fault,
            errors,
            manifest["model_settings"]["fallback"]["model_id"],
            recovery,
        )
        data["episodes.json"].append(episode)
        data["small_requests.json"].append(roles["postfault_small"])
        data["fallback_requests.json"].append(roles["postfault_fallback"])
    return config, data


def archive(path, data):
    payloads = {
        n: (p.canonical(v) + "\n").encode() for n, v in data.items() if n != "manifest.json"
    }
    manifest = deepcopy(data["manifest.json"])
    manifest["payload_sha256"] = {n: p.sha(v) for n, v in payloads.items()}
    payloads["manifest.json"] = (p.canonical(manifest) + "\n").encode()
    with zipfile.ZipFile(path, "x") as z:
        for name, value in payloads.items():
            z.writestr(name, value)
    return p.sha(path.read_bytes()), p.sha(payloads["manifest.json"])


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.config, self.data = fixture()

    def validate(self, count=6):
        return p.validate_plan(self.data, "qwen15b", self.config, count, clean_count=1)

    def test_valid_plan_and_all_role_contexts_counted(self):
        _, roles = self.validate()
        report = p.count_contexts(roles["postfault_small"], Tokenizer(), 8192)
        self.assertEqual(report["requests"], 6)
        self.assertEqual(report["overflow_requests"], 0)
        self.assertEqual(len(report["per_request"]), 6)

    def test_exact_context_boundary_includes_full_output_allowance(self):
        _, roles = self.validate()
        rows = dict(list(roles["postfault_small"].items())[:1])
        size = len(next(iter(rows.values()))["request"]["messages"][-1]["content"])
        self.assertEqual(p.count_contexts(rows, Tokenizer(), 1024 + size)["overflow_requests"], 0)
        self.assertEqual(p.count_contexts(rows, Tokenizer(), 1023 + size)["overflow_requests"], 1)

    def test_overflow_preserved_and_inputs_unchanged(self):
        _, roles = self.validate()
        before = deepcopy(roles)
        result = p.count_contexts(roles["postfault_small"], Tokenizer(), 1024)
        self.assertEqual(result["overflow_requests"], 6)
        self.assertEqual(len(result["per_request"]), 6)
        self.assertEqual(roles, before)

    def test_invalid_token_ids_rejected(self):
        _, roles = self.validate()
        for ids in ([], [True], [[1]], "tokens"):
            with (
                self.subTest(ids=ids),
                patch.object(Tokenizer, "apply_chat_template", return_value=ids),
            ):
                with self.assertRaises(ValueError):
                    p.count_contexts(roles["postfault_small"], Tokenizer(), 8192)

    def test_missing_or_duplicate_role_coverage_rejected(self):
        for duplicate in (False, True):
            _, self.data = fixture()
            if duplicate:
                self.data["small_requests.json"].append(self.data["small_requests.json"][0])
            else:
                self.data["small_requests.json"].pop()
            with self.assertRaises(ValueError):
                self.validate()

    def test_observed_injection_flag_rejected_for_preparation(self):
        self.data["episodes.json"][0]["transition_injected"] = True
        with self.assertRaises(ValueError):
            self.validate()

    def test_no_injection_has_no_request_and_remains_separate(self):
        e = self.data["episodes.json"][0]
        e.update(
            injection_eligible=False,
            transition_injected=False,
            no_injection_reason="initial_no_official_call",
        )
        for filename in ("small_requests.json", "fallback_requests.json"):
            self.data[filename].pop(0)
        _, roles = self.validate(count=5)
        self.assertEqual(len(roles["postfault_small"]), 5)

    def test_wrong_role_model_or_revision_rejected(self):
        self.data["manifest.json"]["model_settings"]["fallback"]["tokenizer_revision"] = "bad"
        with self.assertRaises(ValueError):
            self.validate()

    def test_non_development_episode_rejected(self):
        self.data["episodes.json"][0]["split"] = "test"
        with self.assertRaises(ValueError):
            self.validate()

    def test_duplicate_fault_or_episode_rejected(self):
        self.data["episodes.json"][-1] = deepcopy(self.data["episodes.json"][0])
        with self.assertRaises(ValueError):
            self.validate()

    def test_wrong_generation_settings_rejected(self):
        self.data["small_requests.json"][0]["request"]["max_tokens"] = 1
        with self.assertRaises(ValueError):
            self.validate()

    def test_production_requests_preserve_explicit_nonstreaming(self):
        for filename in ("small_requests.json", "fallback_requests.json"):
            for row in self.data[filename]:
                self.assertIs(row["request"]["stream"], False)
        self.validate()

    def test_stream_true_or_missing_rejected_even_with_recomputed_request_hash(self):
        for filename in ("small_requests.json", "fallback_requests.json"):
            for changed in (True, "missing"):
                _, self.data = fixture()
                row = self.data[filename][0]
                if changed == "missing":
                    del row["request"]["stream"]
                else:
                    row["request"]["stream"] = changed
                row["request_sha256"] = p.sha(p.canonical(row["request"]).encode())
                with self.assertRaises(ValueError):
                    self.validate()

    def test_modified_context_or_request_id_rejected(self):
        for field in ("request_id", "context_messages_sha256", "request_sha256"):
            _, self.data = fixture()
            self.data["small_requests.json"][0][field] = "bad"
            with self.assertRaises(ValueError):
                self.validate()

    def test_readiness_or_dispatch_changes_rejected(self):
        for field in ("dispatch_authorized", "held_out_access_enabled", "main_experiment_ready"):
            _, self.data = fixture()
            self.data["manifest.json"][field] = True
            with self.assertRaises(ValueError):
                self.validate()

    def test_archive_hash_manifest_hash_and_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.zip"
            a, m = archive(path, self.data)
            self.assertEqual(
                p.read_archive(path, a, m)["episodes.json"], self.data["episodes.json"]
            )
            for bad_a, bad_m in (("bad", m), (a, "bad")):
                with self.assertRaises(ValueError):
                    p.read_archive(path, bad_a, bad_m)
            with zipfile.ZipFile(path, "a") as z:
                z.writestr("extra.json", "{}")
            with self.assertRaises(ValueError):
                p.read_archive(path, p.sha(path.read_bytes()), m)

    def test_duplicate_or_nonfinite_json_rejected(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(ValueError):
                p.loads(raw)

    def test_all_four_model_tokenizers_remain_distinct(self):
        ids = set()
        for key in p.TRANSFERS:
            config, data = fixture(key)
            manifest, _ = p.validate_plan(data, key, config, 6, clean_count=1)
            ids.update(
                (s["model_id"], s["tokenizer_revision"])
                for s in manifest["model_settings"].values()
            )
        self.assertEqual(len(ids), 4)

    def test_full_synthetic_run_publishes_fresh_results_and_preserves_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            (repo / "docs/config").mkdir(parents=True)
            (repo / "docs/config/task1_single_sample_v1.json").write_bytes(
                (p.REPO / "docs/config/task1_single_sample_v1.json").read_bytes()
            )
            prepared = repo / p.PREPARATION
            prepared.mkdir(parents=True)
            helper = Path(
                "tools/development_audits/fallback_full_development_scoring_v1/score_fallback_full.py"
            )
            (repo / helper).parent.mkdir(parents=True)
            (repo / helper).write_bytes((p.REPO / helper).read_bytes())
            pins = {}
            for key, value in p.TRANSFERS.items():
                _, data = fixture(key)
                path = prepared / (key + "_recovery_development_transfer_v1.zip")
                a, m = archive(path, data)
                pins[key] = (a, m, 6, value[3])
            original_validator = p.validate_plan

            def validate(data, key, config, eligible):
                return original_validator(data, key, config, eligible, clean_count=1)

            before = {f.name: f.read_bytes() for f in prepared.iterdir()}

            def versions(n):
                return p.TRANSFORMERS_VERSION if n == "transformers" else "synthetic"

            fake_auto = types.SimpleNamespace(from_pretrained=lambda *a, **k: Tokenizer())
            with (
                patch.object(p, "TRANSFERS", pins),
                patch.object(p, "validate_plan", side_effect=validate),
                patch.object(p.subprocess, "run", return_value=types.SimpleNamespace(returncode=0)),
                patch.object(p.importlib.metadata, "version", side_effect=versions),
                patch.dict(
                    sys.modules, {"transformers": types.SimpleNamespace(AutoTokenizer=fake_auto)}
                ),
            ):
                summary = p.run(repo)
                self.assertTrue(summary["all_contexts_fit"])
                self.assertEqual(summary["generation_requests_sent"], 0)
                self.assertFalse(summary["dispatch_authorized"])
                self.assertTrue((repo / p.OUTPUT / "report.json").is_file())
                with self.assertRaises(ValueError):
                    p.run(repo)
            self.assertEqual(before, {f.name: f.read_bytes() for f in prepared.iterdir()})


if __name__ == "__main__":
    unittest.main()
