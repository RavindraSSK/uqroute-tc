"""Prompt, lineage and membership checks; fixtures contain no real case content."""

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import inputs
import run_analysis
from test_analysis import case


def fixture():
    row = case("a", 0.1)
    request = {
        "case_key": "a",
        "benchmark": "bfcl_v3",
        "canonical_base_id": "groupa",
        "source_file": "clean.jsonl",
        "messages_sha256": "m",
        "tools_sha256": "t",
        "request": {
            "model": "Qwen/Qwen2.5-1.5B-Instruct",
            "temperature": 0.001,
            "messages": [{"role": "user", "content": "synthetic"}],
        },
    }
    member = {
        "case_key": "a",
        "benchmark": "bfcl_v3",
        "canonical_base_id": "groupa",
        "construction_status": "candidate",
        "population": "primary",
        "split": "development",
    }
    a = {
        "request": request,
        "member": member,
        "panel": row.panel,
        "flags": [],
        "nll": 0.1,
        "outcome": row.small,
    }
    b = copy.deepcopy(a)
    b["request"]["request"]["model"] = inputs.FALLBACK_ID
    b["outcome"] = row.fallback
    b["nll"] = None
    return {"a": a}, {"a": b}


class InputTests(unittest.TestCase):
    def test_join_preserves_opposite_labels_without_fallback_nll(self):
        a, b = fixture()
        rows = inputs.join(a, b)
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0].small.reference_correct)
        self.assertTrue(rows[0].fallback.reference_correct)

    def test_actual_prompt_and_settings_checked_even_when_hashes_match(self):
        for field, value in (("messages", []), ("temperature", 0.7)):
            a, b = fixture()
            b["a"]["request"]["request"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                inputs.join(a, b)

    def test_each_lineage_field_checked(self):
        for field in inputs.LINEAGE:
            a, b = fixture()
            b["a"]["request"][field] = "different"
            with self.subTest(field=field), self.assertRaises(ValueError):
                inputs.join(a, b)

    def test_primary_development_candidate_membership_required(self):
        for role in (0, 1):
            for field, value in (
                ("split", "test"),
                ("population", "sensitivity_only"),
                ("construction_status", "blocked"),
                ("canonical_base_id", "other"),
                ("benchmark", "other"),
                ("case_key", "other"),
            ):
                a, b = fixture()
                (a, b)[role]["a"]["member"][field] = value
                with self.subTest(role=role, field=field), self.assertRaises(ValueError):
                    inputs.join(a, b)

    def test_empty_and_different_case_sets_rejected(self):
        a, b = fixture()
        for x, y in (({}, {}), (a, {}), ({}, b)):
            with self.assertRaises(ValueError):
                inputs.join(x, y)

    def test_wrong_models_panels_and_reference_flags_rejected(self):
        for target in ("small_model", "fallback_model", "panel", "flags"):
            a, b = fixture()
            if target == "small_model":
                a["a"]["request"]["request"]["model"] = inputs.FALLBACK_ID
            elif target == "fallback_model":
                b["a"]["request"]["request"]["model"] = "other"
            else:
                b["a"][target] = "wrong" if target == "panel" else ["newflag"]
            with self.subTest(target=target), self.assertRaises(ValueError):
                inputs.join(a, b)

    def test_identically_wrong_panel_still_rejected(self):
        a, b = fixture()
        a["a"]["panel"] = b["a"]["panel"] = "tooleyes_relevance"
        with self.assertRaises(ValueError):
            inputs.join(a, b)

    def test_policy_and_frozen_source_fingerprints_match(self):
        raw = (Path(__file__).parent / "policy.json").read_bytes().replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), run_analysis.POLICY_SHA)
        inputs.check_sources(run_analysis.REPO, json.loads(raw))

    def test_missing_input_names_are_actionable(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "missing.json"
            with self.assertRaisesRegex(ValueError, "missing.json"):
                inputs.regular(missing)

    def test_source_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.py"
            path.write_text("modified")
            with self.assertRaisesRegex(ValueError, "source.py"):
                inputs.check_sources(Path(folder), {"source_sha256_lf": {"source.py": "0" * 64}})


if __name__ == "__main__":
    unittest.main()
