"""Synthetic episodes with the real frozen parser and deterministic reference scorer."""

import json
import sys
import unittest
from copy import deepcopy

import score_smoke as audit


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = audit.module(
            "_smoke_test_legacy",
            audit.REPO / "tools/development_audits/full_development_scoring_v1/score_full.py",
        )
        cls.workflow, cls.frozen, parser, scorer = cls.legacy.load_dependencies(
            audit.REPO, cls.legacy.policy()
        )
        cls.parser, cls.scorer = staticmethod(parser), staticmethod(scorer)
        cls.preparer = audit.module(
            "_smoke_test_prepare",
            audit.REPO / "tools/development_audits/recovery_development_v1/prepare.py",
        )
        cls.errors = cls.preparer.released_templates(
            (
                audit.REPO / "tools/development_audits/full_development_v1/official_runner.py"
            ).read_text()
        )
        sys.path.insert(0, str(audit.REPO / "src"))
        from uqroute_tc.routing import recovery

        cls.kernel = recovery

    def fixture(self, post="api()", benchmark="bfcl_v3", initial="api()", fault="timeout"):
        messages = [
            {"role": "system", "content": "synthetic tools"},
            {"role": "user", "content": "synthetic task"},
        ]
        cfg = json.loads((audit.REPO / "docs/config/task1_single_sample_v1.json").read_text())
        candidate = {
            "case_key": "clean.jsonl:synthetic",
            "canonical_base_id": "synthetic",
            "benchmark": benchmark,
            "messages": messages,
            "tools": [],
            "messages_sha256": self.kernel.messages_sha256(messages),
        }
        request = self.workflow.make_requests(
            [candidate],
            {candidate["case_key"]: {"source_file": "clean.jsonl"}},
            cfg["models"][0],
            cfg["single_sample"],
        )[0]
        calls = self.parser(initial, benchmark)
        episode, roles = self.preparer.episode(
            request,
            initial,
            calls,
            "qwen15b",
            fault,
            self.errors,
            cfg["models"][3]["model_id"],
            self.kernel,
        )

        def response(text):
            return {
                "choices": [
                    {
                        "message": {"content": text},
                        "finish_reason": "stop",
                        "logprobs": {
                            "content": [
                                {
                                    "token": text,
                                    "bytes": list(text.encode()),
                                    "logprob": -0.25,
                                    "top_logprobs": [],
                                }
                            ]
                        },
                    }
                ]
            }

        before, after = response(initial), response(post)
        before_saved = self.workflow.evaluate(before, benchmark, self.frozen)
        saved = {
            "request_id": roles["postfault_small"]["request_id"],
            "episode_key": episode["episode_key"],
            "transition_injected": True,
            "ledger_state": "injected_response_saved",
            "context_messages_sha256": episode["context_messages_sha256"],
            "validation": self.workflow.evaluate(after, benchmark, self.frozen),
        }
        ref = {
            "case_key": request["case_key"],
            "eval_config": {"method": "exact_match"},
            "golden_answers": [{"name": "api", "parameters": {}}],
        }
        if benchmark == "tooleyes":
            ref["eval_config"] = {"method": "gpt_judge", "metrics": ["relevance"]}
        member = {
            "case_key": request["case_key"],
            "canonical_base_id": "synthetic",
            "benchmark": benchmark,
            "construction_status": "candidate",
            "split": "development",
            "population": "primary",
            "source_file": "clean.jsonl",
            "corrected_messages_sha256": request["messages_sha256"],
            "reference_audit_status": "completed_bounded_signals_only",
            "reference_audit": {
                "changes_official_labels": False,
                "excluded": False,
                "review_flags": ["synthetic_flag"],
                "review_status": "synthetic",
                "objective_detection": {},
                "reward_kind": None,
            },
        }
        return {
            "request": roles["postfault_small"],
            "episode": episode,
            "saved": saved,
            "response": after,
            "initial_request": request,
            "initial_response": before,
            "initial_saved": before_saved,
            "reference": ref,
            "member": member,
        }

    def score(self, values):
        return audit.score_episode(
            **values,
            parser=self.parser,
            scorer=self.scorer,
            workflow=self.workflow,
            frozen=self.frozen,
            legacy=self.legacy,
            kernel=self.kernel,
            errors=self.errors,
        )

    def test_matching_call_remains_match_without_execution_claim(self):
        row = self.score(self.fixture())
        self.assertTrue(row["initial_reference_match"])
        self.assertTrue(row["postfault_reference_match"])
        self.assertEqual(row["execution_success"], "not_evaluated")

    def test_parsed_wrong_call_is_not_correct(self):
        row = self.score(self.fixture(post="other()"))
        self.assertEqual(row["canonical_parser_status"], "calls")
        self.assertFalse(row["postfault_reference_match"])

    def test_unparsed_refusal_is_preserved_and_scored_by_released_rule(self):
        row = self.score(self.fixture(post="I cannot authenticate."))
        self.assertEqual(row["canonical_parser_status"], "unparsed_or_no_call")
        self.assertFalse(row["postfault_reference_match"])
        self.assertEqual(row["semantic_fault_recovery"], "not_evaluated")

    def test_empty_reference_does_not_force_no_call_to_failure(self):
        values = self.fixture(post="No call.")
        values["reference"]["golden_answers"] = []
        self.assertTrue(self.score(values)["postfault_reference_match"])

    def test_reference_flags_and_labels_unchanged(self):
        values = self.fixture()
        before = deepcopy(values)
        row = self.score(values)
        self.assertEqual(values, before)
        self.assertEqual(row["postfault_score"]["reference_review_flags"], ["synthetic_flag"])
        self.assertFalse(row["postfault_score"]["official_labels_changed"])

    def test_wrong_fault_context_rejected(self):
        values = self.fixture()
        values["request"]["request"]["messages"][-1]["content"] += "changed"
        with self.assertRaises(ValueError):
            self.score(values)

    def test_false_injection_is_not_scored_as_failure(self):
        values = self.fixture()
        values["saved"]["transition_injected"] = False
        with self.assertRaises(ValueError):
            self.score(values)

    def test_unknown_injection_is_not_imputed(self):
        values = self.fixture()
        values["saved"]["transition_injected"] = None
        with self.assertRaises(ValueError):
            self.score(values)

    def test_unknown_response_is_not_imputed(self):
        values = self.fixture()
        values["saved"]["ledger_state"] = "injected_response_unknown_no_resubmit"
        with self.assertRaises(ValueError):
            self.score(values)

    def test_wrong_initial_identity_or_model_role_rejected(self):
        for field, value in (("initial_case_key", "wrong"), ("benchmark", "wrong")):
            values = self.fixture()
            values["episode"][field] = value
            with self.assertRaises(ValueError):
                self.score(values)
        values = self.fixture()
        values["request"]["stage"] = "postfault_fallback"
        with self.assertRaises(ValueError):
            self.score(values)

    def test_all_six_faults_retain_the_same_reference(self):
        for fault in self.errors:
            values = self.fixture(fault=fault)
            before = deepcopy(values["reference"])
            self.assertTrue(self.score(values)["postfault_reference_match"])
            self.assertEqual(values["reference"], before)

    def test_tooleyes_name_relevance_is_separate_from_arguments(self):
        raw = 'Action: api\nAction Input: {"x": 9}'
        initial = 'Action: api\nAction Input: {"x": 1}'
        values = self.fixture(post=raw, initial=initial, benchmark="tooleyes")
        values["reference"]["golden_answers"][0]["parameters"] = {"x": 1}
        row = self.score(values)
        self.assertEqual(row["panel"], "tooleyes_relevance")
        self.assertTrue(row["postfault_reference_match"])

    def test_aggregate_never_pools_tooleyes_with_reference_panel(self):
        primary = self.score(self.fixture())
        relevance = deepcopy(primary)
        relevance.update(panel="tooleyes_relevance", canonical_base_id="synthetic_relevance")
        summary = audit.aggregate([primary, relevance])
        self.assertEqual(summary["panels"]["official_reference_compliance"]["rows"], 1)
        self.assertEqual(summary["panels"]["tooleyes_relevance"]["rows"], 1)
        self.assertNotIn("accuracy", summary)

    def test_paired_changes_reconcile(self):
        rows = []
        for a, b in ((True, True), (True, False), (False, True), (False, False)):
            row = self.score(self.fixture())
            row.update(initial_reference_match=a, postfault_reference_match=b)
            rows.append(row)
        panel = audit.aggregate(rows)["panels"]["official_reference_compliance"]
        self.assertEqual(
            [
                panel[n]
                for n in ("both_match", "match_to_mismatch", "mismatch_to_match", "both_mismatch")
            ],
            [1, 1, 1, 1],
        )

    def test_released_transition_writer_copies_original_reference_and_config(self):
        source = (
            audit.REPO / "tools/development_audits/full_development_v1/official_runner.py"
        ).read_text()
        audit.check_transition_writer(source)
        with self.assertRaises(ValueError):
            audit.check_transition_writer(
                source.replace('"golden_answers": s["golden_answers"]', '"golden_answers": []')
            )

    def test_report_states_semantic_and_dependency_limits(self):
        text = audit.report(audit.aggregate([self.score(self.fixture())]))
        self.assertIn("No execution-success claim", text)
        self.assertIn("semantically appropriate refusal", text)
        self.assertIn("not 30 independent initial generations", text)


if __name__ == "__main__":
    unittest.main()
