"""Compact development frontiers and outcome-independent budget diagnostics."""

from __future__ import annotations

import math
from fractions import Fraction

from uqroute_tc.routing.development import checked_cases, evaluate


def compact(result):
    """Keep per-threshold aggregates without retaining N copies of predictions."""
    result = {k: v for k, v in result.items() if k != "predictions"}
    count = result["reference_matches_known"]
    known = result["reference_outcomes_unavailable"] == 0
    result["attempt_slots_per_reference_match"] = (
        result["accounting"]["model_calls"] / count if count and known else None
    )
    result["request_elapsed_proxy_per_reference_match"] = (
        result["accounting"]["usage"]["elapsed_seconds"]["total"] / count
        if count and known and result["accounting"]["usage"]["elapsed_seconds"]["total"] is not None
        else None
    )
    return result


def frontier(cases):
    rows = checked_cases(cases)
    scores = sorted(
        {r.small_mean_nll for r in rows if r.small.usable and r.small_mean_nll is not None}
    )
    # Retain one transient prediction list at a time, not a quadratic saved file.
    return [compact(evaluate(rows, "gated", threshold=score)) for score in (None, *scores)]


def transition_counts(cases):
    counts = {"CC": 0, "CI": 0, "IC": 0, "II": 0, "unknown": 0}
    for row in checked_cases(cases):
        small, fallback = row.small.reference_correct, row.fallback.reference_correct
        if small is None or fallback is None:
            counts["unknown"] += 1
        else:
            counts[("C" if small else "I") + ("C" if fallback else "I")] += 1
    return counts


def budget_view(cases, points, cap, seeds):
    """Use as much of a declared escalation cap as whole tie blocks permit.

    No reference outcomes enter cutpoint choice. This is a retrospective
    development display, not threshold fitting or a deployment operating point.
    """
    rows = checked_cases(cases)
    if type(cap) not in (int, float) or not math.isfinite(cap) or not 0 <= cap <= 1:
        raise ValueError("Budget cap must be a finite fraction in [0, 1]")
    if (
        not seeds
        or len(set(seeds)) != len(seeds)
        or any(type(seed) is not int or seed < 0 for seed in seeds)
    ):
        raise ValueError("Distinct nonnegative integer random seeds required")
    if not points or any(p["rows"] != len(rows) for p in points):
        raise ValueError("Frontier denominator differs")
    allowed = int(Fraction(str(cap)) * len(rows))
    feasible = [p for p in points if p["fallback_rows"] <= allowed]
    if not feasible:
        return {
            "budget_cap": cap,
            "allowed_fallback_rows": allowed,
            "feasible": False,
            "reason": "below_minimum_forced_escalation",
            "minimum_fallback_rows": min(p["fallback_rows"] for p in points),
            "gated": None,
            "matched_random": [],
            "deployment_threshold_frozen": False,
        }
    chosen = max(feasible, key=lambda p: p["fallback_rows"])
    random = [
        compact(
            evaluate(
                rows,
                "matched_random",
                random_fallback_count=chosen["fallback_rows"],
                random_seed=seed,
            )
        )
        for seed in seeds
    ]
    return {
        "budget_cap": cap,
        "allowed_fallback_rows": allowed,
        "feasible": True,
        "minimum_fallback_rows": min(p["fallback_rows"] for p in points),
        "gated": chosen,
        "matched_random": random,
        "cutpoint_rule": "greatest feasible escalation count; whole exact-score ties",
        "deployment_threshold_frozen": False,
    }


def analyze_scope(cases, caps, seeds):
    rows = checked_cases(cases)
    points = frontier(rows)
    return {
        "rows": len(rows),
        "panel": rows[0].panel,
        "canonical_groups": len({(r.benchmark, r.canonical_group) for r in rows}),
        "all_pair_outcomes_small_then_fallback": transition_counts(rows),
        "baselines": {
            name: compact(evaluate(rows, name))
            for name in ("small_only", "fallback_only", "always_cascade")
        },
        "minimum_fallback_rows": min(p["fallback_rows"] for p in points),
        "frontier": points,
        "budget_views": [budget_view(rows, points, cap, seeds) for cap in caps],
        "routing_threshold_selected": False,
        "held_out_access_enabled": False,
    }
