"""Synthetic CPU regression tests; no benchmark, split, sidecar or model required."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import score_corrected as s

REPO = Path(__file__).resolve().parents[3]


def response(raw):
    return {'choices': [{'message': {'content': raw}, 'finish_reason': 'stop',
                         'logprobs': {'content': [{'token': c, 'bytes': list(c.encode()), 'logprob': -0.5} for c in raw]}}],
            'usage': {'prompt_tokens': 1, 'completion_tokens': len(raw), 'total_tokens': len(raw) + 1}}


class ScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = s.policy()
        # Only Git ancestry is mocked: real hash-checked parser/scorer/uncertainty
        # sources are executed. Synthetic fixtures never assert real outcomes.
        folder = REPO / 'tools/development_audits/corrected_generation_v1'
        import sys
        sys.path.insert(0, str(folder))
        import support
        sys.path.pop(0)
        cls.support = support
        with patch.object(support, 'verify_baseline', return_value='synthetic-head'):
            cls.workflow, cls.frozen, parse, score = s.load_dependencies(REPO, cls.rules)
        cls.parse = staticmethod(parse)
        cls.official = staticmethod(score)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.root = self.repo / 'artifacts/local_development_audits'
        self.evidence = self.root / 'evidence'; self.bundle = self.root / 'bundle'
        self.audit_dir = self.root / 'audit'; self.output = self.root / 'scores'
        self.rules = copy.deepcopy(type(self).rules)
        for name, raw in self.support.source_bytes(REPO).items():
            target = self.repo / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        task1 = s.loads(self.support.source_bytes(REPO)['docs/config/task1_single_sample_v1.json'])
        model = task1['models'][0]; generation = task1['single_sample']
        self.refs = []; self.rows = []; self.requests = []; self.payloads = {}
        self.responses = {}
        groups = {}
        texts = {'apibank': '{"name":"f","parameters":{"x":1}}',
                 'bfcl_v3': '[f(x=(1, 2))]',
                 'rotbench': 'Action: f\nAction Input: {"x":1}',
                 'toolalpaca': 'Action: f\nAction Input: {"x":1}',
                 'tooleyes': 'Action: f\nAction Input: {"x":999}'}
        for i, (benchmark, raw) in enumerate(texts.items()):
            group = 'synthetic_' + str(i); key = 'clean.jsonl:' + group
            messages = [{'role': 'system', 'content': 'synthetic'}, {'role': 'user', 'content': 'synthetic'}]
            req = {'case_key': key, 'benchmark': benchmark, 'canonical_base_id': group,
                   'messages_sha256': s.sha(s.canonical(messages).encode())}
            body = {'model': model['model_id'], 'messages': messages, 'temperature': generation['temperature'],
                    'max_tokens': generation['max_tokens'], 'logprobs': True, 'top_logprobs': generation['top_logprobs'], 'stream': False}
            req.update(request=body, request_sha256=self.support.digest(body), source_file='clean.jsonl', tools_sha256='synthetic')
            self.requests.append(req)
            cfg = {'method': 'rule_based' if benchmark == 'rotbench' else 'gpt_judge' if benchmark in ('toolalpaca', 'tooleyes') else 'exact_match',
                   'metrics': ['relevance' if benchmark == 'tooleyes' else 'complete_accuracy']}
            params = {'x': [1, 2]} if benchmark == 'bfcl_v3' else {'x': 1}
            ref = {'case_key': key, 'golden_answers': [{'name': 'f', 'parameters': params}], 'eval_config': cfg}
            self.refs.append(ref)
            row = {'case_key': key, 'benchmark': benchmark, 'canonical_base_id': group,
                   'source_file': 'clean.jsonl', 'construction_status': 'candidate', 'split': 'development', 'population': 'primary',
                   'official_labels_changed': False, 'corrected_messages_sha256': req['messages_sha256'],
                   'source_reference_sha256': s.sha(s.canonical(ref).encode()),
                   'reference_audit_status': 'completed_bounded_signals_only',
                   'reference_audit': {'review_flags': ['synthetic_ambiguity'], 'review_status': 'requires_review',
                       'objective_detection': {'cost_explicit_detected': False, 'latency_explicit_detected': False},
                       'reward_kind': None, 'changes_official_labels': False, 'excluded': False}}
            self.rows.append(row)
            groups[group] = {'benchmark': benchmark, 'split': 'development', 'population': 'primary'}
            r = response(raw); self.responses[benchmark] = r
            folder = 'run/cases/' + s.sha(key.encode())
            self.payloads[folder + '/http_response.bin'] = s.canonical(r).encode()
            self.payloads[folder + '/validation.json'] = s.canonical(self.workflow.evaluate(r, benchmark, self.frozen)).encode()
        self.manifest = {'version': self.workflow.config()['version'], 'scope': 'corrected-primary-development-only',
                         'held_out_access_enabled': False, 'main_experiment_ready': False,
                         'selection': 'feasibility-five', 'source_hashes': {n: s.sha(v) for n,v in self.support.source_bytes(REPO).items()},
                         'implementation_hashes': self.support.implementation_hashes(), 'model_settings': model,
                         'generation_settings': generation, 'server_settings': generation['server']}
        self.membership = {'split': 'development', 'population': 'primary', 'groups': groups,
                           'expected_groups': 5, 'expected_rows': 5}
        self.write_fixture()

    def write_fixture(self):
        self.manifest.update(requests_sha256=self.support.digest(self.requests), request_count=len(self.requests),
                             case_keys=[r['case_key'] for r in self.requests])
        self.payloads['prepared/manifest.json'] = s.canonical(self.manifest).encode()
        self.payloads['prepared/requests.json'] = s.canonical(self.requests).encode()
        self.rules['prepared_manifest_sha256'] = s.sha(self.payloads['prepared/manifest.json'])
        for name, raw in self.payloads.items():
            p = self.evidence / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(raw)
        self.rules['evidence_file_sha256'] = {n: s.sha(v) for n, v in self.payloads.items()}
        self.bundle.mkdir(parents=True, exist_ok=True); self.audit_dir.mkdir(parents=True, exist_ok=True)
        refs = ('\n'.join(s.canonical(r) for r in self.refs) + '\n').encode()
        membership = s.canonical(self.membership).encode()
        (self.bundle / 'references.jsonl').write_bytes(refs)
        (self.bundle / 'membership.json').write_bytes(membership)
        att = {'partition': 'development', 'population': 'primary', 'held_out_content_exported': False,
               'unselected_nested_payloads_decoded': 0,
               'benchmark_revision': 'd5d03180de41eb30a6c796d04a9bfbd9dad85c1d',
               'split_sha256': '688c1013d8fe9d5c1b454d14d4cbe215659e48adc7bdfd63175580e83e2eb0db',
               'group_count': 5, 'row_count': 5, 'case_key_digest': s.sha(s.canonical(sorted(r['case_key'] for r in self.refs)).encode()),
               'payload_hashes': {'references.jsonl': s.sha(refs), 'membership.json': s.sha(membership)}}
        raw = s.canonical(att).encode(); (self.bundle / 'attestation.json').write_bytes(raw)
        self.rules['attestation_sha256'] = s.sha(raw)
        raw = s.canonical(self.rows).encode(); (self.audit_dir / 'inventory.json').write_bytes(raw)
        self.rules['inventory_sha256'] = s.sha(raw)

    def execute(self):
        with patch.object(s, 'policy', return_value=self.rules), \
             patch.object(s, 'load_dependencies', return_value=(self.workflow, self.frozen, self.parse, self.official)), \
             patch.object(self.support, 'verify_baseline', return_value='synthetic-head'), \
             patch.object(s.subprocess, 'run'), patch.object(s.subprocess, 'check_output', return_value='synthetic-head\n'):
            return s.score(self.repo, self.evidence, self.bundle, self.audit_dir, self.output)

    def test_end_to_end_separate_panels_preserve_flags_and_inputs(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        out = self.execute()
        self.assertEqual(out['official_reference_compliance']['rows'], 4)
        self.assertEqual(out['tooleyes_relevance']['rows'], 1)
        self.assertEqual(out['tooleyes_relevance']['correct'], 1)
        self.assertEqual(out['official_reference_compliance']['flagged_rows_retained'], 4)
        self.assertFalse(out['held_out_access_enabled']); self.assertFalse(out['main_experiment_ready'])
        self.assertEqual(out['network_requests'], 0)
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        self.assertEqual({p.name for p in self.output.iterdir()}, {'summary.json', 'scores.json', 'provenance.json'})

    def test_raw_python_tuple_preserved_not_json_view(self):
        raw = '[f(x=(1, 2))]'
        calls = self.parse(raw, 'bfcl_v3')
        self.assertIsInstance(calls[0]['parameters']['x'], tuple)
        # Pinned scorer distinguishes tuple from list. A JSON roundtrip would
        # change this result; production adapter must retain the original type.
        ref = self.refs[1]
        direct = self.official({'benchmark': 'bfcl_v3', **ref, 'prediction': {'tool_calls': calls}})
        altered = self.official({'benchmark': 'bfcl_v3', **ref, 'prediction': {'tool_calls': json.loads(json.dumps(calls))}})
        self.assertFalse(direct['correct']); self.assertTrue(altered['correct'])
        self.execute()
        row = json.loads((self.output / 'scores.json').read_text())[1]
        self.assertEqual(row['official_score'], direct)

    def test_toolalpaca_exclusion_does_not_remove_official_score(self):
        self.execute()
        rows = json.loads((self.output / 'scores.json').read_text())
        row = next(r for r in rows if r['benchmark'] == 'toolalpaca')
        self.assertIsNone(row['meaningful_token_score']); self.assertTrue(row['official_score']['correct'])

    def test_reference_flag_does_not_override_incorrect_score(self):
        self.refs[0]['golden_answers'][0]['name'] = 'other'
        self.rows[0]['source_reference_sha256'] = s.sha(s.canonical(self.refs[0]).encode())
        self.write_fixture(); self.execute()
        row = json.loads((self.output / 'scores.json').read_text())[0]
        self.assertFalse(row['official_score']['correct']); self.assertFalse(row['ambiguity_exclusion_applied'])

    def test_existing_output_refused(self):
        self.output.mkdir(parents=True)
        with self.assertRaises(ValueError): self.execute()

    def test_output_overlap_refused(self):
        self.output = self.evidence / 'new'
        with self.assertRaises(ValueError): self.execute()

    def test_output_outside_artifacts_refused(self):
        self.output = self.repo / 'scores'
        with self.assertRaises(ValueError): self.execute()

    def test_tampered_response_refused(self):
        next(self.evidence.rglob('http_response.bin')).write_bytes(b'{}')
        with self.assertRaises(ValueError): self.execute()
        self.assertFalse(self.output.exists())

    def test_extra_evidence_refused(self):
        (self.evidence / 'extra').write_text('x')
        with self.assertRaises(ValueError): self.execute()

    def test_reference_sidecar_hash_refused(self):
        (self.bundle / 'references.jsonl').write_text('[]')
        with self.assertRaises(ValueError): self.execute()

    def test_attestation_checked_before_references(self):
        (self.bundle / 'attestation.json').write_text('{}')
        (self.bundle / 'references.jsonl').unlink()
        with self.assertRaisesRegex(ValueError, 'fingerprint'): self.execute()

    def test_inventory_fingerprint_refused(self):
        (self.audit_dir / 'inventory.json').write_text('[]')
        with self.assertRaises(ValueError): self.execute()

    def test_test_membership_rejected(self):
        self.membership['groups']['synthetic_0']['split'] = 'test'; self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def test_duplicate_reference_keys_rejected(self):
        self.refs[1]['case_key'] = self.refs[0]['case_key']; self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def test_reference_lineage_rejected(self):
        self.refs[0]['golden_answers'] = []; self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def test_blocked_case_rejected(self):
        self.rows[0]['construction_status'] = 'blocked'; self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def test_prompt_lineage_rejected(self):
        self.rows[0]['corrected_messages_sha256'] = '0' * 64; self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def test_validation_mismatch_rejected(self):
        name = next(n for n in self.payloads if n.endswith('validation.json'))
        self.payloads[name] = b'{}'; self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def test_truncated_response_rejected(self):
        name = next(n for n in self.payloads if n.endswith('http_response.bin'))
        r = s.loads(self.payloads[name]); r['choices'][0]['finish_reason'] = 'length'
        self.payloads[name] = s.canonical(r).encode(); self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def test_no_metric_substitution_for_tooleyes(self):
        self.refs[-1]['eval_config']['metrics'] = ['complete_accuracy']
        self.rows[-1]['source_reference_sha256'] = s.sha(s.canonical(self.refs[-1]).encode()); self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def test_frozen_workflow_hash_rejected(self):
        rules = copy.deepcopy(type(self).rules)
        rules['workflow_hashes']['support.py'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'implementation'):
            s.load_dependencies(REPO, rules)

    def test_frozen_scorer_hash_rejected(self):
        rules = copy.deepcopy(type(self).rules)
        rules['scorer_sha256_lf'] = '0' * 64
        with patch.object(self.support, 'verify_baseline', return_value='synthetic-head'):
            with self.assertRaisesRegex(ValueError, 'scorer'):
                s.load_dependencies(REPO, rules)

    def test_ambiguity_exclusion_rejected(self):
        self.rows[0]['reference_audit']['excluded'] = True; self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def test_wrong_group_rejected(self):
        self.rows[0]['canonical_base_id'] = 'unapproved'; self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def test_wrong_selected_count_rejected(self):
        self.requests.pop(); self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def test_unknown_method_rejected(self):
        self.refs[0]['eval_config']['method'] = 'unknown'
        self.rows[0]['source_reference_sha256'] = s.sha(s.canonical(self.refs[0]).encode()); self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def test_symlink_input_rejected(self):
        link = self.root / 'linked'
        try:
            link.symlink_to(self.evidence, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('Platform does not permit directory symlinks')
        self.evidence = link
        with self.assertRaises(ValueError): self.execute()

    def test_empty_panel_undefined(self):
        self.assertIsNone(s.panel([])['accuracy'])

    def test_duplicate_and_nonfinite_json_rejected(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}'):
            with self.assertRaises(ValueError): s.loads(raw)

    def test_frozen_policy_integrity(self):
        self.assertEqual(s.sha((s.HERE / 'scoring_policy_v1.json').read_bytes().replace(b'\r\n', b'\n')), s.POLICY_SHA)
        self.assertEqual(len(type(self).rules['evidence_file_sha256']), 36)


    def test_relative_cli_paths_produce_repository_relative_provenance(self):
        import os
        original = Path.cwd()
        try:
            os.chdir(self.repo)
            self.evidence = self.evidence.relative_to(self.repo)
            self.bundle = self.bundle.relative_to(self.repo)
            self.audit_dir = self.audit_dir.relative_to(self.repo)
            self.output = self.output.relative_to(self.repo)
            self.execute()
            provenance = s.loads(
                (self.output / 'provenance.json').read_bytes()
            )
            paths = provenance['input_sha256']
            self.assertTrue(paths)
            self.assertIn(
                'artifacts/local_development_audits/evidence/prepared/manifest.json',
                paths,
            )
            for name in paths:
                self.assertFalse(Path(name).is_absolute())
                self.assertNotIn(chr(92), name)
                self.assertTrue(
                    name.startswith('artifacts/local_development_audits/')
                )
        finally:
            os.chdir(original)


if __name__ == '__main__':
    unittest.main()
