"""Exercise all-row loader wiring with synthetic saved-score and replay fixtures."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import inputs


def encoded(value):
    return json.dumps(value, sort_keys=True).encode()


class LoaderTests(unittest.TestCase):
    def execute_fixture(self, *, bad_timing=False, bad_status=False):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            root = repo / inputs.ROOT
            evidence = root / "evidence"
            previous = root / "scored"
            previous.mkdir(parents=True)
            inventory_path = root / "full_primary_audit_v1/inventory.json"
            inventory_path.parent.mkdir()
            requests, inventory, scores, records = [], [], [], []
            rules = {"prepared_manifest_sha256": "m", "evidence_file_sha256": {}}
            for i in range(1728):
                key = "synthetic-" + str(i)
                request = {"case_key": key, "benchmark": "bfcl_v3", "canonical_base_id": key}
                requests.append(request)
                inventory.append(
                    request
                    | {
                        "population": "primary",
                        "split": "development",
                        "construction_status": "candidate",
                    }
                )
                status = "invalid_evidence" if i == 0 else "complete"
                whole = None if i == 0 else {"mean_token_nll": 0.1}
                scores.append(
                    request
                    | {
                        "evidence_status": status,
                        "whole_output_scores": whole,
                        "panel": "official_reference_compliance",
                        "reference_review_flags": [],
                        "official_score": {"correct": True},
                    }
                )
                records.append(
                    request
                    | {
                        "status": status,
                        "whole_output_scores": whole,
                        "parser_status": "unparsed_or_no_call" if i == 1 else "calls",
                        "parsed_calls_json_view": [] if i == 1 else [{"name": "synthetic"}],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
                    }
                )
                name = "run/cases/" + inputs.sha(key.encode()) + "/response_metadata.json"
                path = evidence / name
                path.parent.mkdir(parents=True)
                raw = encoded({"elapsed_seconds": 0.5})
                path.write_bytes(raw)
                rules["evidence_file_sha256"][name] = inputs.sha(raw)
            inventory_raw = encoded(inventory)
            inventory_path.write_bytes(inventory_raw)
            rules["inventory_sha256"] = inputs.sha(inventory_raw)
            summary = {"rows": 1728}
            saved = {"scores.json": scores, "summary.json": summary}
            replay_values = {"records.json": records, "summary.json": summary}
            for name, value in saved.items():
                (previous / name).write_bytes(encoded(value))
            (evidence / "replay").mkdir()
            for name, value in replay_values.items():
                (evidence / "replay" / name).write_bytes(encoded(value))
            if bad_timing:
                # Pin a deliberately different timing digest for a selected case.
                first = next(k for k in rules["evidence_file_sha256"] if k.startswith("run/"))
                rules["evidence_file_sha256"][first] = "0" * 64
            if bad_status:
                records[0]["status"] = "truncated"
                (evidence / "replay/records.json").write_bytes(encoded(records))

            def score(_repo, _evidence, _bundle, _audit, output):
                output.mkdir()
                for name, value in saved.items():
                    (output / name).write_bytes(encoded(value))
                (output / "provenance.json").write_bytes(encoded({"input_sha256": {}}))

            def replay(_repo, _prepared, _expected, _run, output):
                output.mkdir()
                for name, value in replay_values.items():
                    (output / name).write_bytes(encoded(value))

            workflow = SimpleNamespace(
                load_plan=lambda *_: ({"synthetic": True}, requests), replay=replay
            )
            scorer = SimpleNamespace(
                policy=lambda: rules,
                score=score,
                loads=json.loads,
                load_dependencies=lambda *_: (workflow, None, None, None),
                unique_index=lambda rows: {r["case_key"]: r for r in rows},
            )
            stage = root / "staging"
            stage.mkdir()
            with patch.object(inputs, "module", return_value=scorer):
                return inputs.verified_model(
                    repo,
                    {"scorer": "synthetic.py", "evidence": "evidence", "scored": "scored"},
                    stage,
                    "synthetic",
                    {},
                )

    def test_all_rows_retained_and_canonical_parser_presence_used(self):
        normalized, summary, manifest = self.execute_fixture()
        self.assertEqual(len(normalized), 1728)
        self.assertEqual(summary["rows"], 1728)
        self.assertTrue(manifest["synthetic"])
        self.assertIsNone(normalized["synthetic-0"]["nll"])
        self.assertTrue(normalized["synthetic-0"]["outcome"].reference_correct)
        self.assertFalse(normalized["synthetic-1"]["outcome"].has_parsed_call)
        self.assertEqual(normalized["synthetic-2"]["outcome"].usage.elapsed_seconds, 0.5)

    def test_timing_metadata_must_match_pinned_evidence(self):
        with self.assertRaisesRegex(ValueError, "timing metadata"):
            self.execute_fixture(bad_timing=True)

    def test_scoring_and_replay_statuses_must_match(self):
        with self.assertRaisesRegex(ValueError, "membership differs"):
            self.execute_fixture(bad_status=True)


if __name__ == "__main__":
    unittest.main()
