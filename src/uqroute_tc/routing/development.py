"""Offline development policy replay; no dispatch, threshold fitting or held-out access.

The gate receives only candidate evidence. Reference labels are used solely by
the replay evaluator. A saved-pair replay is a counterfactual estimate, not an
online latency measurement or proof of executable task success.
"""

from __future__ import annotations

import hashlib
import math
from collections import Counter
from dataclasses import dataclass
from typing import Literal

STATUSES = frozenset(
    {
        "complete",
        "truncated",
        "invalid_evidence",
        "request_error",
        "unknown_outcome",
        "malformed_response",
        "unsupported_finish",
        "empty_output",
        "http_error",
        "validation_error",
        "transport_error_outcome_unknown",
        "interrupted_outcome_unknown",
        "interrupted_response_metadata_missing",
    }
)
ABSENT_RESPONSE = frozenset(
    {
        "request_error",
        "unknown_outcome",
        "transport_error_outcome_unknown",
        "interrupted_outcome_unknown",
    }
)
PANELS = frozenset({"official_reference_compliance", "tooleyes_relevance"})
POLICIES = frozenset({"small_only", "fallback_only", "always_cascade", "gated", "matched_random"})


def finite_nonnegative(value: object, name: str) -> None:
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")


def text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be nonempty text")


def boolean(value: object, name: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"{name} must be bool")


@dataclass(frozen=True)
class Usage:
    """Usage for one saved attempt; None means unknown, including failed attempts."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    elapsed_seconds: float | None = None

    def __post_init__(self) -> None:
        for name in ("prompt_tokens", "completion_tokens"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} must be a nonnegative integer or None")
        if self.elapsed_seconds is not None:
            finite_nonnegative(self.elapsed_seconds, "elapsed_seconds")


@dataclass(frozen=True)
class SavedOutcome:
    """One durably attempted model response; no unattempted record is fabricated."""

    reference_correct: bool | None
    evidence_status: str
    has_parsed_call: bool
    usage: Usage

    def __post_init__(self) -> None:
        if self.reference_correct is not None:
            boolean(self.reference_correct, "reference_correct")
        if self.evidence_status not in STATUSES:
            raise ValueError("Unsupported evidence status")
        boolean(self.has_parsed_call, "has_parsed_call")
        if not isinstance(self.usage, Usage):
            raise ValueError("usage must be Usage")
        if self.evidence_status in ABSENT_RESPONSE:
            if self.reference_correct is not None or self.has_parsed_call:
                raise ValueError("An absent response cannot supply a label or parsed call")

    @property
    def usable(self) -> bool:
        return self.evidence_status == "complete" and self.has_parsed_call


@dataclass(frozen=True)
class PairedCase:
    case_key: str
    canonical_group: str
    benchmark: str
    panel: str
    population: Literal["primary", "sensitivity_only"]
    split: Literal["development"]
    small_mean_nll: float | None
    small: SavedOutcome
    fallback: SavedOutcome

    def __post_init__(self) -> None:
        for name in ("case_key", "canonical_group", "benchmark"):
            text(getattr(self, name), name)
        if self.panel not in PANELS or self.population not in {"primary", "sensitivity_only"}:
            raise ValueError("Unsupported panel or population")
        if self.split != "development":
            raise ValueError("Only development replay is supported")
        if not isinstance(self.small, SavedOutcome) or not isinstance(self.fallback, SavedOutcome):
            raise ValueError("Both saved model outcomes are required")
        if self.small_mean_nll is not None:
            finite_nonnegative(self.small_mean_nll, "small_mean_nll")
            if self.small.evidence_status != "complete":
                raise ValueError("Non-complete token evidence must remain unavailable")


def should_escalate(
    *,
    mean_nll: float | None,
    evidence_status: str,
    has_parsed_call: bool,
    threshold: float | None,
) -> bool:
    """Inclusive acceptance: complete parsed candidate with NLL <= threshold.

    None threshold means accept none. Missing/invalid token evidence or no
    parsed call forces escalation. Labels, tool references and fallback
    outcomes are deliberately absent from this API.
    """
    if threshold is not None:
        finite_nonnegative(threshold, "threshold")
    if mean_nll is not None:
        finite_nonnegative(mean_nll, "mean_nll")
    boolean(has_parsed_call, "has_parsed_call")
    if evidence_status not in STATUSES:
        raise ValueError("Unsupported evidence status")
    return (
        threshold is None
        or mean_nll is None
        or evidence_status != "complete"
        or not has_parsed_call
        or mean_nll > threshold
    )


def checked_cases(cases: list[PairedCase]) -> list[PairedCase]:
    if not cases or any(not isinstance(row, PairedCase) for row in cases):
        raise ValueError("Nonempty paired development cases required")
    if len({row.case_key for row in cases}) != len(cases):
        raise ValueError("Duplicate case keys")
    if len({(row.panel, row.population, row.split) for row in cases}) != 1:
        raise ValueError("Replay panels, populations and splits separately")
    # Stable random matching and aggregate arithmetic must not depend on file order.
    return sorted(cases, key=lambda row: row.case_key)


def random_keys(cases: list[PairedCase], count: int, seed: int) -> set[str]:
    if type(count) is not int or not 0 <= count <= len(cases):
        raise ValueError("Random fallback count is outside the full cohort")
    if type(seed) is not int or seed < 0:
        raise ValueError("Random seed must be a nonnegative integer")

    def rank(row: PairedCase) -> tuple[str, str]:
        # Unambiguous length prefix; no label or score enters this ordering.
        key = row.case_key.encode("utf-8")
        raw = f"uqroute-matched-random-v1:{seed}:{len(key)}:".encode() + key
        return hashlib.sha256(raw).hexdigest(), row.case_key

    return {row.case_key for row in sorted(cases, key=rank)[:count]}


def usage_summary(attempts: list[tuple[str, SavedOutcome]]) -> dict:
    totals = {}
    for field in ("prompt_tokens", "completion_tokens", "elapsed_seconds"):
        values = [getattr(outcome.usage, field) for _, outcome in attempts]
        missing = sum(value is None for value in values)
        known = sum(value for value in values if value is not None)
        totals[field] = {
            "known_sum": known,
            "missing_calls": missing,
            "total": None if missing else known,
        }
    return {
        "model_calls": len(attempts),
        "call_count_interpretation": "policy attempt slots; not confirmed server executions",
        "calls_by_role": dict(Counter(role for role, _ in attempts)),
        "attempt_statuses": dict(Counter(outcome.evidence_status for _, outcome in attempts)),
        "usage": totals,
        "elapsed_interpretation": (
            "sum of saved request elapsed time; not online latency or GPU time"
        ),
    }


def evaluate(
    cases: list[PairedCase],
    policy: str,
    *,
    threshold: float | None = None,
    random_fallback_count: int | None = None,
    random_seed: int | None = None,
) -> dict:
    """Evaluate one fixed policy on saved paired development outcomes.

    Fallback is terminal: no retry, return-to-small override or label-based
    selection. Raw official outcomes and output usability remain separate.
    Missing reference outcomes remain unknown and produce bounds, not zeros.
    """
    rows = checked_cases(cases)
    if policy not in POLICIES:
        raise ValueError("Unsupported routing policy")
    if policy != "gated" and threshold is not None:
        raise ValueError("Threshold is only meaningful for gated replay")
    if policy != "matched_random" and (
        random_fallback_count is not None or random_seed is not None
    ):
        raise ValueError("Random settings supplied to a nonrandom policy")
    if policy == "gated" and threshold is not None:
        finite_nonnegative(threshold, "threshold")
    chosen = (
        random_keys(rows, random_fallback_count, random_seed)
        if policy == "matched_random"
        else set()
    )
    predictions = []
    attempts = []
    rescues = harms = paired_unknown = small_accepted = accepted_errors = 0
    for row in rows:
        escalate = policy in {"fallback_only", "always_cascade"}
        if policy == "gated":
            escalate = should_escalate(
                mean_nll=row.small_mean_nll,
                evidence_status=row.small.evidence_status,
                has_parsed_call=row.small.has_parsed_call,
                threshold=threshold,
            )
        elif policy == "matched_random":
            escalate = row.case_key in chosen
        if policy != "fallback_only":
            attempts.append(("small", row.small))
        if escalate:
            attempts.append(("fallback", row.fallback))
        final = row.fallback if escalate else row.small
        if escalate and policy != "fallback_only":
            a, b = row.small.reference_correct, row.fallback.reference_correct
            paired_unknown += a is None or b is None
            rescues += a is False and b is True
            harms += a is True and b is False
        elif not escalate:
            small_accepted += 1
            accepted_errors += row.small.reference_correct is False
        predictions.append(
            {
                "case_key": row.case_key,
                "output_role": "fallback" if escalate else "small",
                "reference_correct": final.reference_correct,
                "evidence_status": final.evidence_status,
                "usable": final.usable,
            }
        )
    n = len(rows)
    matches = sum(p["reference_correct"] is True for p in predictions)
    unknown = sum(p["reference_correct"] is None for p in predictions)
    accepted_unknown = sum(
        p["output_role"] == "small" and p["reference_correct"] is None for p in predictions
    )
    fallback = sum(p["output_role"] == "fallback" for p in predictions)
    return {
        "policy": policy,
        "threshold_inclusive": threshold,
        "random_seed": random_seed,
        "panel": rows[0].panel,
        "population": rows[0].population,
        "split": "development",
        "rows": n,
        "canonical_groups": len({(r.benchmark, r.canonical_group) for r in rows}),
        "reference_matches_known": matches,
        "reference_outcomes_unavailable": unknown,
        "reference_compliance": None if unknown else matches / n,
        "reference_match_fraction_bounds": [matches / n, (matches + unknown) / n],
        "unusable_final_outputs": sum(not p["usable"] for p in predictions),
        "fallback_rows": fallback,
        "fallback_rate": fallback / n,
        "small_accepted_rows": small_accepted,
        "small_accepted_reference_errors": accepted_errors,
        "small_accepted_error_risk": (
            accepted_errors / small_accepted if small_accepted and not accepted_unknown else None
        ),
        "rescues": rescues,
        "harms": harms,
        "escalated_pair_labels_unavailable": paired_unknown,
        "paired_comparison_applicable": policy != "fallback_only",
        "accounting": usage_summary(attempts),
        "predictions": predictions,
        "held_out_access_enabled": False,
        "routing_threshold_selected": False,
        "estimate_type": "cached paired development replay",
    }


def threshold_frontier(cases: list[PairedCase]) -> list[dict]:
    """All distinct eligible-score tie boundaries plus accept-none; no optimum."""
    rows = checked_cases(cases)
    scores = sorted(
        {r.small_mean_nll for r in rows if r.small.usable and r.small_mean_nll is not None}
    )
    return [evaluate(rows, "gated", threshold=t) for t in (None, *scores)]
