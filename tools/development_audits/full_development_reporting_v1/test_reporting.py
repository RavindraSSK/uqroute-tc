import copy
import unittest
import reporting as r

class BandTests(unittest.TestCase):
    def rows(self,values):return [{'case_key':str(i),'whole_output_scores':None if v is None else {'mean_token_nll':v},'official_score':{'correct':bool(i%2)}} for i,v in enumerate(values)]
    def test_empty(self):self.assertEqual(r.low_uncertainty_band([])['accepted_rows'],0)
    def test_all_unavailable(self):self.assertEqual(r.low_uncertainty_band(self.rows([None,None]))['eligible_rows'],0)
    def test_no_imputation(self):self.assertEqual(r.low_uncertainty_band(self.rows([None,1,2,3,4,5]))['accepted_rows'],1)
    def test_boundary_ties_retained(self):self.assertEqual(r.low_uncertainty_band(self.rows([1,1,1,2,3]))['accepted_rows'],3)
    def test_ceil_target(self):self.assertEqual(r.low_uncertainty_band(self.rows(list(range(6))))['accepted_rows'],2)
    def test_single(self):self.assertEqual(r.low_uncertainty_band(self.rows([1]))['accepted_rows'],1)
    def test_failure_label(self):self.assertEqual(r.low_uncertainty_band(self.rows([0,1,2,3,4]))['failure_case_keys'],['0'])
    def test_input_preserved(self):
        rows=self.rows([1,2,3]);before=copy.deepcopy(rows);r.low_uncertainty_band(rows);self.assertEqual(rows,before)
    def test_fraction_rejected(self):
        for value in (0,-1,1.1,float('nan')):
            with self.assertRaises(ValueError):r.low_uncertainty_band([],value)
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):r.low_uncertainty_band(self.rows([float('nan')]))
    def test_calibrated_empty(self):self.assertEqual(r.calibrated_band({'predictions':[]})['oof_eligible_rows'],0)
    def test_calibrated_missing(self):self.assertEqual(r.calibrated_band({'predictions':[{'probability':None}]})['accepted_rows'],0)
    def test_calibrated_boundary(self):
        result=r.calibrated_band({'predictions':[{'probability':.1,'error':True,'case_key':'a'},{'probability':.10001,'error':True,'case_key':'b'}]})
        self.assertEqual(result['accepted_rows'],1);self.assertEqual(result['failure_case_keys'],['a'])
    def test_calibrated_compliant_not_failure(self):self.assertEqual(r.calibrated_band({'predictions':[{'probability':.01,'error':False,'case_key':'a'}]})['failure_case_keys'],[])

class CommonTests(unittest.TestCase):
    def models(self):
        return {m:[{'case_key':str(i),'benchmark':'b','canonical_base_id':str(i),'panel':'official_reference_compliance','official_score':{'correct':i%2==0},'u':{'a':i,'b':i+1}} for i in range(4)] for m in ('qwen15b','llama3b','qwen7b')}
    def call(self,models,names=('a',),scope='official_reference_compliance'):
        return r.common_rows(models,names,{'measures':{'a':['u','a'],'b':['u','b']}},lambda row,loc:None if row[loc[0]] is None else row[loc[0]][loc[1]],scope)
    def test_all_shared(self):self.assertEqual(len(self.call(self.models())[0]),4)
    def test_missing_not_imputed(self):
        models=self.models();models['llama3b'][0]['u']=None;rows,total=self.call(models)
        self.assertEqual(total,4);self.assertEqual(len(rows),3)
    def test_empty_scope(self):self.assertEqual(self.call(self.models(),scope='none'),([],0))
    def test_benchmark_scope(self):self.assertEqual(len(self.call(self.models(),scope='b')[0]),4)
    def test_outcomes_model_specific(self):
        models=self.models();models['llama3b'][0]['official_score']['correct']=False
        row=self.call(models)[0][0];self.assertTrue(row['models']['llama3b']['error']);self.assertFalse(row['models']['qwen15b']['error'])
    def test_different_cases_rejected(self):
        models=self.models();models['qwen7b'].pop()
        with self.assertRaises(ValueError):self.call(models)
    def test_multiple_measures(self):self.assertEqual(set(self.call(self.models(),('a','b'))[0][0]['models']['qwen7b']),{'error','a','b'})
    def test_no_mutation(self):
        models=self.models();before=copy.deepcopy(models);self.call(models);self.assertEqual(models,before)

class TaxonomyTests(unittest.TestCase):
    def data(self):
        rows=[{'case_key':str(i),'benchmark':'b','canonical_base_id':str(i%140),'source_file':'x'} for i in range(1728)]
        records=[{**row,'split':'development','population':'primary','sample':{'perturbation':{'mdp_category':'action','type':'x'}}} for row in rows]
        return records,{'qwen15b':rows}
    def test_full_taxonomy(self):
        records,models=self.data();self.assertEqual(len(r.taxonomy(records,models,lambda x:'action')),1728)
    def test_missing(self):
        records,models=self.data()
        with self.assertRaises(ValueError):r.taxonomy(records[:-1],models,lambda x:'action')
    def test_duplicate(self):
        records,models=self.data()
        with self.assertRaises(ValueError):r.taxonomy(records+[records[0]],models,lambda x:'action')
    def test_partition(self):
        records,models=self.data();records[0]['split']='test'
        with self.assertRaises(ValueError):r.taxonomy(records,models,lambda x:'action')
    def test_lineage(self):
        records,models=self.data();records[0]['benchmark']='other'
        with self.assertRaises(ValueError):r.taxonomy(records,models,lambda x:'action')

if __name__=='__main__':unittest.main()
