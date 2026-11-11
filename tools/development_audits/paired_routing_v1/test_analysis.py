"""Synthetic checks of policy denominators, tie blocks and diagnostic cuts."""

import unittest
from dataclasses import replace

import analysis

from uqroute_tc.routing.development import PairedCase, SavedOutcome, Usage


def case(key, nll, small=False, fallback=True, *, status="complete", parsed=True):
    return PairedCase(
        key,
        "group" + key,
        "bfcl_v3",
        "official_reference_compliance",
        "primary",
        "development",
        nll,
        SavedOutcome(small, status, parsed, Usage(10, 2, 0.5)),
        SavedOutcome(fallback, "complete", True, Usage(20, 4, 1.0)),
    )


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            case("a", 0.1),
            case("b", 0.1, True, False),
            case("c", 0.9),
            case("d", None, status="invalid_evidence"),
        ]

    def test_frontier_preserves_ties_and_forced_escalation(self):
        points = analysis.frontier(self.rows)
        self.assertEqual([p["fallback_rows"] for p in points], [4, 2, 1])
        self.assertEqual([p["threshold_inclusive"] for p in points], [None, 0.1, 0.9])
        self.assertTrue(all("predictions" not in p for p in points))

    def test_budget_cap_below_forced_minimum_is_infeasible(self):
        view = analysis.budget_view(self.rows, analysis.frontier(self.rows), 0, [1729])
        self.assertFalse(view["feasible"])
        self.assertEqual(view["minimum_fallback_rows"], 1)

    def test_budget_does_not_split_boundary_tie(self):
        view = analysis.budget_view(self.rows, analysis.frontier(self.rows), 0.75, [1729, 1730])
        self.assertEqual(view["allowed_fallback_rows"], 3)
        self.assertEqual(view["gated"]["fallback_rows"], 2)
        self.assertEqual([r["fallback_rows"] for r in view["matched_random"]], [2, 2])

    def test_decimal_cap_floors_exactly(self):
        rows = [case(str(i), 0.1) for i in range(10)]
        view = analysis.budget_view(rows, analysis.frontier(rows), 0.29, [1])
        self.assertEqual(view["allowed_fallback_rows"], 2)
        self.assertEqual(view["gated"]["fallback_rows"], 0)

    def test_cutpoint_does_not_depend_on_outcome_labels(self):
        altered = [
            replace(
                r,
                small=replace(r.small, reference_correct=not r.small.reference_correct),
                fallback=replace(r.fallback, reference_correct=False),
            )
            for r in self.rows
        ]
        a = analysis.budget_view(self.rows, analysis.frontier(self.rows), 0.5, [1])
        b = analysis.budget_view(altered, analysis.frontier(altered), 0.5, [1])
        self.assertEqual(a["gated"]["threshold_inclusive"], b["gated"]["threshold_inclusive"])

    def test_reversed_input_produces_identical_diagnostics(self):
        self.assertEqual(
            analysis.analyze_scope(self.rows, [0.5, 1], [1, 2]),
            analysis.analyze_scope(list(reversed(self.rows)), [0.5, 1], [1, 2]),
        )

    def test_transition_net_gain_equals_always_cascade(self):
        result = analysis.analyze_scope(self.rows, [1], [1])
        counts = result["all_pair_outcomes_small_then_fallback"]
        self.assertEqual(counts, {"CC": 0, "CI": 1, "IC": 3, "II": 0, "unknown": 0})
        base = result["baselines"]
        self.assertEqual(
            base["always_cascade"]["reference_matches_known"]
            - base["small_only"]["reference_matches_known"],
            counts["IC"] - counts["CI"],
        )
        self.assertEqual(base["fallback_only"]["accounting"]["model_calls"], 4)
        self.assertEqual(base["always_cascade"]["accounting"]["model_calls"], 8)

    def test_unknown_labels_and_missing_usage_stay_unavailable(self):
        row = replace(
            self.rows[0],
            small=SavedOutcome(None, "unknown_outcome", False, Usage()),
            small_mean_nll=None,
        )
        result = analysis.analyze_scope([row], [1], [1])
        self.assertEqual(result["all_pair_outcomes_small_then_fallback"]["unknown"], 1)
        base = result["baselines"]["small_only"]
        self.assertIsNone(base["reference_compliance"])
        self.assertIsNone(base["attempt_slots_per_reference_match"])
        self.assertIsNone(base["accounting"]["usage"]["prompt_tokens"]["total"])

    def test_unusable_fallback_is_terminal_without_label_override(self):
        row = replace(
            case("a", 0.1, True, False),
            fallback=SavedOutcome(False, "truncated", True, Usage(20, 4, 1)),
        )
        result = analysis.frontier([row])[0]
        self.assertEqual(result["harms"], 1)
        self.assertEqual(result["unusable_final_outputs"], 1)
        self.assertIsNone(result["small_accepted_error_risk"])

    def test_call_absence_forces_escalation_even_with_low_score(self):
        row = case("a", 0, parsed=False)
        self.assertEqual(analysis.analyze_scope([row], [1], [1])["minimum_fallback_rows"], 1)

    def test_invalid_caps_and_seeds_rejected(self):
        for cap in (True, -1, 1.1, float("nan")):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                analysis.budget_view(self.rows, analysis.frontier(self.rows), cap, [1])
        for seeds in ([], [1, 1], [True], [-1]):
            with self.subTest(seeds=seeds), self.assertRaises(ValueError):
                analysis.budget_view(self.rows, analysis.frontier(self.rows), 1, seeds)

    def test_full_cap_is_always_cascade_and_zero_cap_accepts_all_when_usable(self):
        rows = self.rows[:3]
        points = analysis.frontier(rows)
        full = analysis.budget_view(rows, points, 1, [1])["gated"]
        zero = analysis.budget_view(rows, points, 0, [1])["gated"]
        self.assertEqual(full["fallback_rows"], 3)
        self.assertEqual(zero["fallback_rows"], 0)


if __name__ == "__main__":
    unittest.main()
