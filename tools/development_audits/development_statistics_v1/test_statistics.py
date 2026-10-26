"""Synthetic tests; no dataset, server, model or held-out inputs."""
import importlib.util
from pathlib import Path
import random
import sys
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cluster_statistics_tested', HERE/'statistics.py')
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)
sys.path.insert(0,str(HERE))
import run_statistics as run

class StatisticsTests(unittest.TestCase):
    def rows(self):
        return [{'benchmark':b,'canonical_base_id':str(g),'case_key':f'{b}-{g}-{i}'} for b in ('a','b') for g in range(10) for i in range(g%3+1)]

    def test_percentile_interpolation(self):
        self.assertEqual(st.percentile([0,10],.25),2.5)

    def test_percentile_empty(self):
        self.assertIsNone(st.percentile([],.5))

    def test_percentile_endpoints(self):
        self.assertEqual([st.percentile([3,1,2],p) for p in (0,1)],[1,3])

    def test_cluster_reproducible(self):
        self.assertEqual(st.cluster_draw(self.rows(),random.Random(12)),st.cluster_draw(self.rows(),random.Random(12)))

    def test_draw_preserves_complete_group_multiplicity(self):
        rows=self.rows();draw=st.cluster_draw(rows,random.Random(7))
        from collections import Counter
        counts=Counter(r['case_key'] for r in draw)
        for b in ('a','b'):
            multiplicities=[]
            for g in range(10):
                block=[counts[r['case_key']] for r in rows if r['benchmark']==b and r['canonical_base_id']==str(g)]
                self.assertEqual(len(set(block)),1)
                multiplicities.append(block[0])
            self.assertEqual(sum(multiplicities),10)

    def test_duplicate_draws_not_deduplicated(self):
        draw=st.cluster_draw(self.rows(),random.Random(7))
        self.assertLess(len({r['case_key'] for r in draw}),len(draw))

    def test_group_ids_namespaced_by_benchmark(self):
        result=st.bootstrap(self.rows(),lambda r:{'n':len(r)},10)
        self.assertEqual(result['n']['canonical_groups'],20)

    def test_small_group_interval_withheld(self):
        self.assertEqual(st.interval(.5,[.1]*100,100,9)['interval_unavailable_reason'],'fewer_than_10_canonical_groups')

    def test_ten_groups_interval_allowed(self):
        self.assertEqual(st.interval(.5,[.1]*100,100,10)['interval_95_percentile'],[.1,.1])

    def test_undefined_point_withheld(self):
        self.assertEqual(st.interval(None,[.1]*100,100,10)['interval_unavailable_reason'],'point_metric_undefined')

    def test_valid_fraction_boundary(self):
        self.assertIsNotNone(st.interval(.5,[.1]*90+[None]*10,100,10)['interval_95_percentile'])
        self.assertIsNone(st.interval(.5,[.1]*89+[None]*11,100,10)['interval_95_percentile'])

    def test_nonfinite_replicates_invalid(self):
        self.assertEqual(st.interval(.5,[float('nan'),None,.1],3,10)['valid_replicates'],1)

    def test_bootstrap_deterministic(self):
        f=lambda r:{'n':len(r)}
        self.assertEqual(st.bootstrap(self.rows(),f,100),st.bootstrap(self.rows(),f,100))

    def test_bootstrap_rejects_bad_count(self):
        for n in (0,-1,True,1.5):
            with self.subTest(n=n),self.assertRaises(ValueError):st.bootstrap([],lambda r:{},n)

    def test_bootstrap_rejects_changing_metrics(self):
        count=[0]
        def f(rows):
            count[0]+=1
            return {str(count[0]):0}
        with self.assertRaises(ValueError):st.bootstrap(self.rows(),f,2)

    def test_inputs_preserved(self):
        import copy
        rows=self.rows();before=copy.deepcopy(rows)
        st.bootstrap(rows,lambda r:{'n':len(r)},20)
        self.assertEqual(rows,before)

    def test_svg_escapes_title(self):
        self.assertIn('&lt;example&gt;',run.svg({},'<example>'))

    def test_svg_no_origin_risk(self):
        output=run.svg({'a':[{'risk':None,'panel_coverage':0}]},'test')
        self.assertNotIn('<circle',output)

    def test_svg_uses_original_panel_coverage(self):
        output=run.svg({'a':[{'risk':.5,'panel_coverage':.5}]},'test')
        self.assertIn('cx="395.0"',output)
        self.assertNotIn('<polyline',output)

    def test_seed_stable_distinct(self):
        self.assertEqual(st.stable_seed('panel/cohort'),st.stable_seed('panel/cohort'))
        self.assertNotEqual(st.stable_seed('a'),st.stable_seed('b'))


    def test_model_differences_and_direction(self):
        class Metrics:
            @staticmethod
            def discrimination(labels,scores):
                return {'auroc':sum(scores)/len(scores),'average_precision':sum(labels)/len(labels)}
            @staticmethod
            def risk_coverage(labels,scores,total):
                return {'tie_block_right_step_area_on_eligible_coverage':sum(labels)/total}
        rows=[{'models':{'a':{'error':False,'x':.9},'b':{'error':True,'x':.2}}}]
        result=run.evaluate(rows,'x',Metrics)
        self.assertAlmostEqual(result['a-minus-b/auroc'],.7)
        self.assertEqual(result['a-minus-b/average_precision'],-1)

    def test_undefined_difference_retained(self):
        class Metrics:
            @staticmethod
            def discrimination(labels,scores):return {'auroc':None,'average_precision':None}
            @staticmethod
            def risk_coverage(labels,scores,total):return {'tie_block_right_step_area_on_eligible_coverage':0}
        rows=[{'models':{'a':{'error':False,'x':0},'b':{'error':False,'x':0}}}]
        self.assertIsNone(run.evaluate(rows,'x',Metrics)['a-minus-b/auroc'])

    def test_identical_models_paired_zero_differences(self):
        class Metrics:
            @staticmethod
            def discrimination(labels,scores):return {'auroc':sum(scores)/len(scores),'average_precision':sum(labels)/len(labels)}
            @staticmethod
            def risk_coverage(labels,scores,total):return {'tie_block_right_step_area_on_eligible_coverage':sum(labels)/total}
        rows=[{'benchmark':'a','canonical_base_id':str(i),'models':{m:{'error':bool(i%2),'x':i/10} for m in ('a','b')}} for i in range(12)]
        result=st.bootstrap(rows,lambda r:run.evaluate(r,'x',Metrics),100)
        self.assertEqual(result['a-minus-b/auroc']['interval_95_percentile'],[0,0])

    def test_existing_output_refused(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):run.run(Path(d),Path(d))

    def test_empty_cohort_is_explicit(self):
        self.assertEqual(st.bootstrap([],lambda r:{'metric':None},10)['metric']['undefined_replicates'],10)

    def test_single_group_all_rows_retained(self):
        rows=[{'benchmark':'a','canonical_base_id':'g','case_key':str(i)} for i in range(5)]
        self.assertEqual(st.cluster_draw(rows,random.Random(1)),rows)

if __name__=='__main__':unittest.main()
