"""Audited BFCL token selection uses visible bytes and benchmark parsed calls."""

import unittest

from uqroute_tc.uncertainty.alignment import meaningful_token_score


def tokens(parts):
    return [{"token": value, "bytes": list(value.encode("utf-8")), "logprob": -cost}
            for value, cost in parts]


class AlignmentTests(unittest.TestCase):
    def test_apibank_fenced_toolcall_aligns_name_and_json_arguments(self):
        raw = ('```plaintext\n<think>Call the tool.</think>\n'
               '<toolcall tool="ModifyReminder">\n{"city":"München"}\n```')
        chosen = tokens([
            ('```plaintext\n<think>Call the tool.</think>\n<toolcall tool="', 8),
            ('ModifyReminder', .1), ('">\n{"', 8), ('city', .2),
            ('":"', 8), ('München', .3), ('"}\n```', 8),
        ])
        parsed = [{'name': 'ModifyReminder', 'parameters': {'city': 'München'}}]
        score = meaningful_token_score(raw, parsed, chosen, 'stop', 'apibank')
        self.assertEqual(score.selected_token_indices, (1, 3, 5))
        self.assertEqual(score.boundary_crossing_token_indices, ())
        self.assertAlmostEqual(score.mean_token_nll, .2)
        data = raw.encode('utf-8')
        self.assertEqual([data[a:b].decode('utf-8') for a, b in score.argument_value_spans],
                         ['München'])

    def test_apibank_markup_requires_exact_parser_call(self):
        raw = ('```plaintext\n<toolcall tool="ModifyReminder">\n'
               '{"token":"abc"}\n```')
        with self.assertRaisesRegex(ValueError, 'does not match'):
            meaningful_token_score(raw, [{'name': 'ModifyReminder', 'parameters': {}}],
                                   tokens([(raw, .2)]), 'stop', 'apibank')
        other = '```plaintext\n<tool>GetUserToken</tool>\n{"username":"JohnDoe"}\n```'
        with self.assertRaises(ValueError):
            meaningful_token_score(other, [{'name': 'GetUserToken', 'parameters': {}}],
                                   tokens([(other, .2)]), 'stop', 'apibank')
        for malformed in (
            '```plaintext\n<toolcall tool="F">\n{"x":1,"x":2}\n```',
            '```plaintext\n<toolcall tool="F">\n{"x":1}\n```\nextra',
        ):
            with self.subTest(raw=malformed), self.assertRaises(ValueError):
                meaningful_token_score(malformed, [{'name': 'F', 'parameters': {'x': 1}}],
                                       tokens([(malformed, .2)]), 'stop', 'apibank')

    def test_apibank_standalone_json_selects_call_fields(self):
        raw = '{"name":"AddAgenda","parameters":{"token":"x","count":2}}'
        chosen = tokens([
            ('{"name":"', 9), ('AddAgenda', .1), ('","parameters":{"', 9),
            ('token', .2), ('":"', 9), ('x', .3), ('","', 9),
            ('count', .4), ('":', 9), ('2', .5), ('}}', 9),
        ])
        parsed = [{'name': 'AddAgenda', 'parameters': {'token': 'x', 'count': 2}}]
        score = meaningful_token_score(raw, parsed, chosen, 'stop', 'apibank')
        self.assertEqual(score.selected_token_indices, (1, 3, 5, 7, 9))
        self.assertEqual(score.boundary_crossing_token_indices, ())
        self.assertAlmostEqual(score.mean_token_nll, .3)

    def test_apibank_fenced_json_excludes_thought_and_uses_utf8_bytes(self):
        raw = ('<think>Looking up a date.</think>\n\n```plaintext\n'
               '{"name":"QueryHistoryToday","parameters":{"city":"München"}}\n```')
        start = raw.index('{"name"')
        chosen = tokens([
            (raw[:start], 9), (raw[start:], .2), ('<|im_end|>', 9),
        ])
        parsed = [{'name': 'QueryHistoryToday',
                   'parameters': {'city': 'München'}}]
        score = meaningful_token_score(raw, parsed, chosen, 'stop', 'apibank')
        self.assertEqual(score.selected_token_indices, (1,))
        self.assertEqual(score.boundary_crossing_token_indices, (1,))
        data = raw.encode('utf-8')
        self.assertEqual([data[a:b].decode('utf-8') for a,b in score.tool_name_spans],
                         ['QueryHistoryToday'])
        self.assertEqual([data[a:b].decode('utf-8') for a,b in score.argument_value_spans],
                         ['München'])

    def test_apibank_fenced_json_after_plain_prose_or_separate_think_fence(self):
        body = ('```json\n{"name":"Dictionary",'
                '"parameters":{"keyword":"perplexed"}}\n```')
        parsed = [{'name': 'Dictionary', 'parameters': {'keyword': 'perplexed'}}]
        prefixes = (
            'I will look up the definition.\n\n',
            'I will check München first.\n\n',
            '```plaintext\n<think>Look up the definition.</think>\n```\n',
        )
        for prefix in prefixes:
            with self.subTest(prefix=prefix):
                raw = prefix + body
                score = meaningful_token_score(raw, parsed,
                                               tokens([(prefix, 9), (body, .2)]),
                                               'stop', 'apibank')
                self.assertEqual(score.selected_token_indices, (1,))
                self.assertEqual(score.boundary_crossing_token_indices, (1,))
                data = raw.encode('utf-8')
                self.assertEqual([data[a:b].decode() for a,b in score.tool_name_spans],
                                 ['Dictionary'])
                self.assertEqual([data[a:b].decode() for a,b in score.argument_name_spans],
                                 ['keyword'])
                self.assertEqual([data[a:b].decode() for a,b in score.argument_value_spans],
                                 ['perplexed'])

    def test_apibank_rejects_ambiguous_preamble_before_fenced_json(self):
        suffix = '```json\n{"name":"F","parameters":{}}\n```'
        parsed = [{'name': 'F', 'parameters': {}}]
        for prefix in (
            '```json\n{"name":"G","parameters":{}}\n```\n',
            'Action: F\nAction Input: {}\n',
            'A second call F(x=2) is possible.\n',
            'I could also use Action: G.\n',
            '<tool>G</tool>\n',
            '```plaintext\n<think>incomplete\n```\n',
        ):
            raw = prefix + suffix
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                meaningful_token_score(raw, parsed, tokens([(raw, .2)]),
                                       'stop', 'apibank')

    def test_apibank_rejects_ambiguous_json(self):
        parsed = [{'name': 'F', 'parameters': {}}]
        for raw in (
            'Here is the call: {"name":"F","parameters":{}}',
            '{"name":"F","name":"G","parameters":{}}',
            '{"name":"F","parameters":{}} and another call',
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                meaningful_token_score(raw, parsed, tokens([(raw, .1)]),
                                       'stop', 'apibank')
        raw = '{"name":"F","parameters":{}}'
        with self.assertRaisesRegex(ValueError, 'does not match'):
            meaningful_token_score(raw, [{'name': 'G', 'parameters': {}}],
                                   tokens([(raw, .1)]), 'stop', 'apibank')

    def test_react_name_and_json_arguments(self):
        raw = ('Thought: A tool is needed.\nAction: explain_engine\n'
               'Action Input: {"engine_type":"gasoline"}')
        chosen = tokens([
            ('Thought: A tool is needed.\nAction: ', 9),
            ('explain_engine', .1), ('\nAction Input: {', 9),
            ('"engine_type"', .2), (':"', 9), ('gasoline', .3), ('"}', 9),
        ])
        parsed = [{'name': 'explain_engine',
                   'parameters': {'engine_type': 'gasoline'}}]
        score = meaningful_token_score(raw, parsed, chosen, 'stop', 'tooleyes')
        self.assertEqual(score.selected_token_indices, (1, 3, 5))
        self.assertEqual(score.boundary_crossing_token_indices, (3,))
        self.assertAlmostEqual(score.mean_token_nll, .2)

    def test_react_nested_json_and_unicode_byte_spans(self):
        raw = ('Thought: Check.\nAction: ask_to_user\n'
               'Action Input: {"question":"München", "extra":[true, 3]}')
        parsed = [{'name': 'ask_to_user', 'parameters': {
            'question': 'München', 'extra': [True, 3]}}]
        score = meaningful_token_score(raw, parsed, tokens([(raw, .4)]),
                                       'stop', 'rotbench')
        self.assertEqual(score.selected_token_indices, (0,))
        self.assertEqual(score.boundary_crossing_token_indices, (0,))
        start = len(raw[:raw.index('München')].encode('utf-8'))
        self.assertIn((start, start + len('München'.encode('utf-8'))),
                      score.argument_value_spans)

    def test_react_rejects_mismatched_or_ambiguous_calls(self):
        raw = 'Action: finish\nAction Input: {"answer":"No"}'
        chosen = tokens([(raw, .2)])
        with self.assertRaisesRegex(ValueError, 'does not match'):
            meaningful_token_score(raw, [{'name': 'ask_to_user', 'parameters': {}}],
                                   chosen, 'stop', 'rotbench')
        with self.assertRaisesRegex(ValueError, 'one ReAct Action'):
            meaningful_token_score(raw + '\nAction: finish',
                                   [{'name': 'finish', 'parameters': {'answer': 'No'}}],
                                   tokens([(raw + '\nAction: finish', .2)]),
                                   'stop', 'rotbench')
        with self.assertRaisesRegex(ValueError, 'complete JSON object'):
            meaningful_token_score(raw + '\nObservation: done',
                                   [{'name': 'finish', 'parameters': {'answer': 'No'}}],
                                   tokens([(raw + '\nObservation: done', .2)]),
                                   'stop', 'rotbench')
        with self.assertRaisesRegex(ValueError, 'ToolAlpaca meaningful-token alignment is unavailable'):
            meaningful_token_score(raw, [], chosen, 'stop', 'toolalpaca')

    def test_react_rejects_duplicate_argument_keys_even_when_parser_keeps_last(self):
        for arguments, parameters in (
            ('{"city":"Boston","city":"Paris"}', {'city': 'Paris'}),
            ('{"details":{"city":"Boston","city":"Paris"}}',
             {'details': {'city': 'Paris'}}),
        ):
            raw = 'Action: weather\nAction Input: ' + arguments
            parsed = [{'name': 'weather', 'parameters': parameters}]
            for benchmark in ('rotbench', 'tooleyes'):
                with self.subTest(benchmark=benchmark, arguments=arguments):
                    with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
                        meaningful_token_score(raw, parsed, tokens([(raw, .2)]),
                                               'stop', benchmark)

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
