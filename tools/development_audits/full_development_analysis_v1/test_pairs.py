import copy
import unittest
import pairs as p

class Tests(unittest.TestCase):
    def row(self,key='c',source='clean.jsonl',correct=True,nll=.1,group='g',panel='official_reference_compliance'):
        return {'case_key':key,'source_file':source,'official_score':{'correct':correct},'whole_output_scores':None if nll is None else {'mean_token_nll':nll},'benchmark':'b','canonical_base_id':group,'panel':panel,'reference_review_flags':['flag']}
    def test_pair(self):self.assertEqual(len(p.paired([self.row(),self.row('p','x') ])),1)
    def test_duplicate_case(self):
        with self.assertRaises(ValueError):p.paired([self.row(),self.row()])
    def test_duplicate_anchor(self):
        with self.assertRaises(ValueError):p.paired([self.row(),self.row('c2')])
    def test_missing_anchor(self):
        with self.assertRaises(ValueError):p.paired([self.row('p','x')])
    def test_panel_mismatch(self):
        with self.assertRaises(ValueError):p.paired([self.row(),self.row('p','x',panel='tooleyes_relevance')])
    def test_bad_label(self):
        with self.assertRaises(ValueError):p.paired([self.row(),self.row('p','x',correct=1)])
    def test_correct_to_incorrect(self):self.assertEqual(p.paired([self.row(),self.row('p','x',False)])[0]['correctness_change_perturbed_minus_clean'],-1)
    def test_incorrect_to_correct(self):self.assertEqual(p.paired([self.row(correct=False),self.row('p','x')])[0]['correctness_change_perturbed_minus_clean'],1)
    def test_missing_clean_evidence(self):self.assertIsNone(p.paired([self.row(nll=None),self.row('p','x')])[0]['mean_nll_change_perturbed_minus_clean'])
    def test_missing_perturbed_evidence(self):self.assertIsNone(p.paired([self.row(),self.row('p','x',nll=None)])[0]['mean_nll_change_perturbed_minus_clean'])
    def test_nll_direction(self):self.assertAlmostEqual(p.paired([self.row(),self.row('p','x',nll=.4)])[0]['mean_nll_change_perturbed_minus_clean'],.3)
    def test_flags_retained(self):self.assertEqual(p.paired([self.row(),self.row('p','x')])[0]['perturbed_reference_flags'],['flag'])
    def test_inputs_unchanged(self):
        rows=[self.row(),self.row('p','x')];before=copy.deepcopy(rows);p.paired(rows);self.assertEqual(rows,before)
    def test_empty_summary(self):self.assertIsNone(p.summarize([])['pair_weighted_correctness_change'])
    def test_transition_counts(self):self.assertEqual(p.summarize(p.paired([self.row(),self.row('p','x',False)]))['transitions'],{'CI':1})
    def test_weighting_distinguished(self):
        rows=[self.row(),self.row('p','x',False),self.row('p2','y',False),self.row('c2',group='g2'),self.row('p3','x',group='g2')]
        result=p.summarize(p.paired(rows));self.assertAlmostEqual(result['pair_weighted_correctness_change'],-2/3);self.assertEqual(result['equal_group_weighted_correctness_change'],-.5)
    def test_full_1588_pairs(self):
        rows=[self.row('c'+str(g),group=str(g)) for g in range(140)]
        rows += [self.row('p'+str(i),'x',group=str(i%140)) for i in range(1588)]
        self.assertEqual(len(p.paired(rows)),1588)
    def test_correctness_does_not_require_nll(self):self.assertEqual(p.summarize(p.paired([self.row(nll=None),self.row('p','x',False,nll=None)]))['transitions'],{'CI':1})

if __name__=='__main__':unittest.main()
