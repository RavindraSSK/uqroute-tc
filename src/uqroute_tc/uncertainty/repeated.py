"""Ten-sample entropy and disagreement over canonical tool-call outputs."""

from __future__ import annotations

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
) -> RepeatedScores:
    """Compare canonical-call clusters with exact-output clusters.

    This provisional policy assigns empty, parse failure, and ambiguous
    unparsed/no-call outcomes separate canonical keys. The treatment of
    ambiguous no-call output must be audited and frozen before evaluation.
    """
    if len(outputs) != expected_samples:
        raise ValueError(f"expected exactly {expected_samples} samples")
    if any(not isinstance(raw, str) for raw in outputs):
        raise TypeError("outputs must be strings")
    parsed: list[CanonicalPrediction] = [
        parse_prediction(raw, benchmark, reference_parser) for raw in outputs
    ]
    return RepeatedScores(
        canonical=cluster_scores([outcome.key for outcome in parsed],
                                 expected_samples=expected_samples),
        exact_string=cluster_scores(outputs, expected_samples=expected_samples),
        statuses=tuple(outcome.status for outcome in parsed),
    )
