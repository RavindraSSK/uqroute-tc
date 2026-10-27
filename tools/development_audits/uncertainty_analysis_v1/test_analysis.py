"""CPU-only synthetic metric and artifact-boundary tests; no datasets/models."""
import copy
import itertools
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import analyze as a
from metrics import discrimination as d,risk_coverage as rc


def row(i=0,benchmark='apibank',correct=False,meaningful=True):
    return {'case_key':'clean.jsonl:synthetic_'+str(i),'canonical_base_id':'group_'+str(i//2),'benchmark':benchmark,'source_file':'clean.jsonl',
            'panel':'tooleyes_relevance' if benchmark=='tooleyes' else 'official_reference_compliance',
            'official_score':{'correct':correct,'score':float(correct)},'reference_review_flags':['synthetic_signal'],
            'official_labels_changed':False,'ambiguity_exclusion_applied':False,'evidence_status':'complete',
            'whole_output_scores':{'sequence_nll':float(i+1),'mean_token_nll':float(i+1)/10,'max_token_surprisal':float(i+1)/5},
            'meaningful_token_score':{'mean_token_nll':float(i+1)/20} if meaningful else None,
            'alignment_diagnostic':{'category':'eligible' if meaningful else 'synthetic_unavailable'}}

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

class AnalysisTests(unittest.TestCase):
    def setUp(self):self.cfg=a.policy()
    def test_panels_never_pooled(self):
        out=a.analyze([row(0),row(1,'tooleyes',True)],self.cfg)
        self.assertEqual(out['by_panel']['official_reference_compliance']['original_rows'],1)
        self.assertEqual(out['by_panel']['tooleyes_relevance']['official_correct'],1)
        self.assertNotIn('overall_accuracy',out)
    def test_flags_do_not_exclude(self):
        out=a.cohort([row()],self.cfg);self.assertEqual(out['reference_flagged_rows_retained'],1);self.assertEqual(out['original_rows'],1)
    def test_common_cohort_uses_all_measures(self):
        out=a.cohort([row(0,meaningful=False),row(1,correct=True)],self.cfg)
        self.assertEqual(out['available_case_analysis']['mean_token_nll']['discrimination']['eligible_rows'],2)
        self.assertEqual(out['common_eligible_case_analysis']['rows'],1)
        for result in out['common_eligible_case_analysis']['measures'].values():
            self.assertEqual(result['discrimination']['eligible_rows'],1)
            self.assertEqual(result['risk_coverage']['maximum_panel_coverage'],0.5)
    def test_no_meaningful_is_unavailable_not_zero(self):
        out=a.cohort([row(0,meaningful=False)],self.cfg)
        result=out['available_case_analysis']['meaningful_mean_token_nll']
        self.assertIsNone(result['discrimination']['average_precision']);self.assertEqual(result['unavailable_reasons'],{'synthetic_unavailable':1})
    def test_saved_scores_not_mutated(self):
        rows=[row(),row(1,correct=True)];before=copy.deepcopy(rows);a.analyze(rows,self.cfg);self.assertEqual(rows,before)
    def test_uses_correct_boolean_not_partial_score(self):
        r=row();r['official_score']['score']=2/3
        self.assertEqual(a.cohort([r],self.cfg)['official_noncompliant_or_irrelevant'],1)
    def test_missing_measure_key_rejected(self):
        r=row();r['whole_output_scores']={}
        with self.assertRaises(ValueError):a.measured(r,['whole_output_scores','sequence_nll'])
    def test_nan_saved_measure_rejected(self):
        r=row();r['whole_output_scores']['sequence_nll']=float('nan')
        with self.assertRaises(ValueError):a.measured(r,['whole_output_scores','sequence_nll'])
    def test_no_calibration_or_threshold_fitting(self):
        out=a.analyze([row()],self.cfg)
        self.assertEqual(out['calibration'],'not_fitted_or_evaluated');self.assertEqual(out['routing_threshold'],'not_selected')
        self.assertFalse(out['held_out_access_enabled']);self.assertFalse(out['main_experiment_ready'])
    def test_duplicate_json_and_nonfinite_rejected(self):
        for raw in ('{"a":1,"a":2}','{"a":NaN}'):
            with self.assertRaises(ValueError):a.loads(raw)
    def test_duplicate_case_rejected(self):
        with self.assertRaises(ValueError):a.index([row(),row()])
    def test_existing_output_refused_before_inputs(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);out=repo/'artifacts/local_development_audits/analysis';out.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError,'already exists'):a.run(repo,out)
    def test_output_outside_artifacts_refused(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t)
            with self.assertRaisesRegex(ValueError,'inside local'):a.run(repo,repo/'bad')
    def test_policy_integrity(self):
        self.assertEqual(a.sha((a.HERE/'analysis_policy_v1.json').read_bytes().replace(b'\r\n',b'\n')),a.POLICY_SHA)
    def test_publication_transient_permission_retry(self):
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'source';output=Path(t)/'out';source.mkdir();(source/'x').write_bytes(b'unchanged')
            original=Path.rename;attempts=[]
            def rename(path,target):
                attempts.append(1)
                if len(attempts)==1:raise PermissionError('synthetic')
                return original(path,target)
            with patch.object(Path,'rename',new=rename),patch.object(a.time,'sleep'):a.publish(source,output)
            self.assertEqual((output/'x').read_bytes(),b'unchanged');self.assertEqual(len(attempts),2)
    def test_publication_persistent_error_bounded(self):
        with tempfile.TemporaryDirectory() as t:
            source=Path(t)/'source';output=Path(t)/'out';source.mkdir()
            with patch.object(Path,'rename',side_effect=PermissionError('synthetic')) as rename,patch.object(a.time,'sleep') as pause:
                with self.assertRaises(PermissionError):a.publish(source,output)
            self.assertEqual(rename.call_count,6);self.assertEqual(pause.call_count,5);self.assertFalse(output.exists())
    def test_synthetic_integration_absolute_paths_inputs_unchanged(self):
        import os
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t).resolve();root=repo/'artifacts/local_development_audits'
            score_dir=root/'corrected_qwen15b_coverage_official_scoring_v1';prepared=root/'corrected_qwen15b_coverage_import_217d4a47/prepared'
            score_dir.mkdir(parents=True);prepared.mkdir(parents=True)
            rows=[];requests=[];i=0
            for benchmark,n in [('apibank',17),('bfcl_v3',12),('rotbench',17),('toolalpaca',17),('tooleyes',6)]:
                for _ in range(n):
                    item=row(i,benchmark,correct=bool(i%2),meaningful=benchmark!='toolalpaca');rows.append(item)
                    requests.append({k:item[k] for k in ('case_key','canonical_base_id','benchmark','source_file')});i+=1
            manifest={'scope':'corrected-primary-development-only','selection':'coverage','held_out_access_enabled':False,'main_experiment_ready':False,
                      'request_count':69,'requests_sha256':a.sha(a.canonical(requests).encode())}
            provenance={'policy_sha256':'d3681b2f6bbb4a97c639f7a1a4fd01287e8101c550f8d548b6bf7d81b097f071'}
            payloads={'scores.json':(score_dir/'scores.json',rows),'provenance.json':(score_dir/'provenance.json',provenance),
                      'prepared/manifest.json':(prepared/'manifest.json',manifest),'prepared/requests.json':(prepared/'requests.json',requests)}
            cfg=copy.deepcopy(self.cfg);originals={}
            for name,(p,value) in payloads.items():
                raw=a.canonical(value).encode();p.write_bytes(raw);cfg['input_sha256'][name]=a.sha(raw);originals[p]=raw
            cwd=Path.cwd()
            try:
                os.chdir(repo)
                with patch.object(a,'policy',return_value=cfg),patch.object(a.subprocess,'run'):
                    summary=a.run(Path('.'),Path('artifacts/local_development_audits/analysis'))
            finally:os.chdir(cwd)
            self.assertEqual(summary['rows'],69);self.assertEqual({p:p.read_bytes() for p in originals},originals)
            self.assertEqual({p.name for p in (root/'analysis').iterdir()},{'analysis.json','case_measures.json','provenance.json'})
            (score_dir/'scores.json').write_bytes(b'[]')
            with patch.object(a,'policy',return_value=cfg),patch.object(a.subprocess,'run'):
                with self.assertRaisesRegex(ValueError,'fingerprint'):a.run(repo,root/'analysis_after_tamper')
            self.assertFalse((root/'analysis_after_tamper').exists())

if __name__=='__main__':unittest.main()
