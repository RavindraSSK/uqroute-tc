import copy
import json
import unittest
from reference_audit import audit_case, user_segments, advertised_groups, metadata, instruction_without_tool_arrays, analyze


def fixture(file='CD.jsonl',query='Get the information.'):
    t={'name':'expensive','description':'[Cost: $0.10/call] Same operation','parameters':{'properties':{'x':{'type':'string'}},'required':['x']}}
    cheap={**copy.deepcopy(t),'name':'cheap','description':'[Cost: $0.01/call] Same operation'}
    source={'case_key':file+':case','benchmark':'apibank','golden_answers':[{'name':'cheap','parameters':{'x':'value'}}]}
    candidate={'case_key':source['case_key'],'status':'candidate','messages':[{'role':'system','content':'Tools: '+json.dumps([t,cheap])},{'role':'user','content':query}],'tools':[t,cheap]}
    return source,candidate

class AuditTests(unittest.TestCase):
    def test_cost_metadata_not_objective(self):
        s,c=fixture();r=audit_case(s,c)
        self.assertFalse(r['objective_detection']['cost_explicit_detected'])
        self.assertIn('reward_cell_without_detected_explicit_objective',r['review_flags'])
    def test_explicit_cost_detected(self):
        for text in ['Please use a cost-effective option.','Select the most economical option.','Use the cheapest tool.']:
            s,c=fixture(query=text);r=audit_case(s,c)
            self.assertTrue(r['objective_detection']['cost_explicit_detected'])
            self.assertNotIn('reward_cell_without_detected_explicit_objective',r['review_flags'])
    def test_explicit_latency_detected(self):
        s,c=fixture('TD.jsonl','Choose the fastest option available.');r=audit_case(s,c)
        self.assertTrue(r['objective_detection']['latency_explicit_detected'])
    def test_assistant_embedded_history_not_user_objective(self):
        s,c=fixture(query='<user>Get data.</user><response>Use the cheapest tool.</response>')
        self.assertFalse(audit_case(s,c)['objective_detection']['cost_explicit_detected'])
    def test_system_objective_outside_tools_detected(self):
        s,c=fixture();c['messages'][0]['content']+='\nUse the cheapest available tool.'
        self.assertTrue(audit_case(s,c)['objective_detection']['cost_explicit_detected'])
    def test_tool_description_instruction_not_counted(self):
        s,c=fixture();c['tools'][0]['description']='Use the cheapest tool.';c['messages'][0]['content']=json.dumps(c['tools'])
        self.assertFalse(audit_case(s,c)['objective_detection']['cost_explicit_detected'])
    def test_gold_does_not_enter_objective_detection(self):
        s,c=fixture();before=audit_case(s,c)['objective_detection'];s['golden_answers'][0]['parameters']['x']='use cheapest'
        self.assertEqual(before,audit_case(s,c)['objective_detection'])
    def test_model_outcome_noninterference(self):
        s,c=fixture();r=audit_case(s,c)
        s['official_score']={'correct':True};s['prediction']={'raw_output':'cheapest'};c['model_output']='fastest'
        self.assertEqual(r,audit_case(s,c))
    def test_source_immutability(self):
        s,c=fixture();old=copy.deepcopy((s,c));audit_case(s,c);self.assertEqual((s,c),old)
    def test_duplicate_name_flag_not_exclusion(self):
        s,c=fixture();c['tools'].append(copy.deepcopy(c['tools'][1]));r=audit_case(s,c)
        self.assertIn('reference_name_has_multiple_schema_occurrences',r['review_flags']);self.assertFalse(r['excluded'])
    def test_reference_key_failure(self):
        s,c=fixture();s['golden_answers'][0]['parameters']={'unknown':'v'}
        self.assertIn('reference_argument_keys_not_declared',audit_case(s,c)['review_flags'])
    def test_year_flag_is_literal_and_not_semantic_judgment(self):
        s,c=fixture(query='Do this March 16.');s['golden_answers'][0]['parameters']={'x':'2023-03-16 10:00:00'}
        self.assertIn('reference_date_year_not_literal_in_user_turns',audit_case(s,c)['review_flags'])
        c['messages'][1]['content']+=' In 2023.'
        self.assertNotIn('reference_date_year_not_literal_in_user_turns',audit_case(s,c)['review_flags'])
    def test_latest_range_conflict(self):
        s,c=fixture(query='<user>8:00AM to 9:00AM</user><user>9:00AM to 10:00AM</user>')
        s['golden_answers'][0]['parameters']={'from_time':'2023-03-16 07:00:00','to_time':'2023-03-16 08:00:00'}
        self.assertIn('reference_latest_explicit_time_range_mismatch',audit_case(s,c)['review_flags'])
    def test_no_signal_is_not_semantic_clearance(self):
        s,c=fixture('clean.jsonl');c['tools']=[c['tools'][1]];c['messages'][0]['content']=json.dumps(c['tools']);r=audit_case(s,c)
        self.assertIn('not_semantic_clearance',r['review_status'])
    def test_cost_group_preserves_multiple_occurrences(self):
        s,c=fixture();groups=advertised_groups(c['tools']);self.assertEqual(len(groups[0]),2)
        r=audit_case(s,c);check=r['reference_checks'][0]['advertised_preference_checks'][0]
        self.assertTrue(check['reference_name_at_minimum']);self.assertFalse(check['explicit_objective_detected'])
    def test_latency_metadata_parsing(self):
        self.assertEqual(metadata('operation (typically responds in 1432ms)')['declared_latency_ms'],1432)
        self.assertEqual(metadata('operation [Response time: ~23ms]')['declared_latency_ms'],23)
    def test_population_mismatch_rejected(self):
        with self.assertRaises(ValueError):analyze({'cases':[]},{'cases':[]})

if __name__=='__main__':unittest.main()
