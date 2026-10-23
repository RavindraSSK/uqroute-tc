"""Synthetic regression cases for diagnostic-only schema classification."""
import copy
import unittest
from repair import repair_apibank
from test_repair import T, api_prompt

class SchemaDiagnosticTests(unittest.TestCase):
    def test_missing_declaration_blocks_without_mutation(self):
        tool = copy.deepcopy(T)
        tool.update(name='unrelated', description='unrelated description')
        tool['parameters']['properties'] = {}
        before = copy.deepcopy(tool)
        with self.assertRaisesRegex(ValueError, '^No matching schema declaration for unrelated$'):
            repair_apibank(api_prompt([T]), [tool])
        self.assertEqual(tool, before)

    def test_conflicting_duplicate_name_blocks_in_both_orders(self):
        empty = copy.deepcopy(T)
        empty['parameters']['properties'] = {}
        for definitions in ([empty, T], [T, empty]):
            with self.subTest(definitions=definitions):
                with self.assertRaisesRegex(ValueError, '^Conflicting schema declarations for f$'):
                    repair_apibank(api_prompt(definitions), [empty, empty])

    def test_conflicting_alias_blocks(self):
        other = copy.deepcopy(T)
        other['name'] = 'g'
        other['parameters']['properties'] = {'y': {'type': 'int'}}
        alias = {'name': 'alias', 'description': 'desc', 'parameters': {'properties': {}}}
        with self.assertRaisesRegex(ValueError, '^Conflicting schema declarations for alias$'):
            repair_apibank(api_prompt([T, other]), [alias])

    def test_unique_schema_still_restored(self):
        empty = copy.deepcopy(T)
        empty['parameters']['properties'] = {}
        repaired, edits = repair_apibank(api_prompt([T]), [empty])
        self.assertEqual(repaired, [T])
        self.assertEqual(edits[-1]['kind'], 'restore_missing_properties')

    def test_explicit_empty_declaration_still_empty(self):
        empty = copy.deepcopy(T)
        empty['parameters']['properties'] = {}
        repaired, edits = repair_apibank(api_prompt([empty]), [empty])
        self.assertEqual(repaired, [empty])
        self.assertEqual(edits[-1]['kind'], 'retain_explicit_empty_schema')

    def test_identical_duplicate_schemas_are_not_conflicts(self):
        empty = copy.deepcopy(T)
        empty['parameters']['properties'] = {}
        repaired, _ = repair_apibank(api_prompt([T, T]), [empty, empty])
        self.assertEqual(repaired, [T, T])

if __name__ == '__main__':
    unittest.main()
