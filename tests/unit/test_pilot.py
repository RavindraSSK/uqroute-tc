"""Check the pilot's saved evidence and interruption/resume path."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from uqroute_tc.inference.pilot import (
    run_cases,
    select_clean_development_cases,
    token_evidence,
)


def _token(text, logprob=-0.2):
    return {"token": text, "bytes": list(text.encode("utf-8")), "logprob": logprob}


class _FakeClient:
    def __init__(self):
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls += 1
        raw = '[weather(city="St. Louis")]'
        choice = {
            "message": {"content": raw},
            "logprobs": {"content": [_token(raw), _token("<|im_end|>")]},
            "finish_reason": "stop",
        }
        return SimpleNamespace(model_dump=lambda **_ignored: {"choices": [choice], "usage": {}})


class PilotTests(unittest.TestCase):
    def test_token_alignment_excludes_only_verified_trailing_token(self):
        choice = {
            "message": {"content": "é"},
            "logprobs": {"content": [_token("é"), _token("<|im_end|>")]},
        }
        evidence = token_evidence(choice)
        self.assertTrue(evidence["valid"])
        self.assertEqual(evidence["visible_token_spans"], [[0, 2]])
        self.assertEqual(evidence["excluded_trailing_token"], "<|im_end|>")
        choice["logprobs"]["content"][0] = _token("x")
        self.assertFalse(token_evidence(choice)["valid"])

    def test_selection_does_not_take_held_out_case(self):
        samples = [{"id": key} for key in ("test", "dev1", "dev2")]
        split = {"assignments": {
            key: {"population": "primary", "split": side}
            for key, side in (("test", "test"), ("dev1", "development"),
                              ("dev2", "development"))
        }}
        self.assertEqual(
            [case["id"] for case in select_clean_development_cases(samples, split, 2)],
            ["dev1", "dev2"],
        )

    def test_second_run_skips_success_and_preserves_one_scoring_row(self):
        samples = [{
            "id": "dev1", "benchmark": "bfcl_v3", "golden_answers": [],
            "perturbation": None,
        }]
        config = {"model_id": "test-model", "temperature": 0.001,
                  "max_tokens": 1024, "top_logprobs": 5}
        client = _FakeClient()
        with tempfile.TemporaryDirectory() as folder:
            output_dir = Path(folder)
            args = (samples, client, lambda _sample: [], lambda _raw, _bench: [],
                    output_dir, config)
            self.assertEqual(run_cases(*args), (1, 0, 0))
            self.assertEqual(run_cases(*args), (0, 1, 0))
            self.assertEqual(client.calls, 1)
            rows = (output_dir / "pilot.predictions.jsonl").read_text().splitlines()
            self.assertEqual(len(rows), 1)
            record = json.loads(rows[0])
            self.assertEqual(record["uqroute"]["status"], "complete")
            self.assertEqual(record["uqroute"]["evidence"]["visible_token_count"], 1)
            with self.assertRaisesRegex(ValueError, "manifest differs"):
                run_cases(*args[:-1], {**config, "temperature": 0.5})


if __name__ == "__main__":
    unittest.main()
