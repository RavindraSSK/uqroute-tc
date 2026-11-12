"""Production-built matched contexts and inherited no-retry ledger safeguards."""

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import ledger
import stage

prior = stage.module(
    "_matched_prior_ledger_tests",
    stage.REPO / "tools/development_audits/recovery_smoke_v1/test_smoke.py",
)
gpu_folder = stage.REPO / "tools/development_audits/recovery_gpu_smoke_v1"
with patch.object(sys, "path", [str(gpu_folder), *sys.path]):
    gpu = stage.module("_matched_gpu_fixtures", gpu_folder / "test_gpu_smoke.py")


def paired_rows():
    _, data = prior.fixtures.fixture()
    rows = deepcopy(data["fallback_requests.json"][:2])
    for row in rows:
        row["paired_small_request_id"] = ledger.sha(
            ledger.canonical([row["episode_key"], "postfault_small"]).encode()
        )
    return rows


class FallbackLedgerTests(prior.LedgerTests):
    """Run the tested interruption/HTTP/resume cases under the new model/role."""

    def setUp(self):
        self.rows = paired_rows()
        self.binding = {
            "purpose": "qwen14b-postfault-fallback-matched-smoke",
            "request_inventory_sha256": ledger.sha(ledger.canonical(self.rows).encode()),
            "parent_smoke_archive_sha256": stage.PARENT_SHA,
            "known_parent_small_slots": len(self.rows),
            "collection_mode": "all_matched_smoke_episodes_no_threshold",
            "automatic_retries": 0,
            "held_out_access_enabled": False,
            "main_experiment_ready": False,
        }
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "run"
        self.calls = []

    def test_fallback_stage_or_extra_sampling_field_rejected(self):
        for changed in ("stage", "sampling"):
            rows = paired_rows()
            if changed == "stage":
                rows[0]["stage"] = "postfault_small"
            else:
                rows[0]["request"]["seed"] = 1
                rows[0]["request_sha256"] = ledger.sha(
                    ledger.canonical(rows[0]["request"]).encode()
                )
            with self.assertRaises(ValueError):
                ledger.checked_rows(rows)

    def test_missing_known_parent_authority_rejected_before_model_call(self):
        self.binding["known_parent_small_slots"] = 0
        with self.assertRaises(ValueError):
            self.dispatch()
        self.assertFalse(self.calls)

    def test_wrong_paired_small_identity_rejected(self):
        self.rows[0]["paired_small_request_id"] = "bad"
        with self.assertRaises(ValueError):
            ledger.checked_rows(self.rows)


class StageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        _, self.manifest, self.small, self.episodes = gpu.synthetic_plan(
            Path(self.tmp.name) / "prepared"
        )
        config = json.loads((stage.REPO / "docs/config/task1_single_sample_v1.json").read_text())
        errors = gpu.fixtures.preparer.released_templates(
            (
                stage.REPO / "tools/development_audits/full_development_v1/official_runner.py"
            ).read_text()
        )
        self.roles = {"postfault_small": {}, "postfault_fallback": {}}
        self.records = []
        for small, ep in zip(self.small, self.episodes, strict=True):
            initial = {
                "case_key": ep["initial_case_key"],
                "canonical_base_id": ep["canonical_base_id"],
                "source_file": "clean.jsonl",
                "benchmark": ep["benchmark"],
                "messages_sha256": ep["initial_messages_sha256"],
                "request": deepcopy(small["request"]),
            }
            initial["request"]["messages"] = initial["request"]["messages"][:-2]
            _, roles = gpu.fixtures.preparer.episode(
                initial,
                small["request"]["messages"][-2]["content"],
                [{"name": "api"}],
                "qwen15b",
                ep["fault_type"],
                errors,
                config["models"][3]["model_id"],
                gpu.fixtures.recovery,
            )
            self.assertEqual(roles["postfault_small"], small)
            for role in self.roles:
                self.roles[role][ep["episode_key"]] = roles[role]
            self.records.append(
                {
                    "request_id": small["request_id"],
                    "episode_key": ep["episode_key"],
                    "context_messages_sha256": ep["context_messages_sha256"],
                    "ledger_state": "injected_response_saved",
                    "transition_injected": True,
                    "http_status": 200,
                    "usage": {"prompt_tokens": 10, "completion_tokens": 1},
                    "elapsed_seconds": 1.0,
                    "validation": {"status": "complete", "parser_status": "unparsed_or_no_call"},
                }
            )
        self.full = {"episodes.json": deepcopy(self.episodes)}

    def select(self):
        return stage.matched_requests(
            self.small, self.episodes, self.records, self.full, self.roles
        )

    def test_all_thirty_no_call_parents_retained_and_messages_unchanged(self):
        original = deepcopy((self.small, self.episodes, self.records, self.roles))
        rows, receipts = self.select()
        self.assertEqual(len(rows), 30)
        self.assertEqual(len(receipts), 30)
        self.assertTrue(all(r["request"]["model"] == "Qwen/Qwen2.5-14B-Instruct-AWQ" for r in rows))
        self.assertTrue(all(r["parser_status"] == "unparsed_or_no_call" for r in receipts))
        for small, large in zip(self.small, rows, strict=True):
            self.assertEqual(small["request"]["messages"], large["request"]["messages"])
            self.assertEqual(small["request_id"], large["paired_small_request_id"])
        self.assertEqual(original, (self.small, self.episodes, self.records, self.roles))

    def test_missing_parent_or_unknown_response_cannot_authorize_fallback(self):
        self.records.pop()
        with self.assertRaises(ValueError):
            self.select()

    def test_unresolved_parent_rejected(self):
        self.records[0]["ledger_state"] = "injected_response_unknown_no_resubmit"
        with self.assertRaises(ValueError):
            self.select()

    def test_postfault_small_answer_must_not_be_appended(self):
        row = self.roles["postfault_fallback"][self.small[0]["episode_key"]]
        row["request"]["messages"].append(
            {"role": "assistant", "content": "synthetic later answer"}
        )
        with self.assertRaises(ValueError):
            self.select()

    def test_static_fallback_context_rejected(self):
        row = self.roles["postfault_fallback"][self.small[0]["episode_key"]]
        row["request"]["messages"] = row["request"]["messages"][:-2]
        with self.assertRaises(ValueError):
            self.select()

    def test_new_sampling_settings_or_original_episode_change_rejected(self):
        row = self.roles["postfault_fallback"][self.small[0]["episode_key"]]
        row["request"]["max_tokens"] = 2048
        with self.assertRaises(ValueError):
            self.select()

    def test_original_parent_identity_must_match_full_preparation(self):
        self.full["episodes.json"][0]["fault_type"] = "other"
        with self.assertRaises(ValueError):
            self.select()

    def test_reference_labels_cannot_select_a_subset(self):
        first, _ = self.select()
        for index, row in enumerate(self.records):
            row["official_correctness"] = bool(index % 2)
            row["uncertainty"] = index
        again, _ = self.select()
        self.assertEqual(first, again)

    def context_fixture(self):
        rows, _ = self.select()
        settings = json.loads((stage.REPO / "docs/config/task1_single_sample_v1.json").read_text())[
            "models"
        ][3]
        records = [
            {
                n: r[n]
                for n in ("request_id", "episode_key", "request_sha256", "context_messages_sha256")
            }
            | {"prompt_tokens": 7168, "completion_allowance": 1024, "within_limit": True}
            for r in rows
        ]
        records += [{"request_id": "synthetic_other_" + str(i)} for i in range(720)]
        return (
            rows,
            settings,
            {
                "requests": 750,
                "overflow_requests": 0,
                "model_id": settings["model_id"],
                "tokenizer_revision": settings["tokenizer_revision"],
                "context_limit": 8192,
                "per_request": records,
            },
        )

    def test_selected_fallback_tokenizer_boundary_and_overflow(self):
        rows, settings, context = self.context_fixture()
        self.assertEqual(len(stage.context_checks(rows, context, settings)), 30)
        context["per_request"][0]["prompt_tokens"] = 7169
        with self.assertRaises(ValueError):
            stage.context_checks(rows, context, settings)

    def test_wrong_fallback_tokenizer_revision_rejected(self):
        rows, settings, context = self.context_fixture()
        context["tokenizer_revision"] = "small revision"
        with self.assertRaises(ValueError):
            stage.context_checks(rows, context, settings)

    def test_incomplete_full_context_coverage_rejected(self):
        rows, settings, context = self.context_fixture()
        context["per_request"].pop()
        with self.assertRaises(ValueError):
            stage.context_checks(rows, context, settings)

    def review_fixture(self):
        scored = [
            {
                "request_id": r["request_id"],
                "episode_key": e["episode_key"],
                "canonical_base_id": e["canonical_base_id"],
                "benchmark": e["benchmark"],
                "fault_type": e["fault_type"],
                "panel": "synthetic",
                "initial_reference_match": True,
                "postfault_reference_match": False,
            }
            for r, e in zip(self.small, self.episodes, strict=True)
        ]
        raw = {
            "records.json": json.dumps(scored).encode(),
            "summary.json": b"{}",
            "provenance.json": b"{}",
        }
        provenance = {
            "reference_scoring_recomputed_exactly": True,
            "original_scoring_sha256": {n: ledger.sha(b) for n, b in raw.items()},
        }
        return {"rows": 30, "groups": 5}, deepcopy(scored), provenance, scored, raw

    def test_completed_review_keeps_labels_and_identities(self):
        stage.review_checks(*self.review_fixture())

    def test_changed_review_label_or_scoring_bytes_rejected(self):
        values = list(self.review_fixture())
        values[1][0]["postfault_reference_match"] = True
        with self.assertRaises(ValueError):
            stage.review_checks(*values)
        values = list(self.review_fixture())
        values[4]["records.json"] = b"changed"
        with self.assertRaises(ValueError):
            stage.review_checks(*values)


if __name__ == "__main__":
    unittest.main()
