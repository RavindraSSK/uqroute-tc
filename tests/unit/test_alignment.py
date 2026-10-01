"""Audited BFCL token selection uses visible bytes and benchmark parsed calls."""

import unittest

from uqroute_tc.uncertainty.alignment import meaningful_token_score


def tokens(parts):
    return [{"token": value, "bytes": list(value.encode("utf-8")), "logprob": -cost}
            for value, cost in parts]


class AlignmentTests(unittest.TestCase):
    def test_selects_semantics_and_reports_mixed_syntax_tokens(self):
        raw = "[weather(city='München', days=2)]"
        chosen = tokens([
            ("[", 50), ("weather", .1), ("(city", .2), ("='", 50),
            ("Mün", .3), ("chen", .4), ("',", 50), (" days", .5),
            ("=", 50), ("2", .6), (")]", 50), ("<|eot_id|>", 50),
        ])
        parsed = [{"name": "weather", "parameters": {"city": "München", "days": 2}}]
        score = meaningful_token_score(raw, parsed, chosen, "stop")
        self.assertEqual(score.selected_token_indices, (1, 2, 4, 5, 7, 9))
        self.assertEqual(score.boundary_crossing_token_indices, (2, 7))
        self.assertAlmostEqual(score.mean_token_nll, .35)
        self.assertEqual(score.argument_value_spans[-1], (len(raw[:raw.index("2")].encode()),
                                                        len(raw[:raw.index("2")].encode()) + 1))

    def test_parsed_calls_must_match_full_expression(self):
        raw = "f(x=1)"
        with self.assertRaisesRegex(ValueError, "do not match"):
            meaningful_token_score(raw, [{"name": "f", "parameters": {"x": 2}}],
                                   tokens([(raw, .1)]), "stop")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            meaningful_token_score("f(x=1, x=2)", [],
                                   tokens([("f(x=1, x=2)", .1)]), "stop")

    def test_rejects_invalid_evidence_and_unsupported_expressions(self):
        parsed = [{"name": "f", "parameters": {"x": "ok"}}]
        with self.assertRaisesRegex(ValueError, "invalid token evidence"):
            meaningful_token_score("f(x='ok')", parsed, tokens([("f(x='no')", .1)]), "stop")
        with self.assertRaisesRegex(ValueError, "truncated"):
            meaningful_token_score("f(x='ok')", parsed, tokens([("f(x='ok')", .1)]), "length")
        with self.assertRaisesRegex(ValueError, "not a literal"):
            meaningful_token_score("f(x=other)", parsed, tokens([("f(x=other)", .1)]), "stop")
        with self.assertRaisesRegex(ValueError, "plain or dotted"):
            meaningful_token_score("f().g(x=1)", [], tokens([("f().g(x=1)", .1)]), "stop")

    def test_empty_string_and_dotted_name(self):
        raw = "[a.b(x='')]"
        parsed = [{"name": "a.b", "parameters": {"x": ""}}]
        score = meaningful_token_score(raw, parsed, tokens([(raw, .2)]), "stop")
        self.assertEqual(score.selected_token_indices, (0,))
        self.assertEqual(score.argument_value_spans, ((7, 9),))
        self.assertEqual(score.boundary_crossing_token_indices, (0,))


if __name__ == "__main__":
    unittest.main()
