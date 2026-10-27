"""Synthetic regression tests; no model, dataset or held-out records."""
from pathlib import Path
import copy
import math
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import calibration as c

class Tests(unittest.TestCase):
    def rows(self):
        return [{'case_key':str(i),'benchmark':'a','canonical_base_id':str(i//2),'score':i/10,'error':bool(i%3)} for i in range(60)]

    def test_sigmoid_extremes(self):
        self.assertEqual(c.sigmoid(-1000),0);self.assertEqual(c.sigmoid(1000),1)
    def test_sigmoid_zero(self):self.assertEqual(c.sigmoid(0),.5)
    def test_softplus_stable(self):self.assertTrue(math.isfinite(c.softplus(1000)))
    def test_folds_group_separated(self):
        rows=self.rows();f=c.folds(rows)
        self.assertEqual(len(f),30)
        self.assertEqual(set(f.values()),set(range(5)))
    def test_folds_order_independent(self):self.assertEqual(c.folds(self.rows()),c.folds(list(reversed(self.rows()))))
    def test_folds_ignore_labels(self):
        rows=self.rows();other=[{**r,'error':not r['error'],'score':999} for r in rows]
        self.assertEqual(c.folds(rows),c.folds(other))
    def test_fit_monotonic_signal(self):
        m=c.fit([0,0,.1,1,2,3],[False,False,False,True,True,True])
        self.assertGreater(c.predict(m,3),c.predict(m,0))
    def test_fit_constant_feature(self):
        m=c.fit([1]*4,[False,False,True,True]);self.assertAlmostEqual(c.predict(m,1),.5)
    def test_fit_one_class_refused(self):
        with self.assertRaises(ValueError):c.fit([1,2],[True,True])
    def test_fit_nonfinite_refused(self):
        for x in (float('inf'),float('nan'),-1,True):
            with self.subTest(x=x),self.assertRaises(ValueError):c.fit([x,1],[False,True])
    def test_labels_boolean(self):
        with self.assertRaises(ValueError):c.fit([1,2],[0,1])
    def test_baseline_scores(self):
        m=c.measures([{'probability':.5,'error':True},{'probability':.5,'error':False}])
        self.assertEqual(m['brier_score'],.25);self.assertAlmostEqual(m['log_loss_clipped_1e_minus_15'],math.log(2));self.assertEqual(m['ece_10_equal_width_bins'],0)
    def test_perfect_scores(self):
        m=c.measures([{'probability':1,'error':True},{'probability':0,'error':False}])
        self.assertEqual(m['brier_score'],0);self.assertEqual(m['ece_10_equal_width_bins'],0)
    def test_empty_metrics(self):self.assertIsNone(c.measures([])['brier_score'])
    def test_fixed_bin_boundaries(self):
        bins=c.measures([{'probability':.1,'error':True},{'probability':1.,'error':False}])['reliability_bins']
        self.assertEqual(bins[1]['rows'],1);self.assertEqual(bins[9]['rows'],1)
    def test_bad_probabilities(self):
        for p in (-.1,1.1,float('nan'),True):
            with self.subTest(p=p),self.assertRaises(ValueError):c.measures([{'probability':p,'error':True}])
    def test_crossfit_covers_all_rows(self):
        rows=self.rows();r=c.crossfit(rows,c.folds(rows));self.assertEqual(r['oof_rows'],60)
    def test_crossfit_no_group_overlap(self):
        rows=self.rows();idx={r['case_key']:r['canonical_base_id'] for r in rows}
        for f in c.crossfit(rows,c.folds(rows))['folds']:
            self.assertFalse({idx[k] for k in f['train_case_keys']} & {idx[k] for k in f['validation_case_keys']})
    def test_crossfit_preserves_inputs(self):
        rows=self.rows();before=copy.deepcopy(rows);c.crossfit(rows,c.folds(rows));self.assertEqual(rows,before)
    def test_crossfit_deterministic(self):
        rows=self.rows();self.assertEqual(c.crossfit(rows,c.folds(rows)),c.crossfit(rows,c.folds(rows)))
    def test_one_class_unavailable(self):
        rows=[{**r,'error':False} for r in self.rows()];r=c.crossfit(rows,c.folds(rows));self.assertEqual(r['oof_rows'],0)
    def test_small_cohort_unavailable(self):
        rows=self.rows()[:10];self.assertEqual(c.crossfit(rows,c.folds(rows))['oof_rows'],0)
    def test_duplicate_identity_rejected(self):
        rows=self.rows();rows.append(rows[0])
        with self.assertRaises(ValueError):c.crossfit(rows,c.folds(rows))
    def test_train_only_scaling(self):
        rows=self.rows();assignment=c.folds(rows);first=c.crossfit(rows,assignment)
        altered=[{**r,'score':10000,'error':not r['error']} if assignment[('a',r['canonical_base_id'])]==0 else r for r in rows]
        second=c.crossfit(altered,assignment)
        self.assertEqual(first['folds'][0]['fitted_parameters'],second['folds'][0]['fitted_parameters'])
        self.assertEqual(first['folds'][0]['training_fold_smoothed_baseline'],second['folds'][0]['training_fold_smoothed_baseline'])

if __name__=='__main__':unittest.main()
