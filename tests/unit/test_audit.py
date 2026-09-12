import json
from pathlib import Path
from typing import Any

import pytest

from uqroute_tc.data.audit import audit_dataset


def _row(
    row_id: str,
    *,
    category: str = "BFCL_v3_multiple",
    original_id: str = "multiple_193",
    conversation: str = "test request",
) -> dict[str, Any]:
    return {
        "id": row_id,
        "benchmark": "bfcl_v3",
        "category": category,
        "source": json.dumps(
            {
                "original_id": original_id,
                "benchmark": "bfcl_v3",
                "file": "source.json",
                "extra": {},
            }
        ),
        "conversation": json.dumps([{"role": "user", "content": conversation}]),
    }


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_audit_reports_clean_anchored_and_all_single_populations(
    tmp_path: Path,
) -> None:
    clean_multiple = "bfcl_v3__BFCL_v3_multiple__multiple_193"
    clean_api = "apibank__level1_357"

    _write_jsonl(
        tmp_path / "clean.jsonl",
        [
            _row(clean_multiple),
            _row(
                clean_api,
                category="level-1",
                original_id="0",
                conversation="API request",
            ),
        ],
    )

    _write_jsonl(
        tmp_path / "same_name_A.jsonl",
        [
            _row("bfcl_v3__BFCL_v3_multiple_type_A__same_name_multiple_type_A_193"),
            _row(
                "bfcl_v3__BFCL_v3_multiple_type_A__same_name_multiple_type_A_106",
                original_id="same_name_multiple_type_A_106",
                conversation="perturbation-only request",
            ),
            _row(
                "bfcl_v3__multi_turn__task",
                category="reward_multi_turn_test",
                original_id="multi_turn_test",
            ),
        ],
    )

    report = audit_dataset(tmp_path)

    assert report["valid"] is True
    assert report["static_files"] == 2
    assert report["total_static_rows"] == 5
    assert report["single_turn_rows"] == 4
    assert report["multi_turn_rows"] == 1
    assert report["clean_base_groups"] == 2
    assert report["all_single_base_groups"] == 3
    assert report["clean_anchored_rows"] == 3
    assert report["clean_anchored_base_groups"] == 2
    assert report["perturbation_only_rows"] == 1
    assert report["perturbation_only_base_groups"] == 1
    assert report["rewritten_same_name_rows"] == 2
    assert report["unrecognized_rows"] == []
    assert report["same_name_conversation_collisions"] == []


def test_audit_marks_unknown_identity_pattern_invalid(
    tmp_path: Path,
) -> None:
    clean_id = "apibank__level1_357"

    _write_jsonl(
        tmp_path / "clean.jsonl",
        [
            _row(
                clean_id,
                category="level-1",
                original_id="0",
            )
        ],
    )

    _write_jsonl(
        tmp_path / "query_paraphrase.jsonl",
        [_row("unknown__rewritten__task")],
    )

    report = audit_dataset(tmp_path)

    assert report["valid"] is False
    assert len(report["unrecognized_rows"]) == 1
    assert report["unrecognized_rows"][0]["id"] == ("unknown__rewritten__task")


def test_audit_requires_clean_baseline(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / "realistic_typos.jsonl",
        [_row("apibank__level1_357")],
    )

    with pytest.raises(FileNotFoundError, match="clean baseline"):
        audit_dataset(tmp_path)
