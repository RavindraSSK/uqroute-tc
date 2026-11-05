"""Synthetic archive and metric checks; no inference or benchmark records."""
import importlib.util
import io
from pathlib import Path
import stat
import unittest
import zipfile


REPO = Path(__file__).resolve().parents[3]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


analysis = load("sensitivity_results", Path(__file__).with_name("run_sensitivity_results_v1.py"))
metrics = load("sensitivity_metrics", REPO / "tools/development_audits/"
               "three_model_uncertainty_v1/metrics.py")


def archive(names, symlink=False):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as z:
        for name in names:
            entry = zipfile.ZipInfo(name)
            if symlink:
                entry.create_system = 3
                entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(entry, b"fixture")
    return stream.getvalue()


class ArchiveTests(unittest.TestCase):
    def test_regular_member(self):
        self.assertEqual(analysis.unpack(archive(["prepared/manifest.json"]), {"prepared"}),
                         {"prepared/manifest.json": b"fixture"})

    def test_unsafe_names(self):
        for name in ("../escape", "/prepared/escape", "prepared/../escape",
                     "prepared\\escape", "prepared/C:escape", "other/file",
                     "prepared/trailing.", "prepared/trailing "):
            with self.subTest(name=name), self.assertRaises(ValueError):
                analysis.unpack(archive([name]), {"prepared"})

    def test_symlink_and_case_collision(self):
        with self.assertRaises(ValueError):
            analysis.unpack(archive(["prepared/link"], symlink=True), {"prepared"})
        with self.assertRaises(ValueError):
            analysis.unpack(archive(["prepared/A", "prepared/a"]), {"prepared"})


class MetricTests(unittest.TestCase):
    def test_unavailable_evidence_keeps_scoring_denominator_and_flags(self):
        def row(i, correct, available):
            whole = {s: float(i) for s in analysis.MEASURES[:-1]} if available else None
            return {"canonical_base_id": str(i), "official_score": {
                "correct": correct, "score": float(correct)}, "whole_output_scores": whole,
                "meaningful_token_score": None, "reference_review_flags": ["review_signal"],
                "evidence_status": "complete" if available else "truncated"}
        result = analysis.summarize(
            [row(0, True, True), row(1, False, True), row(2, True, False)],
            metrics, {"known_finished_session_wall_seconds": 1.0})
        self.assertEqual((result["rows"], result["reference_matches"]), (3, 2))
        self.assertEqual(result["flagged_rows_retained"], 3)
        self.assertEqual(result["whole_output_eligible"], 2)
        nll = result["available_case_metrics"]["mean_token_nll"]
        self.assertEqual(nll["discrimination"]["auroc"], 1.0)
        meaningful = result["available_case_metrics"]["meaningful_mean_token_nll"]
        self.assertIsNone(meaningful["discrimination"]["auroc"])


if __name__ == "__main__":
    unittest.main()
