import copy
import json
import unittest
from repair import build, repair_apibank
import base_adapter as base

T={'name':'f','description':'desc','parameters':{'type':'object','properties':{'x':{'type':'str'}}}}

def api_prompt(rows):
    return '**Available Tools**\n'+''.join(f'{i}. Name: {t["name"]}\nDescription: {t["description"]}\nParameters: {t["parameters"]["properties"]!r}\n' for i,t in enumerate(rows,1))+'**Steps for Each Turn**\nKeep instructions.'

class RepairTests(unittest.TestCase):
    def test_restore_missing_and_no_mutation(self):
        broken=copy.deepcopy(T);broken['parameters']['properties']={}
        out,edits=repair_apibank(api_prompt([T]),[broken])
        self.assertEqual(out,[T]);self.assertEqual(broken['parameters']['properties'],{})
    def test_alias_uses_unique_description_not_reference(self):
        alias=copy.deepcopy(T);alias['name']='renamed';alias['parameters']['properties']={}
        out,_=repair_apibank(api_prompt([T]),[alias]);self.assertEqual(out[0]['name'],'renamed');self.assertEqual(out[0]['parameters'],T['parameters'])
    def test_ambiguous_alias_blocks(self):
        other=copy.deepcopy(T);other['name']='g';other['parameters']['properties']={'y':{'type':'int'}}
        alias={'name':'renamed','description':'desc','parameters':{'properties':{}}}
        with self.assertRaises(ValueError):repair_apibank(api_prompt([T,other]),[alias])
    def test_duplicate_names_keep_intentional_empty(self):
        empty=copy.deepcopy(T);empty['parameters']['properties']={}
        out,_=repair_apibank(api_prompt([T,empty]),[T,empty]);self.assertEqual(out,[T,empty])
    def test_duplicate_names_recover_distinct_missing_schema(self):
        other=copy.deepcopy(T);other['parameters']['properties']={'z':{'type':'int'}}
        broken=copy.deepcopy(other);broken['parameters']['properties']={}
        out,_=repair_apibank(api_prompt([T,other]),[T,broken]);self.assertEqual(out,[T,other])
    def test_instruction_artifact_metadata_removed(self):
        phantom={'name':'**Think','description':'** Recall relevant context and analyze the current user goal. [Cost: $0.217/call]','parameters':{'properties':{}}}
        out,_=repair_apibank(api_prompt([T]),[T,phantom]);self.assertEqual(out,[T])
    def test_unrecognized_think_not_silently_removed(self):
        phantom={'name':'**Think','description':'legitimate custom tool','parameters':{'properties':{}}}
        with self.assertRaises(ValueError):repair_apibank(api_prompt([T]),[T,phantom])
    def test_rotbench_replaces_stale_tools_and_removes_target(self):
        old={**T,'name':'old'}
        system='Specifically, you have access of the following tools:\n'+json.dumps([old])+"\nLet's Begin!"
        messages=[{'role':'system','content':system},{'role':'user','content':'query'},{'role':'assistant','content':'target'}]
        out=build('rotbench',messages,[T]);self.assertEqual(base.tool_sets(out['messages']),[[T]]);self.assertEqual(len(out['messages']),2);self.assertEqual(len(messages),3)
    def test_history_never_deleted(self):
        with self.assertRaises(ValueError):build('rotbench',[{'role':'system','content':''},{'role':'user','content':''},{'role':'assistant','content':''},{'role':'user','content':''}],[T])
    def test_toolalpaca_structured_vocabulary_and_duplicates_preserved(self):
        ts=[T,{**T,'description':'distractor'}]
        out=build('toolalpaca',[{'role':'system','content':'old documentation target name'},{'role':'user','content':'q'}],ts)
        self.assertEqual(base.tool_sets(out['messages']),[ts]);self.assertNotIn('old documentation',out['messages'][0]['content'])
    def test_bfcl_stale_schema_rejected(self):
        with self.assertRaises(ValueError):build('bfcl_v3',[{'role':'system','content':json.dumps([{**T,'name':'old'}])},{'role':'user','content':'q'}],[T])

if __name__=='__main__':unittest.main()
