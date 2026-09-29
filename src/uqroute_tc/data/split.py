"""Reproducible base-task split for the pinned RobustBench-TC release."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from uqroute_tc.data.audit import audit_dataset
from uqroute_tc.data.identity import canonical_base_id, is_multi_turn

BENCHMARK_REVISION = "d5d03180de41eb30a6c796d04a9bfbd9dad85c1d"
SPLIT_SEED = 1729
TEST_NUMERATOR = 3
TEST_DENOMINATOR = 10


def assign_groups(
    clean_rows: list[dict[str, Any]],
    static_rows: list[dict[str, Any]],
    *,
    seed: int = SPLIT_SEED,
) -> dict[str, dict[str, str]]:
    """Stratify groups by population and benchmark, then hash-rank each stratum."""
    clean_ids = [str(row["id"]) for row in clean_rows]
    if len(clean_ids) != len(set(clean_ids)):
        raise ValueError("Duplicate clean IDs")
    if any(is_multi_turn(row) for row in clean_rows):
        raise ValueError("Clean source contains a multi-turn case")

    groups: dict[str, tuple[str, str]] = {}
    seen_clean: set[str] = set()
    for row in static_rows:
        if is_multi_turn(row):
            continue
        row_id = str(row["id"])
        base_id = canonical_base_id(row_id, clean_ids)
        benchmark = str(row["benchmark"])
        if not benchmark:
            raise ValueError(f"Missing benchmark for {row_id}")
        population = "primary" if base_id in clean_ids else "sensitivity_only"
        label = (population, benchmark)
        if base_id in groups and groups[base_id] != label:
            raise ValueError(f"Conflicting group labels for {base_id}")
        groups[base_id] = label
        if row_id in clean_ids:
            seen_clean.add(row_id)

    if seen_clean != set(clean_ids):
        raise ValueError("Some clean source IDs are absent from the static rows")

    strata: dict[tuple[str, str], list[str]] = defaultdict(list)
    for base_id, label in groups.items():
        strata[label].append(base_id)

    assignments: dict[str, dict[str, str]] = {}
    for (population, benchmark), base_ids in sorted(strata.items()):
        n_test = (len(base_ids) * TEST_NUMERATOR + TEST_DENOMINATOR // 2) // TEST_DENOMINATOR
        if not 0 < n_test < len(base_ids):
            raise ValueError(f"Stratum cannot be split: {population}/{benchmark}")

        ranked = sorted(
            base_ids,
            key=lambda base_id: (
                hashlib.sha256(
                    f"uqroute-tc/split-v1\0{seed}\0{population}\0{benchmark}\0{base_id}".encode()
                ).hexdigest(),
                base_id,
            ),
        )
        held_out = set(ranked[:n_test])
        for base_id in base_ids:
            assignments[base_id] = {
                "benchmark": benchmark,
                "population": population,
                "split": "test" if base_id in held_out else "development",
            }

    return dict(sorted(assignments.items()))


def build_manifest(data_dir: Path, *, seed: int = SPLIT_SEED) -> dict[str, Any]:
    """Audit the clone and produce a manifest without reading model predictions."""
    data_dir = data_dir.resolve()
    repo_root = data_dir.parents[2]
    if data_dir != repo_root / "hf_data" / "datasets" / "api_eval":
        raise ValueError("Expected hf_data/datasets/api_eval inside the benchmark clone")

    revision = subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True
    ).strip()
    if revision != BENCHMARK_REVISION:
        raise ValueError(f"Expected benchmark revision {BENCHMARK_REVISION}, got {revision}")
    dirty = subprocess.check_output(
        ["git", "-C", str(repo_root), "status", "--porcelain", "--", "hf_data/datasets/api_eval"],
        text=True,
    )
    if dirty:
        raise ValueError("Benchmark evaluation data contains uncommitted changes")

    audit = audit_dataset(data_dir)
    if not audit["valid"]:
        raise ValueError("Benchmark population audit failed")

    paths = sorted(data_dir.glob("*.jsonl"))
    clean_rows = [json.loads(line) for line in (data_dir / "clean.jsonl").read_text().splitlines()]
    static_rows = [
        json.loads(line)
        for path in paths
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assignments = assign_groups(clean_rows, static_rows, seed=seed)

    clean_ids = {str(row["id"]) for row in clean_rows}
    group_counts: dict[str, Counter[str]] = defaultdict(Counter)
    stratum_counts: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    row_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for assignment in assignments.values():
        group_counts[assignment["population"]][assignment["split"]] += 1
        stratum_counts[assignment["population"]][assignment["benchmark"]][
            assignment["split"]
        ] += 1
    for row in static_rows:
        if is_multi_turn(row):
            continue
        base_id = canonical_base_id(str(row["id"]), clean_ids)
        assignment = assignments[base_id]
        row_counts[assignment["population"]][assignment["split"]] += 1

    if len(assignments) != audit["all_single_base_groups"]:
        raise ValueError("Split does not cover all single-turn groups")
    if sum(sum(counts.values()) for counts in row_counts.values()) != audit["single_turn_rows"]:
        raise ValueError("Split does not cover all single-turn rows")

    return {
        "benchmark_revision": revision,
        "method": "sha256 rank of seed, population, benchmark, and canonical base ID",
        "seed": seed,
        "test_fraction": f"{TEST_NUMERATOR}/{TEST_DENOMINATOR}",
        "test_count_rule": "round half up within each population/benchmark stratum",
        "excludes_multi_turn": True,
        "group_counts": {key: dict(value) for key, value in sorted(group_counts.items())},
        "stratum_group_counts": {
            population: {
                benchmark: dict(counts) for benchmark, counts in sorted(benchmarks.items())
            }
            for population, benchmarks in sorted(stratum_counts.items())
        },
        "row_counts": {key: dict(value) for key, value in sorted(row_counts.items())},
        "assignments": assignments,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the RobustBench-TC grouped split.")
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    manifest = build_manifest(args.data_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")
    print("Group counts:", manifest["group_counts"])
    print("Row counts:", manifest["row_counts"])


if __name__ == "__main__":
    main()
