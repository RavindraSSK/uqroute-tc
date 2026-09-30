"""Single-output uncertainty from saved, byte-aligned chosen-token evidence."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from uqroute_tc.inference.pilot import token_evidence


@dataclass(frozen=True)
class SingleSampleScores:
    visible_token_count: int
    sequence_nll: float
    mean_token_nll: float
    max_token_surprisal: float


def single_sample_scores(record: dict[str, Any]) -> SingleSampleScores:
    """Revalidate the original response; never score incomplete evidence.

    Meaningful-token uncertainty requires separate, audited token-to-call
    alignment and is intentionally absent from this initial component.
    """
    uqroute = record.get("uqroute") or {}
    if uqroute.get("status") != "complete":
        raise ValueError("record is not complete")
    response = uqroute.get("response") or {}
    choices = response.get("choices") or []
    if len(choices) != 1:
        raise ValueError("expected one saved response choice")
    if choices[0].get("finish_reason") == "length":
        raise ValueError("completion was truncated")
    checked = token_evidence(choices[0])
    if not checked["valid"]:
        raise ValueError(f"invalid chosen-token evidence: {checked['reason']}")
    saved = uqroute.get("evidence") or {}
    if not saved.get("valid"):
        raise ValueError("saved evidence was not validated")
    for field in ("visible_token_count", "visible_token_spans", "excluded_trailing_token"):
        if saved.get(field) != checked[field]:
            raise ValueError(f"saved {field} differs from the response")
    for field in ("sequence_nll", "mean_token_nll", "max_token_surprisal"):
        value = saved.get(field)
        if not isinstance(value, (int, float)) or not math.isclose(
            value, checked[field], rel_tol=1e-12, abs_tol=1e-12
        ):
            raise ValueError(f"saved {field} differs from the response")
    return SingleSampleScores(
        checked["visible_token_count"],
        checked["sequence_nll"],
        checked["mean_token_nll"],
        checked["max_token_surprisal"],
    )
