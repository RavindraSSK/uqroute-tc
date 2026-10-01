"""Equivalence boundaries for uncertainty clustering, independent of the scorer."""

import json
import unittest

from uqroute_tc.parsing.canonical import canonical_key, parse_prediction


class CanonicalTests(unittest.TestCase):
    def test_mapping_order_and_different_surface_formats_can_share_a_key(self):
        python_calls = [{"name": "weather", "parameters": {"city": "St. Louis", "days": 2}}]
        json_calls = [{"name": "weather", "arguments": {"days": 2, "city": "St. Louis"}}]
        self.assertEqual(canonical_key(python_calls), canonical_key(json_calls))

    def test_meaningful_differences_are_preserved(self):
        base = [{"name": "weather", "parameters": {"days": 2, "ids": [1, 2]}}]
        key = canonical_key(base)
        variants = [
            [{"name": "Weather", "parameters": base[0]["parameters"]}],
            [{"name": "weather", "parameters": {"days": "2", "ids": [1, 2]}}],
            [{"name": "weather", "parameters": {"days": 2, "ids": [2, 1]}}],
            [{"name": "weather", "parameters": {"days": 2, "ids": (1, 2)}}],
            [{"name": "weather", "parameters": {"day": 2, "ids": [1, 2]}}],
            base + base,
            list(reversed(base + [{"name": "other", "parameters": {}}])),
        ]
        for variant in variants:
            with self.subTest(variant=variant):
                self.assertNotEqual(key, canonical_key(variant))

    def test_nested_mapping_reordering_does_not_change_key(self):
        left = [{"name": "f", "parameters": {"nested": {"x": True, "y": [None, 1]}}}]
        right = [{"name": "f", "parameters": {"nested": {"y": [None, 1], "x": True}}}]
        self.assertEqual(canonical_key(left), canonical_key(right))
        self.assertNotEqual(canonical_key(left), canonical_key([
            {"name": "f", "parameters": {"nested": {"x": 1, "y": [None, 1]}}}
        ]))

    def test_no_call_empty_and_invalid_are_distinct(self):
        no_calls = parse_prediction("[]", "bfcl_v3", lambda _r, _b: [])
        empty = parse_prediction("  ", "bfcl_v3", lambda _r, _b: [])
        ambiguous = parse_prediction("No tool is needed.", "bfcl_v3", lambda _r, _b: [])
        invalid = parse_prediction("[f(x=?)]", "bfcl_v3", lambda _r, _b: [
            {"name": "f", "parameters": [1]}
        ])
        self.assertEqual((no_calls.status, empty.status, invalid.status),
                         ("no_calls", "empty", "parse_failure"))
        self.assertEqual(ambiguous.status, "unparsed_or_no_call")
        self.assertEqual(len({no_calls.key, empty.key, invalid.key, ambiguous.key}), 4)
        self.assertIsNotNone(invalid.error)

    def test_call_sequence_is_preserved(self):
        calls = [{"name": "f", "parameters": {}}, {"name": "g", "parameters": {}}]
        self.assertNotEqual(canonical_key(calls), canonical_key(list(reversed(calls))))
        self.assertEqual(json.loads(canonical_key(calls))[0], "calls")

    def test_pinned_parser_output_is_not_rewritten_for_scoring(self):
        parsed = [{"name": "tools.lookup", "parameters": {"city": "St. Louis"}}]
        result = parse_prediction(
            '<tool_call>{"name":"tools.lookup","parameters":{"city":"St. Louis"}}</tool_call>',
            "apibank", lambda _raw, _bench: parsed,
        )
        self.assertEqual(result.status, "calls")
        self.assertEqual(result.calls, tuple(parsed))
        self.assertIs(result.calls[0], parsed[0])

    def test_malformed_call_or_nonfinite_number_is_rejected(self):
        for calls in ([{"name": "f", "parameters": {"x": float("nan")}}],
                      [{"name": "f", "parameters": {"x": float("inf")}}],
                      [{"name": "", "parameters": {}}],
                      [{"name": "f", "parameters": {}, "arguments": {}}]):
            with self.subTest(calls=calls), self.assertRaises(ValueError):
                canonical_key(calls)


if __name__ == "__main__":
    unittest.main()
