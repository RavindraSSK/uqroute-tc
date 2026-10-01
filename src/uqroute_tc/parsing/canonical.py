"""Conservative, type-aware keys for the pinned benchmark's parsed tool calls.

The benchmark's ``run_eval.parse_tool_calls`` remains responsible for turning
raw Python/JSON/XML/ReAct output into ``[{name, parameters}, ...]``. This module
does not alter the calls passed to the official scorer.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class CanonicalPrediction:
    status: str
    key: str
    calls: tuple[dict[str, Any], ...]
    error: str | None = None


def _typed(value: Any) -> list[Any]:
    """Keep types and sequence order, ignoring only mapping insertion order."""
    if value is None:
        return ["null"]
    if isinstance(value, bool):
        return ["bool", value]
    if isinstance(value, int):
        return ["int", str(value)]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("nonfinite numeric argument")
        return ["float", value.hex()]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, (list, tuple)):
        return ["tuple" if isinstance(value, tuple) else "list", [_typed(x) for x in value]]
    if isinstance(value, dict):
        entries = [(_typed(key), _typed(item)) for key, item in value.items()]
        entries.sort(key=lambda pair: _serialize(pair[0]))
        return ["dict", [[key, item] for key, item in entries]]
    raise ValueError(f"unsupported argument type: {type(value).__name__}")


def _serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def canonical_key(calls: list[dict[str, Any]]) -> str:
    """Build a stable key without using gold answers or changing scorer inputs.

    Mapping key order is ignored. Call order, list order, argument types and
    values, case, and tool names are preserved. No schema-based coercion occurs.
    """
    if not isinstance(calls, list):
        raise ValueError("parsed calls must be a list")
    normalized = []
    for call in calls:
        if not isinstance(call, dict):
            raise ValueError("each call must be a mapping")
        name = call.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("call has no valid tool name")
        if "parameters" in call and "arguments" in call:
            raise ValueError("ambiguous parameter fields")
        parameters = call.get("parameters", call.get("arguments", {}))
        if not isinstance(parameters, dict):
            raise ValueError("call parameters must be a mapping")
        normalized.append(["call", name, _typed(parameters)])
    return _serialize(["calls", normalized])


def parse_prediction(
    raw: str,
    benchmark: str,
    reference_parser: Callable[[str, str], list[dict[str, Any]]],
) -> CanonicalPrediction:
    """Wrap the pinned parser; retain empty, no-call and failed outcomes.

    The official parser returns an empty list for both an intentional no-tool
    reply and some unrecognized outputs. Only an explicit ``[]`` is classified
    as ``no_calls``; other nonempty outputs with no parsed calls are labelled
    ``unparsed_or_no_call`` until a manual audit can resolve them.
    """
    if not isinstance(raw, str):
        raise TypeError("raw model output must be a string")
    if not raw.strip():
        return CanonicalPrediction("empty", '["empty"]', ())
    try:
        parsed = reference_parser(raw, benchmark)
        key = canonical_key(parsed)
    except Exception as exc:
        return CanonicalPrediction("parse_failure", '["parse_failure"]', (), str(exc))
    if not parsed:
        if raw.strip() == "[]":
            return CanonicalPrediction("no_calls", key, ())
        return CanonicalPrediction("unparsed_or_no_call", '["unparsed_or_no_call"]', ())
    return CanonicalPrediction("calls", key, tuple(parsed))
