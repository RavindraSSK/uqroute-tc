"""Synthetic group isolation, budget, tie, missingness and aggregation regressions."""

import hashlib
import json
import unittest
from dataclasses import replace
from pathlib import Path

import run_validation
import validation

from uqroute_tc.routing.development import PairedCase, SavedOutcome, Usage, evaluate


def row(i, score=0.1, *, correct=False, fallback=True, status="complete", parsed=True):
    return PairedCase(
        str(i),
        "group" + str(i),
        "bfcl_v3",
        "official_reference_compliance",
        "primary",
        "development",
        score,
        SavedOutcome(correct, status, parsed, Usage(10, 2, 0.5)),
        SavedOutcome(fallback, "complete", True, Usage(20, 4, 1)),
    )


class ThresholdTests(unittest.TestCase):
    def test_exact_ties_preserve_whole_blocks(self):
        rows = [row(0, 0.1), row(1, 0.1), row(2, 0.1), row(3, 0.9)]
        fitted = validation.fit_cap(rows, 0.5)
        self.assertEqual(fitted["threshold"], 0.1)
        self.assertEqual(fitted["training_fallback_rows"], 1)

    def test_forced_escalation_can_make_training_cap_infeasible(self):
        rows = [row(0, None, status="invalid_evidence"), row(1)]
        self.assertFalse(validation.fit_cap(rows, 0.25)["feasible"])
        self.assertTrue(validation.fit_cap(rows, 0.5)["feasible"])

    def test_zero_and_full_cap(self):
        rows = [row(i, i) for i in range(5)]
        self.assertEqual(validation.fit_cap(rows, 0)["training_fallback_rows"], 0)
        full = validation.fit_cap(rows, 1)
        self.assertIsNone(full["threshold"])
        self.assertEqual(full["training_fallback_rows"], 5)

    def test_threshold_never_uses_labels_or_fallback_usage(self):
        rows = [row(i, i / 10) for i in range(10)]
        changed = [
            replace(
                r,
                small=replace(r.small, reference_correct=True),
                fallback=replace(r.fallback, reference_correct=False, usage=Usage()),
            )
            for r in rows
        ]
        self.assertEqual(validation.fit_cap(rows, 0.25), validation.fit_cap(changed, 0.25))

    def test_invalid_caps_rejected(self):
        for cap in (True, -1, 1.1, float("nan"), float("inf")):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                validation.fit_cap([row(0)], cap)

    def test_no_parsed_call_forces_escalation(self):
        fitted = validation.fit_cap([row(0, 0, parsed=False), row(1, 0.5)], 0.5)
        self.assertEqual(fitted["training_forced_fallback"], 1)
        self.assertEqual(fitted["training_fallback_rows"], 1)


class FoldTests(unittest.TestCase):
    def setUp(self):
        self.rows = [row(i, i / 10, correct=i % 2 == 0, fallback=i % 3 == 0) for i in range(15)]

    def test_same_group_variants_stay_together(self):
        extra = replace(self.rows[0], case_key="perturbed")
        mapping = validation.assign_folds(self.rows + [extra])
        self.assertEqual(len(mapping), 15)
        self.assertEqual(
            mapping[validation.group_key(extra)], mapping[validation.group_key(self.rows[0])]
        )

    def test_fold_assignment_is_stable_and_balanced(self):
        a = validation.assign_folds(self.rows)
        b = validation.assign_folds(list(reversed(self.rows)))
        self.assertEqual(a, b)
        self.assertEqual(sorted(list(a.values()).count(i) for i in range(5)), [3] * 5)

    def test_benchmark_qualifies_group_identity(self):
        other = replace(self.rows[0], benchmark="apibank", case_key="other")
        self.assertEqual(len(validation.assign_folds(self.rows + [other])), 16)

    def test_model_labels_do_not_change_assignment(self):
        changed = [
            replace(r, small=replace(r.small, reference_correct=not r.small.reference_correct))
            for r in self.rows
        ]
        self.assertEqual(validation.assign_folds(changed), validation.assign_folds(self.rows))

    def test_training_and_validation_groups_disjoint_and_fitted_separately(self):
        assignment = validation.assign_folds(self.rows)
        result = validation.validate_cap(self.rows, assignment, 0.25, seeds=(1, 2))
        for fitted in result["folds"]:
            train = [r for r in self.rows if assignment[validation.group_key(r)] != fitted["fold"]]
            valid = [r for r in self.rows if assignment[validation.group_key(r)] == fitted["fold"]]
            self.assertFalse(
                {validation.group_key(r) for r in train} & {validation.group_key(r) for r in valid}
            )
            self.assertEqual(fitted["threshold"], validation.fit_cap(train, 0.25)["threshold"])
        self.assertEqual(result["gated"]["evaluated_rows"], 15)
        self.assertTrue(result["gated"]["complete_oof_coverage"])

    def test_validation_score_cannot_change_its_own_fitted_threshold(self):
        assignment = validation.assign_folds(self.rows)
        target = assignment[validation.group_key(self.rows[0])]
        changed = [
            replace(r, small_mean_nll=1000) if assignment[validation.group_key(r)] == target else r
            for r in self.rows
        ]
        a = validation.validate_cap(self.rows, assignment, 0.25)
        b = validation.validate_cap(changed, assignment, 0.25)
        self.assertEqual(a["folds"][target]["threshold"], b["folds"][target]["threshold"])

    def test_realized_validation_budget_can_exceed_training_cap(self):
        rows = [row(i, score) for i, score in enumerate((0, 0.1, 0.2, 0.3, 100))]
        assignment = {validation.group_key(r): i for i, r in enumerate(rows)}
        result = validation.validate_cap(rows, assignment, 0.25)
        self.assertTrue(result["folds"][4]["validation_cap_exceeded"])
        self.assertEqual(result["folds"][4]["validation_fallback_rows"], 1)

    def test_random_baselines_exactly_match_aggregate_fallback_counts(self):
        result = validation.validate_cap(
            self.rows, validation.assign_folds(self.rows), 0.25, seeds=(1, 2, 3)
        )
        for random in result["random_same_fold_counts"].values():
            self.assertEqual(random["fallback_rows"], result["gated"]["fallback_rows"])
            self.assertEqual(random["evaluated_rows"], 15)

    def test_infeasible_folds_do_not_get_imputed_zero_outcomes(self):
        rows = [row(0, None, status="truncated")] + self.rows[1:]
        result = validation.validate_cap(rows, validation.assign_folds(rows), 0)
        gate = result["gated"]
        self.assertLess(gate["evaluated_rows"], 15)
        self.assertFalse(gate["complete_oof_coverage"])
        self.assertIsNone(gate["reference_compliance_full_cohort"])
        self.assertEqual(len(gate["predictions"]), gate["evaluated_rows"])

    def test_complete_cascade_equals_full_cohort_baseline(self):
        result = validation.validate_cap(self.rows, validation.assign_folds(self.rows), 1)
        direct = evaluate(self.rows, "always_cascade")
        self.assertEqual(
            result["gated"]["known_matches_evaluated"], direct["reference_matches_known"]
        )
        self.assertEqual(
            result["gated"]["accounting"]["model_calls"], direct["accounting"]["model_calls"]
        )
        self.assertAlmostEqual(
            result["gated"]["accounting"]["usage"]["elapsed_seconds"]["total"],
            direct["accounting"]["usage"]["elapsed_seconds"]["total"],
        )

    def test_zero_cap_fits_when_all_candidates_are_usable(self):
        result = validation.validate_cap(self.rows, validation.assign_folds(self.rows), 0)
        self.assertTrue(result["gated"]["complete_oof_coverage"])
        # A training maximum may be exceeded by validation scores, even at cap zero.
        self.assertGreaterEqual(result["gated"]["fallback_rows"], 0)

    def test_invalid_assignments_folds_and_seeds_rejected(self):
        assignment = validation.assign_folds(self.rows)
        for changed in ({}, dict.fromkeys(assignment, 5), dict.fromkeys(assignment, True)):
            with self.assertRaises(ValueError):
                validation.validate_cap(self.rows, changed, 0.5)
        for folds in (True, 1, 0):
            with self.assertRaises(ValueError):
                validation.assign_folds(self.rows, folds)
        for seeds in ((), (1, 1), (True,), (-1,)):
            with self.assertRaises(ValueError):
                validation.validate_cap(self.rows, assignment, 0.5, seeds=seeds)


class AggregationTests(unittest.TestCase):
    def test_duplicate_validation_predictions_rejected(self):
        rows = [row(0)]
        result = evaluate(rows, "small_only")
        with self.assertRaises(ValueError):
            validation.combine([result, result], rows, 1)

    def test_incomplete_coverage_retains_bounds(self):
        rows = [row(0, correct=True), row(1)]
        result = validation.combine([evaluate(rows[:1], "small_only")], rows, 2)
        self.assertEqual(result["full_cohort_match_fraction_bounds"], [0.5, 1])
        self.assertIsNone(result["reference_compliance_full_cohort"])

    def test_unknown_outcomes_and_missing_usage_remain_unknown(self):
        r = row(0)
        r = replace(
            r, small=SavedOutcome(None, "unknown_outcome", False, Usage()), small_mean_nll=None
        )
        result = validation.combine([evaluate([r], "small_only")], [r], 1)
        self.assertIsNone(result["reference_compliance_full_cohort"])
        self.assertIsNone(result["accounting"]["usage"]["elapsed_seconds"]["total"])
        self.assertIsNone(result["request_seconds_per_match_evaluated"])

    def test_empty_fold_union_does_not_fabricate_predictions(self):
        result = validation.combine([], [row(0)], 1)
        self.assertEqual(result["evaluated_rows"], 0)
        self.assertIsNone(result["reference_compliance_evaluated"])
        self.assertEqual(result["full_cohort_match_fraction_bounds"], [0, 1])

    def test_wrong_original_denominator_rejected(self):
        with self.assertRaises(ValueError):
            validation.combine([], [row(0)], 0)

    def test_pinned_policy_and_sources_match(self):
        raw = (Path(__file__).parent / "policy.json").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), run_validation.POLICY_SHA)
        policy = json.loads(raw)
        for name, expected in policy["source_sha256_lf"].items():
            self.assertEqual(
                hashlib.sha256(
                    (run_validation.REPO / name).read_bytes().replace(b"\r\n", b"\n")
                ).hexdigest(),
                expected,
            )

    def test_oof_results_serialize_without_nonfinite_values(self):
        rows = [row(i, i / 10) for i in range(15)]
        result = validation.validate_cap(rows, validation.assign_folds(rows), 0.25)
        self.assertEqual(json.loads(run_validation.canonical(result)), result)

    def test_report_labels_incomplete_coverage_and_keeps_baselines(self):
        result = validation.validate_cap(
            [row(i, i / 10) for i in range(15)],
            validation.assign_folds([row(i, i / 10) for i in range(15)]),
            0.25,
        )
        view = {
            **validation.compact(result["gated"]),
            "model": "synthetic",
            "panel": "reference",
            "cap": 0.25,
            "validation_cap_exceeded_folds": 0,
            "random_mean_matches_evaluated": result["random_mean_matches_evaluated"],
            "small_matches_same_rows": 0,
            "fallback_matches_same_rows": 15,
        }
        rendered = run_validation.report({"views": [view]})
        self.assertIn("Small matches", rendered)
        self.assertIn("No final threshold", rendered)
        view["reference_compliance_full_cohort"] = None
        self.assertIn("incomplete/unavailable", run_validation.report({"views": [view]}))

    def test_existing_output_preserved_before_input_access(self):
        import tempfile

        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            output = repo / run_validation.OUTPUT
            output.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "preserve existing"):
                run_validation.run(repo)


if __name__ == "__main__":
    unittest.main()
