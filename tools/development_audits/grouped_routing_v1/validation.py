"""Exploratory group-separated validation of fixed training escalation-cap rules."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from fractions import Fraction

from uqroute_tc.routing.development import checked_cases, evaluate


def group_key(row):
    return row.benchmark, row.canonical_group


def assign_folds(cases, folds=5, seed=1729):
    if type(folds) is not int or folds < 2 or type(seed) is not int or seed < 0:
        raise ValueError("At least two folds and a nonnegative integer seed required")
    if not cases or len({r.case_key for r in cases}) != len(cases):
        raise ValueError("Unique nonempty development cases required")
    if any(r.split != "development" or r.population != "primary" for r in cases):
        raise ValueError("Primary development cases only")
    groups = {group_key(r) for r in cases}
    result = {}
    for benchmark in sorted({b for b, _ in groups}):
        subset = sorted(g for g in groups if g[0] == benchmark)
        subset.sort(
            key=lambda g: (
                hashlib.sha256(
                    json.dumps(
                        ["uqroute-grouped-routing-v1", seed, *g], separators=(",", ":")
                    ).encode()
                ).hexdigest(),
                g,
            )
        )
        for index, group in enumerate(subset):
            result[group] = index % folds
    return result


def fit_cap(training, cap):
    """Smallest training-score boundary accepting enough rows to satisfy a cap.

    Neither labels nor fallback outcomes/usage enter the threshold calculation.
    Entire score ties stay together; no validation row enters this function.
    """
    rows = checked_cases(training)
    if type(cap) not in (int, float) or not math.isfinite(cap) or not 0 <= cap <= 1:
        raise ValueError("Finite cap in [0, 1] required")
    allowed = int(Fraction(str(cap)) * len(rows))
    scores = sorted(
        r.small_mean_nll for r in rows if r.small.usable and r.small_mean_nll is not None
    )
    forced = len(rows) - len(scores)
    common = {
        "training_rows": len(rows),
        "training_allowed_fallback": allowed,
        "training_forced_fallback": forced,
        "cap": cap,
    }
    if forced > allowed:
        return common | {
            "feasible": False,
            "reason": "training_forced_fallback_exceeds_cap",
            "threshold": None,
            "training_fallback_rows": None,
        }
    needed = len(rows) - allowed
    threshold = scores[needed - 1] if needed else None
    accepted = sum(score <= threshold for score in scores) if threshold is not None else 0
    return common | {
        "feasible": True,
        "reason": None,
        "threshold": threshold,
        "training_fallback_rows": len(rows) - accepted,
    }


def combine(results, cases, original_rows):
    """Aggregate disjoint validation-fold kernel evaluations without zero imputation."""
    index = {r.case_key: r for r in checked_cases(cases)}
    if type(original_rows) is not int or original_rows != len(index):
        raise ValueError("Original denominator must equal the full case cohort")
    predictions = sorted(
        [p for result in results for p in result["predictions"]], key=lambda p: p["case_key"]
    )
    keys = {p["case_key"] for p in predictions}
    if len(keys) != len(predictions) or not keys <= set(index):
        raise ValueError("Validation predictions overlap or differ from case membership")
    n = len(predictions)
    unknown = sum(p["reference_correct"] is None for p in predictions)
    correct = sum(p["reference_correct"] is True for p in predictions)
    full = n == original_rows
    accepted = [p for p in predictions if p["output_role"] == "small"]
    accepted_unknown = any(p["reference_correct"] is None for p in accepted)
    calls = sum(r["accounting"]["model_calls"] for r in results)
    usage = {}
    for field in ("prompt_tokens", "completion_tokens", "elapsed_seconds"):
        parts = [r["accounting"]["usage"][field] for r in results]
        missing = sum(p["missing_calls"] for p in parts)
        known = sum(p["known_sum"] for p in parts)
        usage[field] = {
            "known_sum": known,
            "missing_calls": missing,
            "total": known if n and not missing else None,
        }
    roles, statuses = Counter(), Counter()
    for result in results:
        roles.update(result["accounting"]["calls_by_role"])
        statuses.update(result["accounting"]["attempt_statuses"])
    seconds = usage["elapsed_seconds"]["total"]
    fallback = sum(p["output_role"] == "fallback" for p in predictions)
    return {
        "original_rows": original_rows,
        "evaluated_rows": n,
        "complete_oof_coverage": full,
        "unevaluated_rows": original_rows - n,
        "evaluated_canonical_groups": len({group_key(index[k]) for k in keys}),
        "known_matches_evaluated": correct,
        "unknown_outcomes_evaluated": unknown,
        "reference_compliance_full_cohort": correct / original_rows
        if full and not unknown
        else None,
        "reference_compliance_evaluated": correct / n if n and not unknown else None,
        "full_cohort_match_fraction_bounds": [
            correct / original_rows,
            (correct + unknown + original_rows - n) / original_rows,
        ],
        "fallback_rows": fallback,
        "fallback_rate_evaluated": fallback / n if n else None,
        "unusable_final_outputs": sum(not p["usable"] for p in predictions),
        "small_accepted_rows": len(accepted),
        "small_accepted_error_risk": (
            sum(p["reference_correct"] is False for p in accepted) / len(accepted)
            if accepted and not accepted_unknown
            else None
        ),
        "rescues": sum(r["rescues"] for r in results),
        "harms": sum(r["harms"] for r in results),
        "accounting": {
            "model_calls": calls,
            "calls_by_role": dict(roles),
            "attempt_statuses": dict(statuses),
            "usage": usage,
        },
        "calls_per_match_evaluated": calls / correct if correct and not unknown else None,
        "request_seconds_per_match_evaluated": (
            seconds / correct if correct and not unknown and seconds is not None else None
        ),
        "predictions": predictions,
    }


def compact(result):
    return {k: v for k, v in result.items() if k != "predictions"}


def validate_cap(cases, assignment, cap, folds=5, seeds=(1729,)):
    rows = checked_cases(cases)
    if type(folds) is not int or folds < 2:
        raise ValueError("At least two integer folds required")
    if type(cap) not in (int, float) or not math.isfinite(cap) or not 0 <= cap <= 1:
        raise ValueError("Finite cap in [0, 1] required")
    if any(group_key(r) not in assignment for r in rows) or any(
        type(assignment[group_key(r)]) is not int or not 0 <= assignment[group_key(r)] < folds
        for r in rows
    ):
        raise ValueError("Missing or invalid group-fold assignment")
    if (
        not seeds
        or len(set(seeds)) != len(seeds)
        or any(type(s) is not int or s < 0 for s in seeds)
    ):
        raise ValueError("Distinct nonnegative random seeds required")
    fits, gated_results = [], []
    random_results = {seed: [] for seed in seeds}
    baseline_results = {name: [] for name in ("small_only", "fallback_only", "always_cascade")}
    for fold in range(folds):
        training = [r for r in rows if assignment[group_key(r)] != fold]
        validation = [r for r in rows if assignment[group_key(r)] == fold]
        if not training or not validation:
            fits.append(
                {
                    "fold": fold,
                    "feasible": False,
                    "reason": "empty_training_or_validation",
                    "validation_rows": len(validation),
                }
            )
            continue
        if {group_key(r) for r in training} & {group_key(r) for r in validation}:
            raise ValueError("Group leakage")
        fitted = fit_cap(training, cap)
        fitted.update(
            {
                "fold": fold,
                "validation_rows": len(validation),
                "training_groups": len({group_key(r) for r in training}),
                "validation_groups": len({group_key(r) for r in validation}),
            }
        )
        if fitted["feasible"]:
            gate = evaluate(validation, "gated", threshold=fitted["threshold"])
            gated_results.append(gate)
            actual = gate["fallback_rows"]
            fitted["validation_fallback_rows"] = actual
            fitted["validation_cap_exceeded"] = actual > int(Fraction(str(cap)) * len(validation))
            for seed in seeds:
                random_results[seed].append(
                    evaluate(
                        validation, "matched_random", random_fallback_count=actual, random_seed=seed
                    )
                )
            for name in baseline_results:
                baseline_results[name].append(evaluate(validation, name))
        fits.append(fitted)
    gate = combine(gated_results, rows, len(rows))
    random = {
        str(seed): compact(combine(parts, rows, len(rows)))
        for seed, parts in random_results.items()
    }
    mean = (
        sum(r["known_matches_evaluated"] for r in random.values()) / len(random)
        if gate["evaluated_rows"]
        else None
    )
    return {
        "cap": cap,
        "folds": fits,
        "gated": gate,
        "random_same_fold_counts": random,
        "random_mean_matches_evaluated": mean,
        "baselines_on_same_evaluated_rows": {
            name: compact(combine(parts, rows, len(rows)))
            for name, parts in baseline_results.items()
        },
        "validation_cap_not_guaranteed": True,
        "deployment_threshold_selected": False,
    }
