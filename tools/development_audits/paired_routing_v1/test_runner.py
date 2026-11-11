"""Publication and report boundaries without requiring private development inputs."""

import json
import tempfile
import unittest
from pathlib import Path

import analysis
import run_analysis
from test_analysis import case


class RunnerTests(unittest.TestCase):
    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            output = repo / run_analysis.OUTPUT
            output.mkdir(parents=True)
            marker = output / "preserve.txt"
            marker.write_text("unchanged")
            with self.assertRaisesRegex(ValueError, "preserve existing"):
                run_analysis.run(repo, output)
            self.assertEqual(marker.read_text(), "unchanged")

    def test_outside_artifacts_output_rejected_before_input_access(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            with self.assertRaisesRegex(ValueError, "Fresh output"):
                run_analysis.run(repo, repo / "outside")

    def test_synthetic_report_distinguishes_potential_and_actual_rescues(self):
        result = analysis.analyze_scope(
            [case("a", 0.1), case("b", 0.9, True, False)], [0, 1], [1, 2]
        )
        panel = "official_reference_compliance"
        summary = {
            "paired_panels": {
                "synthetic": {
                    panel: {
                        "rows": 2,
                        "small_matches": 1,
                        "fallback_matches": 1,
                        "minimum_fallback_rows": 0,
                        "all_pair_outcomes_small_then_fallback": result[
                            "all_pair_outcomes_small_then_fallback"
                        ],
                    }
                }
            }
        }
        # Keep both endpoints in this report fixture without creating real model claims.
        results = {"synthetic": {"panel/" + p: result for p in (panel, "tooleyes_relevance")}}
        report = run_analysis.report(summary, results)
        self.assertIn("Potential rescues", report)
        self.assertIn("not confidence intervals", report)
        self.assertIn("No deployment threshold", report)
        self.assertIn("not online latency", report)
        self.assertNotIn("NaN", run_analysis.canonical(result))
        self.assertEqual(json.loads(run_analysis.canonical(result)), result)


if __name__ == "__main__":
    unittest.main()
