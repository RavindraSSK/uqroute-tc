import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_analysis as a
import engine as e

CFG={'version':'synthetic','scope':'synthetic','measures':{
    'sequence_nll':['whole_output_scores','sequence_nll'],
    'mean_token_nll':['whole_output_scores','mean_token_nll'],
    'max_token_surprisal':['whole_output_scores','max_token_surprisal'],
    'meaningful_mean_token_nll':['meaningful_token_score','mean_token_nll']}}

def row(i=0,b='apibank',correct=False,meaningful=True):
    return {'case_key':'clean.jsonl:synthetic_'+str(i),'canonical_base_id':'group_'+str(i//2),
            'benchmark':b,'source_file':'clean.jsonl','panel':a.PANELS[b=='tooleyes'],
            'official_score':{'correct':correct,'score':float(correct)},'reference_review_flags':['synthetic'],
            'official_labels_changed':False,'ambiguity_exclusion_applied':False,'evidence_status':'complete',
            'whole_output_scores':{'sequence_nll':float(i+1),'mean_token_nll':float(i+1)/10,'max_token_surprisal':float(i+1)/5},
            'meaningful_token_score':{'mean_token_nll':float(i+1)/20} if meaningful else None,
            'alignment_diagnostic':{'category':'eligible' if meaningful else 'unavailable'}}

def fixtures():
    q=[];requests=[];i=0
    for b,n in [('apibank',17),('bfcl_v3',12),('rotbench',17),('toolalpaca',17),('tooleyes',6)]:
        for _ in range(n):
            r=row(i,b,correct=i%3==0);q.append(r)
            requests.append({k:r[k] for k in ('case_key','canonical_base_id','benchmark','source_file')}|{
                'request':{'model':'Qwen/Qwen2.5-1.5B-Instruct','messages':[{'role':'user','content':'synthetic'}],'temperature':0.001}})
            i+=1
    return q,requests

class ComparisonTests(unittest.TestCase):
    def test_shared_cohort_is_intersection(self):
        q=[row(0),row(1)];l=copy.deepcopy(q);l[1]['meaningful_token_score']=None
        v=a.paired_cohort(q,l,CFG)
        self.assertEqual(v['per_measure_joint_eligible']['mean_token_nll']['rows'],2)
        self.assertEqual(v['all_measures_both_models_common']['rows'],1)
    def test_truncated_kept_for_correctness(self):
        q=[row(0,correct=True)];l=copy.deepcopy(q);l[0].update(evidence_status='truncated',whole_output_scores=None,meaningful_token_score=None)
        v=a.paired_cohort(q,l,CFG)
        self.assertEqual(v['original_rows'],1)
        self.assertEqual(v['paired_correctness_transitions_qwen_to_llama'],{'correct_to_correct':1})
        self.assertEqual(v['per_measure_joint_eligible']['mean_token_nll']['rows'],0)
    def test_changed_outcomes_reported(self):
        q=[row(0),row(1,correct=True)];l=copy.deepcopy(q)
        l[0]['official_score']['correct']=True;l[1]['official_score']['correct']=False
        v=a.paired_cohort(q,l,CFG)['paired_correctness_transitions_qwen_to_llama']
        self.assertEqual(v,{'incorrect_to_correct':1,'correct_to_incorrect':1})
    def test_no_negative_tooleyes_undefined(self):
        q=[row(0,'tooleyes',True),row(1,'tooleyes',True)]
        v=a.compare(q,copy.deepcopy(q),CFG)['by_panel']['tooleyes_relevance']
        d=v['per_measure_joint_eligible']['mean_token_nll']['llama']['discrimination']
        self.assertIsNone(d['auroc']);self.assertIsNone(d['average_precision'])
    def test_all_errors_auroc_undefined(self):
        d=e.analyze([row(0),row(1)],CFG)['by_benchmark']['apibank']['available_case_analysis']['mean_token_nll']['discrimination']
        self.assertIsNone(d['auroc']);self.assertEqual(d['average_precision'],1)
    def test_flag_mismatch_rejected(self):
        q=[row()];l=copy.deepcopy(q);l[0]['reference_review_flags']=[]
        with self.assertRaises(ValueError):a.paired_cohort(q,l,CFG)
    def test_case_mismatch_rejected(self):
        with self.assertRaises(ValueError):a.paired_cohort([row(0)],[row(1)],CFG)
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):a.paired_cohort([row(),row()],[row()],CFG)
    def test_inputs_unchanged(self):
        q=[row(0),row(1)];l=copy.deepcopy(q);before=copy.deepcopy((q,l))
        a.compare(q,l,CFG);self.assertEqual((q,l),before)
    def test_correct_boolean_not_partial(self):
        q=[row(0)];q[0]['official_score']['score']=0.99
        self.assertEqual(a.paired_cohort(q,q,CFG)['paired_correctness_transitions_qwen_to_llama'],{'incorrect_to_incorrect':1})
    def test_original_coverage_denominator(self):
        q=[row(0),row(1,meaningful=False)];v=a.paired_cohort(q,q,CFG)
        self.assertEqual(v['per_measure_joint_eligible']['meaningful_mean_token_nll']['qwen']['risk_coverage']['maximum_panel_coverage'],0.5)
    def test_same_requests_allow_only_model_difference(self):
        _,q=fixtures();l=copy.deepcopy(q)
        for r in l:r['request']['model']='meta-llama/Llama-3.2-3B-Instruct'
        a.same_requests(q,l)
        l[0]['request']['temperature']=0.6
        with self.assertRaises(ValueError):a.same_requests(q,l)
    def test_request_order_rejected(self):
        _,q=fixtures();l=copy.deepcopy(q)
        for r in l:r['request']['model']='meta-llama/Llama-3.2-3B-Instruct'
        l.reverse()
        with self.assertRaises(ValueError):a.same_requests(q,l)
    def test_truncated_fake_measure_rejected(self):
        q,r=fixtures();q[0]['evidence_status']='truncated'
        with self.assertRaises(ValueError):e.validate_rows(q,r,CFG)
    def test_complete_and_truncated_validation(self):
        q,r=fixtures();q[0].update(evidence_status='truncated',whole_output_scores=None,meaningful_token_score=None)
        e.validate_rows(q,r,CFG)
    def test_output_preserved(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);out=repo/a.ROOT/'old';out.mkdir(parents=True)
            with self.assertRaises(ValueError):a.run(repo,out)
    def test_output_outside_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ValueError):a.run(Path(t),Path(t)/'outside')
    def test_nan_rejected(self):
        q=[row()];q[0]['whole_output_scores']['mean_token_nll']=float('nan')
        with self.assertRaises(ValueError):a.paired_cohort(q,q,CFG)
    def test_policy_and_core_hashes(self):
        cfg=a.checked(a.HERE/'policy.json',a.POLICY_SHA,{})
        for n,h in cfg['own_source_sha256_lf'].items():self.assertEqual(e.sha(e.regular(a.HERE/n).replace(b'\r\n',b'\n')),h)

class PipelineTests(unittest.TestCase):
    def test_synthetic_full_pipeline_and_preservation(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);root=repo/a.ROOT;out=root/'new'
            cfg=copy.deepcopy(CFG);cfg.update(baseline_commit='synthetic',own_source_sha256_lf={},llama_scoring_source_sha256_lf={},qwen_input_sha256={})
            q,qr=fixtures();l=copy.deepcopy(q);lr=copy.deepcopy(qr)
            for r in lr:r['request']['model']='meta-llama/Llama-3.2-3B-Instruct'
            l[-1].update(evidence_status='truncated',whole_output_scores=None,meaningful_token_score=None)
            values={a.QWEN+'/scores.json':q,a.QWEN+'/provenance.json':{},a.QI+'/prepared/requests.json':qr,a.QI+'/prepared/manifest.json':{},
                    a.LLAMA+'/scores.json':l,a.LLAMA+'/summary.json':{'rows':69},a.LI+'/prepared/manifest.json':{},a.LI+'/prepared/requests.json':lr}
            for n,v in values.items():
                p=root/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(e.canonical(v))
            for name,rel in [('scores.json',a.QWEN+'/scores.json'),('provenance.json',a.QWEN+'/provenance.json'),('prepared/requests.json',a.QI+'/prepared/requests.json'),('prepared/manifest.json',a.QI+'/prepared/manifest.json')]:cfg['qwen_input_sha256'][name]=a.hash_file(root/rel)
            before={p:p.read_bytes() for p in root.rglob('*') if p.is_file()}
            def mock_run(command,**kw):
                if '--output' in command:
                    dest=Path(command[command.index('--output')+1]);dest.mkdir()
                    for n,v in [('scores.json',l),('summary.json',{'rows':69}),('provenance.json',{})]:(dest/n).write_text(e.canonical(v))
                return type('Result',(),{'returncode':0,'stderr':''})()
            original_checked=a.checked
            def mocked_checked(path,expected,ledger):
                if path==a.HERE/'policy.json':return cfg
                return original_checked(path,expected,ledger)
            with patch.object(a,'checked',side_effect=mocked_checked),patch.object(a.subprocess,'run',side_effect=mock_run):
                with contextlib.redirect_stdout(io.StringIO()): a.run(repo,out)
            self.assertTrue((out/'REPORT.md').is_file());self.assertTrue((out/'matched_comparison.json').is_file())
            for p,raw in before.items():self.assertEqual(p.read_bytes(),raw)
    def test_wrong_input_hash_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'data';p.write_text('{}')
            with self.assertRaises(ValueError):a.checked(p,'0'*64,{})
