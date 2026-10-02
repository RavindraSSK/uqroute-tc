"""Repeated-sample selection stays in development groups and pairs each variant."""

import json
import tempfile
import unittest
from pathlib import Path

from uqroute_tc.data.repeated_subset import BENCHMARKS, select_repeated_subset


class RepeatedSubsetTests(unittest.TestCase):
    def test_development_pairs_are_distinct_and_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            clean = []
            perturbations = {name: [] for name in (
                "query_paraphrase", "redundant", "CD_AB", "realistic_typos"
            )}
            split = {"benchmark_revision": "d5d03180de41eb30a6c796d04a9bfbd9dad85c1d",
                     "assignments": {}}
            for benchmark in BENCHMARKS:
                for number in range(5):
                    case_id = f"{benchmark}__case_{number}"
                    clean.append({"id": case_id, "benchmark": benchmark, "category": "single"})
                    split["assignments"][case_id] = {
                        "benchmark": benchmark, "population": "primary",
                        "split": "test" if number == 4 else "development",
                    }
                    for rows in perturbations.values():
                        rows.append({"id": case_id, "benchmark": benchmark,
                                     "category": "single"})
            for stem, rows in {"clean": clean, **perturbations}.items():
                (data / f"{stem}.jsonl").write_text(
                    "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
                )

            selected = select_repeated_subset(data, split)
            self.assertEqual(selected, select_repeated_subset(data, split))
            self.assertEqual(len(selected), 30)
            self.assertEqual(len({row["base_id"] for row in selected}), 15)
            self.assertTrue(all(not row["base_id"].endswith("case_4") for row in selected))
            for first, second in zip(selected[::2], selected[1::2]):
                self.assertEqual(first["base_id"], second["base_id"])
                self.assertEqual(first["source_file"], "clean.jsonl")
                self.assertNotEqual(second["source_file"], "clean.jsonl")


if __name__ == "__main__":
    unittest.main()
