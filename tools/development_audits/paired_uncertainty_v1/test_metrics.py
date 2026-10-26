import itertools
import math
import unittest
from metrics import discrimination as d, risk_coverage as rc

class MetricTests(unittest.TestCase):
    def test_perfect_ranking(self):
        out=d([False,True],[0,1]);self.assertEqual(out['auroc'],1);self.assertEqual(out['average_precision'],1)
    def test_reversed_ranking(self):
        out=d([False,True],[1,0]);self.assertEqual(out['auroc'],0);self.assertEqual(out['average_precision'],0.5)
    def test_all_tied(self):
        out=d([True,False],[1,1]);self.assertEqual(out['auroc'],0.5);self.assertEqual(out['average_precision'],0.5)
    def test_mixed_tie_ap_definition(self):
        out=d([True,False,True],[2,2,1]);self.assertAlmostEqual(out['average_precision'],7/12);self.assertEqual(out['auroc'],0.25)
    def test_all_error_class(self):
        out=d([True,True],[1,2]);self.assertIsNone(out['auroc']);self.assertEqual(out['auroc_undefined_reason'],'one_class_outcomes');self.assertEqual(out['average_precision'],1)
    def test_no_error_class(self):
        out=d([False,False],[1,2]);self.assertIsNone(out['auroc']);self.assertIsNone(out['average_precision']);self.assertEqual(out['error_prevalence'],0)
    def test_empty_is_not_zero(self):
        out=d([],[]);self.assertIsNone(out['auroc']);self.assertIsNone(out['average_precision']);self.assertIsNone(out['error_prevalence'])
    def test_nonfinite_bool_and_none_rejected(self):
        for x in (float('nan'),float('inf'),-float('inf'),True,None,'1'):
            with self.assertRaises(ValueError):d([True],[x])
    def test_boolean_labels_required(self):
        for x in (1,0,None,'true'):
            with self.assertRaises(ValueError):d([x],[0])
    def test_mismatched_lengths(self):
        with self.assertRaises(ValueError):d([True],[])
    def test_permutation_invariance(self):
        pairs=[(True,2),(False,2),(True,1)]
        for perm in itertools.permutations(pairs):
            self.assertEqual(d(*zip(*perm)),d(*zip(*pairs)))
            self.assertEqual(rc(*zip(*perm),3),rc(*zip(*pairs),3))
    def test_auroc_exhaustive_pairwise_oracle(self):
        for n in range(2,5):
            for labels in itertools.product((False,True),repeat=n):
                if not any(labels) or all(labels):continue
                for scores in itertools.product((0,1,2),repeat=n):
                    pos=[v for v,y in zip(scores,labels) if y];neg=[v for v,y in zip(scores,labels) if not y]
                    expected=sum((p>q)+0.5*(p==q) for p in pos for q in neg)/(len(pos)*len(neg))
                    self.assertAlmostEqual(d(labels,scores)['auroc'],expected)
    def test_ap_exhaustive_threshold_oracle(self):
        for n in range(1,5):
            for labels in itertools.product((False,True),repeat=n):
                if not any(labels):continue
                for scores in itertools.product((0,1,2),repeat=n):
                    previous_recall=0;expected=0
                    for threshold in sorted(set(scores),reverse=True):
                        selected=[y for y,x in zip(labels,scores) if x>=threshold]
                        recall=sum(selected)/sum(labels);precision=sum(selected)/len(selected)
                        expected+=(recall-previous_recall)*precision;previous_recall=recall
                    self.assertAlmostEqual(d(labels,scores)['average_precision'],expected)
    def test_risk_zero_acceptance_undefined(self):
        out=rc([True,False],[0,1],2);self.assertIsNone(out['points'][0]['risk']);self.assertFalse(out['routing_threshold_selected'])
    def test_risk_ties_not_split(self):
        points=rc([True,False,True],[2,2,1],3)['points']
        self.assertEqual([p['accepted_rows'] for p in points],[0,1,3]);self.assertAlmostEqual(points[-1]['risk'],2/3)
    def test_missing_evidence_caps_original_panel_coverage(self):
        out=rc([True,False],[0,1],4);self.assertEqual(out['maximum_panel_coverage'],0.5);self.assertEqual(out['points'][-1]['panel_coverage'],0.5)
    def test_right_step_area(self):
        out=rc([False,True,False],[0,1,2],3)
        self.assertAlmostEqual(out['tie_block_right_step_area_on_eligible_coverage'],5/18)
    def test_risk_empty(self):
        out=rc([],[],5);self.assertIsNone(out['tie_block_right_step_area_on_eligible_coverage']);self.assertIsNone(out['points'][0]['risk']);self.assertEqual(out['maximum_panel_coverage'],0)
    def test_invalid_panel_denominator(self):
        for n in (-1,True,0,1.5):
            with self.assertRaises(ValueError):rc([True],[0],n)
    def test_monotonic_transform_preserves_rank_metrics(self):
        labels=[False,True,False,True];scores=[-1,0,0,1]
        self.assertEqual(d(labels,scores),d(labels,[3*x+10 for x in scores]))
