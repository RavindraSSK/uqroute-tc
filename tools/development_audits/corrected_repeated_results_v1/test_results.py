"""Synthetic checks for matched repeated-sample comparisons; no benchmark access."""
import copy
import importlib.util
from pathlib import Path
import unittest


REPO = Path(__file__).resolve().parents[3]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analysis = load("repeated_results", Path(__file__).with_name(
    "run_qwen7b_corrected_repeated_analysis_v1.py"))
metrics = load("results_metrics", REPO / "tools/development_audits/"
               "three_model_uncertainty_v1/metrics.py")


def cases():
    rows = []
    for i in range(30):
        panel = analysis.PANELS[i >= 24]
        rows.append({
            "case_key": f"fixture-{i}", "benchmark": "fixture",
            "canonical_base_id": f"group-{i // 2}", "source_file": "fixture.jsonl",
            "panel": panel, "single_official_score": {"correct": i % 2 == 0},
            "signals": {s: float(i % 2) for s in analysis.SIGNALS},
            "sample_slots": 10, "sample_slots_reference_match": 10 if i % 2 == 0 else 0,
            "canonical": {"cluster_count": 1},
        })
    return {m: copy.deepcopy(rows) for m in ("qwen15b", "llama3b", "qwen7b")}


class ComparisonTests(unittest.TestCase):
    def compare(self, rows):
        return analysis.compare(rows, metrics)

    def test_case_units_and_error_direction(self):
        result = self.compare(cases())
        ref = result["panels"][analysis.PANELS[0]]
        cohort = ref["cohorts"]["shared_whole_and_repeated"]
        self.assertEqual((cohort["cases"], cohort["canonical_groups"]), (24, 12))
        self.assertEqual(cohort["models"]["qwen7b"]["measures"]
                         ["canonical_entropy"]["auroc"], 1.0)
        self.assertEqual(ref["model_outcomes"]["qwen7b"]["sample_slots"], 240)
        self.assertFalse(result["held_out_access_enabled"])

    def test_joint_missingness_does_not_change_original_denominator(self):
        rows = cases()
        rows["llama3b"][0]["signals"]["single_meaningful_token_nll"] = None
        ref = self.compare(rows)["panels"][analysis.PANELS[0]]
        self.assertEqual(ref["original_cases"], 24)
        self.assertEqual(ref["cohorts"]["shared_whole_and_repeated"]["cases"], 24)
        self.assertEqual(ref["cohorts"]["shared_all_signals"]["cases"], 23)

    def test_model_outcomes_are_not_pooled_labels(self):
        rows = cases()
        for r in rows["llama3b"]:
            r["single_official_score"]["correct"] = True
        cohort = self.compare(rows)["panels"][analysis.PANELS[0]]["cohorts"]\
            ["shared_whole_and_repeated"]["models"]
        self.assertIsNone(cohort["llama3b"]["measures"]["single_mean_token_nll"]["auroc"])
        self.assertEqual(cohort["qwen7b"]["measures"]["single_mean_token_nll"]["auroc"], 1.0)

    def test_identity_and_denominator_failures(self):
        for mutation in ("duplicate", "lineage", "missing", "panel", "label"):
            with self.subTest(mutation=mutation):
                rows = cases()
                if mutation == "duplicate":
                    rows["llama3b"].append(copy.deepcopy(rows["llama3b"][0]))
                elif mutation == "lineage":
                    rows["llama3b"][0]["canonical_base_id"] = "other"
                elif mutation == "missing":
                    rows["llama3b"].pop()
                elif mutation == "panel":
                    for model in rows:
                        rows[model][0]["panel"] = analysis.PANELS[1]
                else:
                    rows["llama3b"][0]["single_official_score"]["correct"] = 1
                with self.assertRaises(ValueError):
                    self.compare(rows)


if __name__ == "__main__":
    unittest.main()
