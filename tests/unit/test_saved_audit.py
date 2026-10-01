"""Audit checks all four pilots and surfaces mismatched saved evidence."""

import json
import tempfile
import unittest
from pathlib import Path

from uqroute_tc.inference.pilot import _record_path, token_evidence
from uqroute_tc.parsing.audit import PILOT_FOLDERS, audit_pilots


def parser(_raw, _benchmark):
    return [{"name": "weather", "parameters": {"city": "St. Louis"}}]


class SavedAuditTests(unittest.TestCase):
    def test_same_cases_are_audited_and_bad_evidence_is_reported(self):
        ids = [f"dev{i}" for i in range(5)]
        config = {"benchmark": {"revision": "pinned"}, "models": [
            {"model_id": model, "model_revision": "rev", "tokenizer_revision": "rev",
             "dtype": "bfloat16"} for model in PILOT_FOLDERS
        ]}
        split = {"assignments": {row_id: {"split": "development", "population": "primary"}
                                 for row_id in ids}}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for model, folder in PILOT_FOLDERS.items():
                location = root / folder
                location.mkdir()
                (location / "manifest.json").write_text(json.dumps({
                    "model_id": model, "model_revision": "rev", "tokenizer_revision": "rev",
                    "dtype": "bfloat16", "benchmark_revision": "pinned", "case_ids": ids,
                }))
                for row_id in ids:
                    raw = 'weather(city="St. Louis")'
                    choice = {"message": {"content": raw}, "finish_reason": "stop",
                              "logprobs": {"content": [
                                  {"token": raw, "bytes": list(raw.encode()), "logprob": -0.2}
                              ]}}
                    record = {"id": row_id, "benchmark": "bfcl_v3",
                              "prediction": {
                                  "raw_output": raw, "tool_calls": parser(raw, "bfcl_v3")
                              },
                              "uqroute": {"status": "complete", "response": {"choices": [choice]},
                                          "evidence": token_evidence(choice)}}
                    _record_path(location, row_id).parent.mkdir(exist_ok=True)
                    _record_path(location, row_id).write_text(json.dumps(record))
            report = audit_pilots(root, config, split, parser)
            self.assertEqual((report["total"], report["parser_matches_saved"],
                              report["valid_single_sample_scores"]), (20, 20, 20))
            bad_path = _record_path(root / next(iter(PILOT_FOLDERS.values())), ids[0])
            bad_record = json.loads(bad_path.read_text())
            bad_record["prediction"]["tool_calls"] = []
            bad_record["uqroute"]["evidence"]["sequence_nll"] = 999
            bad_path.write_text(json.dumps(bad_record))
            report = audit_pilots(root, config, split, parser)
            self.assertEqual((report["parser_matches_saved"],
                              report["valid_single_sample_scores"]), (19, 19))


if __name__ == "__main__":
    unittest.main()
