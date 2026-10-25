"""Synthetic CPU checks; do not open development/held-out data or use models."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import review as r

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.cfg=r.policy()
        self.messages=[{'role':'system','content':'Available tools.'},{'role':'user','content':'Please use minimal cost.'}]
        body={'messages':self.messages}
        self.request={'case_key':'clean.jsonl:synthetic','canonical_base_id':'synthetic','benchmark':'apibank','source_file':'clean.jsonl',
                      'request':body,'messages_sha256':r.sha(r.canonical(self.messages).encode()),'request_sha256':r.sha(r.canonical(body).encode())}
        self.score={'case_key':self.request['case_key'],'canonical_base_id':'synthetic','benchmark':'apibank','source_file':'clean.jsonl',
                    'panel':'official_reference_compliance','official_score':{'correct':False,'score':0.0},
                    'official_labels_changed':False,'ambiguity_exclusion_applied':False,
                    'reference_review_flags':['original_flag'],'objective_detection':{'cost_explicit_detected':False,'latency_explicit_detected':False}}
        self.reference={'case_key':self.request['case_key'],'golden_answers':[{'name':'f','parameters':{'api_key':'synthetic_secret'}}]}

    def check(self):return r.review_case(self.request,self.score,self.reference,self.cfg)
    def update_messages(self):
        self.request['messages_sha256']=r.sha(r.canonical(self.messages).encode())
        self.request['request_sha256']=r.sha(r.canonical(self.request['request']).encode())

    def test_missing_credential_signal_without_value_disclosure(self):
        out=self.check();self.assertTrue(out['reference_credential_literal_absence_signal'])
        self.assertNotIn('synthetic_secret',r.canonical(out));self.assertNotIn(r.sha(b'synthetic_secret'),r.canonical(out))

    def test_presence_in_system_or_user_is_not_absence(self):
        for i in (0,1):
            messages=copy.deepcopy(self.messages);messages[i]['content']='synthetic_secret'
            checks=r.credential_signals(self.reference,messages,{'api_key'})
            self.assertTrue(checks[0]['literal_present']);self.assertEqual(checks[0]['message_indices_with_literal'],[i])

    def test_presence_is_case_sensitive(self):
        self.messages[1]['content']='SYNTHETIC_SECRET';self.update_messages()
        self.assertTrue(self.check()['reference_credential_literal_absence_signal'])

    def test_empty_numeric_and_unlisted_fields_not_inferred(self):
        self.reference['golden_answers'][0]['parameters']={'api_key':'','token':123,'unlisted':'secret'}
        self.assertEqual(self.check()['credential_literal_checks'],[])

    def test_arguments_alias_supported(self):
        self.reference['golden_answers']=[{'name':'f','arguments':{'token':'secret'}}]
        self.assertTrue(self.check()['reference_credential_literal_absence_signal'])

    def test_nested_values_are_not_guessed(self):
        self.reference['golden_answers'][0]['parameters']={'auth':{'api_key':'secret'}}
        self.assertEqual(self.check()['credential_literal_checks'],[])

    def test_minimal_cost_is_separate_signal(self):
        out=self.check();self.assertFalse(out['original_objective_detection_flags']['cost_explicit_detected'])
        self.assertTrue(out['supplemental_user_phrase_diagnostics']['cost']['old_detector_nondetection_with_new_phrase'])
        self.assertEqual(out['original_reference_review_flags'],['original_flag'])
        self.assertEqual(out['official_score'],self.score['official_score'])

    def test_most_responsive_is_separate_signal(self):
        self.messages[1]['content']='Select the most responsive option.';self.update_messages()
        self.assertTrue(self.check()['supplemental_user_phrase_diagnostics']['latency']['old_detector_nondetection_with_new_phrase'])

    def test_phrase_in_system_description_not_promoted(self):
        self.messages[0]['content']='Tool description: minimal cost, most responsive option.'
        self.messages[1]['content']='Hello';self.update_messages()
        out=self.check()
        self.assertFalse(out['supplemental_user_phrase_diagnostics']['cost']['supplemental_phrase_present'])

    def test_embedded_assistant_dialogue_excluded(self):
        self.messages[1]['content']='<user>Hello</user><response>minimal cost</response>';self.update_messages()
        self.assertFalse(self.check()['supplemental_user_phrase_diagnostics']['cost']['supplemental_phrase_present'])

    def test_negation_remains_review_signal_not_intent_label(self):
        self.messages[1]['content']='Do not optimize for minimal cost.';self.update_messages()
        out=self.check();self.assertTrue(out['supplemental_user_phrase_diagnostics']['cost']['supplemental_phrase_present'])
        self.assertEqual(out['semantic_adjudication'],'not_performed');self.assertFalse(out['excluded'])

    def test_old_detection_true_not_replaced(self):
        self.score['objective_detection']['cost_explicit_detected']=True
        out=self.check();self.assertTrue(out['original_objective_detection_flags']['cost_explicit_detected'])
        self.assertFalse(out['supplemental_user_phrase_diagnostics']['cost']['old_detector_nondetection_with_new_phrase'])

    def test_outcome_independent_signal(self):
        before=self.check();self.score['official_score']={'correct':True,'score':1.0};after=self.check()
        self.assertEqual(before['credential_literal_checks'],after['credential_literal_checks'])
        self.assertEqual(before['supplemental_user_phrase_diagnostics'],after['supplemental_user_phrase_diagnostics'])

    def test_inputs_not_mutated(self):
        before=copy.deepcopy((self.request,self.score,self.reference));self.check()
        self.assertEqual(before,(self.request,self.score,self.reference))

    def test_prompt_fingerprint_rejected(self):
        self.messages[1]['content']='tampered'
        with self.assertRaises(ValueError):self.check()

    def test_identity_mismatch_rejected(self):
        self.reference['case_key']='wrong'
        with self.assertRaises(ValueError):self.check()

    def test_label_changes_rejected(self):
        self.score['official_labels_changed']=True
        with self.assertRaises(ValueError):self.check()

    def test_tooleyes_panel_stays_separate(self):
        self.request['benchmark']=self.score['benchmark']='tooleyes';self.score['panel']='tooleyes_relevance'
        report=r.summarize([self.check()],self.cfg)
        self.assertEqual(report['by_panel']['official_reference_compliance']['rows'],0)
        self.assertEqual(report['by_panel']['tooleyes_relevance']['rows'],1)

    def test_invalid_old_detection_rejected(self):
        self.score['objective_detection']['cost_explicit_detected']='false'
        with self.assertRaises(ValueError):self.check()

    def test_duplicate_and_nonfinite_json_rejected(self):
        for raw in ('{"a":1,"a":2}','{"a":NaN}'):
            with self.assertRaises(ValueError):r.loads(raw)

    def test_duplicate_case_rejected(self):
        with self.assertRaises(ValueError):r.index([self.score,self.score])

    def test_policy_integrity(self):
        self.assertEqual(r.sha((r.HERE/'review_policy_v1.json').read_bytes().replace(b'\r\n',b'\n')),r.POLICY_SHA)
        self.assertFalse(self.cfg['held_out_access_enabled'])

    def test_existing_output_rejected_before_inputs(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);out=repo/'artifacts/local_development_audits/review';out.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError,'already exists'):r.run(repo,out)

    def test_synthetic_end_to_end_relative_paths_and_preserved_inputs(self):
        import os
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t).resolve();root=repo/'artifacts/local_development_audits'
            score_dir=root/'corrected_qwen15b_coverage_official_scoring_v1'
            prepared=root/'corrected_qwen15b_coverage_import_217d4a47/prepared'
            score_dir.mkdir(parents=True);prepared.mkdir(parents=True)
            requests=[];scores=[];refs=[]
            for i in range(69):
                key='clean.jsonl:synthetic_'+str(i)
                req=copy.deepcopy(self.request);req['case_key']=key
                score=copy.deepcopy(self.score);score['case_key']=key
                ref=copy.deepcopy(self.reference);ref['case_key']=key
                requests.append(req);scores.append(score);refs.append(ref)
            ref_bundle={'scope':'selected-primary-development-references-only',
                'source_sha256':'ec1bccc61aca1fb57eefd072fb81e3a9b37ed7aabc2575b161e4033abbe0df93','references':refs}
            prov={'input_sha256':{
                'artifacts/local_development_audits/full_primary_export_v1/attestation.json':'77071dc342a19b0f32995fed9f9f9e25840294e633ef5368830f07a3ccf3ccb9',
                'artifacts/local_development_audits/full_primary_export_v1/references.jsonl':ref_bundle['source_sha256']}}
            manifest={'scope':'corrected-primary-development-only','selection':'coverage',
                      'held_out_access_enabled':False,'main_experiment_ready':False,'request_count':69,
                      'requests_sha256':r.sha(r.canonical(requests).encode())}
            values={'scores.json':(score_dir/'scores.json',scores),
                    'provenance.json':(score_dir/'provenance.json',prov),
                    'coverage_reference_review_inputs_v1.json':(root/'coverage_reference_review_inputs_v1.json',ref_bundle),
                    'prepared/manifest.json':(prepared/'manifest.json',manifest),
                    'prepared/requests.json':(prepared/'requests.json',requests)}
            cfg=copy.deepcopy(self.cfg);originals={}
            for name,(path,value) in values.items():
                raw=r.canonical(value).encode();path.write_bytes(raw)
                cfg['input_sha256'][name]=r.sha(raw);originals[path]=raw
            cwd=Path.cwd()
            try:
                os.chdir(repo)
                with patch.object(r,'policy',return_value=cfg),patch.object(r.subprocess,'run'):
                    report=r.run(Path('.'),Path('artifacts/local_development_audits/review'))
            finally:os.chdir(cwd)
            self.assertEqual(report['rows'],69)
            self.assertEqual({p:p.read_bytes() for p in originals},originals)
            self.assertEqual({p.name for p in (root/'review').iterdir()},{'summary.json','diagnostics.json','provenance.json'})

    def test_publish_transient_error_recovers(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'src';dst=Path(t)/'dst';src.mkdir();(src/'x').write_text('preserved')
            original=Path.rename;attempts=[]
            def rename(p,target):
                attempts.append(1)
                if len(attempts)==1:raise PermissionError('synthetic')
                return original(p,target)
            with patch.object(Path,'rename',new=rename),patch.object(r.time,'sleep'):r.publish(src,dst)
            self.assertEqual((dst/'x').read_text(),'preserved');self.assertEqual(len(attempts),2)

    def test_publish_persistent_error_bounded(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'src';dst=Path(t)/'dst';src.mkdir()
            with patch.object(Path,'rename',side_effect=PermissionError('synthetic')) as call,patch.object(r.time,'sleep') as pause:
                with self.assertRaises(PermissionError):r.publish(src,dst)
            self.assertEqual(call.call_count,6);self.assertEqual(pause.call_count,5);self.assertTrue(src.exists());self.assertFalse(dst.exists())

    def test_publish_preserves_existing_destination(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'src';dst=Path(t)/'dst';src.mkdir();dst.mkdir();(dst/'x').write_text('prior')
            with self.assertRaises(ValueError):r.publish(src,dst)
            self.assertEqual((dst/'x').read_text(),'prior')

if __name__=='__main__':unittest.main()
