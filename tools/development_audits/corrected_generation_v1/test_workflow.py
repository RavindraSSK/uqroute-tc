"""CPU-only tests with synthetic inputs, fake HTTP and the real pinned methods."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import workflow as w
from support import (BASE, canonical, digest, fresh_directory, json_once, loads,
                     methods, read, sha, source_bytes, write_once)

REPO = Path(__file__).resolve().parents[3]


def response(raw='f(x=1)', finish='stop', usage=True):
    tokens = [{'token': c, 'bytes': list(c.encode('utf-8')), 'logprob': -0.5} for c in raw]
    r = {'choices': [{'message': {'content': raw}, 'finish_reason': finish,
                      'logprobs': {'content': tokens}}]}
    if usage: r['usage'] = {'prompt_tokens': 10, 'completion_tokens': len(tokens), 'total_tokens': 10 + len(tokens)}
    return r


def small_candidates():
    cs = []; rows = []
    for i, benchmark in enumerate(('apibank', 'bfcl_v3', 'rotbench', 'toolalpaca', 'tooleyes')):
        key = 'clean.jsonl:synthetic_' + str(i)
        messages = [{'role': 'system', 'content': 'synthetic tools'}, {'role': 'user', 'content': 'synthetic question'}]
        tools = [{'name': 'f', 'parameters': {'type': 'object', 'properties': {'x': {'type': 'int'}}}}]
        c = {'case_key': key, 'canonical_base_id': 'g'+str(i), 'benchmark': benchmark,
             'messages': messages, 'tools': tools, 'messages_sha256': digest(messages)}
        rows.append({'case_key': key, 'canonical_base_id': c['canonical_base_id'], 'benchmark': benchmark,
                     'source_file': 'clean.jsonl', 'construction_status': 'candidate', 'split': 'development',
                     'population': 'primary', 'corrected_messages_sha256': digest(messages),
                     'tool_occurrence_schema_sha256': [digest(t) for t in tools]})
        cs.append(c)
    return cs, rows


def runtime(manifest):
    model = manifest['model_settings']; server = manifest['server_settings']
    return {**{k: model[k] for k in ('model_id','model_revision','tokenizer_revision','dtype','quantization')},
            **{k: server[k] for k in ('max_model_len','gpu_memory_utilization','chat_template')},
            'vllm_version': server['version'], 'effective_temperature': 0.01,
            'gpu_name': 'SYNTHETIC TEST GPU', 'gpu_memory_mib': 23034,
            'platform': 'synthetic-test', 'quota_note': 'synthetic, not actual capacity',
            'launch_command_sha256': 'a'*64, 'server_log_sha256': 'b'*64}


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen = methods(REPO)
        cls.task1 = loads(source_bytes(REPO)['docs/config/task1_single_sample_v1.json'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.candidates, self.rows = small_candidates()
        self.index = w.validate_candidates(self.candidates, self.rows)
        self.records = w.make_requests(self.candidates, self.index, self.task1['models'][0], self.task1['single_sample'])
        self.binding = {'synthetic': True}
        self.manifest = {'model_settings': self.task1['models'][0], 'server_settings': self.task1['single_sample']['server']}

    def test_frozen_whole_and_meaningful_scores(self):
        result = w.evaluate(response(), 'bfcl_v3', self.frozen)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['whole_output_scores']['mean_token_nll'], 0.5)
        self.assertIsNotNone(result['meaningful_token_score'])
        self.assertIsNone(result['official_correctness'])

    def test_truncation_retains_parsing_but_no_scores(self):
        result = w.evaluate(response(finish='length'), 'bfcl_v3', self.frozen)
        self.assertEqual(result['status'], 'truncated')
        self.assertEqual(result['parser_status'], 'calls')
        self.assertIsNone(result['whole_output_scores'])
        self.assertIsNone(result['meaningful_token_score'])

    def test_internal_special_token_remains_invalid(self):
        r = response(); r['choices'][0]['logprobs']['content'].insert(1, {'token':'<|im_start|>', 'bytes':list(b'<|im_start|>'), 'logprob':-0.1})
        result = w.evaluate(r, 'bfcl_v3', self.frozen)
        self.assertEqual(result['status'], 'invalid_evidence')
        self.assertIsNone(result['whole_output_scores'])

    def test_single_trailing_terminator_rule_preserved(self):
        r = response(); r['choices'][0]['logprobs']['content'].append({'token':'<|im_end|>', 'bytes':list(b'<|im_end|>'), 'logprob':-0.1})
        result = w.evaluate(r, 'bfcl_v3', self.frozen)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['evidence']['excluded_trailing_token'], '<|im_end|>')

    def test_toolalpaca_scoped_exclusion_preserved(self):
        result = w.evaluate(response(), 'toolalpaca', self.frozen)
        self.assertIsNotNone(result['whole_output_scores'])
        self.assertIsNone(result['meaningful_token_score'])

    def test_unsupported_finish_and_empty_unavailable(self):
        for r, expected in [(response(finish='tool_calls'), 'unsupported_finish'), (response(''), 'empty_output')]:
            result = w.evaluate(r, 'bfcl_v3', self.frozen)
            self.assertEqual(result['status'], expected)
            self.assertIsNone(result['whole_output_scores'])

    def test_multiple_choices_rejected(self):
        r=response();r['choices']*=2
        self.assertEqual(w.evaluate(r, 'bfcl_v3', self.frozen)['status'],'malformed_response')

    def test_invalid_probability_stays_unavailable(self):
        r=response();r['choices'][0]['logprobs']['content'][0]['logprob']=float('nan')
        self.assertEqual(w.evaluate(r,'bfcl_v3',self.frozen)['status'],'invalid_evidence')

    def test_prompt_tampering_rejected(self):
        self.candidates[0]['messages'][1]['content']='modified'
        with self.assertRaises(ValueError):w.validate_candidates(self.candidates,self.rows)

    def test_assistant_target_rejected(self):
        self.candidates[0]['messages'].append({'role':'assistant','content':'target'})
        with self.assertRaises(ValueError):w.validate_candidates(self.candidates,self.rows)

    def test_blocked_and_unknown_candidates_rejected(self):
        self.rows[0]['construction_status']='blocked'
        with self.assertRaises(ValueError):w.validate_candidates(self.candidates,self.rows)

    def test_held_out_candidate_rejected(self):
        self.rows[0]['split']='test'
        with self.assertRaises(ValueError):w.validate_candidates(self.candidates,self.rows)

    def test_reference_field_rejected(self):
        self.candidates[0]['golden_answers']=[]
        with self.assertRaises(ValueError):w.validate_candidates(self.candidates,self.rows)

    def test_selection_deterministic_and_requests_frozen(self):
        a=w.select(self.candidates,self.index,'feasibility-five')
        b=w.select(list(reversed(self.candidates)),self.index,'feasibility-five')
        self.assertEqual(a,b);self.assertEqual(len(a),5)
        for r in self.records:
            self.assertEqual(r['request']['max_tokens'],1024)
            self.assertEqual(r['request']['temperature'],0.001)
            self.assertNotIn('tools',r['request']);self.assertNotIn('seed',r['request'])

    def test_remote_and_credential_endpoints_rejected(self):
        for url in ('https://api.example.com/v1','http://localhost.evil/v1','http://u:p@localhost/v1','http://localhost/v1?token=secret'):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):w.endpoint_url(url)

    def test_dispatch_flag_required_before_network(self):
        with patch('workflow.transport', side_effect=AssertionError('network forbidden')):
            with self.assertRaises(ValueError):w.run(REPO,self.root,'a'*64,self.root,'http://localhost:8000/v1',self.root,False)

    def test_runtime_revision_mismatch_rejected(self):
        m={'model_settings':self.task1['models'][0],'server_settings':self.task1['single_sample']['server']}
        r=runtime(m);w.check_runtime(r,m);r['model_revision']='wrong'
        with self.assertRaises(ValueError):w.check_runtime(r,m)

    def test_intent_written_before_request_and_resume_skips(self):
        out=self.root/'run';calls=[]
        def caller(body):
            c=self.records[len(calls)]
            self.assertTrue((w.slot(out,c)/'intent.json').is_file());calls.append(body)
            return 200,canonical(response()).encode()
        w.dispatch(self.records,{},out,self.binding,self.frozen,caller)
        old={str(p):read(p) for p in out.rglob('*') if p.is_file()}
        result=w.dispatch(self.records,{},out,self.binding,self.frozen,lambda _:self.fail('resubmission'))
        self.assertEqual(len(calls),5);self.assertEqual(result['resumed_without_request'],5)
        for p,raw in old.items():self.assertEqual(read(Path(p)),raw)

    def test_transport_failure_never_automatically_retried(self):
        out=self.root/'run'
        def fail(_):raise TimeoutError('synthetic timeout')
        w.dispatch(self.records[:1],{},out,self.binding,self.frozen,fail)
        result=w.dispatch(self.records[:1],{},out,self.binding,self.frozen,lambda _:self.fail('retry'))
        self.assertEqual(result['resumed_without_request'],1)
        self.assertTrue((w.slot(out,self.records[0])/'transport_error.json').exists())

    def test_crash_after_intent_preserves_unknown_outcome(self):
        out=self.root/'run'
        def interrupt(_):raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):w.dispatch(self.records[:1],{},out,self.binding,self.frozen,interrupt)
        result=w.dispatch(self.records[:1],{},out,self.binding,self.frozen,lambda _:self.fail('retry'))
        self.assertEqual(result['resumed_without_request'],1)

    def test_resume_prevalidates_later_intents_before_any_request(self):
        out=self.root/'run';out.mkdir();json_once(out/'run_manifest.json',self.binding)
        folder=w.slot(out,self.records[-1]);json_once(folder/'intent.json',{'case_key':self.records[-1]['case_key'],'request_sha256':'wrong'})
        with self.assertRaises(ValueError):w.dispatch(self.records,{},out,self.binding,self.frozen,lambda _:self.fail('new request before prior validation'))

    def test_response_persisted_even_if_validation_fails(self):
        out=self.root/'run'
        with patch('workflow.evaluate',side_effect=RuntimeError('synthetic validation error')):
            w.dispatch(self.records[:1],{},out,self.binding,self.frozen,lambda _:(200,canonical(response()).encode()))
        self.assertTrue((w.slot(out,self.records[0])/'http_response.bin').is_file())
        self.assertEqual(loads(read(w.slot(out,self.records[0])/'validation.json'))['status'],'validation_error')

    def test_resume_manifest_mismatch_rejected(self):
        out=self.root/'run'
        w.dispatch([],{},out,self.binding,self.frozen,lambda _:None)
        with self.assertRaises(ValueError):w.dispatch([],{},out,{'changed':True},self.frozen,lambda _:None)

    def test_stale_lock_prevents_dispatch(self):
        out=self.root/'run';out.mkdir();json_once(out/'run_manifest.json',self.binding);write_once(out/'.writer.lock',b'prior')
        with self.assertRaises(FileExistsError):w.dispatch(self.records,{},out,self.binding,self.frozen,lambda _:self.fail('dispatch'))
        self.assertEqual(read(out/'.writer.lock'),b'prior')

    def test_existing_artifacts_never_overwritten(self):
        out=self.root/'data';fresh_directory(out,{'x.json':{'x':1}})
        with self.assertRaises(ValueError):fresh_directory(out,{'x.json':{'x':2}})
        with self.assertRaises(FileExistsError):json_once(out/'x.json',{'x':2})

    def test_duplicate_and_nonfinite_json_rejected(self):
        for raw in ('{"x":1,"x":2}','{"x":Infinity}'):
            with self.assertRaises(ValueError):loads(raw)

    def replay_setup(self, caller=None):
        repo=self.root/'repo';out=repo/'artifacts/local_development_audits/run'
        binding={'prepared_manifest_sha256':'a'*64,'implementation_hashes':w.implementation_hashes(),'held_out_access_enabled':False,
                 'main_experiment_ready':False,'automatic_retries':0,'request_count':len(self.records),
                 'runtime_attestation':runtime(self.manifest),'runtime_canonical_sha256':digest(runtime(self.manifest)),
                 'endpoint':'http://127.0.0.1:8000/v1'}
        w.dispatch(self.records,{},out,binding,self.frozen,caller or (lambda _:(200,canonical(response()).encode())))
        return repo,out

    def test_cpu_replay_preserves_old_files_and_counts_usage(self):
        repo,out=self.replay_setup();before={str(p):read(p) for p in out.rglob('*') if p.is_file()}
        with patch('workflow.load_plan',return_value=(self.manifest,self.records)),patch('workflow.methods',return_value=self.frozen),patch('workflow.transport',side_effect=AssertionError('CPU replay network')):
            summary=w.replay(repo,self.root/'prepared','a'*64,out,out.parent/'replay')
        self.assertEqual(summary['whole_output_eligible'],5)
        self.assertEqual(summary['known_token_totals']['prompt_tokens'],50)
        for p,raw in before.items():self.assertEqual(read(Path(p)),raw)

    def test_replay_rejects_response_tampering(self):
        repo,out=self.replay_setup();p=w.slot(out,self.records[0])/'http_response.bin';p.write_bytes(b'{}')
        with patch('workflow.load_plan',return_value=(self.manifest,self.records)),patch('workflow.methods',return_value=self.frozen):
            with self.assertRaises(ValueError):w.replay(repo,self.root/'prepared','a'*64,out,out.parent/'replay')

    def test_cpu_recovery_without_rewriting_saved_run(self):
        repo,out=self.replay_setup();folder=w.slot(out,self.records[0]);(folder/'validation.json').unlink()
        with patch('workflow.load_plan',return_value=(self.manifest,self.records)),patch('workflow.methods',return_value=self.frozen):
            w.replay(repo,self.root/'prepared','a'*64,out,out.parent/'replay')
        self.assertFalse((folder/'validation.json').exists())
        recovered=loads(read(out.parent/'replay'/'records.json'))
        self.assertTrue(recovered[0]['validation_recovered_on_cpu'])

    def test_missing_usage_is_not_zero_usage(self):
        repo,out=self.replay_setup(lambda _:(200,canonical(response(usage=False)).encode()))
        with patch('workflow.load_plan',return_value=(self.manifest,self.records)),patch('workflow.methods',return_value=self.frozen):
            summary=w.replay(repo,self.root/'prepared','a'*64,out,out.parent/'replay')
        self.assertEqual(summary['missing_usage_attempts']['prompt_tokens'],5)

    def test_replay_counts_interrupted_and_unattempted_slots(self):
        repo=self.root/'repo';out=repo/'artifacts/local_development_audits/run'
        binding={'prepared_manifest_sha256':'a'*64,'implementation_hashes':w.implementation_hashes(),'held_out_access_enabled':False,
                 'main_experiment_ready':False,'automatic_retries':0,'request_count':len(self.records),
                 'runtime_attestation':runtime(self.manifest),'runtime_canonical_sha256':digest(runtime(self.manifest)),
                 'endpoint':'http://127.0.0.1:8000/v1'}
        def crash(_):raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):w.dispatch(self.records,{},out,binding,self.frozen,crash)
        with patch('workflow.load_plan',return_value=(self.manifest,self.records)),patch('workflow.methods',return_value=self.frozen):
            summary=w.replay(repo,self.root/'prepared','a'*64,out,out.parent/'replay')
        self.assertEqual(summary['status_counts'],{'interrupted_outcome_unknown':1,'not_attempted':4})
        self.assertEqual(summary['missing_usage_attempts']['completion_tokens'],1)

    def test_unparsed_output_can_keep_whole_output_scores(self):
        result=w.evaluate(response('unrecognized prose'), 'bfcl_v3', self.frozen)
        self.assertEqual(result['parser_status'],'unparsed_or_no_call')
        self.assertIsNotNone(result['whole_output_scores'])
        self.assertIsNone(result['meaningful_token_score'])

    def test_null_usage_counted_as_missing(self):
        r=response();r['usage']=None
        repo,out=self.replay_setup(lambda _:(200,canonical(r).encode()))
        with patch('workflow.load_plan',return_value=(self.manifest,self.records)),patch('workflow.methods',return_value=self.frozen):
            summary=w.replay(repo,self.root/'prepared','a'*64,out,out.parent/'replay')
        self.assertEqual(summary['missing_usage_attempts']['prompt_tokens'],5)

    def test_prepare_and_load_full_count_fixture_without_network(self):
        import shutil
        from collections import Counter
        pop=self.frozen['population_plan']
        population_module=__import__('_corrected_dev_population')
        rows=[];candidates=[]
        groups=[]
        for b,n in [('apibank',52),('bfcl_v3',22),('rotbench',15),('toolalpaca',15),('tooleyes',36)]:
            groups.extend([(b+'_synthetic_'+str(i),b) for i in range(n)])
        official=[g for g in groups if g[1]!='tooleyes'];eyes=[g for g in groups if g[1]=='tooleyes']
        def add(g,source,blocked=False):
            group,b=g;key=source+':'+group
            messages=[{'role':'system','content':'SYNTHETIC test tools'},{'role':'user','content':'SYNTHETIC test query'}]
            tools=[{'name':'f','parameters':{'type':'object','properties':{'x':{'type':'int'}}}}]
            r={'case_key':key,'row_id':group,'canonical_base_id':group,'benchmark':b,'source_file':source,
               'split':'development','population':'primary','construction_status':'blocked' if blocked else 'candidate',
               'excluded_from_inventory':False,'official_labels_changed':False,
               'uncertainty_eligibility':'not_assessed_before_inference'}
            if blocked:r.update(construction_reason='retained synthetic block',reference_audit_status=population_module.BLOCKED_STATUS)
            else:
                r.update(reference_audit_status=population_module.COMPLETED,corrected_messages_sha256=digest(messages),tool_occurrence_schema_sha256=[digest(t) for t in tools],
                         reference_audit={'case_key':key,'benchmark':b,'changes_official_labels':False,'excluded':False,
                                          'review_flags':[],'objective_detection':{'cost_explicit_detected':False,'latency_explicit_detected':False}})
                candidates.append({'case_key':key,'canonical_base_id':group,'benchmark':b,'messages':messages,'tools':tools,'messages_sha256':digest(messages)})
            rows.append(r)
        for g in groups:add(g,'clean.jsonl')
        for i,(g,f) in enumerate([(g,f) for f in sorted(population_module.REWARD) for g in official][:498]):add(g,f,i<12)
        other=sorted(population_module.SOURCE_FILES-population_module.REWARD-{'clean.jsonl'})
        for i,(g,f) in enumerate([(g,f) for f in other for g in official][:936]):add(g,f,i<14)
        for f in other[:5]:
            for g in eyes:add(g,f)
        summarize=population_module.summarize
        filt=lambda predicate:[r for r in rows if predicate(r)]
        summary={'format_version':'uqroute-development-pipeline-1.0.0','readiness':'DEVELOPMENT_AUDIT_ONLY_MAIN_EXPERIMENT_NOT_READY',
                 'population':'primary','partition':'development','all_input_rows_retained':True,
                 'official_labels_changed':False,'reference_corrections_applied':False,'ambiguity_exclusions_applied':False,
                 'held_out_bundle_rows_accepted':0,'raw_benchmark_files_opened_by_auditor':0,
                 'totals':summarize(rows),
                 'by_benchmark':{b:summarize(filt(lambda r:r['benchmark']==b)) for b in {r['benchmark'] for r in rows}},
                 'by_source_file':{f:summarize(filt(lambda r:r['source_file']==f)) for f in {r['source_file'] for r in rows}},
                 'reference_audit_status_counts':dict(Counter(r['reference_audit_status'] for r in rows)),
                 'clean_anchor_pairing':{'perturbed_rows':1614,'with_unique_clean_anchor':1614,'both_constructed':1588},
                 'reference_compliance_candidate_inventory':summarize(filt(lambda r:r['benchmark']!='tooleyes')),
                 'separate_tooleyes_relevance_candidate_inventory':summarize(filt(lambda r:r['benchmark']=='tooleyes')),
                 'reward_panel':{**summarize(filt(lambda r:r['source_file'] in population_module.REWARD)),
                                 'objective_detection_assessed_rows':486,'objective_not_detected_rows':486},
                 'provenance':{'attestation_sha256':w.ATTESTATION,'benchmark_revision':population_module.BENCHMARK,'split_sha256':population_module.SPLIT}}
        report,_,_=pop(rows,summary)
        cfg=w.config()
        cfg['prior_summary_sha256']=sha((canonical(summary)+'\n').encode());cfg['prior_inventory_sha256']=sha((canonical(rows)+'\n').encode())
        report['provenance']={'prior_summary_sha256':cfg['prior_summary_sha256'],'prior_inventory_sha256':cfg['prior_inventory_sha256']}
        repo=self.root/'repo'
        shutil.copytree(REPO/'src',repo/'src')
        shutil.copytree(REPO/'docs/config',repo/'docs/config')
        shutil.copytree(REPO/'tools/development_audits/full_development_v1',repo/'tools/development_audits/full_development_v1')
        shutil.copytree(REPO/'tools/development_audits/population_policy_v1',repo/'tools/development_audits/population_policy_v1')
        root=repo/'artifacts/local_development_audits';audit=root/'old';population=root/'population';audit.mkdir(parents=True)
        for name,data in [('summary.json',summary),('inventory.json',rows),('candidates.json',candidates)]:json_once(audit/name,data)
        json_once(population/'denominators.json',report)
        prepared=root/'prepared'
        with patch('workflow.config',return_value=cfg),patch('workflow.verify_baseline',return_value=BASE),patch('workflow.transport',side_effect=AssertionError('prepare network')):
            result=w.prepare(repo,audit,population/'denominators.json',sha(read(audit/'candidates.json')),sha(read(population/'denominators.json')),'qwen15b','feasibility-five',prepared)
        self.assertEqual(result['prepared_requests'],5)
        with patch('workflow.verify_baseline',return_value=BASE):
            manifest,requests=w.load_plan(repo,prepared,result['manifest_sha256'])
        self.assertEqual(len(requests),5);self.assertEqual(manifest['construction_blocks_retained'],26)
        requests[0]['request']['temperature']=0.9
        (prepared/'requests.json').write_text(canonical(requests),encoding='utf-8')
        with patch('workflow.verify_baseline',return_value=BASE):
            with self.assertRaises(ValueError):w.load_plan(repo,prepared,result['manifest_sha256'])


if __name__ == '__main__':unittest.main()
