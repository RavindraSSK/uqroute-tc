"""Saved response evidence must cover visible bytes before scoring."""

import copy
import unittest

from uqroute_tc.inference.pilot import token_evidence
from uqroute_tc.uncertainty.single import single_sample_scores


def token(raw, logprob):
    return {"token": raw, "bytes": list(raw.encode()), "logprob": logprob}


def record(choice):
    return {"uqroute": {
        "status": "complete", "response": {"choices": [choice]},
        "evidence": token_evidence(choice),
    }}


class SingleTests(unittest.TestCase):
    def test_visible_tokens_only_and_saved_values_are_rechecked(self):
        choice = {"message": {"content": "aé"}, "finish_reason": "stop", "logprobs": {
            "content": [token("a", -.1), token("é", -.3), token("<|eot_id|>", -4)]
        }}
        scores = single_sample_scores(record(choice))
        self.assertEqual(scores.visible_token_count, 2)
        self.assertAlmostEqual(scores.sequence_nll, .4)
        self.assertAlmostEqual(scores.mean_token_nll, .2)
        self.assertAlmostEqual(scores.max_token_surprisal, .3)

    def test_mismatched_bytes_and_stale_saved_metrics_fail(self):
        choice = {"message": {"content": "a"}, "finish_reason": "stop", "logprobs": {
            "content": [token("a", -.1)]
        }}
        saved = record(choice)
        stale = copy.deepcopy(saved)
        stale["uqroute"]["response"]["choices"][0]["logprobs"]["content"][0] = token("b", -.1)
        with self.assertRaisesRegex(ValueError, "invalid chosen-token evidence"):
            single_sample_scores(stale)
        saved["uqroute"]["evidence"]["mean_token_nll"] = 999
        with self.assertRaisesRegex(ValueError, "saved mean_token_nll differs"):
            single_sample_scores(saved)

    def test_noncomplete_and_truncated_records_fail(self):
        choice = {"message": {"content": "a"}, "finish_reason": "length", "logprobs": {
            "content": [token("a", -.1)]
        }}
        saved = record(choice)
        with self.assertRaisesRegex(ValueError, "truncated"):
            single_sample_scores(saved)
        saved["uqroute"]["status"] = "invalid_evidence"
        with self.assertRaisesRegex(ValueError, "not complete"):
            single_sample_scores(saved)


if __name__ == "__main__":
    unittest.main()
