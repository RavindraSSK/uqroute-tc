"""Policy replay invariants on artificial outcomes, with no benchmark access."""

import inspect
import math
import unittest
from dataclasses import replace

from uqroute_tc.routing.development import (
    PairedCase,
    SavedOutcome,
    Usage,
    evaluate,
    should_escalate,
    threshold_frontier,
)


def outcome(correct=True, status="complete", parsed=True, usage=None):
    return SavedOutcome(correct, status, parsed, usage or Usage(10, 2, 0.5))


def case(key="a", score=0.1, small=True, fallback=True):
    return PairedCase(
        key,
        "group-" + key,
        "fixture",
        "official_reference_compliance",
        "primary",
        "development",
        score,
        outcome(small),
        outcome(fallback),
    )


class GateTests(unittest.TestCase):
    def test_gate_has_no_reference_or_fallback_input(self):
        self.assertEqual(
            set(inspect.signature(should_escalate).parameters),
            {"mean_nll", "evidence_status", "has_parsed_call", "threshold"},
        )

    def test_inclusive_threshold_and_zero_score(self):
        for score, threshold, escalates in (
            (0.1, 0.1, False),
            (0.2, 0.1, True),
            (0, 0, False),
            (0, None, True),
        ):
            self.assertEqual(
                should_escalate(
                    mean_nll=score,
                    threshold=threshold,
                    evidence_status="complete",
                    has_parsed_call=True,
                ),
                escalates,
            )

    def test_missing_invalid_truncated_or_unparsed_forces_fallback(self):
        for score, status, parsed in (
            (None, "complete", True),
            (0, "invalid_evidence", True),
            (0, "truncated", True),
            (None, "unknown_outcome", False),
            (0, "complete", False),
        ):
            self.assertTrue(
                should_escalate(
                    mean_nll=score, threshold=100, evidence_status=status, has_parsed_call=parsed
                )
            )

    def test_reject_nonfinite_negative_boolean_or_wrong_type(self):
        for value in (math.nan, math.inf, -0.1, True, "0.1"):
            for field in ("mean_nll", "threshold"):
                with self.subTest(field=field, value=value):
                    args = dict(
                        mean_nll=0.1, threshold=1, evidence_status="complete", has_parsed_call=True
                    )
                    args[field] = value
                    with self.assertRaises(ValueError):
                        should_escalate(**args)


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            case("a", 0.1, True, False),
            case("b", 0.2, False, True),
            case("c", 0.2, True, True),
            case("d", 0.9, False, False),
        ]

    def test_rescues_harms_and_accounting(self):
        result = evaluate(self.rows, "gated", threshold=0.1)
        self.assertEqual((result["fallback_rows"], result["rescues"], result["harms"]), (3, 1, 0))
        self.assertEqual(result["reference_matches_known"], 3)
        self.assertEqual(result["accounting"]["model_calls"], 7)
        self.assertEqual(result["accounting"]["calls_by_role"], {"small": 4, "fallback": 3})
        self.assertEqual(result["accounting"]["usage"]["prompt_tokens"]["total"], 70)

    def test_fallback_can_harm_and_cannot_be_overridden_using_labels(self):
        result = evaluate(self.rows, "gated")
        self.assertEqual((result["rescues"], result["harms"]), (1, 1))
        self.assertEqual(result["predictions"][0]["output_role"], "fallback")
        self.assertFalse(result["predictions"][0]["reference_correct"])

    def test_fallback_only_and_cascade_have_same_outcomes_different_calls(self):
        only = evaluate(self.rows, "fallback_only")
        cascade = evaluate(self.rows, "always_cascade")
        self.assertEqual(only["predictions"], cascade["predictions"])
        self.assertEqual(only["accounting"]["model_calls"], 4)
        self.assertEqual(cascade["accounting"]["model_calls"], 8)
        self.assertEqual(only["accounting"]["calls_by_role"], {"fallback": 4})
        self.assertFalse(only["paired_comparison_applicable"])

    def test_small_only_does_not_charge_for_cached_fallback(self):
        result = evaluate(self.rows, "small_only")
        self.assertEqual(result["accounting"]["calls_by_role"], {"small": 4})
        self.assertEqual(result["reference_compliance"], 0.5)

    def test_unusable_fallback_is_terminal_and_does_not_relabel_reference(self):
        row = replace(self.rows[0], fallback=outcome(True, "truncated", True))
        result = evaluate([row], "gated")
        self.assertEqual(result["accounting"]["model_calls"], 2)
        self.assertEqual(result["unusable_final_outputs"], 1)
        self.assertTrue(result["predictions"][0]["reference_correct"])

    def test_missing_labels_produce_bounds_not_imputed_failure(self):
        row = replace(self.rows[0], fallback=outcome(None, "unknown_outcome", False, Usage()))
        result = evaluate([row, self.rows[1]], "gated")
        self.assertIsNone(result["reference_compliance"])
        self.assertEqual(result["reference_match_fraction_bounds"], [0.5, 1.0])
        self.assertEqual(result["escalated_pair_labels_unavailable"], 1)
        self.assertIsNone(result["predictions"][0]["reference_correct"])

    def test_missing_usage_does_not_become_zero_or_use_only_successful_attempts(self):
        row = replace(
            self.rows[0], small=outcome(None, "request_error", False, Usage()), small_mean_nll=None
        )
        result = evaluate([row], "gated", threshold=1)
        usage = result["accounting"]["usage"]["completion_tokens"]
        self.assertEqual(usage, {"known_sum": 2, "missing_calls": 1, "total": None})
        self.assertEqual(result["accounting"]["attempt_statuses"]["request_error"], 1)

    def test_empty_acceptance_has_undefined_risk(self):
        self.assertIsNone(evaluate(self.rows, "gated")["small_accepted_error_risk"])

    def test_unknown_small_label_does_not_imply_zero_accepted_error(self):
        row = replace(self.rows[0], small=outcome(None))
        result = evaluate([row], "small_only")
        self.assertIsNone(result["small_accepted_error_risk"])

    def test_frontier_keeps_entire_score_ties_and_selects_nothing(self):
        points = threshold_frontier(self.rows)
        self.assertEqual([p["threshold_inclusive"] for p in points], [None, 0.1, 0.2, 0.9])
        self.assertEqual([p["small_accepted_rows"] for p in points], [0, 1, 3, 4])
        self.assertTrue(all(p["routing_threshold_selected"] is False for p in points))
        self.assertTrue(all(p["held_out_access_enabled"] is False for p in points))

    def test_frontier_ignores_ineligible_boundaries_and_retains_original_denominator(self):
        rows = [
            self.rows[0],
            replace(self.rows[1], small=outcome(False, parsed=False)),
            replace(self.rows[2], small_mean_nll=None),
        ]
        points = threshold_frontier(rows)
        self.assertEqual(len(points), 2)
        self.assertEqual(points[-1]["rows"], 3)
        self.assertEqual(points[-1]["fallback_rows"], 2)

    def test_random_matches_count_independent_of_order_scores_and_labels(self):
        result = evaluate(self.rows, "matched_random", random_fallback_count=2, random_seed=1729)
        modified = [
            replace(r, small=outcome(not r.small.reference_correct), small_mean_nll=100)
            for r in reversed(self.rows)
        ]
        other = evaluate(modified, "matched_random", random_fallback_count=2, random_seed=1729)

        def chosen(r):
            return [p["case_key"] for p in r["predictions"] if p["output_role"] == "fallback"]

        self.assertEqual(chosen(result), chosen(other))
        self.assertEqual(result["fallback_rows"], 2)
        self.assertEqual(result["accounting"]["model_calls"], 6)

    def test_gate_choices_independent_of_both_models_reference_labels(self):
        before = evaluate(self.rows, "gated", threshold=0.1)
        modified = [replace(r, small=outcome(False), fallback=outcome(True)) for r in self.rows]
        after = evaluate(modified, "gated", threshold=0.1)
        self.assertEqual(
            [p["output_role"] for p in before["predictions"]],
            [p["output_role"] for p in after["predictions"]],
        )

    def test_invalid_replay_inputs_fail(self):
        for rows in (
            [],
            self.rows + [self.rows[0]],
            [self.rows[0], replace(self.rows[1], panel="tooleyes_relevance")],
            [self.rows[0], replace(self.rows[1], population="sensitivity_only")],
        ):
            with self.assertRaises(ValueError):
                evaluate(rows, "gated")

    def test_held_out_and_unattempted_or_fabricated_outcomes_rejected(self):
        with self.assertRaises(ValueError):
            replace(self.rows[0], split="test")
        with self.assertRaises(ValueError):
            outcome(True, "unknown_outcome", False)
        with self.assertRaises(ValueError):
            outcome(None, "unattempted", False)
        with self.assertRaises(ValueError):
            replace(self.rows[0], small_mean_nll=0.1, small=outcome(False, "truncated"))

    def test_invalid_labels_usage_and_policy_arguments_rejected(self):
        with self.assertRaises(ValueError):
            outcome(1)
        for kwargs in (
            {"prompt_tokens": True},
            {"completion_tokens": -1},
            {"elapsed_seconds": math.nan},
        ):
            with self.assertRaises(ValueError):
                Usage(**kwargs)
        for policy, kwargs in (
            ("oracle", {}),
            ("small_only", {"threshold": 0.1}),
            ("gated", {"random_seed": 1729}),
            ("matched_random", {"random_fallback_count": -1, "random_seed": 1729}),
            ("matched_random", {"random_fallback_count": 2, "random_seed": True}),
        ):
            with self.subTest(policy=policy, kwargs=kwargs), self.assertRaises(ValueError):
                evaluate(self.rows, policy, **kwargs)


if __name__ == "__main__":
    unittest.main()
