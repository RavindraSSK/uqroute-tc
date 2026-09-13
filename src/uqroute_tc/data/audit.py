"""Audit the released RobustBench-TC evaluation population."""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from collections import Counter, defaultdict
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


def _transition_runner_spec(run_eval_path: Path) -> dict[str, Any]:
    """Read transition choices and the default source file from ``run_eval.py``."""
    tree = ast.parse(run_eval_path.read_text(encoding="utf-8"), filename=str(run_eval_path))

    messages: dict[str, str] | None = None
    for node in tree.body:
        target_name: str | None = None
        value: ast.expr | None = None

        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value = node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                target_name = target.id
                value = node.value

        if target_name == "TRANSITION_ERROR_MESSAGES" and value is not None:
            candidate = ast.literal_eval(value)
            if not isinstance(candidate, dict) or not all(
                isinstance(key, str) and isinstance(message, str)
                for key, message in candidate.items()
            ):
                raise ValueError("TRANSITION_ERROR_MESSAGES must map strings to strings")
            messages = candidate
            break

    if not messages:
        raise ValueError(f"No transition fault definitions found in {run_eval_path}")

    main_node = next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "main"
        ),
        None,
    )
    if main_node is None:
        raise ValueError(f"No main function found in {run_eval_path}")

    transition_argument: ast.Call | None = None
    skip_multi_turn_argument: ast.Call | None = None
    for node in ast.walk(main_node):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        first_arg = node.args[0]
        if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
            continue
        if first_arg.value == "--transition-type":
            transition_argument = node
        elif first_arg.value == "--skip-multi-turn":
            skip_multi_turn_argument = node

    if transition_argument is None:
        raise ValueError(f"No --transition-type argument found in {run_eval_path}")

    choices = next(
        (keyword.value for keyword in transition_argument.keywords if keyword.arg == "choices"),
        None,
    )
    if choices is None or "TRANSITION_ERROR_MESSAGES" not in ast.unparse(choices):
        raise ValueError("--transition-type choices are not derived from transition definitions")

    if skip_multi_turn_argument is None:
        raise ValueError(f"No --skip-multi-turn argument found in {run_eval_path}")

    skip_default_node = next(
        (
            keyword.value
            for keyword in skip_multi_turn_argument.keywords
            if keyword.arg == "default"
        ),
        None,
    )
    if skip_default_node is None:
        raise ValueError("--skip-multi-turn has no explicit default")
    skip_multi_turn_default = ast.literal_eval(skip_default_node)
    if not isinstance(skip_multi_turn_default, bool):
        raise ValueError("--skip-multi-turn default must be boolean")

    source_files: set[str] = set()
    for node in ast.walk(main_node):
        if not isinstance(node, ast.If):
            continue
        test_text = ast.unparse(node.test)
        if "args.mode" not in test_text or "transition" not in test_text:
            continue
        for statement in node.body:
            if not isinstance(statement, ast.Assign):
                continue
            if not any(
                isinstance(target, ast.Name) and target.id == "files"
                for target in statement.targets
            ):
                continue
            source_files.update(
                value.value
                for value in ast.walk(statement.value)
                if isinstance(value, ast.Constant)
                and isinstance(value.value, str)
                and value.value.endswith(".jsonl")
            )

    if len(source_files) != 1:
        raise ValueError(
            "Expected one transition source JSONL file, found "
            f"{sorted(source_files)}"
        )

    return {
        "fault_types": list(messages),
        "source_file": next(iter(source_files)),
        "skip_multi_turn_default": skip_multi_turn_default,
    }


def _published_prediction_total(repo_root: Path) -> tuple[int, str]:
    readme_path = repo_root / "README.md"
    text = readme_path.read_text(encoding="utf-8")
    matches = re.findall(
        r"(\d[\d{},]*)\s+predictions per model in total",
        text,
        flags=re.IGNORECASE,
    )
    totals = {int(re.sub(r"\D", "", match)) for match in matches}

    if len(totals) != 1:
        raise ValueError(
            "Expected one published prediction total in "
            f"{readme_path}, found {sorted(totals)}"
        )

    return next(iter(totals)), str(readme_path.relative_to(repo_root))


def _optional_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, str):
        value = json.loads(value)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError("Expected a JSON object or null")
    return value


def audit_transition_release(repo_root: Path) -> dict[str, Any]:
    """Measure transition generation and population reconciliation from a clone."""
    repo_root = repo_root.resolve()
    data_dir = repo_root / "hf_data" / "datasets" / "api_eval"
    run_eval_path = repo_root / "scripts" / "run_eval.py"

    if not run_eval_path.exists():
        raise FileNotFoundError(f"Missing evaluation runner: {run_eval_path}")

    static_report = audit_dataset(data_dir)
    if not static_report["valid"]:
        raise ValueError("Static dataset audit failed; transition counts are not reliable")

    runner_spec = _transition_runner_spec(run_eval_path)
    source_path = data_dir / runner_spec["source_file"]
    if not source_path.exists():
        raise FileNotFoundError(f"Missing transition source file: {source_path}")

    clean_rows = _load_jsonl(data_dir / "clean.jsonl")
    clean_ids = {str(row["id"]) for row in clean_rows}

    all_single_groups: set[str] = set()
    clean_anchored_groups: set[str] = set()
    static_transition_rows = 0
    static_transition_files: set[str] = set()

    for path in sorted(data_dir.glob("*.jsonl")):
        for row in _load_jsonl(path):
            perturbation = _optional_object(row.get("perturbation"))
            if (
                perturbation is not None
                and str(perturbation.get("mdp_category") or "").lower()
                == "transition"
            ):
                static_transition_rows += 1
                static_transition_files.add(path.name)

            if is_multi_turn(row):
                continue

            base_id = canonical_base_id(str(row.get("id") or ""), clean_ids)
            all_single_groups.add(base_id)
            if base_id in clean_ids:
                clean_anchored_groups.add(base_id)

    source_rows = _load_jsonl(source_path)
    source_multi_turn_rows = sum(is_multi_turn(row) for row in source_rows)
    if runner_spec["skip_multi_turn_default"]:
        eligible_source_rows = [row for row in source_rows if not is_multi_turn(row)]
    else:
        eligible_source_rows = source_rows

    source_group_counts = Counter(
        canonical_base_id(str(row.get("id") or ""), clean_ids)
        for row in eligible_source_rows
    )
    source_groups = set(source_group_counts)
    fault_types = runner_spec["fault_types"]
    runtime_rows = len(eligible_source_rows) * len(fault_types)
    variants_per_group = sorted(
        {row_count * len(fault_types) for row_count in source_group_counts.values()}
    )
    published_total, published_source = _published_prediction_total(repo_root)
    stored_plus_runtime = static_report["total_static_rows"] + runtime_rows
    retained_plus_runtime = static_report["single_turn_rows"] + runtime_rows

    return {
        "dataset_revision": static_report["dataset_revision"],
        "runner_file": str(run_eval_path.relative_to(repo_root)),
        "transition_source_file": str(source_path.relative_to(repo_root)),
        "fault_types": fault_types,
        "fault_type_count": len(fault_types),
        "skip_multi_turn_default": runner_spec["skip_multi_turn_default"],
        "transition_source_rows": len(source_rows),
        "eligible_transition_source_rows": len(eligible_source_rows),
        "eligible_transition_source_base_groups": len(source_groups),
        "runtime_variants_per_source_row": len(fault_types),
        "runtime_variants_per_base_group": variants_per_group,
        "runtime_generated_transition_rows": runtime_rows,
        "static_transition_rows": static_transition_rows,
        "static_transition_files": sorted(static_transition_files),
        "excluded_multi_turn_rows": static_report["multi_turn_rows"],
        "excluded_multi_turn_rows_in_transition_source": source_multi_turn_rows,
        "published_total_cases": published_total,
        "published_total_source": published_source,
        "stored_static_rows": static_report["total_static_rows"],
        "stored_static_plus_runtime_transition_rows": stored_plus_runtime,
        "published_minus_stored_plus_runtime": published_total - stored_plus_runtime,
        "retained_single_turn_rows": static_report["single_turn_rows"],
        "retained_single_turn_plus_runtime_transition_rows": retained_plus_runtime,
        "published_minus_retained_plus_runtime": published_total - retained_plus_runtime,
        "clean_anchored_base_groups": len(clean_anchored_groups),
        "all_single_base_groups": len(all_single_groups),
        "transition_base_groups_in_clean_anchored_population": len(
            source_groups & clean_anchored_groups
        ),
        "transition_base_groups_in_full_population": len(
            source_groups & all_single_groups
        ),
        "full_population_groups_without_transition_source": len(
            all_single_groups - source_groups
        ),
    }


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
