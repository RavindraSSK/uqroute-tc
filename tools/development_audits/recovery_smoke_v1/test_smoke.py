"""Production-built smoke plans and synthetic write-once transport checks."""

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import ledger
import stage

CONTEXT = stage.REPO / "tools/development_audits/recovery_context_preflight_v1"
with patch.object(sys, "path", [str(CONTEXT), *sys.path]):
    spec = importlib.util.spec_from_file_location(
        "_smoke_production_fixtures", CONTEXT / "test_preflight.py"
    )
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)


def binding(rows):
    return {
        "purpose": "qwen15b-postfault-small-resource-smoke",
        "request_inventory_sha256": ledger.sha(ledger.canonical(rows).encode()),
        "automatic_retries": 0,
        "held_out_access_enabled": False,
        "main_experiment_ready": False,
    }


def report_fixture():
    plans, reports, pins = {}, {}, {}
    for key, value in fixtures.p.TRANSFERS.items():
        config, data = fixtures.fixture(key)
        plans[key] = fixtures.p.validate_plan(data, key, config, 6, clean_count=1)
        manifest, roles = plans[key]
        reports[key] = {}
        pins[key] = ("synthetic-archive-" + key, *value[1:])
        for role, rows in roles.items():
            result = fixtures.p.count_contexts(rows, fixtures.Tokenizer(), 8192)
            settings = manifest["model_settings"][
                "small" if role == "postfault_small" else "fallback"
            ]
            result.update(
                model_id=settings["model_id"], tokenizer_revision=settings["tokenizer_revision"]
            )
            reports[key][role] = result
    summary = {
        "version": "uqroute-recovery-context-preflight-1.0.0",
        "all_contexts_fit": True,
        "generation_requests_sent": 0,
        "observed_fault_conditioned_dispatches": 0,
        "dispatch_authorized": False,
        "held_out_access_enabled": False,
        "main_experiment_ready": False,
        "prompts_truncated": False,
        "requests_dropped": 0,
        "models": {
            k: {
                role: {n: v for n, v in r.items() if n != "per_request"}
                for role, r in model.items()
            }
            for k, model in reports.items()
        },
    }
    report = {
        "models": reports,
        "task1_settings_sha256_lf": fixtures.p.CONFIG_SHA,
        "input_archive_sha256": {
            key + "_recovery_development_transfer_v1.zip": v[0] for key, v in pins.items()
        },
    }
    return summary, report, plans, pins


class LedgerTests(unittest.TestCase):
    def setUp(self):
        _, data = fixtures.fixture()
        self.rows = data["small_requests.json"][:2]
        self.binding = binding(self.rows)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "run"
        self.calls = []

    def caller(self, body, submitted):
        self.calls.append(body)
        submitted()
        return 200, b'{"choices":[]}'

    def dispatch(self, caller=None, execute=True):
        return ledger.dispatch(
            self.rows, self.output, self.binding, caller or self.caller, execute_development=execute
        )

    def test_two_saved_responses_and_resume_makes_no_new_calls(self):
        result = self.dispatch()
        self.assertEqual(result["observed_injected"], 2)
        self.assertEqual(result["saved_responses"], 2)
        self.assertEqual(self.dispatch()["saved_responses"], 2)
        self.assertEqual(len(self.calls), 2)

    def test_explicit_execute_required(self):
        with self.assertRaises(ValueError):
            self.dispatch(execute=False)
        self.assertFalse(self.output.exists())
        self.assertFalse(self.calls)

    def test_before_submission_failure_remains_unknown_and_stops_batch(self):
        def fail(body, submitted):
            self.calls.append(body)
            raise OSError("synthetic transport failure")

        result = self.dispatch(fail)
        self.assertEqual(result["observed_injected"], 0)
        self.assertEqual(result["unknown_slots"], 1)
        self.assertEqual(result["pending"], 1)
        with self.assertRaises(ValueError):
            self.dispatch()
        self.assertEqual(len(self.calls), 1)

    def test_after_submission_failure_preserves_observed_injection(self):
        def fail(body, submitted):
            submitted()
            raise TimeoutError("synthetic read timeout")

        result = self.dispatch(fail)
        self.assertEqual(result["observed_injected"], 1)
        self.assertEqual(result["unknown_slots"], 1)
        self.assertEqual(result["saved_responses"], 0)
        with self.assertRaises(ValueError):
            self.dispatch()

    def test_missing_submission_callback_cannot_create_response(self):
        with self.assertRaises(ValueError):
            self.dispatch(lambda body, submitted: (200, b"{}"))
        self.assertEqual(ledger.replay(self.rows, self.output, self.binding)["unknown_slots"], 1)

    def test_known_http_failure_preserved_and_continuation_blocked(self):
        def fail(body, submitted):
            submitted()
            return 429, b'{"error":"synthetic rate limit"}'

        result = self.dispatch(fail)
        self.assertEqual(result["known_http_errors"], 1)
        self.assertEqual(result["observed_injected"], 1)
        self.assertEqual(result["pending"], 1)
        with self.assertRaises(ValueError):
            self.dispatch()

    def test_abandoned_lock_is_not_deleted_or_retried(self):
        self.output.mkdir()
        (self.output / ".writer.lock").write_text("abandoned")
        with self.assertRaises(FileExistsError):
            self.dispatch()
        self.assertEqual((self.output / ".writer.lock").read_text(), "abandoned")
        self.assertFalse(self.calls)

    def test_resume_binding_change_rejected(self):
        self.dispatch()
        self.binding["runtime"] = "changed"
        with self.assertRaises(ValueError):
            self.dispatch()
        self.assertEqual(len(self.calls), 2)

    def test_raw_response_tampering_rejected(self):
        self.dispatch()
        (self.output / "cases" / self.rows[0]["request_id"] / "http_response.bin").write_bytes(
            b"tampered"
        )
        with self.assertRaises(ValueError):
            ledger.replay(self.rows, self.output, self.binding)

    def test_request_hash_or_context_tampering_rejected_before_call(self):
        self.rows[0]["request"]["messages"][-1]["content"] += "changed"
        with self.assertRaises(ValueError):
            self.dispatch()
        self.assertFalse(self.calls)

    def test_fallback_stage_or_extra_sampling_field_rejected(self):
        for changed in ("stage", "sampling"):
            _, data = fixtures.fixture()
            rows = data["small_requests.json"][:1]
            if changed == "stage":
                rows[0]["stage"] = "postfault_fallback"
            else:
                rows[0]["request"]["seed"] = 1
                rows[0]["request_sha256"] = ledger.sha(
                    ledger.canonical(rows[0]["request"]).encode()
                )
            with self.assertRaises(ValueError):
                ledger.checked_rows(rows)

    def test_over_budget_or_duplicate_requests_rejected(self):
        for rows in ([], self.rows * 16, self.rows + self.rows):
            with self.assertRaises(ValueError):
                ledger.checked_rows(rows)

    def test_output_symlink_rejected(self):
        target = Path(self.tmp.name) / "target"
        target.mkdir()
        try:
            self.output.symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation unavailable")
        with self.assertRaises(ValueError):
            self.dispatch()
        self.assertFalse(list(target.iterdir()))

    def test_only_loopback_endpoint_allowed(self):
        for url in (
            "https://127.0.0.1/v1",
            "http://example.com/v1",
            "http://user:pass@localhost/v1",
            "http://localhost/v1?x=1",
        ):
            with self.assertRaises(ValueError):
                ledger.local_caller(url)

    def test_local_transport_records_submission_after_write_before_response(self):
        events = []
        response = types.SimpleNamespace(status=200, read=lambda: b"{}")

        def request(*args):
            events.append("write")
            self.assertEqual(args[0:2], ("POST", "/v1/chat/completions"))
            self.assertEqual(json.loads(args[2]), self.rows[0]["request"])

        def getresponse():
            self.assertEqual(events, ["write", "submitted"])
            return response

        connection = types.SimpleNamespace(
            request=request, getresponse=getresponse, close=lambda: events.append("closed")
        )
        with patch.object(ledger.http.client, "HTTPConnection", return_value=connection):
            result = ledger.local_caller("http://127.0.0.1:8000/v1")(
                self.rows[0]["request"], lambda: events.append("submitted")
            )
        self.assertEqual(result, (200, b"{}"))
        self.assertEqual(events, ["write", "submitted", "closed"])


class StageTests(unittest.TestCase):
    def setUp(self):
        self.summary, self.report, self.plans, self.pins = report_fixture()

    def verify(self):
        stage.verify_preflight(
            self.summary, self.report, self.plans, self.pins, fixtures.p.CONFIG_SHA
        )

    def test_complete_preflight_accepted_without_tokenizer_loading(self):
        self.verify()

    def test_missing_role_or_request_rejected(self):
        self.report["models"]["qwen15b"]["postfault_small"]["per_request"].pop()
        with self.assertRaises(ValueError):
            self.verify()

    def test_wrong_context_or_overflow_rejected(self):
        row = self.report["models"]["qwen15b"]["postfault_small"]["per_request"][0]
        row["context_messages_sha256"] = "bad"
        with self.assertRaises(ValueError):
            self.verify()

    def test_false_readiness_or_incomplete_owner_summary_rejected(self):
        self.summary["all_contexts_fit"] = False
        with self.assertRaises(ValueError):
            self.verify()

    def test_wrong_preflight_source_archive_rejected(self):
        self.report["input_archive_sha256"]["qwen15b_recovery_development_transfer_v1.zip"] = "bad"
        with self.assertRaises(ValueError):
            self.verify()

    def test_selection_retains_all_six_faults_and_only_small_requests(self):
        _, data = fixtures.fixture()
        _, roles = self.plans["qwen15b"]
        episodes, rows, missing = stage.select_smoke(data["episodes.json"], roles)
        self.assertEqual(len(episodes), 6)
        self.assertEqual(len(rows), 6)
        self.assertFalse(missing)
        self.assertTrue(all(r["stage"] == "postfault_small" for r in rows))
        self.assertEqual(
            (episodes, rows, missing), stage.select_smoke(data["episodes.json"][::-1], roles)
        )

    def test_no_call_benchmark_is_reported_without_inventing_request(self):
        _, data = fixtures.fixture()
        no_call = deepcopy(data["episodes.json"][0])
        no_call.update(
            benchmark="synthetic_no_call", injection_eligible=False, transition_injected=False
        )
        data["episodes.json"].append(no_call)
        _, roles = self.plans["qwen15b"]
        _, rows, missing = stage.select_smoke(data["episodes.json"], roles)
        self.assertEqual(len(rows), 6)
        self.assertEqual(missing, ["synthetic_no_call"])

    def test_selection_ignores_correctness_labels(self):
        _, data = fixtures.fixture()
        _, roles = self.plans["qwen15b"]
        _, rows, _ = stage.select_smoke(data["episodes.json"], roles)
        for e in data["episodes.json"]:
            e["official_correctness"] = "poisoned label must not affect selection"
        _, again, _ = stage.select_smoke(data["episodes.json"], roles)
        self.assertEqual(rows, again)

    def test_five_benchmarks_choose_one_ranked_group_each_and_thirty_requests(self):
        config, _ = fixtures.fixture()
        episodes, roles, expected_groups = [], {"postfault_small": {}}, set()
        errors = fixtures.preparer.released_templates(
            (
                stage.REPO / "tools/development_audits/full_development_v1/official_runner.py"
            ).read_text()
        )
        for benchmark in ("apibank", "bfcl_v3", "rotbench", "toolalpaca", "tooleyes"):
            groups = [benchmark + "_group_a", benchmark + "_group_b"]
            chosen = min(
                groups, key=lambda group: ledger.sha(ledger.canonical([benchmark, group]).encode())
            )
            expected_groups.add(chosen)
            for group in groups:
                messages = [
                    {"role": "system", "content": "tools"},
                    {"role": "user", "content": "task"},
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
                    episode, requests = fixtures.preparer.episode(
                        initial,
                        "api()",
                        [{"name": "api"}],
                        "qwen15b",
                        fault,
                        errors,
                        config["models"][3]["model_id"],
                        fixtures.recovery,
                    )
                    episodes.append(episode)
                    roles["postfault_small"][episode["episode_key"]] = requests["postfault_small"]
        selected, rows, missing = stage.select_smoke(episodes, roles)
        self.assertEqual(len(rows), 30)
        self.assertFalse(missing)
        self.assertEqual({e["canonical_base_id"] for e in selected}, expected_groups)

    def test_full_synthetic_staging_preserves_evidence_and_packages_small_role_only(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            config_path = repo / "docs/config/task1_single_sample_v1.json"
            config_path.parent.mkdir(parents=True)
            config_path.write_bytes(
                (stage.REPO / "docs/config/task1_single_sample_v1.json").read_bytes()
            )
            helper = Path(
                "tools/development_audits/fallback_full_development_scoring_v1/score_fallback_full.py"
            )
            (repo / helper).parent.mkdir(parents=True)
            (repo / helper).write_bytes((stage.REPO / helper).read_bytes())
            prepared = repo / fixtures.p.PREPARATION
            prepared.mkdir(parents=True)
            pins = {}
            for key, value in fixtures.p.TRANSFERS.items():
                _, data = fixtures.fixture(key)
                path = prepared / (key + "_recovery_development_transfer_v1.zip")
                a, m = fixtures.archive(path, data)
                pins[key] = (a, m, 6, value[3])
            self.report["input_archive_sha256"] = {
                key + "_recovery_development_transfer_v1.zip": value[0]
                for key, value in pins.items()
            }
            preflight_dir = repo / stage.PREFLIGHT
            preflight_dir.mkdir()
            for name, value in (("summary.json", self.summary), ("report.json", self.report)):
                (preflight_dir / name).write_text(json.dumps(value))
            inputs = {p: p.read_bytes() for p in repo.rglob("*") if p.is_file()}
            original_validator = fixtures.p.validate_plan
            original_loader = stage.load_module

            def validate(data, key, config, eligible):
                return original_validator(data, key, config, eligible, clean_count=1)

            def load(name, path):
                return (
                    fixtures.p
                    if name == "_recovery_smoke_preflight"
                    else original_loader(name, path)
                )

            with (
                patch.object(fixtures.p, "TRANSFERS", pins),
                patch.object(fixtures.p, "validate_plan", side_effect=validate),
                patch.object(stage, "load_module", side_effect=load),
                patch.object(
                    stage.subprocess, "run", return_value=types.SimpleNamespace(returncode=0)
                ),
            ):
                summary = stage.stage(repo)
                self.assertEqual(summary["planned_postfault_small"], 6)
                self.assertEqual(summary["planned_fallback_requests"], 0)
                self.assertEqual(summary["generation_requests_sent"], 0)
                self.assertFalse(summary["dispatch_authorized"])
                archive = repo / stage.OUTPUT / summary["archive"]
                with fixtures.zipfile.ZipFile(archive) as zipped:
                    self.assertEqual(
                        set(zipped.namelist()),
                        {"manifest.json", "requests.json", "episodes.json", "ledger.py"},
                    )
                    rows = json.loads(zipped.read("requests.json"))
                    self.assertTrue(all(r["stage"] == "postfault_small" for r in rows))
                with self.assertRaises(ValueError):
                    stage.stage(repo)
            self.assertTrue(all(p.read_bytes() == raw for p, raw in inputs.items()))


if __name__ == "__main__":
    unittest.main()
