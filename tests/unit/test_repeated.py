"""Disagreement separates syntax changes from tool-call changes."""

import math
import unittest

from uqroute_tc.uncertainty.repeated import cluster_scores, repeated_scores


class RepeatedTests(unittest.TestCase):
    @staticmethod
    def parse(raw, _benchmark):
        if raw == "BAD":
            raise ValueError("parser failed")
        if raw.startswith("tool"):
            return [{"name": "weather", "parameters": {"days": int(raw[-1])}}]
        return []

    def test_ten_equivalent_calls_have_zero_canonical_disagreement(self):
        outputs = ["tool a 2", "tool b 2"] * 5
        scores = repeated_scores(outputs, "bfcl_v3", self.parse)
        self.assertEqual(scores.canonical.cluster_sizes, (10,))
        self.assertEqual(scores.canonical.disagreement, 0)
        self.assertEqual(scores.canonical.entropy_nats, 0)
        self.assertEqual(scores.exact_string.cluster_sizes, (5, 5))
        self.assertAlmostEqual(scores.exact_string.entropy_nats, math.log(2))

    def test_nine_one_split_and_failure_do_not_drop_samples(self):
        outputs = ["tool a 2"] * 9 + ["BAD"]
        scores = repeated_scores(outputs, "bfcl_v3", self.parse)
        self.assertEqual(scores.canonical.cluster_sizes, (9, 1))
        self.assertAlmostEqual(scores.canonical.disagreement, .1)
        self.assertAlmostEqual(scores.canonical.entropy_nats,
                               -.9 * math.log(.9) - .1 * math.log(.1))
        self.assertEqual(scores.statuses[-1], "parse_failure")

    def test_empty_and_ambiguous_no_call_are_distinct(self):
        outputs = ["tool a 2"] * 7 + ["", "[]", "Cannot call a tool"]
        scores = repeated_scores(outputs, "bfcl_v3", self.parse)
        self.assertEqual(scores.canonical.cluster_sizes, (7, 1, 1, 1))
        self.assertEqual(scores.statuses[-3:],
                         ("empty", "no_calls", "unparsed_or_no_call"))

    def test_wrong_sample_count_fails_before_scoring(self):
        with self.assertRaisesRegex(ValueError, "exactly 10"):
            repeated_scores(["tool a 2"] * 9, "bfcl_v3", self.parse)
        with self.assertRaisesRegex(ValueError, "exactly 10"):
            cluster_scores([])


if __name__ == "__main__":
    unittest.main()
