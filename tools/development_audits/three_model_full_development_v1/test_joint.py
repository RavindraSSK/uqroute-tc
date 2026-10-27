"""Exercise the unchanged comparison engine on synthetic full-size cohorts."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

class JointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior=Path(__file__).resolve().parents[3]/'tools/development_audits/three_model_uncertainty_v1'
        sys.path.insert(0,str(prior))
        spec=importlib.util.spec_from_file_location('_full_joint_test_core',prior/'run_analysis.py')
        cls.core=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.core)
        cls.cfg=json.loads((prior/'policy.json').read_text())
    def data(self):
        return {model:[{'case_key':str(i),'canonical_base_id':str(i%140),'benchmark':'apibank','source_file':'synthetic.jsonl',
                        'panel':'official_reference_compliance','reference_review_flags':[],
                        'official_score':{'correct':i%3==j},'whole_output_scores':{'mean_token_nll':i/100,'sequence_nll':i/10,'max_token_surprisal':i/50},
                        'meaningful_token_score':{'mean_token_nll':i/200} if i%10==0 else None} for i in range(1728)]
                for j,model in enumerate(('llama3b','qwen15b','qwen7b'))}
    def test_full_size_joint_cohorts(self):
        joint=self.core.joint_cohort(self.data(),self.cfg)
        self.assertEqual(joint['original_rows'],1728)
        self.assertEqual(joint['per_measure_all_models_joint']['mean_token_nll']['rows'],1728)
        self.assertEqual(joint['all_measures_all_models_common']['rows'],173)
        self.assertEqual(joint['outcome_patterns_C_correct_I_incorrect'],{'CII':576,'ICI':576,'IIC':576})
    def test_nonrandom_missingness_not_imputed(self):
        data=self.data();data['llama3b'][0]['whole_output_scores']=None
        joint=self.core.joint_cohort(data,self.cfg)
        self.assertEqual(joint['original_rows'],1728)
        self.assertEqual(joint['per_measure_all_models_joint']['mean_token_nll']['rows'],1727)
        self.assertEqual(joint['per_measure_all_models_joint']['meaningful_mean_token_nll']['rows'],173)
        self.assertEqual(joint['all_measures_all_models_common']['rows'],172)
    def test_lineage_mismatch_rejected(self):
        data=self.data();data['qwen7b'][0]['canonical_base_id']='other'
        with self.assertRaises(ValueError):self.core.joint_cohort(data,self.cfg)
    def test_model_specific_labels_preserved(self):
        data=self.data();old=copy.deepcopy(data)
        joint=self.core.joint_cohort(data,self.cfg)
        d=joint['per_measure_all_models_joint']['mean_token_nll']['models']
        self.assertEqual(d['llama3b']['discrimination']['error_positive_rows'],1152)
        self.assertEqual(data,old)

if __name__=='__main__':unittest.main()
