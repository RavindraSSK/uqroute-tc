"""Checks for the group boundary that protects held-out evaluation."""

from typing import Any

import pytest

from uqroute_tc.data.split import assign_groups


def _case(row_id: str, benchmark: str = "bfcl_v3", category: str = "single") -> dict[str, Any]:
    return {"id": row_id, "benchmark": benchmark, "category": category}


def test_related_variants_cannot_cross_split_and_order_does_not_matter() -> None:
    clean = [_case(f"bfcl_v3__BFCL_v3_multiple__multiple_{number}") for number in range(10)]
    perturbations = [
        _case(f"bfcl_v3__BFCL_v3_multiple_type_A__same_name_multiple_type_A_{number}")
        for number in range(10)
    ]
    static = clean + perturbations + [_case("excluded", category="multi_turn")]

    forward = assign_groups(clean, static)
    backward = assign_groups(list(reversed(clean)), list(reversed(static)))

    assert forward == backward
    assert len(forward) == 10
    assert sum(label["split"] == "test" for label in forward.values()) == 3
    for row in perturbations:
        original = row["id"].replace(
            "bfcl_v3__BFCL_v3_multiple_type_A__same_name_multiple_type_A_",
            "bfcl_v3__BFCL_v3_multiple__multiple_",
        )
        assert forward[original]["population"] == "primary"


def test_sensitivity_only_groups_get_their_own_stratum() -> None:
    clean = [_case(f"bfcl_v3__BFCL_v3_multiple__multiple_{number}") for number in range(10)]
    extra = [
        _case(f"bfcl_v3__BFCL_v3_multiple_type_B__same_name_multiple_type_B_{number}")
        for number in range(10, 20)
    ]
    assignments = assign_groups(clean, clean + extra)

    assert sum(label["split"] == "test" for label in assignments.values()) == 6
    assert sum(
        label["population"] == "sensitivity_only" and label["split"] == "test"
        for label in assignments.values()
    ) == 3


def test_unknown_variant_fails_instead_of_entering_wrong_group() -> None:
    clean = [_case(f"bfcl_v3__BFCL_v3_multiple__multiple_{number}") for number in range(10)]
    with pytest.raises(ValueError, match="Unrecognized RobustBench-TC row ID"):
        assign_groups(clean, clean + [_case("unknown__variant")])
