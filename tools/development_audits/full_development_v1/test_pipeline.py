import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import audit_development as auditor
import export_development as exporter
from common import (BENCHMARK_REVISION,SPLIT_SHA,SOURCE_FILES,VERSION,canonical,code_hashes,json_bytes,lines_bytes,sha)

DEV='rotbench__development'
TEST='rotbench__SECRET_HELDOUT_ID'
TOOL={'name':'lookup','description':'Look up item','parameters':{'type':'object','properties':{'id':{'type':'string'}},'required':['id']}}


def raw_row(row_id,query='Look up the item'):
    system='Specifically, you have access of the following tools:\n'+json.dumps([TOOL])+"\nLet's Begin!"
    return {'id':row_id,'benchmark':'rotbench','category':'clean','level':None,
            'perturbation':json.dumps({'type':None}),
            'conversation':json.dumps([{'role':'system','content':system},{'role':'user','content':query},{'role':'assistant','content':'Action: lookup\nAction Input: {"id":"x"}'}]),
            'tools':json.dumps([TOOL]),'golden_answers':json.dumps([{'name':'lookup','parameters':{'id':'x'}}]),'eval_config':json.dumps({'method':'rule_based'})}


def fixture():
    split={'benchmark_revision':BENCHMARK_REVISION,'excludes_multi_turn':True,
           'assignments':{DEV:{'benchmark':'rotbench','population':'primary','split':'development'},TEST:{'benchmark':'rotbench','population':'primary','split':'test'}},
           'group_counts':{'primary':{'development':1,'test':1}},'row_counts':{'primary':{'development':2,'test':2}}}
    held=raw_row(TEST);held['conversation']='INVALID_NESTED_HELDOUT_SECRET';held['golden_answers']='INVALID_HELDOUT_REFERENCE_SECRET'
    sources=[('clean.jsonl',[lines_bytes([raw_row(DEV)]),lines_bytes([held])]),('query_paraphrase.jsonl',[lines_bytes([raw_row(DEV,'Find the item')]),lines_bytes([held])])]
    return split,sources


def bundle_parts():
    split,sources=fixture();samples,refs,membership,counts=exporter.partition_sources(sources,split,'primary')
    payloads={'samples.jsonl':lines_bytes(samples),'references.jsonl':lines_bytes(refs),'membership.json':json_bytes(membership)}
    att={'format_version':VERSION,'exporter_base_commit':exporter.BASE_COMMIT,'project_head':exporter.BASE_COMMIT,'implementation_hash_scheme':'sha256_source_bytes_with_CRLF_normalized_to_LF','access_boundary':'synthetic trusted exporter fixture','integrity_limit':'hashes are not a signature','benchmark_revision':BENCHMARK_REVISION,'split_sha256':SPLIT_SHA,'population':'primary','partition':'development','row_count':2,'group_count':1,'case_key_digest':sha(canonical(sorted(r['case_key'] for r in samples)).encode()),'source_file_hashes':{n:'0'*64 for n in SOURCE_FILES},'payload_hashes':{n:sha(v) for n,v in payloads.items()},'code_hashes':code_hashes(),'held_out_content_exported':False,'unselected_nested_payloads_decoded':0,'trusted_stage_counts':counts}
    return samples,refs,membership,att,payloads

class ExportTests(unittest.TestCase):
    def test_nested_heldout_payload_never_decoded(self):
        split,sources=fixture();seen=[];original=exporter.decode_development_sample
        def spy(row):
            seen.append(row['id']);return original(row)
        with patch('export_development.decode_development_sample',side_effect=spy):
            samples,refs,member,counts=exporter.partition_sources(sources,split,'primary')
        self.assertEqual(seen,[DEV,DEV]);self.assertEqual(counts['mixed_source_rows_read'],4)
        self.assertNotIn('SECRET',canonical([samples,refs,member,counts]))
    def test_builder_sample_has_no_reference_or_outcome(self):
        samples,refs,_,_,_=bundle_parts()
        self.assertNotIn('golden_answers',samples[0]['sample']);self.assertIn('golden_answers',refs[0])
    def test_duplicate_source_row_fails_without_identifier_leak(self):
        split,sources=fixture();sources[0][1].append(lines_bytes([raw_row(DEV)]))
        with self.assertRaises(ValueError) as cm:exporter.partition_sources(sources,split,'primary')
        self.assertNotIn(DEV,str(cm.exception))
    def test_unknown_identity_fails_without_payload_leak(self):
        split,sources=fixture();sources[0][1].append(json_bytes(raw_row('SECRET_UNKNOWN')))
        with self.assertRaises(ValueError) as cm:exporter.partition_sources(sources,split,'primary')
        self.assertNotIn('SECRET',str(cm.exception))
    def test_missing_development_variant_fails_count_check(self):
        split,sources=fixture();sources.pop()
        with self.assertRaises(ValueError):exporter.partition_sources(sources,split,'primary')
    def test_benchmark_assignment_conflict_fails(self):
        split,sources=fixture();row=raw_row(DEV);row['benchmark']='apibank';sources[0][1][0]=json_bytes(row)
        with self.assertRaises(ValueError):exporter.partition_sources(sources,split,'primary')
    def test_multi_turn_not_exported_or_nested_decoded(self):
        split,sources=fixture();row=raw_row('SECRET_MULTITURN');row['category']='multi_turn';row['conversation']='INVALID';sources[0][1].append(json_bytes(row))
        samples,refs,membership,counts=exporter.partition_sources(sources,split,'primary')
        self.assertEqual(len(samples),2);self.assertEqual(counts['multi_turn_rows_not_exported'],1)
    def test_group_partition_metadata_validation(self):
        split,_=fixture();split['assignments'][DEV]['split']='unknown'
        with self.assertRaises(ValueError):exporter.validate_assignments(split,'primary')
    def test_sensitivity_same_name_normalization(self):
        base='bfcl_v3__BFCL_v3_multiple__multiple_7';rowid='bfcl_v3__BFCL_v3_multiple_type_A__same_name_multiple_type_A_7'
        split={'benchmark_revision':BENCHMARK_REVISION,'excludes_multi_turn':True,'assignments':{base:{'benchmark':'bfcl_v3','population':'sensitivity_only','split':'development'}},'group_counts':{'sensitivity_only':{'development':1}},'row_counts':{'sensitivity_only':{'development':1}}}
        row=raw_row(rowid);row['benchmark']='bfcl_v3'
        samples,_,_,_=exporter.partition_sources([('same_name_A.jsonl',[json_bytes(row)])],split,'sensitivity_only')
        self.assertEqual(samples[0]['canonical_base_id'],base)
    def test_json_duplicate_keys_rejected(self):
        split,sources=fixture();sources[0][1][0]=b'{"id":"a","id":"b"}'
        with self.assertRaises(ValueError):exporter.partition_sources(sources,split,'primary')
    def test_model_outcome_fields_not_exported(self):
        split,sources=fixture();row=raw_row(DEV);row['prediction']={'raw_output':'SECRET_OUTPUT'};row['official_score']={'correct':True};sources[0][1][0]=json_bytes(row)
        samples,refs,_,_=exporter.partition_sources(sources,split,'primary')
        self.assertNotIn('SECRET_OUTPUT',canonical(samples));self.assertNotIn('official_score',canonical([samples,refs]))

class AuditorTests(unittest.TestCase):
    def test_actual_builder_repair_and_pairing_integration(self):
        samples,refs,member,att,_=bundle_parts();old=copy.deepcopy((samples,refs,member,att))
        inventory,candidates,pairs,summary=auditor.analyze(samples,refs,member,att,auditor.load_builder())
        self.assertEqual((samples,refs,member,att),old)
        self.assertEqual(len(inventory),2);self.assertEqual(len(candidates),2);self.assertTrue(pairs[0]['both_constructed'])
        self.assertEqual(summary['totals']['construction_status_counts'],{'candidate':2})
    def test_builder_reference_noninterference(self):
        samples,refs,member,att,_=bundle_parts()
        before=auditor.analyze(samples,refs,member,att,auditor.load_builder())[1]
        refs[0]['golden_answers']=[{'name':'different','parameters':{'arbitrary':'different'}}]
        after=auditor.analyze(samples,refs,member,att,auditor.load_builder())[1]
        self.assertEqual(before,after)
    def test_gold_never_supplied_to_message_builder(self):
        samples,refs,member,att,_=bundle_parts();builder=auditor.load_builder()
        def spy(sample):self.assertNotIn('golden_answers',sample);return builder(sample)
        auditor.analyze(samples,refs,member,att,spy)
    def test_unconstructable_case_retained(self):
        samples,refs,member,att,_=bundle_parts();builder=auditor.load_builder()
        def broken(sample):
            if sample['conversation'][1]['content']=='Find the item':raise ValueError('Unsupported layout')
            return builder(sample)
        inventory,candidates,pairs,summary=auditor.analyze(samples,refs,member,att,broken)
        self.assertEqual(len(inventory),2);self.assertEqual(len(candidates),1);self.assertFalse(pairs[0]['both_constructed']);self.assertTrue(summary['all_input_rows_retained'])
    def test_reference_error_retained_separately(self):
        samples,refs,member,att,_=bundle_parts()
        def broken(*args):raise ValueError('Unsupported reference')
        inv,candidates,_,summary=auditor.analyze(samples,refs,member,att,auditor.load_builder(),reference_auditor=broken)
        self.assertEqual(len(candidates),2);self.assertEqual(summary['reference_audit_status_counts'],{'unresolved_audit_error':2})
    def test_non_development_membership_fails(self):
        samples,refs,member,att,_=bundle_parts();member['groups'][DEV]['split']='test'
        with self.assertRaises(ValueError):auditor.validate_bundle(samples,refs,member,att)
    def test_raw_record_outcome_fields_rejected(self):
        samples,refs,member,att,_=bundle_parts();samples[0]['prediction']={}
        with self.assertRaises(ValueError):auditor.validate_bundle(samples,refs,member,att)
    def test_sample_reference_field_rejected(self):
        samples,refs,member,att,_=bundle_parts();samples[0]['sample']['golden_answers']=[]
        with self.assertRaises(ValueError):auditor.validate_bundle(samples,refs,member,att)
    def test_missing_clean_anchor_fails(self):
        samples,refs,member,att,_=bundle_parts();samples[0]['source_file']='CD.jsonl';samples[0]['case_key']='CD.jsonl:'+DEV;refs[0]['case_key']=samples[0]['case_key'];att['case_key_digest']=sha(canonical(sorted(r['case_key'] for r in samples)).encode())
        with self.assertRaises(ValueError):auditor.validate_bundle(samples,refs,member,att)
    def test_duplicate_reference_identity_fails(self):
        samples,refs,member,att,_=bundle_parts();refs[1]=copy.deepcopy(refs[0])
        with self.assertRaises(ValueError):auditor.validate_bundle(samples,refs,member,att)
    def test_digest_and_revision_mismatch_fails(self):
        samples,refs,member,att,_=bundle_parts();att['case_key_digest']='0'*64
        with self.assertRaises(ValueError):auditor.validate_bundle(samples,refs,member,att)
    def test_auditor_cli_has_no_raw_benchmark_or_split_argument(self):
        source=Path(auditor.__file__).read_text();cli=source.split("if __name__=='__main__':",1)[1]
        self.assertNotIn('--benchmark-root',cli);self.assertNotIn('--split',cli)
    def test_file_bundle_integration_and_no_network_or_git(self):
        samples,refs,member,att,payloads=bundle_parts()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);bundle=root/'bundle';bundle.mkdir()
            for n,raw in payloads.items():(bundle/n).write_bytes(raw)
            ar=json_bytes(att);(bundle/'attestation.json').write_bytes(ar)
            with patch('subprocess.run',side_effect=AssertionError('Auditor cannot call Git/network')):
                result=auditor.audit_bundle(bundle,sha(ar),root/'audit')
            self.assertEqual(result['totals']['rows'],2);self.assertNotIn('SECRET',''.join(p.read_text() for p in (root/'audit').iterdir()))
            self.assertTrue((root/'audit'/'summary.json').is_file())
    def test_unapproved_attestation_fails_before_builder(self):
        _,_,_,att,payloads=bundle_parts()
        with tempfile.TemporaryDirectory() as tmp:
            bundle=Path(tmp)/'bundle';bundle.mkdir()
            for n,raw in payloads.items():(bundle/n).write_bytes(raw)
            (bundle/'attestation.json').write_bytes(json_bytes(att))
            with patch('audit_development.load_builder',side_effect=AssertionError('Must not build')):
                with self.assertRaises(ValueError):auditor.audit_bundle(bundle,'0'*64,Path(tmp)/'audit')
    def test_payload_tamper_fails(self):
        _,_,_,att,payloads=bundle_parts()
        with tempfile.TemporaryDirectory() as tmp:
            bundle=Path(tmp)/'bundle';bundle.mkdir()
            for n,raw in payloads.items():(bundle/n).write_bytes(raw)
            (bundle/'samples.jsonl').write_text('{}\n');ar=json_bytes(att);(bundle/'attestation.json').write_bytes(ar)
            with self.assertRaises(ValueError):auditor.audit_bundle(bundle,sha(ar),Path(tmp)/'audit')


class TrustedExportIntegrationTests(unittest.TestCase):
    def test_complete_export_and_audit_on_synthetic_partition(self):
        import hashlib
        split,sources=fixture();split_raw=json_bytes(split);fixture_split_hash=sha(split_raw)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);project=root/'project';project.mkdir();benchmark=root/'benchmark';data=benchmark/'hf_data/datasets/api_eval';data.mkdir(parents=True)
            supplied=dict(sources)
            for name in SOURCE_FILES:(data/name).write_bytes(b''.join(supplied.get(name,[])))
            tree=''.join('100644 blob '+hashlib.sha1(b'blob '+str(len((data/name).read_bytes())).encode()+b'\0'+(data/name).read_bytes()).hexdigest()+'\thf_data/datasets/api_eval/'+name+'\n' for name in SOURCE_FILES).encode()
            def fake_git(path,*args):
                if args[0]=='merge-base':return b''
                if args==('rev-parse','HEAD'):return ((BENCHMARK_REVISION if Path(path)==benchmark else exporter.BASE_COMMIT)+'\n').encode()
                if args[0]=='status':return b''
                if args[0]=='ls-tree':return tree
                if args==('show',exporter.BASE_COMMIT+':docs/config/task1_single_sample_v1.json'):
                    return json_bytes({'benchmark':{'revision':BENCHMARK_REVISION,'split_sha256':fixture_split_hash,'split_manifest':'docs/splits/group_split_v1.json'}})
                if args==('show',exporter.BASE_COMMIT+':docs/splits/group_split_v1.json'):return split_raw
                raise AssertionError(args)
            with patch('export_development.git',side_effect=fake_git),patch('export_development.SPLIT_SHA',fixture_split_hash),patch('audit_development.SPLIT_SHA',fixture_split_hash):
                result=exporter.export(project,benchmark,project/'artifacts/bundle','primary')
                self.assertEqual(result['rows'],2);self.assertEqual(result['groups'],1)
                bundle=project/'artifacts/bundle'
                self.assertNotIn('SECRET',''.join(p.read_text() for p in bundle.iterdir()))
                audited=auditor.audit_bundle(bundle,result['attestation_sha256'],project/'artifacts/audit')
                self.assertEqual(audited['totals']['rows'],2)
                with self.assertRaises(ValueError):exporter.export(project,benchmark,bundle,'primary')
    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/'output';out.mkdir();(out/'keep').write_text('unchanged')
            with self.assertRaises(ValueError):exporter.export(root/'project',root/'benchmark',out,'primary')
            self.assertEqual((out/'keep').read_text(),'unchanged')


class AdditionalBoundaryTests(unittest.TestCase):
    def test_unselected_direct_nested_objects_reject_export(self):
        split,sources=fixture();row=raw_row(TEST);row['conversation']=[{'role':'user','content':'SECRET'}];sources[0][1][1]=json_bytes(row)
        with self.assertRaises(ValueError):exporter.partition_sources(sources,split,'primary')
    def test_invalid_selected_reference_fails_export(self):
        split,sources=fixture();row=raw_row(DEV);row['golden_answers']='INVALID';sources[0][1][0]=json_bytes(row)
        with self.assertRaises(ValueError):exporter.partition_sources(sources,split,'primary')
    def test_wrong_code_hash_blocks_auditor(self):
        _,_,_,att,payloads=bundle_parts();att['code_hashes']['repair.py']='0'*64
        with tempfile.TemporaryDirectory() as tmp:
            bundle=Path(tmp)/'bundle';bundle.mkdir()
            for n,raw in payloads.items():(bundle/n).write_bytes(raw)
            ar=json_bytes(att);(bundle/'attestation.json').write_bytes(ar)
            with self.assertRaises(ValueError):auditor.audit_bundle(bundle,sha(ar),Path(tmp)/'audit')
    def test_bundle_symlink_not_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);target=p/'target';target.write_text('{}');link=p/'link'
            try:link.symlink_to(target)
            except (OSError,NotImplementedError):self.skipTest('Symlinks unavailable in this environment')
            from common import read_regular
            with self.assertRaises(ValueError):read_regular(link)


class ToolEyesBoundaryTests(unittest.TestCase):
    def test_name_only_reference_not_validated_as_executable_arguments(self):
        samples,refs,member,att,_=bundle_parts()
        member['groups'][DEV]['benchmark']='tooleyes'
        for row in samples:
            row['benchmark']='tooleyes';row['sample']['benchmark']='tooleyes';row['sample']['conversation']=row['sample']['conversation'][:-1]
        for ref in refs:ref['golden_answers']=[{'name':'lookup','arguments':{}}]
        inventory,_,_,_=auditor.analyze(samples,refs,member,att,auditor.load_builder())
        self.assertEqual(inventory[0]['reference_schema_diagnostics'][0]['argument_validation'],'not_applicable_name_only_reference')

if __name__=='__main__':unittest.main()
