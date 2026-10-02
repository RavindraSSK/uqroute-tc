"""Deterministic, development-only subset for ten-generation diagnostics."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from uqroute_tc.data.identity import canonical_base_id, is_multi_turn

SEED = 1729
BENCHMARKS = ("apibank", "bfcl_v3", "rotbench", "toolalpaca", "tooleyes")
PAIR_FILES = ("query_paraphrase", "redundant", "CD_AB")
TOOLEYES_FILES = ("query_paraphrase", "redundant", "realistic_typos")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def select_repeated_subset(data_dir: Path, split: dict[str, Any]) -> list[dict[str, str]]:
    """Pick three disjoint development groups per benchmark without using labels.

    Each selected group contributes its clean row and one static perturbation.
    The Tooleyes release has no reward variants, so its third pair uses typos.
    """
    clean_rows = _read_rows(data_dir / "clean.jsonl")
    clean = {str(row["id"]): row for row in clean_rows}
    if len(clean) != len(clean_rows):
        raise ValueError("duplicate clean ID")
    assignments = split["assignments"]
    if split.get("benchmark_revision") != "d5d03180de41eb30a6c796d04a9bfbd9dad85c1d":
        raise ValueError("unexpected benchmark revision in split")

    selected: list[dict[str, str]] = []
    for benchmark in BENCHMARKS:
        used_groups: set[str] = set()
        stems = TOOLEYES_FILES if benchmark == "tooleyes" else PAIR_FILES
        for stem in stems:
            eligible: list[tuple[str, dict[str, Any]]] = []
            seen: set[str] = set()
            for row in _read_rows(data_dir / f"{stem}.jsonl"):
                if is_multi_turn(row) or row["benchmark"] != benchmark:
                    continue
                base = canonical_base_id(str(row["id"]), clean)
                assignment = assignments.get(base)
                if assignment != {"benchmark": benchmark, "population": "primary",
                                  "split": "development"}:
                    continue
                if base in seen:
                    raise ValueError(f"duplicate group in {stem}: {base}")
                seen.add(base)
                if base not in clean:
                    raise ValueError(f"no clean row for {base}")
                eligible.append((base, row))
            eligible.sort(key=lambda pair: (
                hashlib.sha256(f"uqroute-tc/repeated-subset-v1\0{SEED}\0"
                               f"{benchmark}\0{stem}\0{pair[0]}".encode()).hexdigest(),
                pair[0],
            ))
            choice = next(((base, row) for base, row in eligible if base not in used_groups), None)
            if choice is None:
                raise ValueError(f"no distinct development group for {benchmark}/{stem}")
            base, row = choice
            used_groups.add(base)
            selected.extend((
                {"benchmark": benchmark, "base_id": base, "source_file": "clean.jsonl",
                 "case_id": base},
                {"benchmark": benchmark, "base_id": base,
                 "source_file": f"{stem}.jsonl", "case_id": str(row["id"])},
            ))
    if len(selected) != 30:
        raise AssertionError("expected 15 clean/perturbed pairs")
    return selected
