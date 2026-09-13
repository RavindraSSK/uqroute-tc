import json
from pathlib import Path
from typing import Any

import pytest

from uqroute_tc.data.audit import audit_dataset, audit_transition_release


def _row(
    row_id: str,
    *,
    category: str = "BFCL_v3_multiple",
    original_id: str = "multiple_193",
    conversation: str = "test request",
    perturbation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
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
    if perturbation is not None:
        row["perturbation"] = json.dumps(perturbation)
    return row


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _write_transition_runner(repo_root: Path, fault_types: tuple[str, ...]) -> None:
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True)
    messages = {fault_type: f"error for {fault_type}" for fault_type in fault_types}
    (scripts_dir / "run_eval.py").write_text(
        "\n".join(
            [
                "from pathlib import Path",
                f"TRANSITION_ERROR_MESSAGES: dict[str, str] = {messages!r}",
                "def main():",
                "    parser.add_argument('--skip-multi-turn', action='store_true', default=True)",
                "    parser.add_argument(",
                "        '--transition-type',",
                "        choices=tuple(TRANSITION_ERROR_MESSAGES.keys()),",
                "    )",
                "    args = parser.parse_args()",
                "    data_dir = Path(args.data_dir)",
                "    if args.files:",
                "        files = [data_dir / name for name in args.files]",
                "    elif args.mode == 'transition':",
                "        files = [data_dir / 'clean.jsonl']",
                "    else:",
                "        files = sorted(data_dir.glob('*.jsonl'))",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_published_total(repo_root: Path, total: int) -> None:
    (repo_root / "README.md").write_text(
        f"The release has {total:,} predictions per model in total.\n",
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


def test_transition_audit_measures_generation_and_reconciliation(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "hf_data" / "datasets" / "api_eval"
    data_dir.mkdir(parents=True)
    clean_multiple = "bfcl_v3__BFCL_v3_multiple__multiple_193"
    clean_api = "apibank__level1_357"

    _write_jsonl(
        data_dir / "clean.jsonl",
        [
            _row(clean_multiple),
            _row(clean_api, category="level-1", original_id="0"),
        ],
    )
    _write_jsonl(
        data_dir / "same_name_A.jsonl",
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
    _write_transition_runner(tmp_path, ("timeout", "server_error"))
    _write_published_total(tmp_path, 8)

    report = audit_transition_release(tmp_path)

    assert report["fault_types"] == ["timeout", "server_error"]
    assert report["fault_type_count"] == 2
    assert report["transition_source_file"] == "hf_data/datasets/api_eval/clean.jsonl"
    assert report["transition_source_rows"] == 2
    assert report["eligible_transition_source_rows"] == 2
    assert report["eligible_transition_source_base_groups"] == 2
    assert report["runtime_variants_per_source_row"] == 2
    assert report["runtime_variants_per_base_group"] == [2]
    assert report["runtime_generated_transition_rows"] == 4
    assert report["static_transition_rows"] == 0
    assert report["static_transition_files"] == []
    assert report["excluded_multi_turn_rows"] == 1
    assert report["excluded_multi_turn_rows_in_transition_source"] == 0
    assert report["published_total_cases"] == 8
    assert report["stored_static_rows"] == 5
    assert report["stored_static_plus_runtime_transition_rows"] == 9
    assert report["published_minus_stored_plus_runtime"] == -1
    assert report["retained_single_turn_rows"] == 4
    assert report["retained_single_turn_plus_runtime_transition_rows"] == 8
    assert report["published_minus_retained_plus_runtime"] == 0
    assert report["clean_anchored_base_groups"] == 2
    assert report["all_single_base_groups"] == 3
    assert report["transition_base_groups_in_clean_anchored_population"] == 2
    assert report["transition_base_groups_in_full_population"] == 2
    assert report["full_population_groups_without_transition_source"] == 1


def test_transition_audit_measures_static_and_multi_turn_overlap(
    tmp_path: Path,
) -> None:
    data_dir = tmp_path / "hf_data" / "datasets" / "api_eval"
    data_dir.mkdir(parents=True)
    clean_id = "apibank__level1_357"

    _write_jsonl(
        data_dir / "clean.jsonl",
        [
            _row(clean_id, category="level-1", original_id="0"),
            _row(
                "bfcl_v3__multi_turn__clean_task",
                category="reward_multi_turn_test",
                original_id="multi_turn_test",
            ),
        ],
    )
    _write_jsonl(
        data_dir / "transition_static.jsonl",
        [
            _row(
                clean_id,
                category="level-1",
                original_id="0",
                perturbation={"mdp_category": "transition", "type": "transient_timeout"},
            )
        ],
    )
    _write_transition_runner(
        tmp_path,
        ("timeout", "rate_limit", "malformed_response"),
    )
    _write_published_total(tmp_path, 5)

    report = audit_transition_release(tmp_path)

    assert report["runtime_generated_transition_rows"] == 3
    assert report["runtime_variants_per_base_group"] == [3]
    assert report["static_transition_rows"] == 1
    assert report["static_transition_files"] == ["transition_static.jsonl"]
    assert report["excluded_multi_turn_rows"] == 1
    assert report["excluded_multi_turn_rows_in_transition_source"] == 1
    assert report["published_minus_stored_plus_runtime"] == -1
    assert report["published_minus_retained_plus_runtime"] == 0
    assert report["transition_base_groups_in_clean_anchored_population"] == 1
    assert report["transition_base_groups_in_full_population"] == 1
