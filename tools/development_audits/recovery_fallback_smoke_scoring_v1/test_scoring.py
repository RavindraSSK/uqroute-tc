"""Real frozen scoring on synthetic pairs; no private references or model requests."""

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import score_pairs as audit

OLD = audit.REPO / "tools/development_audits/recovery_smoke_scoring_v1"
with patch.object(sys, "path", [str(OLD), *sys.path]):
    fixtures = audit.module("_paired_scoring_test_fixtures", OLD / "test_scoring.py")


class PairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.ScoringTests.setUpClass()
        cls.old = fixtures.ScoringTests()

    def fixture(
        self, small="api()", large="api()", benchmark="bfcl_v3", initial="api()", fault="timeout"
    ):
        values = self.old.fixture(post=small, benchmark=benchmark, initial=initial, fault=fault)
        parent = self.old.score(values)
        big_values = self.old.fixture(post=large, benchmark=benchmark, initial=initial, fault=fault)
        _, roles = self.old.preparer.episode(
            values["initial_request"],
            initial,
            self.old.parser(initial, benchmark),
            "qwen15b",
            fault,
            self.old.errors,
            "Qwen/Qwen2.5-14B-Instruct-AWQ",
            self.old.kernel,
        )
        request = roles["postfault_fallback"]
        request["paired_small_request_id"] = values["request"]["request_id"]
        saved = deepcopy(big_values["saved"])
        saved.update(request_id=request["request_id"], http_status=200)
        return {
            "request": request,
            "small_request": values["request"],
            "episode": values["episode"],
            "saved": saved,
            "response": big_values["response"],
            "initial_request": values["initial_request"],
            "parent_score": parent,
            "reference": values["reference"],
            "member": values["member"],
        }

    def score(self, values):
        return audit.score_pair(
            **values,
            parser=self.old.parser,
            scorer=self.old.scorer,
            workflow=self.old.workflow,
            frozen=self.old.frozen,
            legacy=self.old.legacy,
        )

    def test_matches_remain_reference_diagnostics(self):
        row = self.score(self.fixture())
        self.assertTrue(row["small_reference_match"])
        self.assertTrue(row["fallback_reference_match"])
        self.assertEqual(row["execution_success"], "not_evaluated")
        self.assertEqual(row["semantic_fault_recovery"], "not_evaluated")

    def test_parsed_wrong_fallback_does_not_become_correct(self):
        row = self.score(self.fixture(large="other()"))
        self.assertEqual(row["fallback_parser_status"], "calls")
        self.assertFalse(row["fallback_reference_match"])

    def test_no_call_small_is_retained_and_can_pair_with_a_match(self):
        row = self.score(self.fixture(small="I cannot authenticate."))
        self.assertFalse(row["small_reference_match"])
        self.assertTrue(row["fallback_reference_match"])
        panel = audit.aggregate([row])["panels"]["official_reference_compliance"]
        self.assertEqual(panel["rows"], 1)
        self.assertEqual(panel["small_mismatch_to_fallback_match"], 1)

    def test_fallback_refusal_is_not_semantically_relabeled(self):
        row = self.score(self.fixture(large="I cannot authenticate."))
        self.assertFalse(row["fallback_reference_match"])
        self.assertEqual(row["fallback_parser_status"], "unparsed_or_no_call")
        self.assertEqual(row["semantic_fault_recovery"], "not_evaluated")

    def test_empty_reference_uses_released_no_call_rule(self):
        values = self.fixture(small="No call.", large="No call.")
        values["reference"]["golden_answers"] = []
        original = self.old.fixture(post="No call.")
        original["reference"]["golden_answers"] = []
        values["parent_score"] = self.old.score(original)
        self.assertTrue(self.score(values)["fallback_reference_match"])

    def test_changed_parent_boolean_cannot_contradict_saved_score(self):
        values = self.fixture()
        values["parent_score"]["postfault_reference_match"] = False
        with self.assertRaises(ValueError):
            self.score(values)

    def test_no_input_mutation_and_original_flags_preserved(self):
        values = self.fixture()
        original = deepcopy(values)
        row = self.score(values)
        self.assertEqual(values, original)
        self.assertEqual(row["fallback_score"]["reference_review_flags"], ["synthetic_flag"])
        self.assertFalse(row["fallback_score"]["official_labels_changed"])

    def test_wrong_role_model_or_paired_identity_rejected(self):
        for field, value in (("stage", "postfault_small"), ("paired_small_request_id", "wrong")):
            values = self.fixture()
            values["request"][field] = value
            with self.assertRaises(ValueError):
                self.score(values)
        values = self.fixture()
        values["request"]["request"]["model"] = "small"
        with self.assertRaises(ValueError):
            self.score(values)

    def test_unknown_or_false_injection_cannot_be_imputed(self):
        for value in (False, None):
            values = self.fixture()
            values["saved"]["transition_injected"] = value
            with self.assertRaises(ValueError):
                self.score(values)
        values = self.fixture()
        values["saved"]["ledger_state"] = "injected_response_unknown_no_resubmit"
        with self.assertRaises(ValueError):
            self.score(values)

    def test_http_error_and_changed_saved_identity_rejected(self):
        for field, value in (
            ("http_status", 500),
            ("request_id", "wrong"),
            ("episode_key", "wrong"),
        ):
            values = self.fixture()
            values["saved"][field] = value
            with self.assertRaises(ValueError):
                self.score(values)

    def test_appended_small_answer_or_changed_context_rejected(self):
        for messages in ([], [{"role": "assistant", "content": "later small answer"}]):
            values = self.fixture()
            values["request"]["request"]["messages"] = messages
            with self.assertRaises(ValueError):
                self.score(values)

    def test_changed_sampling_settings_rejected(self):
        values = self.fixture()
        values["request"]["request"]["seed"] = 42
        with self.assertRaises(ValueError):
            self.score(values)

    def test_wrong_original_initial_or_parent_fault_rejected(self):
        for part, field in (
            ("initial_request", "case_key"),
            ("parent_score", "fault_type"),
            ("parent_score", "benchmark"),
        ):
            values = self.fixture()
            values[part][field] = "wrong"
            with self.assertRaises(ValueError):
                self.score(values)

    def test_validation_is_recomputed_from_actual_saved_text(self):
        values = self.fixture()
        values["saved"]["validation"]["parser_status"] = "wrong"
        with self.assertRaises(ValueError):
            self.score(values)

    def test_all_six_faults_preserve_the_reference(self):
        for fault in self.old.errors:
            values = self.fixture(fault=fault)
            original = deepcopy(values["reference"])
            self.assertTrue(self.score(values)["fallback_reference_match"])
            self.assertEqual(values["reference"], original)

    def test_tooleyes_name_match_does_not_establish_argument_correctness(self):
        raw = 'Action: api\nAction Input: {"x": 9}'
        initial = 'Action: api\nAction Input: {"x": 1}'
        values = self.fixture(small=initial, large=raw, initial=initial, benchmark="tooleyes")
        row = self.score(values)
        self.assertEqual(row["panel"], "tooleyes_relevance")
        self.assertTrue(row["fallback_reference_match"])

    def test_four_paired_cells_and_margins_reconcile(self):
        rows = []
        for i, (a, b) in enumerate(((True, True), (True, False), (False, True), (False, False))):
            row = self.score(self.fixture())
            row.update(
                episode_key="synthetic_" + str(i),
                small_reference_match=a,
                fallback_reference_match=b,
            )
            rows.append(row)
        p = audit.aggregate(rows)["panels"]["official_reference_compliance"]
        self.assertEqual(
            [
                p[n]
                for n in (
                    "both_match",
                    "small_match_to_fallback_mismatch",
                    "small_mismatch_to_fallback_match",
                    "both_mismatch",
                )
            ],
            [1, 1, 1, 1],
        )
        self.assertEqual(p["small_postfault_matches"], 2)
        self.assertEqual(p["fallback_postfault_matches"], 2)
        self.assertEqual(
            p["rows"],
            sum(
                p[n]
                for n in (
                    "both_match",
                    "both_mismatch",
                    "small_match_to_fallback_mismatch",
                    "small_mismatch_to_fallback_match",
                )
            ),
        )

    def test_panels_are_never_pooled_and_duplicate_pairs_rejected(self):
        first = self.score(self.fixture())
        second = deepcopy(first)
        second.update(
            episode_key="synthetic_tool", benchmark="tooleyes", panel="tooleyes_relevance"
        )
        summary = audit.aggregate([first, second])
        self.assertEqual([p["rows"] for p in summary["panels"].values()], [1, 1])
        self.assertNotIn("accuracy", summary)
        with self.assertRaises(ValueError):
            audit.aggregate([first, deepcopy(first)])

    def test_missing_outcome_is_not_silently_dropped(self):
        row = self.score(self.fixture())
        row["fallback_reference_match"] = None
        with self.assertRaises(ValueError):
            audit.aggregate([row])

    def test_original_score_bytes_must_match_exactly(self):
        original = {n: b"synthetic" for n in ("records.json", "summary.json", "provenance.json")}
        audit.compare_original_scores(original, deepcopy(original))
        changed = deepcopy(original)
        changed["records.json"] += b" "
        with self.assertRaises(ValueError):
            audit.compare_original_scores(original, changed)

    def test_replay_checkout_imports_do_not_poison_reference_checkout(self):
        from types import SimpleNamespace

        wrong = SimpleNamespace(__file__="synthetic_other_checkout/support.py")
        with patch.dict(sys.modules, {"support": wrong, "workflow": wrong}):
            with audit.workflow_modules():
                workflow, frozen, parser, scorer = self.old.legacy.load_dependencies(
                    audit.REPO, self.old.legacy.policy()
                )
                self.assertTrue(callable(parser))
                self.assertTrue(callable(scorer))
                self.assertIn("parse", frozen)
                self.assertEqual(
                    Path(workflow.__file__).resolve().parent,
                    audit.REPO / "tools/development_audits/corrected_generation_v1",
                )
            self.assertIs(sys.modules["support"], wrong)
            self.assertIs(sys.modules["workflow"], wrong)

    def test_module_scope_restores_cache_after_failure(self):
        sentinel = object()
        with patch.dict(sys.modules, {"support": sentinel}):
            with self.assertRaises(ValueError), audit.workflow_modules():
                sys.modules["support"] = object()
                raise ValueError("synthetic replay failure")
            self.assertIs(sys.modules["support"], sentinel)

    def test_policy_hash_is_pinned(self):
        import hashlib

        raw = (Path(audit.__file__).parent / "policy.json").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), audit.POLICY_SHA)
        self.assertFalse(json.loads(raw)["held_out_access_enabled"])

    def test_report_omits_case_identifiers_and_states_scope(self):
        text = audit.report(audit.aggregate([self.score(self.fixture())]))
        for required in (
            "No execution-success claim",
            "semantically appropriate refusal",
            "1.05",
            "1.1",
            "not 30 independent",
            "Reference matches gained",
        ):
            self.assertIn(required, text)
        self.assertNotIn("clean.jsonl:synthetic", text)
        self.assertNotIn("api()", text)


if __name__ == "__main__":
    unittest.main()
