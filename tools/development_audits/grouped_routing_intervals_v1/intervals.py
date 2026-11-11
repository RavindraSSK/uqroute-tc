"""Paired cluster-bootstrap contrasts conditional on fixed development OOF policies."""

from __future__ import annotations

import math
import random
from collections import Counter

from uqroute_tc.routing.development import checked_cases

METRICS = (
    "match_fraction_difference",
    "unusable_fraction_difference",
    "calls_per_match_difference",
    "request_seconds_per_match_difference",
    "prompt_tokens_per_match_difference",
    "completion_tokens_per_match_difference",
)


def group_key(row):
    return row.benchmark, row.canonical_group


def make_plan(cases, replicates=2000, seed=1729):
    rows = checked_cases(cases)
    if type(replicates) is not int or replicates < 2 or type(seed) is not int or seed < 0:
        raise ValueError("At least two replicates and a nonnegative integer seed required")
    groups = sorted({group_key(r) for r in rows})
    strata = {
        b: [i for i, g in enumerate(groups) if g[0] == b] for b in sorted({g[0] for g in groups})
    }
    rng = random.Random(seed)
    draws = []
    for _ in range(replicates):
        counts = Counter()
        for indices in strata.values():
            for _ in indices:
                counts[indices[rng.randrange(len(indices))]] += 1
        draws.append(sorted(counts.items()))
    return {
        "groups": groups,
        "strata_group_counts": {b: len(v) for b, v in strata.items()},
        "replicates": replicates,
        "seed": seed,
        "draws": draws,
    }


def group_vectors(cases, predictions, baseline):
    rows = checked_cases(cases)
    if baseline not in {"small_only", "fallback_only", "always_cascade"}:
        raise ValueError("Unsupported paired baseline")
    index = {p["case_key"]: p for p in predictions}
    if len(index) != len(predictions) or set(index) != {r.case_key for r in rows}:
        raise ValueError("Complete unique OOF coverage required; no missing-row imputation")
    groups = sorted({group_key(r) for r in rows})
    vectors = {g: [0] * 13 for g in groups}
    blocked = {}
    for row in rows:
        saved = index[row.case_key]
        role = saved["output_role"]
        if role not in {"small", "fallback"}:
            raise ValueError("Unexpected OOF output role")
        gate = row.fallback if role == "fallback" else row.small
        base = row.small if baseline == "small_only" else row.fallback
        if saved["reference_correct"] != gate.reference_correct or saved["usable"] != gate.usable:
            raise ValueError("OOF prediction differs from the bound model outcome")
        gate_attempts = [row.small] + ([row.fallback] if role == "fallback" else [])
        base_attempts = [row.small, row.fallback] if baseline == "always_cascade" else [base]
        if gate.reference_correct is None or base.reference_correct is None:
            for metric in METRICS:
                if metric != "unusable_fraction_difference":
                    blocked[metric] = "unknown_reference_outcome"
        values = [
            1,
            int(gate.reference_correct is True),
            int(base.reference_correct is True),
            int(not gate.usable),
            int(not base.usable),
            len(gate_attempts),
            len(base_attempts),
        ]
        for field, metric in (
            ("elapsed_seconds", "request_seconds_per_match_difference"),
            ("prompt_tokens", "prompt_tokens_per_match_difference"),
            ("completion_tokens", "completion_tokens_per_match_difference"),
        ):
            for attempts in (gate_attempts, base_attempts):
                usage = [getattr(a.usage, field) for a in attempts]
                if any(v is None for v in usage):
                    blocked.setdefault(metric, "missing_" + field)
                # Known sums support other metrics; an affected metric is withheld,
                # never estimated using these partial totals as complete usage.
                values.append(sum(v for v in usage if v is not None))
        vector = vectors[group_key(row)]
        for i, value in enumerate(values):
            vector[i] += value
    return groups, [vectors[g] for g in groups], blocked


def metrics(values):
    n, correct_a, correct_b, unusable_a, unusable_b, calls_a, calls_b, *usage = values
    result = {
        "match_fraction_difference": (correct_a - correct_b) / n,
        "unusable_fraction_difference": (unusable_a - unusable_b) / n,
    }
    pairs = [(calls_a, calls_b), (usage[0], usage[1]), (usage[2], usage[3]), (usage[4], usage[5])]
    for name, (a, b) in zip(METRICS[2:], pairs, strict=True):
        result[name] = a / correct_a - b / correct_b if correct_a and correct_b else None
    return result


def percentile(values, fraction):
    ordered = sorted(values)
    at = (len(ordered) - 1) * fraction
    lo, hi = math.floor(at), math.ceil(at)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (at - lo)


def contrast(cases, predictions, baseline, plan, min_groups=10, min_valid=0.9):
    if (
        type(min_groups) is not int
        or min_groups < 2
        or type(min_valid) not in (int, float)
        or not math.isfinite(min_valid)
        or not 0 < min_valid <= 1
    ):
        raise ValueError("Invalid bootstrap eligibility settings")
    groups, vectors, blocked = group_vectors(cases, predictions, baseline)
    if groups != plan["groups"] or len(plan["draws"]) != plan["replicates"]:
        raise ValueError("Shared bootstrap plan does not match the full paired cohort")
    point = metrics([sum(v[j] for v in vectors) for j in range(13)])
    samples = {name: [] for name in METRICS}
    if len(groups) >= min_groups:
        for draw in plan["draws"]:
            if any(
                type(i) is not int
                or not 0 <= i < len(groups)
                or type(weight) is not int
                or weight <= 0
                for i, weight in draw
            ):
                raise ValueError("Invalid bootstrap multiplicity")
            counts = Counter()
            for i, weight in draw:
                counts[groups[i][0]] += weight
            if dict(counts) != plan["strata_group_counts"]:
                raise ValueError("Draw changed benchmark group denominators")
            totals = [sum(vectors[i][j] * weight for i, weight in draw) for j in range(13)]
            estimate = metrics(totals)
            for name in METRICS:
                if name not in blocked and estimate[name] is not None:
                    samples[name].append(estimate[name])
    results = {}
    for name in METRICS:
        valid = samples[name]
        attempted = plan["replicates"] if len(groups) >= min_groups and name not in blocked else 0
        reason = blocked.get(name)
        if reason is None and len(groups) < min_groups:
            reason = "fewer_than_minimum_canonical_groups"
        if reason is None and len(valid) < math.ceil(min_valid * plan["replicates"]):
            reason = "insufficient_valid_replicates"
        results[name] = {
            "point": None if name in blocked else point[name],
            "point_unavailable_reason": blocked.get(name)
            or ("zero_reference_match_denominator" if point[name] is None else None),
            "interval_95_percentile": [percentile(valid, 0.025), percentile(valid, 0.975)]
            if reason is None
            else None,
            "unavailable_reason": reason,
            "requested_replicates": plan["replicates"],
            "attempted_replicates": attempted,
            "valid_replicates": len(valid),
            "undefined_replicates": attempted - len(valid),
        }
    return {
        "baseline": baseline,
        "rows": len(cases),
        "canonical_groups": len(groups),
        "strata_group_counts": plan["strata_group_counts"],
        "metrics": results,
        "interpretation": "gate minus baseline; fixed-OOF conditional paired group bootstrap",
    }
