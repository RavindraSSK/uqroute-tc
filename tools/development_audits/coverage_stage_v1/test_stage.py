"""CPU tests use synthetic development records and the genuine frozen selector."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import stage as s
from preflight import context_report

REPO = Path(__file__).resolve().parents[3]

class CoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow, cls.support = s.dependencies(REPO)

    def setUp(self):
        self.cs=[];self.rows=[]
        for b in sorted(s.BENCHMARKS):
            for source in ('clean.jsonl','realistic_typos.jsonl'):
                for i in range(2):
                    key=source+':synthetic_'+b+'_'+str(i)
                    messages=[{'role':'system','content':'synthetic tools'},{'role':'user','content':'synthetic question'}]
                    tools=[{'name':'f','parameters':{'type':'object'}}]
                    c={'case_key':key,'canonical_base_id':b+str(i),'benchmark':b,'messages':messages,'tools':tools,
                       'messages_sha256':self.support.digest(messages)}
                    row={'case_key':key,'canonical_base_id':c['canonical_base_id'],'benchmark':b,'source_file':source,
                         'construction_status':'candidate','split':'development','population':'primary',
                         'corrected_messages_sha256':c['messages_sha256'],'tool_occurrence_schema_sha256':[self.support.digest(t) for t in tools]}
                    self.cs.append(c);self.rows.append(row)
        self.index=self.workflow.validate_candidates(self.cs,self.rows)
        task1=self.support.loads(self.support.source_bytes(REPO)['docs/config/task1_single_sample_v1.json'])
        selected=self.workflow.select(self.cs,self.index,'coverage')
        self.requests=self.workflow.make_requests(selected,self.index,task1['models'][0],task1['single_sample'])
        self.manifest={'selection':'coverage','request_count':len(self.requests),'held_out_access_enabled':False,'main_experiment_ready':False}

    def report(self):return s.coverage_report(self.manifest,self.requests,self.cs,self.rows,self.workflow)

    def test_outcome_independent_bounded_coverage(self):
        r=self.report();self.assertEqual(r['rows'],10);self.assertEqual(len(r['covered_strata']),10)
        self.assertEqual(r['prior_feasibility_cases_deliberately_repeated'],5)
        self.assertEqual(r['maximum_completion_tokens'],10240)
        self.assertFalse(r['held_out_access_enabled']);self.assertFalse(r['main_experiment_ready'])
        self.assertEqual(r['network_requests'],0)

    def test_order_invariance(self):
        expected=self.report();self.cs.reverse();self.rows.reverse();self.assertEqual(self.report(),expected)

    def test_blocked_rows_retained_not_selected(self):
        self.rows.append({'case_key':'blocked','construction_status':'blocked'})
        self.assertEqual(self.report()['construction_blocks_retained'],1)

    def test_missing_selected_case_rejected(self):
        self.requests.pop()
        with self.assertRaises(ValueError):self.report()

    def test_duplicate_request_rejected(self):
        self.requests.append(copy.deepcopy(self.requests[0]))
        with self.assertRaises(ValueError):self.report()

    def test_alternative_not_hash_minimum_rejected(self):
        keys={r['case_key'] for r in self.requests}
        alt=next(c for c in self.cs if c['case_key'] not in keys)
        self.requests[0]['case_key']=alt['case_key']
        with self.assertRaises(ValueError):self.report()

    def test_non_development_rejected(self):
        self.rows[0]['split']='test'
        with self.assertRaises(ValueError):self.report()

    def test_prompt_tamper_rejected(self):
        self.cs[0]['messages'][1]['content']='changed'
        with self.assertRaises(ValueError):self.report()

    def test_tool_tamper_rejected(self):
        self.cs[0]['tools'][0]['name']='changed'
        with self.assertRaises(ValueError):self.report()

    def test_readiness_change_rejected(self):
        self.manifest['main_experiment_ready']=True
        with self.assertRaises(ValueError):self.report()

    def test_held_out_change_rejected(self):
        self.manifest['held_out_access_enabled']=True
        with self.assertRaises(ValueError):self.report()

    def test_missing_benchmark_rejected(self):
        self.cs=[c for c in self.cs if c['benchmark']!='tooleyes']
        self.rows=[r for r in self.rows if r['benchmark']!='tooleyes']
        self.requests=[r for r in self.requests if r['benchmark']!='tooleyes'];self.manifest['request_count']=len(self.requests)
        with self.assertRaises(ValueError):self.report()

    def test_unsupported_source_rejected(self):
        for r in self.rows:r['source_file']='unknown.jsonl'
        self.index=self.workflow.validate_candidates(self.cs,self.rows)
        task1=self.support.loads(self.support.source_bytes(REPO)['docs/config/task1_single_sample_v1.json'])
        self.requests=self.workflow.make_requests(self.workflow.select(self.cs,self.index,'coverage'),self.index,task1['models'][0],task1['single_sample'])
        self.manifest['request_count']=len(self.requests)
        with self.assertRaises(ValueError):self.report()

    def test_no_pairing_claim(self):
        r=self.report();self.assertIn('not a clean/perturbed paired',r['pairing_limit'])
        self.assertLessEqual(r['selected_perturbed_rows_with_selected_clean_anchor'],r['selected_perturbed_rows'])

    def test_dependency_hash_tamper_rejected(self):
        with patch.dict(s.WORKFLOW_HASHES,{'workflow.py':'0'*64}):
            with self.assertRaises(ValueError):s.dependencies(REPO)

    def test_existing_output_rejected_without_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp);root=repo/'artifacts/local_development_audits';out=root/'out';out.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError,'exists'):
                s.prepare(repo,root/'audit',root/'population/denominators.json',out)

    def test_output_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp);root=repo/'artifacts/local_development_audits'
            with self.assertRaisesRegex(ValueError,'overlaps'):
                s.prepare(repo,root/'audit',root/'population/denominators.json',root/'audit/new')

    def test_prepare_publishes_absolute_paths_and_reference_free_transfer(self):
        import os
        import zipfile
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp).resolve();root=repo/'artifacts/local_development_audits'
            audit=root/'audit';denom=root/'population/denominators.json';out=root/'coverage'
            audit.mkdir(parents=True);denom.parent.mkdir(parents=True)
            for name in ('candidates.json','inventory.json','summary.json'):(audit/name).write_text('{}')
            denom.write_text('{}')
            originals={p:p.read_bytes() for p in (audit/'candidates.json',audit/'inventory.json',audit/'summary.json',denom)}
            def approved(path, expected):return self.cs if path.name=='candidates.json' else self.rows
            def frozen_prepare(repo_arg,audit_arg,denom_arg,candidates_hash,denom_hash,model,selection,prepared):
                self.assertEqual((candidates_hash,denom_hash,model,selection),(s.CANDIDATES,s.DENOMINATORS,'qwen15b','coverage'))
                self.assertTrue(prepared.is_absolute());prepared.mkdir()
                (prepared/'manifest.json').write_text(s.canonical(self.manifest))
                (prepared/'requests.json').write_text(s.canonical(self.requests))
            fake=SimpleNamespace(approved_file=approved,config=self.workflow.config,prepare=frozen_prepare,
                load_plan=lambda *args:(self.manifest,self.requests),validate_candidates=self.workflow.validate_candidates,select=self.workflow.select)
            cwd=Path.cwd()
            try:
                os.chdir(repo)
                with patch.object(s,'dependencies',return_value=(fake,self.support)),patch.object(s.subprocess,'run'):
                    report=s.prepare(Path('.'),audit.relative_to(repo),denom.relative_to(repo),out.relative_to(repo))
            finally:os.chdir(cwd)
            with zipfile.ZipFile(out/'corrected_qwen15b_coverage_transfer_v1.zip') as z:
                self.assertEqual(set(z.namelist()),{'manifest.json','requests.json'})
            self.assertEqual(report['rows'],10)
            self.assertEqual({p:p.read_bytes() for p in originals},originals)
            self.assertTrue((out/'MANIFEST_SHA256.txt').is_file())

    def test_context_exact_boundary_allowed(self):
        r=context_report([7168],1);self.assertTrue(r['all_fit']);self.assertFalse(r['prompts_truncated'])

    def test_context_overflow_reported_not_dropped(self):
        r=context_report([7169,20],2);self.assertFalse(r['all_fit']);self.assertEqual(r['over_limit_request_indices'],[0]);self.assertEqual(r['requests_dropped'],0)

    def test_context_invalid_counts_rejected(self):
        for counts,n in [([],0),([1],2),([True],1),([0],1),([-1],1),([1.5],1)]:
            with self.assertRaises(ValueError):context_report(counts,n)

if __name__=='__main__':unittest.main()
