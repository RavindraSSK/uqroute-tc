import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import diagnostics as d

CONFIG=json.loads(Path(__file__).with_name('analysis_config_v1.json').read_text())
ALIASES=CONFIG['diagnostics']['type_aliases']
TOOL={'name':'f','parameters':{'properties':{'x':{'type':'integer'}},'required':['x']}}

def fixture(benchmark='apibank',correct=False):
    score={'correct':correct,'score':int(correct),'method':CONFIG['official_labels']['scorer_methods'][benchmark]}
    messages=[{'role':'system','content':'tools'},{'role':'user','content':'Please only make one tool call'}]
    record={'case_key':benchmark+':fixture','official_score':score,'status':'returned','finish_reason':'stop','request':{'messages':messages},'prediction':{'raw_output':'Action: f\nAction Input: {"x": 1}','tool_calls':[{'name':'f','parameters':{'x':1}}]}}
    candidate={'benchmark':benchmark,'messages':messages,'tools':[TOOL]}
    return record,candidate

class TypeTests(unittest.TestCase):
    def test_boolean_is_not_integer_or_number(self):
        for kind in ('integer','int','number','float'):self.assertEqual(d.type_compatibility(True,kind,ALIASES),'incompatible')
    def test_numeric_strings_are_not_coerced(self):
        self.assertEqual(d.type_compatibility('1','int',ALIASES),'incompatible')
    def test_aliases_and_integer_float(self):
        self.assertEqual(d.type_compatibility(1.0,'int',ALIASES),'compatible')
        self.assertEqual(d.type_compatibility(1.5,'integer',ALIASES),'incompatible')
        self.assertEqual(d.type_compatibility('a','str',ALIASES),'compatible')
    def test_unknown_type_and_union(self):
        self.assertEqual(d.type_compatibility(1,'mystery',ALIASES),'unknown')
        self.assertEqual(d.type_compatibility(None,['string','null'],ALIASES),'compatible')
        self.assertEqual(d.type_compatibility(1,['string','mystery'],ALIASES),'unknown')
    def test_nonfinite_rejected(self):
        self.assertEqual(d.type_compatibility(float('inf'),'number',ALIASES),'incompatible')
        self.assertEqual(d.type_compatibility(float('nan'),'integer',ALIASES),'incompatible')

class SchemaTests(unittest.TestCase):
    def test_missing_required_metadata_is_unknown(self):
        x=d.schema_occurrence({}, {'properties':{}},ALIASES)
        self.assertEqual(x['required_key_presence'],'unknown')
        self.assertEqual(x['declared_argument_checks'],'unknown')
    def test_explicit_empty_required_is_known(self):
        self.assertEqual(d.schema_occurrence({}, {'properties':{},'required':[]},ALIASES)['declared_argument_checks'],'compatible')
    def test_missing_required_key(self):
        x=d.schema_occurrence({},TOOL['parameters'],ALIASES)
        self.assertEqual(x['missing_required_keys'],['x']);self.assertEqual(x['declared_argument_checks'],'incompatible')
    def test_unknown_argument_is_declared_interface_issue(self):
        x=d.schema_occurrence({'x':1,'extra':2},TOOL['parameters'],ALIASES)
        self.assertEqual(x['undeclared_argument_keys'],['extra']);self.assertEqual(x['full_json_schema_validity'],'not_assessed')
    def test_missing_property_schema_is_unknown(self):
        self.assertEqual(d.schema_occurrence({}, {},ALIASES)['declared_argument_checks'],'unknown')
    def test_nonmapping_arguments_incompatible(self):
        self.assertEqual(d.schema_occurrence([],TOOL['parameters'],ALIASES)['declared_argument_checks'],'incompatible')
    def test_duplicate_name_occurrences_retained(self):
        t={'name':'f','parameters':{'properties':{'y':{'type':'string'}},'required':['y']}}
        x=d.inspect_call({'name':'f','parameters':{'x':1}},[t,TOOL],ALIASES)
        self.assertEqual(len(x['occurrence_checks']),2);self.assertTrue(x['duplicate_name_ambiguity']);self.assertEqual(x['declared_argument_checks'],'compatible')
    def test_duplicate_unknown_not_falsely_invalid(self):
        t={'name':'f','parameters':{}}
        x=d.inspect_call({'name':'f','parameters':{'z':1}},[TOOL,t],ALIASES)
        self.assertEqual(x['declared_argument_checks'],'unknown')
    def test_unavailable_literal_name(self):
        x=d.inspect_call({'name':'not_f','parameters':{'x':1}},[TOOL],ALIASES)
        self.assertFalse(x['name_available']);self.assertEqual(x['declared_argument_checks'],'incompatible')

class PolicyTests(unittest.TestCase):
    def test_no_official_label_changes_with_ambiguity(self):
        r,c=fixture();original=copy.deepcopy(r)
        ann={'flags':['reference_latest_intent_conflict'],'reason':'reviewed'}
        x=d.analyze_record(r,c,ann,CONFIG)
        self.assertEqual(x['official_score'],original['official_score']);self.assertEqual(r,original);self.assertEqual(x['reference_ambiguity_status'],'flagged')
        x['official_score']['correct']=True;self.assertFalse(r['official_score']['correct'])
    def test_unreviewed_is_unknown(self):
        r,c=fixture();x=d.analyze_record(r,c,None,CONFIG)
        self.assertEqual(x['reference_ambiguity_status'],'unknown')
    def test_extra_calls_and_marker_boundary(self):
        r,c=fixture();r['prediction']['tool_calls']*=2
        self.assertTrue(d.analyze_record(r,c,None,CONFIG)['explicit_one_call_violation'])
        r['prediction']['tool_calls']=r['prediction']['tool_calls'][:1]
        r['prediction']['raw_output']+='\nAction: f\nAction Input: {"x": 1}'
        x=d.analyze_record(r,c,None,CONFIG);self.assertTrue(x['raw_action_markers_exceed_parsed_calls'])
    def test_all_smoke_uncertainty_unavailable(self):
        r,c=fixture();x=d.analyze_record(r,c,None,CONFIG)
        self.assertIsNone(x['uncertainty']['scores']);self.assertFalse(x['uncertainty']['score_eligible']);self.assertEqual(x['execution_success'],'not_measured')
    def test_tooleyes_separate_and_ambiguity_does_not_exclude(self):
        a,ca=fixture('apibank',False);t,ct=fixture('tooleyes',True)
        ann={'changes_labels':False,'excludes_cases':False,'annotations':{a['case_key']:{'flags':['reference_latest_intent_conflict']}}}
        x=d.analyze(CONFIG,ann,[a,t],{a['case_key']:ca,t['case_key']:ct})
        self.assertEqual(x['primary_reference_compliance']['n'],1);self.assertEqual(x['primary_reference_compliance']['official_correct'],0)
        self.assertEqual(x['separate_tooleyes_name_relevance']['official_correct'],1)
        self.assertEqual(x['supplementary_all_benchmark_official_matches']['n'],2)
    def test_config_rejects_score_rewriting_and_routing(self):
        for section,key,value in [('official_labels','immutable',False),('official_labels','ambiguity_exclusions',True),('uncertainty','impute_missing',True),('diagnostics','coerce_values',True),('uncertainty','routing_execution_enabled',True)]:
            c=copy.deepcopy(CONFIG);c[section][key]=value
            with self.assertRaises(ValueError):d.validate_config(c)
    def test_duplicate_response_ids_rejected(self):
        r,c=fixture();ann={'changes_labels':False,'excludes_cases':False,'annotations':{}}
        with self.assertRaises(ValueError):d.analyze(CONFIG,ann,[r,r],{r['case_key']:c})
    def test_unexpected_scoring_method_rejected(self):
        r,c=fixture();r['official_score']['method']='name_match'
        with self.assertRaises(ValueError):d.analyze_record(r,c,None,CONFIG)
    def test_request_candidate_mismatch_rejected(self):
        r,c=fixture();c=copy.deepcopy(c);c['messages'][1]['content']='different'
        ann={'changes_labels':False,'excludes_cases':False,'annotations':{}}
        with self.assertRaises(ValueError):d.analyze(CONFIG,ann,[r],{r['case_key']:c})
    def test_unapproved_inputs_rejected_before_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'a.zip').write_bytes(b'unapproved');(p/'audit.json').write_text('{}')
            (p/'config.json').write_text(json.dumps(CONFIG));(p/'flags.json').write_text('{}')
            with patch('diagnostics.replay') as replay:
                with self.assertRaises(ValueError):d.run(p/'a.zip',p/'audit.json',p/'config.json',p/'flags.json')
                replay.assert_not_called()

if __name__=='__main__':unittest.main()
