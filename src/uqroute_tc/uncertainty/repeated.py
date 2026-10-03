"""Ten-sample entropy and disagreement over canonical tool-call outputs."""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from uqroute_tc.parsing.canonical import CanonicalPrediction, parse_prediction


@dataclass(frozen=True)
class ClusterScores:
    sample_count: int
    cluster_count: int
    entropy_nats: float
    disagreement: float
    cluster_sizes: tuple[int, ...]


@dataclass(frozen=True)
class RepeatedScores:
    canonical: ClusterScores
    exact_string: ClusterScores
    statuses: tuple[str, ...]


def cluster_scores(keys: Sequence[str], *, expected_samples: int = 10) -> ClusterScores:
    """Preserve failure/empty keys in the denominator and count duplicates."""
    if expected_samples < 2 or len(keys) != expected_samples:
        raise ValueError(f"expected exactly {expected_samples} samples")
    if any(not isinstance(key, str) for key in keys):
        raise ValueError("all cluster keys must be strings")
    sizes = tuple(sorted(Counter(keys).values(), reverse=True))
    entropy = -sum((n / len(keys)) * math.log(n / len(keys)) for n in sizes)
    return ClusterScores(len(keys), len(sizes), entropy, 1 - sizes[0] / len(keys), sizes)


def repeated_scores(
    outputs: Sequence[str],
    benchmark: str,
    reference_parser: Callable[[str, str], list[dict[str, Any]]],
    *,
    expected_samples: int = 10,
    generation_statuses: Sequence[str] | None = None,
) -> RepeatedScores:
    """Compare canonical-call clusters with exact-output clusters.

    This provisional policy assigns empty, parse failure, and ambiguous
    unparsed/no-call outcomes separate canonical keys. When generation
    statuses are provided, truncated and request-error slots receive their
    own clusters even if their partial text resembles a complete call.
    Token-evidence errors leave parseable raw outputs usable for this
    probability-free repeated measure, while remaining flagged in the record.
    """
    if len(outputs) != expected_samples:
        raise ValueError(f"expected exactly {expected_samples} samples")
    if any(not isinstance(raw, str) for raw in outputs):
        raise TypeError("outputs must be strings")
    if generation_statuses is not None:
        if len(generation_statuses) != expected_samples:
            raise ValueError(f"expected exactly {expected_samples} generation statuses")
        allowed = {"complete", "invalid_evidence", "truncated", "request_error"}
        if any(status not in allowed for status in generation_statuses):
            raise ValueError("unknown generation status")
    parsed: list[CanonicalPrediction] = []
    exact_keys: list[str] = []
    for index, raw in enumerate(outputs):
        status = generation_statuses[index] if generation_statuses is not None else "complete"
        if status in {"truncated", "request_error"}:
            parsed.append(CanonicalPrediction(status, json.dumps([status]), ()))
            exact_keys.append(json.dumps([status, raw], ensure_ascii=False))
        else:
            parsed.append(parse_prediction(raw, benchmark, reference_parser))
            exact_keys.append(raw if generation_statuses is None else
                              json.dumps(["output", raw], ensure_ascii=False))
    return RepeatedScores(
        canonical=cluster_scores([outcome.key for outcome in parsed],
                                 expected_samples=expected_samples),
        exact_string=cluster_scores(exact_keys, expected_samples=expected_samples),
        statuses=tuple(outcome.status for outcome in parsed),
    )
