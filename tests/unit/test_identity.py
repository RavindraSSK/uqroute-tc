import pytest

from uqroute_tc.data.identity import (
    canonical_base_id,
    is_multi_turn,
    normalize_same_name_id,
)


def test_exact_clean_id_is_preserved() -> None:
    row_id = "apibank__level1_357"

    assert canonical_base_id(row_id, {row_id}) == row_id


def test_same_name_multiple_id_is_normalized() -> None:
    row_id = "bfcl_v3__BFCL_v3_multiple_type_A__same_name_multiple_type_A_193"

    assert normalize_same_name_id(row_id) == ("bfcl_v3__BFCL_v3_multiple__multiple_193")


def test_same_name_parallel_multiple_id_is_normalized() -> None:
    row_id = "bfcl_v3__BFCL_v3_parallel_multiple_type_B__same_name_parallel_multiple_type_B_152"

    assert normalize_same_name_id(row_id) == (
        "bfcl_v3__BFCL_v3_parallel_multiple__parallel_multiple_152"
    )


def test_perturbation_only_normalized_id_is_allowed() -> None:
    row_id = "bfcl_v3__BFCL_v3_multiple_type_C__same_name_multiple_type_C_106"

    assert canonical_base_id(row_id, set()) == ("bfcl_v3__BFCL_v3_multiple__multiple_106")


def test_unknown_id_pattern_fails() -> None:
    with pytest.raises(ValueError, match="Unrecognized"):
        canonical_base_id("unknown__rewritten__task", set())


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("BFCL_v3_multiple", False),
        ("reward_multi_turn_miss_func_type_CD", True),
        (None, False),
    ],
)
def test_multi_turn_rule(category: str | None, expected: bool) -> None:
    assert is_multi_turn({"category": category}) is expected
