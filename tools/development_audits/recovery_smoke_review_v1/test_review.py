"""Structural review checks using the actual frozen canonical parser."""

import unittest

import review


class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        support = review.module(
            "_review_test_support",
            review.REPO / "tools/development_audits/corrected_generation_v1/support.py",
        )
        cls.parse = staticmethod(support.methods(review.REPO)["parse"])

    def describe(self, initial, after, benchmark="bfcl_v3"):
        return review.behaviour(
            self.parse(initial, benchmark), self.parse(after, benchmark), benchmark
        )

    def row(self, initial="api()", after="other()", panel="official_reference_compliance"):
        return {
            "canonical_base_id": "synthetic",
            "fault_type": "timeout",
            "panel": panel,
            "initial_reference_match": True,
            "postfault_reference_match": False,
            "behaviour": self.describe(initial, after),
        }

    def test_equivalent_dictionary_order_is_unchanged(self):
        result = self.describe("api(a=1, b=2)", "api(b=2, a=1)")
        self.assertEqual(result["bucket"], "identical_canonical_calls")

    def test_changed_values_with_same_names_are_separate(self):
        self.assertEqual(
            self.describe("api(x=1)", "api(x=2)")["bucket"], "same_name_sequence_changed_arguments"
        )

    def test_removed_keys_counted_without_schema_or_correctness_label(self):
        result = self.describe("api(a=1, b=2)", "api(a=1)")
        self.assertEqual(result["removed_top_level_argument_keys"], 1)
        self.assertNotIn("correct", result)

    def test_changed_tool_names_and_call_order_remain_visible(self):
        self.assertEqual(self.describe("api()", "other()")["bucket"], "changed_name_sequence")
        self.assertEqual(
            self.describe("[api(), other()]", "[other(), api()]")["bucket"], "changed_name_sequence"
        )

    def test_no_call_prose_and_explicit_empty_call_list_not_relabelled(self):
        for text in ("Please retry later.", "[]"):
            result = self.describe("api()", text)
            self.assertEqual(result["bucket"], "no_parsed_postfault_call")
            self.assertIsNone(result["removed_top_level_argument_keys"])

    def test_initial_control_literal_is_benchmark_scoped(self):
        raw = "Thought: synthetic\nAction: finish\nAction Input: {}"
        result = self.describe(raw, raw, "rotbench")
        self.assertEqual(result["initial_first_control_name_literal"], "finish")
        self.assertTrue(result["postfault_has_control_name_literal"])
        self.assertIsNone(
            self.describe("finish()", "finish()")["initial_first_control_name_literal"]
        )

    def test_postfault_control_literal_is_not_semantic_success(self):
        result = self.describe(
            "Action: api\nAction Input: {}",
            'Action: ask_to_user\nAction Input: {"question":"synthetic"}',
            "tooleyes",
        )
        self.assertTrue(result["postfault_has_control_name_literal"])
        self.assertNotIn("execution_success", result)

    def test_empty_string_replacement_is_structure_only(self):
        result = self.describe('api(key="")', 'api(key="synthetic-placeholder")')
        self.assertEqual(result["empty_string_argument_replacements"], 1)
        self.assertNotIn("valid_credentials", result)

    def test_argument_types_are_not_coerced(self):
        result = self.describe("api(x=True)", "api(x=1)")
        self.assertEqual(result["bucket"], "same_name_sequence_changed_arguments")

    def test_reference_labels_cannot_change_structural_bucket(self):
        row = self.row()
        first = review.summarize([row])["buckets"]
        row.update(initial_reference_match=False, postfault_reference_match=True)
        self.assertEqual(first, review.summarize([row])["buckets"])

    def test_panels_remain_separate(self):
        rows = [self.row(), self.row(panel="tooleyes_relevance")]
        summary = review.summarize(rows)
        self.assertEqual(summary["panels"]["official_reference_compliance"]["rows"], 1)
        self.assertEqual(summary["panels"]["tooleyes_relevance"]["rows"], 1)
        self.assertFalse(summary["labels_changed"])
        self.assertEqual(summary["rows_excluded"], 0)

    def test_reference_matches_with_removed_keys_are_counted_without_repair(self):
        row = self.row("api(a=1,b=2)", "api(a=1)")
        row["postfault_reference_match"] = True
        result = review.summarize([row])["panels"]["official_reference_compliance"]
        self.assertEqual(result["matching_rows_with_removed_argument_keys"], 1)
        self.assertEqual(result["postfault_reference_matches"], 1)

    def test_private_fence_preserves_literal_backticks(self):
        text = "synthetic ``` and ````` markers"
        value = review.fence(text)
        self.assertTrue(value.startswith("``````text\n"))
        self.assertTrue(value.endswith("\n``````\n"))
        self.assertIn(text, value)

    def test_aggregate_report_omits_identifiers_and_carries_scope_limits(self):
        row = self.row()
        row["request_id"] = "PRIVATE_SYNTHETIC_ID"
        text = review.report(review.summarize([row]))
        self.assertNotIn("PRIVATE_SYNTHETIC_ID", text)
        self.assertIn("Do not drop control-action episodes", text)
        self.assertIn("no semantic correctness is assigned", text)


if __name__ == "__main__":
    unittest.main()
