"""Synthetic taxonomy and immutable score-join regression tests."""
import copy
from collections import Counter
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import categories as c

class Tests(unittest.TestCase):
    def records(self):
        out=[]
        for source,(category,kind,count) in c.EXPECTED.items():
            for i in range(count):
                out.append({'case_key':source+str(i),'source_file':source,'benchmark':'test',
                            'canonical_base_id':str(i),'split':'development','population':'primary',
                            'sample':{'perturbation':{'mdp_category':None if category=='clean' else category,'type':kind}}})
        return out
    def requests(self,records):return [{k:r[k] for k in ('case_key','source_file','benchmark','canonical_base_id')} for r in records]
    def test_selected_counts(self):
        rows=self.records();t=c.taxonomy(rows,self.requests(rows))
        self.assertEqual(Counter(r['analysis_category'] for r in t.values()),{'clean':5,'observation':20,'action':24,'reward':20})
    def test_clean_null(self):
        self.assertEqual(c.metadata(next(r for r in self.records() if r['source_file']=='clean.jsonl')),'clean')
    def test_clean_literal_none_retained(self):
        r=next(r for r in self.records() if r['source_file']=='clean.jsonl');r['sample']['perturbation']={'mdp_category':'None','type':'None'}
        self.assertEqual(c.metadata(r),'clean');self.assertEqual(r['sample']['perturbation']['mdp_category'],'None')
    def test_missing_metadata_rejected(self):
        r=self.records()[0];r['sample']={}
        with self.assertRaises(ValueError):c.metadata(r)
    def test_non_dict_metadata_rejected(self):
        r=self.records()[0];r['sample']['perturbation']='reward'
        with self.assertRaises(ValueError):c.metadata(r)
    def test_missing_category_rejected(self):
        r=self.records()[0];del r['sample']['perturbation']['mdp_category']
        with self.assertRaises(ValueError):c.metadata(r)
    def test_wrong_category_rejected(self):
        r=self.records()[0];r['sample']['perturbation']['mdp_category']='action'
        with self.assertRaises(ValueError):c.metadata(r)
    def test_wrong_type_rejected(self):
        r=self.records()[0];r['sample']['perturbation']['type']='TD'
        with self.assertRaises(ValueError):c.metadata(r)
    def test_unknown_source_rejected(self):
        r=self.records()[0];r['source_file']='new.jsonl'
        with self.assertRaises(ValueError):c.metadata(r)
    def test_clean_mislabeled_rejected(self):
        r=next(r for r in self.records() if r['source_file']=='clean.jsonl');r['sample']['perturbation']['mdp_category']='observation'
        with self.assertRaises(ValueError):c.metadata(r)
    def test_duplicate_requests_rejected(self):
        rows=self.records();requests=self.requests(rows);requests[-1]=requests[0]
        with self.assertRaises(ValueError):c.taxonomy(rows,requests)
    def test_duplicate_samples_rejected(self):
        rows=self.records()
        with self.assertRaises(ValueError):c.taxonomy(rows+[rows[0]],self.requests(rows))
    def test_missing_case_rejected(self):
        rows=self.records()
        with self.assertRaises(ValueError):c.taxonomy(rows[:-1],self.requests(rows))
    def test_non_development_rejected(self):
        rows=self.records();rows[0]['split']='test'
        with self.assertRaises(ValueError):c.taxonomy(rows,self.requests(rows))
    def test_sensitivity_rejected(self):
        rows=self.records();rows[0]['population']='sensitivity'
        with self.assertRaises(ValueError):c.taxonomy(rows,self.requests(rows))
    def test_lineage_rejected(self):
        rows=self.records();requests=self.requests(rows);requests[0]['canonical_base_id']='wrong'
        with self.assertRaises(ValueError):c.taxonomy(rows,requests)
    def test_unselected_development_ignored(self):
        rows=self.records();other={**rows[0],'case_key':'not-selected'}
        self.assertEqual(len(c.taxonomy(rows+[other],self.requests(rows))),69)
    def test_inputs_preserved(self):
        rows=self.records();old=copy.deepcopy(rows);c.taxonomy(rows,self.requests(rows));self.assertEqual(rows,old)
    def test_join_preserves_outcomes(self):
        rows=self.records();t=c.taxonomy(rows,self.requests(rows));scores=[{**r,'official_score':{'correct':False,'score':.333},'reference_review_flags':['flag']} for r in self.requests(rows)]
        old=copy.deepcopy(scores);joined=c.join(scores,t)
        self.assertEqual(scores,old);self.assertEqual([r['official_score'] for r in joined],[r['official_score'] for r in scores])
        self.assertTrue(all(r['reference_review_flags']==['flag'] for r in joined))
    def test_join_rejects_duplicates(self):
        rows=self.records();t=c.taxonomy(rows,self.requests(rows));scores=self.requests(rows);scores[-1]=scores[0]
        with self.assertRaises(ValueError):c.join(scores,t)
    def test_join_rejects_lineage(self):
        rows=self.records();t=c.taxonomy(rows,self.requests(rows));scores=self.requests(rows);scores[0]['benchmark']='wrong'
        with self.assertRaises(ValueError):c.join(scores,t)
    def test_row_order_independent(self):
        rows=self.records();self.assertEqual(c.taxonomy(rows,self.requests(rows)),c.taxonomy(list(reversed(rows)),self.requests(rows)))

if __name__=='__main__':unittest.main()
