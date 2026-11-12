"""Frozen-parser transitions and endpoint joins without outcome relabeling."""

import hashlib
import json
import unittest
from copy import deepcopy

import review_pairs as audit


class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client = audit.module(
            "_review_test_client",
            audit.REPO / "tools/development_audits/recovery_gpu_fallback_smoke_v1/client.py",
        )
        scoring = audit.module(
            "_review_test_scoring",
            audit.REPO
            / "tools/development_audits/recovery_fallback_smoke_scoring_v1/score_pairs.py",
        )
        with scoring.workflow_modules():
            support, _ = client.dependencies(audit.REPO)
            cls.frozen = support.methods(audit.REPO)
        cls.old = audit.module(
            "_review_test_structure",
            audit.REPO / "tools/development_audits/recovery_smoke_review_v1/review.py",
        )

    def parse(self, text, benchmark="bfcl_v3"):
        return self.frozen["parse"](text, benchmark)

    def row(self, small="api()", fallback="api()", a=True, b=True, benchmark="bfcl_v3"):
        left, right = self.parse(small, benchmark), self.parse(fallback, benchmark)
        row = {
            "episode_key": "synthetic",
            "canonical_base_id": "synthetic_group",
            "benchmark": benchmark,
            "fault_type": "timeout",
            "panel": "tooleyes_relevance"
            if benchmark == "tooleyes"
            else "official_reference_compliance",
            "small_reference_match": a,
            "fallback_reference_match": b,
            "small_parser_status": left.status,
            "fallback_parser_status": right.status,
        }
        row["structure"] = audit.describe(
            row, self.parse("api()", benchmark), left, right, self.old.behaviour
        )
        return row

    def test_all_six_transition_buckets(self):
        examples = [
            ("No call.", "No call.", "neither_parsed"),
            ("No call.", "api()", "small_no_call_to_fallback_call"),
            ("api()", "No call.", "small_call_to_fallback_no_call"),
            ("api()", "api()", "identical_calls"),
            ("api(x=1)", "api(x=2)", "same_names_changed_arguments"),
            ("api()", "other()", "changed_names"),
        ]
        for small, fallback, expected in examples:
            self.assertEqual(audit.transition(self.parse(small), self.parse(fallback)), expected)

    def test_argument_order_is_canonical_but_types_remain_distinct(self):
        self.assertEqual(
            audit.transition(self.parse("api(x=1,y=2)"), self.parse("api(y=2,x=1)")),
            "identical_calls",
        )
        self.assertEqual(
            audit.transition(self.parse("api(x=1)"), self.parse('api(x="1")')),
            "same_names_changed_arguments",
        )

    def test_call_sequence_order_change_is_visible(self):
        self.assertEqual(
            audit.transition(self.parse("api(); other()"), self.parse("other(); api()")),
            "changed_names",
        )

    def test_labels_do_not_change_structural_bucket(self):
        for a, b in ((True, True), (False, True), (True, False), (False, False)):
            row = self.row(small="No call.", a=a, b=b)
            self.assertEqual(row["structure"]["transition"], "small_no_call_to_fallback_call")

    def test_four_reference_cells_reconcile(self):
        rows = []
        for i, (a, b) in enumerate(((True, True), (False, True), (True, False), (False, False))):
            row = self.row(a=a, b=b)
            row["episode_key"] = "synthetic_" + str(i)
            rows.append(row)
        counts = audit.summarize(rows)["reference_pairs"]
        self.assertEqual(set(counts.values()), {1})
        self.assertEqual(sum(counts.values()), 4)

    def test_unknown_outcome_is_not_imputed(self):
        row = self.row()
        row["fallback_reference_match"] = None
        with self.assertRaises(ValueError):
            audit.outcome(row)

    def test_changed_parser_status_rejected(self):
        row = self.row()
        row["small_parser_status"] = "wrong"
        with self.assertRaises(ValueError):
            audit.describe(
                row,
                self.parse("api()"),
                self.parse("api()"),
                self.parse("api()"),
                self.old.behaviour,
            )

    def test_duplicate_pair_rejected(self):
        row = self.row()
        with self.assertRaises(ValueError):
            audit.summarize([row, deepcopy(row)])

    def test_panels_are_separate(self):
        first = self.row()
        second = self.row(benchmark="tooleyes")
        second["episode_key"] = "synthetic_tooleyes"
        result = audit.summarize([first, second])
        self.assertEqual([r["rows"] for r in result["panels"].values()], [1, 1])
        self.assertNotIn("accuracy", result)

    def test_control_names_are_literal_and_benchmark_scoped(self):
        control = self.parse("Action: finish\nAction Input: {}", "tooleyes")
        row = self.row(benchmark="tooleyes")
        result = audit.describe(
            row,
            control,
            self.parse("api()", "tooleyes"),
            self.parse("api()", "tooleyes"),
            self.old.behaviour,
        )
        self.assertEqual(
            result["initial_to_fallback"]["initial_first_control_name_literal"], "finish"
        )
        self.assertIsNone(
            self.old.behaviour(self.parse("finish()"), self.parse("api()"), "bfcl_v3")[
                "initial_first_control_name_literal"
            ]
        )

    def test_removed_keys_and_empty_string_changes_are_structural(self):
        before = self.parse('api(x="",y=1)')
        after = self.parse('api(x="synthetic")')
        result = self.old.behaviour(before, after, "bfcl_v3")
        self.assertEqual(result["removed_top_level_argument_keys"], 1)
        self.assertEqual(result["empty_string_argument_replacements"], 1)

    def test_original_rows_unchanged_and_report_contains_no_task_text(self):
        rows = [self.row()]
        before = deepcopy(rows)
        summary = audit.summarize(rows)
        text = audit.report(summary)
        self.assertEqual(rows, before)
        self.assertNotIn("api()", text)
        self.assertNotIn("synthetic_group", text)
        self.assertIn("PRIVATE_REVIEW.md", text)
        self.assertFalse(summary["labels_changed"])
        self.assertFalse(summary["policy_evaluation"])
        self.assertEqual(summary["rows_excluded"], 0)

    def test_private_fence_cannot_be_closed_by_model_text(self):
        text = "synthetic ``` output ```` text"
        fenced = self.old.fence(text)
        self.assertTrue(fenced.startswith("`````text\n"))

    def test_policy_is_pinned_and_retains_owner_results(self):
        raw = (audit.HERE / "policy.json").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), audit.POLICY_SHA)
        policy = json.loads(raw)
        self.assertEqual(
            policy["expected_panels"]["official_reference_compliance"][
                "fallback_postfault_matches"
            ],
            10,
        )
        self.assertFalse(policy["labels_changed"])


if __name__ == "__main__":
    unittest.main()
