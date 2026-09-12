"""Base-task identity rules for the released RobustBench-TC data."""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from typing import Any

_SAME_NAME_ID = re.compile(
    r"^bfcl_v3__BFCL_v3_(parallel_multiple|multiple)_type_([A-E])"
    r"__same_name_\1_type_\2_(\d+)$"
)


def is_multi_turn(row: Mapping[str, Any]) -> bool:
    """Return the multi-turn decision used by the released runner."""
    category = str(row.get("category") or "")
    return "multi_turn" in category


def normalize_same_name_id(row_id: str) -> str | None:
    """Map a verified BFCL same-name variant ID to its task identity."""
    match = _SAME_NAME_ID.fullmatch(row_id)
    if match is None:
        return None

    family, _variant, number = match.groups()
    return f"bfcl_v3__BFCL_v3_{family}__{family}_{number}"


def canonical_base_id(
    row_id: str,
    clean_ids: Collection[str],
) -> str:
    """Return a base-task ID or fail on an unsupported identity pattern.

    Exact clean IDs are already stable across most perturbations. The only
    verified rewrite in release d5d0318 is the BFCL same-name A-E pattern.
    Some normalized same-name IDs are perturbation-only and therefore need
    not appear in ``clean_ids``.
    """
    if row_id in clean_ids:
        return row_id

    normalized = normalize_same_name_id(row_id)
    if normalized is not None:
        return normalized

    raise ValueError(f"Unrecognized RobustBench-TC row ID: {row_id}")
