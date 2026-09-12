"""Audit the released RobustBench-TC evaluation population."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

from uqroute_tc.data.identity import (
    canonical_base_id,
    is_multi_turn,
    normalize_same_name_id,
)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _decode_object(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        value = json.loads(value)

    if not isinstance(value, dict):
        raise TypeError("Expected a JSON object")

    return value


def _canonical_json(value: Any) -> str:
    if isinstance(value, str):
        value = json.loads(value)

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _dataset_revision(data_dir: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(data_dir), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    return result.stdout.strip()


def audit_dataset(data_dir: Path) -> dict[str, Any]:
    """Return a machine-readable audit of a RobustBench-TC release."""
    paths = sorted(data_dir.glob("*.jsonl"))
    clean_path = data_dir / "clean.jsonl"

    if not paths:
        raise FileNotFoundError(f"No JSONL files found in {data_dir}")

    if not clean_path.exists():
        raise FileNotFoundError(f"Missing clean baseline: {clean_path}")

    clean_rows = _load_jsonl(clean_path)
    clean_ids = {str(row["id"]) for row in clean_rows}

    duplicate_clean_ids = len(clean_rows) - len(clean_ids)
    clean_conversations = {
        str(row["id"]): _canonical_json(row.get("conversation")) for row in clean_rows
    }

    total_rows = 0
    single_rows = 0
    multi_rows = 0
    clean_anchored_rows = 0
    perturbation_only_rows = 0
    source_decode_errors = 0
    missing_original_ids = 0

    all_groups: set[str] = set()
    perturbation_only_groups: set[str] = set()
    unrecognized_rows: list[dict[str, Any]] = []
    same_name_conversations: dict[str, set[str]] = defaultdict(set)
    rewritten_same_name_rows = 0
    per_file: dict[str, dict[str, int]] = {}

    for path in paths:
        file_counts = {
            "total": 0,
            "single_turn": 0,
            "multi_turn": 0,
            "clean_anchored": 0,
            "perturbation_only": 0,
            "unrecognized": 0,
        }

        for line_number, row in enumerate(_load_jsonl(path), start=1):
            total_rows += 1
            file_counts["total"] += 1

            try:
                source = _decode_object(row.get("source"))
            except (TypeError, json.JSONDecodeError):
                source_decode_errors += 1
                source = {}

            if not source.get("original_id"):
                missing_original_ids += 1

            if is_multi_turn(row):
                multi_rows += 1
                file_counts["multi_turn"] += 1
                continue

            single_rows += 1
            file_counts["single_turn"] += 1
            row_id = str(row.get("id") or "")

            try:
                base_id = canonical_base_id(row_id, clean_ids)
            except ValueError:
                file_counts["unrecognized"] += 1
                unrecognized_rows.append(
                    {
                        "file": path.name,
                        "line": line_number,
                        "id": row_id,
                    }
                )
                continue

            all_groups.add(base_id)

            if base_id in clean_ids:
                clean_anchored_rows += 1
                file_counts["clean_anchored"] += 1
            else:
                perturbation_only_rows += 1
                file_counts["perturbation_only"] += 1
                perturbation_only_groups.add(base_id)

            if normalize_same_name_id(row_id) is not None:
                rewritten_same_name_rows += 1
                same_name_conversations[base_id].add(_canonical_json(row.get("conversation")))

                if base_id in clean_conversations:
                    same_name_conversations[base_id].add(clean_conversations[base_id])

        per_file[path.name] = file_counts

    conversation_collisions = sorted(
        base_id
        for base_id, conversations in same_name_conversations.items()
        if len(conversations) > 1
    )

    valid = all(
        [
            duplicate_clean_ids == 0,
            source_decode_errors == 0,
            missing_original_ids == 0,
            len(unrecognized_rows) == 0,
            len(conversation_collisions) == 0,
            single_rows + multi_rows == total_rows,
        ]
    )

    return {
        "valid": valid,
        "dataset_revision": _dataset_revision(data_dir),
        "data_directory": str(data_dir.resolve()),
        "static_files": len(paths),
        "total_static_rows": total_rows,
        "single_turn_rows": single_rows,
        "multi_turn_rows": multi_rows,
        "clean_rows": len(clean_rows),
        "clean_base_groups": len(clean_ids),
        "all_single_base_groups": len(all_groups),
        "clean_anchored_rows": clean_anchored_rows,
        "clean_anchored_base_groups": len(all_groups & clean_ids),
        "perturbation_only_rows": perturbation_only_rows,
        "perturbation_only_base_groups": len(perturbation_only_groups),
        "rewritten_same_name_rows": rewritten_same_name_rows,
        "duplicate_clean_ids": duplicate_clean_ids,
        "source_decode_errors": source_decode_errors,
        "missing_original_ids": missing_original_ids,
        "unrecognized_rows": unrecognized_rows,
        "same_name_conversation_collisions": conversation_collisions,
        "files": per_file,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a RobustBench-TC evaluation release.")
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = audit_dataset(args.data_dir)
    rendered = json.dumps(report, indent=2, ensure_ascii=False)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)

    if not report["valid"]:
        raise SystemExit("Dataset audit failed validation.")


if __name__ == "__main__":
    main()
