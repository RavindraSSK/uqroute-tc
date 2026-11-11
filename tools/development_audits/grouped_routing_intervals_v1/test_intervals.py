"""Synthetic paired resampling, denominator and missingness checks."""

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import intervals
import run_intervals

from uqroute_tc.routing.development import PairedCase, SavedOutcome, Usage, evaluate


def row(i):
    return PairedCase(
        str(i),
        "group" + str(i),
        "bfcl_v3",
        "official_reference_compliance",
        "primary",
        "development",
        0.1,
        SavedOutcome(False, "complete", True, Usage(10, 2, 0.5)),
        SavedOutcome(True, "complete", True, Usage(20, 4, 1)),
    )


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.rows = [row(i) for i in range(12)]
        self.rows = [
            replace(r, benchmark="apibank") if i < 6 else r for i, r in enumerate(self.rows)
        ]

    def test_group_counts_preserved_within_each_benchmark(self):
        plan = intervals.make_plan(self.rows, 30, 1729)
        for draw in plan["draws"]:
            counts = {
                b: sum(w for i, w in draw if plan["groups"][i][0] == b)
                for b in plan["strata_group_counts"]
            }
            self.assertEqual(counts, {"apibank": 6, "bfcl_v3": 6})

    def test_plan_is_stable_under_case_order_and_label_changes(self):
        changed = [
            replace(r, small=replace(r.small, reference_correct=True)) for r in reversed(self.rows)
        ]
        self.assertEqual(intervals.make_plan(changed, 30, 1), intervals.make_plan(self.rows, 30, 1))

    def test_related_variants_remain_one_resampling_unit(self):
        variants = self.rows + [replace(r, case_key="variant" + r.case_key) for r in self.rows]
        plan = intervals.make_plan(variants, 30, 1)
        predictions = evaluate(variants, "always_cascade")["predictions"]
        groups, vectors, _ = intervals.group_vectors(variants, predictions, "fallback_only")
        self.assertEqual(len(groups), 12)
        self.assertTrue(all(v[0] == 2 for v in vectors))
        self.assertTrue(
            all(sum(vectors[i][0] * w for i, w in draw) == 24 for draw in plan["draws"])
        )

    def test_invalid_seed_and_replicate_count_rejected(self):
        for count, seed in ((1, 1), (True, 1), (20, -1), (20, True)):
            with self.subTest(count=count, seed=seed), self.assertRaises(ValueError):
                intervals.make_plan(self.rows, count, seed)


class ContrastTests(unittest.TestCase):
    def setUp(self):
        self.rows = [row(i) for i in range(12)]
        self.predictions = evaluate(self.rows, "always_cascade")["predictions"]
        self.plan = intervals.make_plan(self.rows, 60, 1729)

    def estimate(self, baseline="fallback_only"):
        return intervals.contrast(self.rows, self.predictions, baseline, self.plan)

    def test_hand_computed_call_time_and_token_differences(self):
        result = self.estimate()["metrics"]
        expected = {
            "match_fraction_difference": 0,
            "unusable_fraction_difference": 0,
            "calls_per_match_difference": 1,
            "request_seconds_per_match_difference": 0.5,
            "prompt_tokens_per_match_difference": 10,
            "completion_tokens_per_match_difference": 2,
        }
        for name, point in expected.items():
            with self.subTest(metric=name):
                self.assertEqual(result[name]["point"], point)
                self.assertEqual(result[name]["interval_95_percentile"], [point, point])
                self.assertEqual(result[name]["valid_replicates"], 60)

    def test_matched_correctness_difference_has_expected_sign(self):
        result = self.estimate("small_only")["metrics"]["match_fraction_difference"]
        self.assertEqual(result["point"], 1)
        self.assertEqual(result["interval_95_percentile"], [1, 1])

    def test_zero_match_denominator_is_unavailable(self):
        result = self.estimate("small_only")["metrics"]["calls_per_match_difference"]
        self.assertIsNone(result["point"])
        self.assertEqual(result["point_unavailable_reason"], "zero_reference_match_denominator")
        self.assertEqual(result["unavailable_reason"], "insufficient_valid_replicates")
        self.assertEqual(result["undefined_replicates"], 60)

    def test_identical_gate_and_small_baseline_produce_zero_differences(self):
        rows = [replace(r, small=replace(r.small, reference_correct=True)) for r in self.rows]
        predictions = evaluate(rows, "small_only")["predictions"]
        result = intervals.contrast(rows, predictions, "small_only", self.plan)
        self.assertTrue(all(metric["point"] == 0 for metric in result["metrics"].values()))

    def test_unknown_label_withholds_affected_metrics_without_dropping_case(self):
        unknown = replace(
            self.rows[0],
            small=SavedOutcome(None, "unknown_outcome", False, Usage()),
            small_mean_nll=None,
        )
        rows = [unknown] + self.rows[1:]
        predictions = evaluate(rows, "always_cascade")["predictions"]
        result = intervals.contrast(rows, predictions, "small_only", self.plan)
        self.assertEqual(result["rows"], 12)
        self.assertIsNone(result["metrics"]["match_fraction_difference"]["point"])
        self.assertEqual(
            result["metrics"]["match_fraction_difference"]["unavailable_reason"],
            "unknown_reference_outcome",
        )
        self.assertIsNotNone(result["metrics"]["unusable_fraction_difference"]["point"])

    def test_missing_usage_withholds_only_affected_usage_metric(self):
        rows = [
            replace(self.rows[0], small=replace(self.rows[0].small, usage=Usage(None, 2, 0.5)))
        ] + self.rows[1:]
        predictions = evaluate(rows, "always_cascade")["predictions"]
        result = intervals.contrast(rows, predictions, "fallback_only", self.plan)["metrics"]
        self.assertIsNone(result["prompt_tokens_per_match_difference"]["point"])
        self.assertEqual(
            result["prompt_tokens_per_match_difference"]["unavailable_reason"],
            "missing_prompt_tokens",
        )
        self.assertEqual(result["request_seconds_per_match_difference"]["point"], 0.5)
        self.assertEqual(result["match_fraction_difference"]["point"], 0)

    def test_low_group_count_retains_point_but_withholds_interval(self):
        rows = self.rows[:9]
        result = intervals.contrast(
            rows,
            evaluate(rows, "always_cascade")["predictions"],
            "fallback_only",
            intervals.make_plan(rows, 60, 1),
        )
        metric = result["metrics"]["calls_per_match_difference"]
        self.assertEqual(metric["point"], 1)
        self.assertIsNone(metric["interval_95_percentile"])
        self.assertEqual(metric["attempted_replicates"], 0)
        self.assertEqual(metric["unavailable_reason"], "fewer_than_minimum_canonical_groups")

    def test_incomplete_and_duplicate_predictions_rejected(self):
        for predictions in (self.predictions[:-1], self.predictions + [self.predictions[0]]):
            with self.assertRaisesRegex(ValueError, "Complete unique OOF"):
                intervals.contrast(self.rows, predictions, "fallback_only", self.plan)

    def test_mismatched_prediction_label_or_usability_rejected(self):
        for name in ("reference_correct", "usable"):
            predictions = [dict(p) for p in self.predictions]
            predictions[0][name] = False
            with self.subTest(name=name), self.assertRaises(ValueError):
                intervals.contrast(self.rows, predictions, "fallback_only", self.plan)

    def test_invalid_output_role_rejected(self):
        predictions = [dict(p) for p in self.predictions]
        predictions[0]["output_role"] = "unknown"
        with self.assertRaises(ValueError):
            intervals.contrast(self.rows, predictions, "fallback_only", self.plan)

    def test_incompatible_group_plan_rejected(self):
        plan = intervals.make_plan(self.rows[:-1], 60, 1)
        with self.assertRaisesRegex(ValueError, "Shared bootstrap plan"):
            intervals.contrast(self.rows, self.predictions, "fallback_only", plan)

    def test_invalid_resampling_weights_rejected(self):
        plan = intervals.make_plan(self.rows, 60, 1)
        plan["draws"][0] = [(0, 0)]
        with self.assertRaisesRegex(ValueError, "multiplicity"):
            intervals.contrast(self.rows, self.predictions, "fallback_only", plan)

    def test_changed_stratum_group_denominators_rejected(self):
        plan = intervals.make_plan(self.rows, 60, 1)
        plan["draws"][0] = [(0, 13)]
        with self.assertRaisesRegex(ValueError, "benchmark group denominators"):
            intervals.contrast(self.rows, self.predictions, "fallback_only", plan)

    def test_invalid_baseline_and_eligibility_settings_rejected(self):
        with self.assertRaises(ValueError):
            self.estimate("unrecognized")
        for minimum, valid in ((True, 0.9), (1, 0.9), (10, True), (10, 0), (10, float("nan"))):
            with self.subTest(minimum=minimum, valid=valid), self.assertRaises(ValueError):
                intervals.contrast(
                    self.rows, self.predictions, "fallback_only", self.plan, minimum, valid
                )

    def test_case_weighted_point_is_not_equal_group_average(self):
        rows = [replace(row(i), canonical_group="large") for i in range(9)]
        rows.append(
            replace(
                row(9),
                canonical_group="small",
                small=replace(row(9).small, reference_correct=True),
                fallback=replace(row(9).fallback, reference_correct=False),
            )
        )
        result = intervals.contrast(
            rows,
            evaluate(rows, "always_cascade")["predictions"],
            "small_only",
            intervals.make_plan(rows, 60, 1),
            min_groups=2,
        )
        self.assertEqual(result["metrics"]["match_fraction_difference"]["point"], 0.8)

    def test_ratio_interval_withheld_when_too_many_draws_have_zero_matches(self):
        rows = [
            replace(r, fallback=replace(r.fallback, reference_correct=(i == 0)))
            for i, r in enumerate(self.rows)
        ]
        result = intervals.contrast(
            rows,
            evaluate(rows, "always_cascade")["predictions"],
            "fallback_only",
            intervals.make_plan(rows, 100, 1729),
        )
        metric = result["metrics"]["calls_per_match_difference"]
        self.assertEqual(metric["point"], 12)
        self.assertLess(metric["valid_replicates"], 90)
        self.assertIsNone(metric["interval_95_percentile"])
        self.assertEqual(metric["unavailable_reason"], "insufficient_valid_replicates")

    def test_canonical_output_has_no_nonfinite_values(self):
        result = self.estimate("small_only")
        self.assertEqual(json.loads(run_intervals.canonical(result)), result)


class PresentationTests(unittest.TestCase):
    def test_percentile_linear_interpolation(self):
        self.assertAlmostEqual(intervals.percentile([0, 10], 0.025), 0.25)
        self.assertAlmostEqual(intervals.percentile([0, 10], 0.975), 9.75)

    def test_report_explains_conditional_and_incomplete_estimates(self):
        unavailable = {"unavailable_reason": "incomplete_oof_coverage"}
        summary = {
            "views": [
                {
                    "model": "synthetic",
                    "panel": "reference",
                    "cap": 0.25,
                    "evaluated_rows": 0,
                    "original_rows": 12,
                    "known_matches": 0,
                    "fallback_rows": 0,
                    "comparisons": {"small_only": unavailable, "fallback_only": unavailable},
                }
            ]
        }
        rendered = run_intervals.report(summary, [0.25])
        self.assertIn("incomplete_oof_coverage", rendered)
        self.assertIn("thresholds are not refitted", rendered)
        self.assertIn("No multiplicity correction", rendered)

    def test_metric_display_uses_percentage_points(self):
        result = {
            "metrics": {"difference": {"point": 0.05, "interval_95_percentile": [-0.01, 0.1]}}
        }
        self.assertEqual(
            run_intervals.format_metric(result, "difference", 100), "5.000 [-1.000, 10.000]"
        )

    def test_policy_and_source_pins_match(self):
        raw = (Path(__file__).parent / "policy.json").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), run_intervals.POLICY_SHA)
        for name, wanted in json.loads(raw)["source_sha256_lf"].items():
            self.assertEqual(
                hashlib.sha256(
                    (run_intervals.REPO / name).read_bytes().replace(b"\r\n", b"\n")
                ).hexdigest(),
                wanted,
            )

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            (repo / run_intervals.OUTPUT).mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "preserve previous"):
                run_intervals.run(repo)


if __name__ == "__main__":
    unittest.main()
