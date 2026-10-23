import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from verify_plan import validate,verify,verify_git,BASE

ROOT=Path(__file__).resolve().parents[3]
PLAN=json.loads((ROOT/'docs/research_track_v1/main_experiment_plan_v1.json').read_text())
MANIFEST=json.loads((ROOT/'docs/research_track_v1/source_manifest.json').read_text())

class PlanTests(unittest.TestCase):
    def test_current_proposal_valid(self):self.assertEqual(validate(PLAN,MANIFEST),[])
    def test_each_execution_switch_rejected(self):
        for field in ('main_experiment_ready','inference_enabled','held_out_access_enabled','training_enabled'):
            plan=copy.deepcopy(PLAN);plan[field]=True;self.assertTrue(validate(plan,MANIFEST))
    def test_label_changes_and_resplitting_rejected(self):
        for field in ('existing_official_labels_immutable','existing_split_unchanged'):
            plan=copy.deepcopy(PLAN);plan[field]=False;self.assertTrue(validate(plan,MANIFEST))
    def test_tooleyes_pooling_rejected(self):
        plan=copy.deepcopy(PLAN);plan['reporting_panels']['tool_name_relevance']['pooled_into_primary_compliance']=True
        self.assertTrue(validate(plan,MANIFEST))
    def test_reward_objective_collapse_rejected(self):
        plan=copy.deepcopy(PLAN);plan['reporting_panels']['cost_latency_preference']['objective_detected_and_not_detected_separate']=False
        self.assertTrue(validate(plan,MANIFEST))
    def test_missing_decision_rejected(self):
        plan=copy.deepcopy(PLAN);plan['decisions'].pop();self.assertTrue(validate(plan,MANIFEST))
    def test_pretend_freeze_rejected(self):
        plan=copy.deepcopy(PLAN);plan['status']='frozen';plan['decisions'][0]['status']='resolved'
        self.assertTrue(validate(plan,MANIFEST))
    def test_data_source_path_rejected(self):
        manifest=copy.deepcopy(MANIFEST);manifest['sources'][0]['path']='hf_data/datasets/api_eval/clean.jsonl'
        self.assertTrue(validate(PLAN,manifest))
    def test_bad_hash_and_baseline_rejected(self):
        manifest=copy.deepcopy(MANIFEST);manifest['sources'][0]['git_blob_sha']='not-a-hash';self.assertTrue(validate(PLAN,manifest))
        plan=copy.deepcopy(PLAN);plan['baseline_commit']='0'*40;self.assertTrue(validate(plan,MANIFEST))
    def test_package_verification_no_git_or_dataset_access(self):
        with patch('verify_plan.subprocess.run',side_effect=AssertionError('Unexpected process')):
            result=verify(ROOT,check_git=False)
        self.assertEqual(result['dataset_files_opened'],0);self.assertFalse(result['git_baseline_verified']);self.assertFalse(result['main_experiment_ready'])
    def test_git_verification_only_source_object_ids(self):
        from subprocess import CompletedProcess
        calls=[]
        def run(cmd,**kwargs):
            calls.append(cmd)
            args=cmd[3:]
            if args==['rev-parse','HEAD']:return CompletedProcess(cmd,0,BASE+'\n','')
            if args==['merge-base','--is-ancestor',BASE,'HEAD']:return CompletedProcess(cmd,0,'','')
            if args[0]=='rev-parse':
                path=args[1].split(':',1)[1]
                blob=next(s['git_blob_sha'] for s in MANIFEST['sources'] if s['path']==path)
                return CompletedProcess(cmd,0,blob+'\n','')
            raise AssertionError(cmd)
        with patch('verify_plan.subprocess.run',side_effect=run):self.assertEqual(verify_git(ROOT,MANIFEST),BASE)
        self.assertEqual(len(calls),10)
        self.assertTrue(all('show' not in cmd and 'checkout' not in cmd for cmd in calls))
    def test_unknown_missing_scores_not_imputed(self):
        plan=copy.deepcopy(PLAN);plan['proposed_analysis']['impute_missing_scores']=True;self.assertTrue(validate(plan,MANIFEST))

if __name__=='__main__':unittest.main()
