"""Synthetic CPU regression tests; no benchmark, split, sidecar or model required."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import score_qwen7b_full as s

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
        self.rules['request_count'] = 5
        self.rules.update(inventory_rows=5,inventory_groups=5,construction_blocks=0,constructed_clean_rows=5,constructed_perturbed_rows=0)
        self.rules['by_benchmark'] = {b:1 for b in s.BENCHMARKS}
        for name, raw in self.support.source_bytes(REPO).items():
            target = self.repo / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        task1 = s.loads(self.support.source_bytes(REPO)['docs/config/task1_single_sample_v1.json'])
        model = task1['models'][2]; generation = task1['single_sample']
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
                         'selection': 'full-development', 'source_hashes': {n: s.sha(v) for n,v in self.support.source_bytes(REPO).items()},
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
               'group_count': len(self.membership['groups']), 'row_count': len(self.refs), 'case_key_digest': s.sha(s.canonical(sorted(r['case_key'] for r in self.refs)).encode()),
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
        self.assertEqual({p.name for p in self.output.iterdir()}, {'summary.json', 'scores.json', 'provenance.json', 'alignment_diagnostics.json'})

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

    def test_truncation_with_stale_validation_rejected(self):
        name = next(n for n in self.payloads if n.endswith('http_response.bin'))
        r = s.loads(self.payloads[name]); r['choices'][0]['finish_reason'] = 'length'
        self.payloads[name] = s.canonical(r).encode(); self.write_fixture()
        with self.assertRaises(ValueError): self.execute()

    def set_truncated(self, benchmark):
        row = next(r for r in self.requests if r['benchmark'] == benchmark)
        prefix = 'run/cases/' + s.sha(row['case_key'].encode())
        response = s.loads(self.payloads[prefix + '/http_response.bin'])
        response['choices'][0]['finish_reason'] = 'length'
        self.payloads[prefix + '/http_response.bin'] = s.canonical(response).encode()
        self.payloads[prefix + '/validation.json'] = s.canonical(self.workflow.evaluate(response, benchmark, self.frozen)).encode()
        self.write_fixture()

    def test_truncated_valid_call_retained_and_scored(self):
        self.set_truncated('apibank')
        out = self.execute()
        rows = s.loads((self.output / 'scores.json').read_bytes())
        row = next(r for r in rows if r['benchmark'] == 'apibank')
        self.assertEqual(out['official_reference_compliance']['rows'], 4)
        self.assertEqual(row['evidence_status'], 'truncated')
        self.assertTrue(row['official_score']['correct'])
        self.assertIsNone(row['whole_output_scores'])
        self.assertIsNone(row['meaningful_token_score'])
        self.assertEqual(row['alignment_diagnostic']['category'], 'truncated_output')

    def test_truncated_incomplete_call_not_repaired(self):
        req = next(r for r in self.requests if r['benchmark'] == 'bfcl_v3')
        prefix = 'run/cases/' + s.sha(req['case_key'].encode())
        self.payloads[prefix + '/http_response.bin'] = s.canonical(response('[f(x=')).encode()
        self.set_truncated('bfcl_v3')
        out = self.execute()
        row = next(r for r in s.loads((self.output / 'scores.json').read_bytes()) if r['benchmark'] == 'bfcl_v3')
        self.assertFalse(row['official_score']['correct'])
        self.assertEqual(out['official_reference_compliance']['rows'], 4)

    def test_truncated_tooleyes_stays_separate(self):
        self.set_truncated('tooleyes')
        out = self.execute()
        self.assertEqual(out['tooleyes_relevance']['rows'], 1)
        self.assertEqual(out['tooleyes_relevance']['correct'], 1)
        self.assertEqual(out['evidence_eligibility']['by_panel']['tooleyes_relevance']['whole_output_eligible'], 0)

    def test_wrong_model_rejected(self):
        self.rules['model_id'] = 'wrong/model'
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

    def test_apibank_xml_keeps_official_score_but_explains_alignment(self):
        key=self.requests[0]['case_key'];folder='run/cases/'+s.sha(key.encode())
        r=response('<tool_call>{"name":"f","parameters":{"x":1}}</tool_call>')
        self.payloads[folder+'/http_response.bin']=s.canonical(r).encode()
        self.payloads[folder+'/validation.json']=s.canonical(self.workflow.evaluate(r,'apibank',self.frozen)).encode()
        self.write_fixture();self.execute()
        row=s.loads((self.output/'scores.json').read_bytes())[0]
        self.assertEqual(row['alignment_diagnostic']['category'],'apibank_frozen_format_exclusion')
        self.assertTrue(row['official_score']['correct'])
        self.assertIsNone(row['meaningful_token_score'])

    def test_no_parsed_call_remains_in_official_denominator(self):
        key=self.requests[0]['case_key'];folder='run/cases/'+s.sha(key.encode())
        r=response('No call provided.')
        self.payloads[folder+'/http_response.bin']=s.canonical(r).encode()
        self.payloads[folder+'/validation.json']=s.canonical(self.workflow.evaluate(r,'apibank',self.frozen)).encode()
        self.write_fixture();out=self.execute()
        row=s.loads((self.output/'scores.json').read_bytes())[0]
        self.assertEqual(row['alignment_diagnostic']['category'],'no_parsed_call_or_parse_failure')
        self.assertFalse(row['official_score']['correct'])
        self.assertEqual(out['official_reference_compliance']['rows'],4)

    def test_react_multiple_actions_explained_without_repair(self):
        i=2;key=self.requests[i]['case_key'];folder='run/cases/'+s.sha(key.encode())
        r=response('Action: f\nAction Input: {"x":1}\nAction: other\nAction Input: {}')
        self.payloads[folder+'/http_response.bin']=s.canonical(r).encode()
        self.payloads[folder+'/validation.json']=s.canonical(self.workflow.evaluate(r,'rotbench',self.frozen)).encode()
        self.write_fixture();self.execute()
        row=s.loads((self.output/'scores.json').read_bytes())[i]
        self.assertEqual(row['alignment_diagnostic']['category'],'react_single_action_rule_exclusion')
        self.assertTrue(row['official_score']['correct'])
        self.assertEqual(row['official_parser_call_count'],1)  # pinned ReAct parser keeps its original behavior

    def test_perturbed_source_accepted_with_lineage_and_objective_diagnostics(self):
        self.rows[0]['source_file']='CD.jsonl';self.requests[0]['source_file']='CD.jsonl'
        self.rules.update(constructed_clean_rows=4,constructed_perturbed_rows=1)
        self.rows[0]['canonical_base_id']=self.rows[1]['canonical_base_id']
        self.requests[0]['canonical_base_id']=self.requests[1]['canonical_base_id']
        self.rows[0]['benchmark']='bfcl_v3';self.requests[0]['benchmark']='bfcl_v3'
        self.rules['by_benchmark']={'apibank':0,'bfcl_v3':2,'rotbench':1,'toolalpaca':1,'tooleyes':1}
        del self.rules['by_benchmark']['apibank']
        self.membership['groups']['synthetic_0']['benchmark']='bfcl_v3'
        self.rules['inventory_groups']=4
        # Use a valid BFCL response for the reassigned synthetic request.
        prefix='run/cases/'+s.sha(self.requests[0]['case_key'].encode())
        r=response('[f(x=1)]')
        self.payloads[prefix+'/http_response.bin']=s.canonical(r).encode()
        self.payloads[prefix+'/validation.json']=s.canonical(self.workflow.evaluate(r,'bfcl_v3',self.frozen)).encode()
        self.rows[0]['reference_audit']['reward_kind']='cost'
        self.write_fixture();out=self.execute()
        self.assertEqual(out['reward_objective_diagnostics']['by_kind'],{'cost':1})
        self.assertEqual(out['reward_objective_diagnostics']['preference_success'],'not_assessed')
        self.assertIn('CD.jsonl',out['by_source_file'])

    def test_mismatched_request_source_rejected(self):
        self.requests[0]['source_file']='CD.jsonl';self.write_fixture()
        with self.assertRaises(ValueError):self.execute()

    def test_eligibility_panels_do_not_mix_relevance(self):
        out=self.execute();panels=out['evidence_eligibility']['by_panel']
        self.assertEqual(panels['official_reference_compliance']['rows'],4)
        self.assertEqual(panels['tooleyes_relevance']['rows'],1)
        self.assertEqual(panels['official_reference_compliance']['alignment_categories']['toolalpaca_frozen_scope_exclusion'],1)

    def test_empty_panel_undefined(self):
        self.assertIsNone(s.panel([])['accuracy'])

    def test_duplicate_and_nonfinite_json_rejected(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}'):
            with self.assertRaises(ValueError): s.loads(raw)

    def test_frozen_policy_integrity(self):
        self.assertEqual(s.sha((s.HERE / 'scoring_policy_v1.json').read_bytes().replace(b'\r\n', b'\n')), s.POLICY_SHA)
        self.assertEqual(len(type(self).rules['evidence_file_sha256']), 6940)


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
            provenance = s.loads((self.output / 'provenance.json').read_bytes())
            paths = provenance['input_sha256']
            self.assertTrue(paths)
            self.assertIn(
                'artifacts/local_development_audits/evidence/prepared/manifest.json',
                paths,
            )
            for name in paths:
                self.assertFalse(Path(name).is_absolute())
                self.assertNotIn('\\', name)
                self.assertTrue(name.startswith('artifacts/local_development_audits/'))
        finally:
            os.chdir(original)


    def set_invalid(self, benchmark):
        request = next(r for r in self.requests if r['benchmark']==benchmark)
        prefix = 'run/cases/'+s.sha(request['case_key'].encode())
        value = s.loads(self.payloads[prefix+'/http_response.bin'])
        value['choices'][0]['logprobs']['content'][0]['logprob'] = None
        saved = self.workflow.evaluate(value,benchmark,self.frozen)
        self.assertEqual(saved['status'],'invalid_evidence')
        self.payloads[prefix+'/http_response.bin'] = s.canonical(value).encode()
        self.payloads[prefix+'/validation.json'] = s.canonical(saved).encode()
        self.write_fixture()

    def test_invalid_evidence_keeps_correct_raw_call(self):
        self.set_invalid('apibank');out=self.execute()
        row=next(r for r in s.loads((self.output/'scores.json').read_bytes()) if r['benchmark']=='apibank')
        self.assertTrue(row['official_score']['correct'])
        self.assertEqual(row['evidence_status'],'invalid_evidence')
        self.assertEqual(row['alignment_diagnostic']['category'],'invalid_token_evidence')
        self.assertIsNone(row['whole_output_scores']);self.assertIsNone(row['meaningful_token_score'])
        self.assertEqual(out['official_reference_compliance']['rows'],4)

    def test_invalid_evidence_wrong_call_stays_wrong(self):
        self.refs[0]['golden_answers'][0]['name']='other'
        self.rows[0]['source_reference_sha256']=s.sha(s.canonical(self.refs[0]).encode())
        self.set_invalid('apibank');self.execute()
        row=s.loads((self.output/'scores.json').read_bytes())[0]
        self.assertFalse(row['official_score']['correct'])

    def test_invalid_evidence_never_recovers_probability(self):
        with self.assertRaises(ValueError):
            s.alignment_diagnostic('x','apibank',{'status':'invalid_evidence','whole_output_scores':{},'meaningful_token_score':None},{})

    def test_unselected_candidate_coverage_rejected(self):
        inventory=s.unique_index(self.rows)
        added={**self.rows[0],'case_key':'unselected'};inventory['unselected']=added
        self.rules['inventory_rows']=6
        with self.assertRaises(ValueError):s.construction_coverage(self.requests,inventory,self.rules)

    def test_blocked_coverage_retained_without_scoring(self):
        ref=copy.deepcopy(self.refs[0]);ref['case_key']='blocked-case';self.refs.append(ref)
        row=copy.deepcopy(self.rows[0]);row.update(case_key='blocked-case',construction_status='blocked',construction_reason='synthetic missing declaration',source_reference_sha256=s.sha(s.canonical(ref).encode()))
        self.rows.append(row);self.rules.update(inventory_rows=6,construction_blocks=1)
        self.membership['expected_rows']=6;self.write_fixture();out=self.execute()
        self.assertEqual(out['rows'],5);self.assertEqual(out['construction_coverage']['blocked_rows'],1)
        self.assertEqual(out['construction_coverage']['blocked_case_keys'],['blocked-case'])
        self.assertFalse(out['construction_coverage']['blocked_score_imputation'])
        self.assertNotIn('blocked-case',{r['case_key'] for r in s.loads((self.output/'scores.json').read_bytes())})

    def test_missing_clean_anchor_rejected(self):
        self.requests[0]['source_file']='CD.jsonl';self.rules.update(constructed_clean_rows=4,constructed_perturbed_rows=1)
        with self.assertRaises(ValueError):s.construction_coverage(self.requests,s.unique_index(self.rows),self.rules)

    def test_wrong_selection_rejected(self):
        self.manifest['selection']='coverage';self.write_fixture()
        with self.assertRaises(ValueError):self.execute()

    def test_unsupported_finish_not_silently_scored(self):
        request=self.requests[0];prefix='run/cases/'+s.sha(request['case_key'].encode())
        value=s.loads(self.payloads[prefix+'/http_response.bin']);value['choices'][0]['finish_reason']='other'
        self.payloads[prefix+'/http_response.bin']=s.canonical(value).encode()
        self.payloads[prefix+'/validation.json']=s.canonical(self.workflow.evaluate(value,'apibank',self.frozen)).encode()
        self.write_fixture()
        with self.assertRaises(ValueError):self.execute()

    def test_full_1728_synthetic_population_with_26_blocks(self):
        templates={r['benchmark']:(copy.deepcopy(r),copy.deepcopy(self.rows[i]),copy.deepcopy(self.refs[i])) for i,r in enumerate(self.requests)}
        import shutil
        shutil.rmtree(self.evidence)  # synthetic fixture reset only
        self.requests=[];self.rows=[];self.refs=[];self.payloads={};groups={}
        clean_counts={'apibank':100,'bfcl_v3':10,'rotbench':10,'toolalpaca':10,'tooleyes':10}
        for benchmark,count in type(self).rules['by_benchmark'].items():
            request_template,row_template,ref_template=templates[benchmark]
            for i in range(count):
                group=benchmark+'-'+str(i%clean_counts[benchmark])
                source='clean.jsonl' if i<clean_counts[benchmark] else 'synthetic_perturbed.jsonl'
                key=source+':'+benchmark+':'+str(i)
                request=copy.deepcopy(request_template);request.update(case_key=key,canonical_base_id=group,source_file=source)
                row=copy.deepcopy(row_template);row.update(case_key=key,canonical_base_id=group,source_file=source)
                ref=copy.deepcopy(ref_template);ref['case_key']=key;row['source_reference_sha256']=s.sha(s.canonical(ref).encode())
                self.requests.append(request);self.rows.append(row);self.refs.append(ref)
                groups[group]={'benchmark':benchmark,'split':'development','population':'primary'}
                value=copy.deepcopy(self.responses[benchmark]);prefix='run/cases/'+s.sha(key.encode())
                self.payloads[prefix+'/http_response.bin']=s.canonical(value).encode()
                self.payloads[prefix+'/validation.json']=s.canonical(self.workflow.evaluate(value,benchmark,self.frozen)).encode()
        for i in range(26):
            row=copy.deepcopy(self.rows[0]);ref=copy.deepcopy(self.refs[0]);key='blocked-'+str(i)
            ref['case_key']=key;row.update(case_key=key,construction_status='blocked',construction_reason='synthetic block',source_reference_sha256=s.sha(s.canonical(ref).encode()))
            self.rows.append(row);self.refs.append(ref)
        self.rules.update(request_count=1728,by_benchmark=copy.deepcopy(type(self).rules['by_benchmark']),inventory_rows=1754,inventory_groups=140,construction_blocks=26,constructed_clean_rows=140,constructed_perturbed_rows=1588)
        self.membership.update(groups=groups,expected_rows=1754,expected_groups=140)
        self.write_fixture();out=self.execute()
        self.assertEqual(out['rows'],1728)
        self.assertEqual(out['official_reference_compliance']['rows'],1512)
        self.assertEqual(out['tooleyes_relevance']['rows'],216)
        self.assertEqual(out['construction_coverage']['blocked_rows'],26)
        self.assertEqual(out['construction_coverage']['constructed_clean_perturbed_pairs'],1588)


class PublicationTests(unittest.TestCase):
    """Exercise transient locks, persistent failure and no-overwrite behavior."""

    def test_transient_publication_permission_error_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'prepared'; output = root / 'result'
            source.mkdir(); (source / 'record.json').write_bytes(b'original')
            original = Path.rename; attempts = []
            def rename(path, target):
                attempts.append((path, target))
                if len(attempts) < 3:
                    raise PermissionError('synthetic temporary lock')
                return original(path, target)
            with patch.object(Path, 'rename', new=rename), patch('time.sleep') as pause:
                s.publish_directory(source, output)
            self.assertEqual(len(attempts), 3)
            self.assertEqual(pause.call_count, 2)
            self.assertEqual((output / 'record.json').read_bytes(), b'original')
            self.assertFalse(source.exists())

    def test_persistent_publication_failure_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'prepared'; output = root / 'result'
            source.mkdir(); (source / 'record.json').write_bytes(b'original')
            with patch.object(Path, 'rename', side_effect=PermissionError('synthetic persistent lock')) as rename, patch('time.sleep') as pause:
                with self.assertRaises(PermissionError):
                    s.publish_directory(source, output)
            self.assertEqual(rename.call_count, 6)
            self.assertEqual(pause.call_count, 5)
            self.assertEqual((source / 'record.json').read_bytes(), b'original')
            self.assertFalse(output.exists())

    def test_existing_publication_destination_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'prepared'; output = root / 'result'
            source.mkdir(); output.mkdir()
            (output / 'prior.json').write_bytes(b'preserved')
            with patch.object(Path, 'rename') as rename:
                with self.assertRaises(ValueError):
                    s.publish_directory(source, output)
            rename.assert_not_called()
            self.assertEqual((output / 'prior.json').read_bytes(), b'preserved')
            self.assertTrue(source.exists())

    def test_nonpermission_error_is_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'prepared'; output = root / 'result'
            source.mkdir()
            with patch.object(Path, 'rename', side_effect=OSError('synthetic other error')) as rename, patch('time.sleep') as pause:
                with self.assertRaises(OSError):
                    s.publish_directory(source, output)
            self.assertEqual(rename.call_count, 1)
            pause.assert_not_called()
            self.assertTrue(source.exists())
            self.assertFalse(output.exists())

    def test_destination_appearing_during_retry_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root / 'prepared'; output = root / 'result'
            source.mkdir()
            def rename(path, target):
                output.mkdir(); (output / 'prior.json').write_bytes(b'preserved')
                raise PermissionError('synthetic competing destination')
            with patch.object(Path, 'rename', new=rename), patch('time.sleep'):
                with self.assertRaises(ValueError):
                    s.publish_directory(source, output)
            self.assertEqual((output / 'prior.json').read_bytes(), b'preserved')
            self.assertTrue(source.exists())


if __name__ == '__main__':
    unittest.main()
