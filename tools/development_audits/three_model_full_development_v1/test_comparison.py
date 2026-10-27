import copy
import unittest
from run_comparison import same_requests

class RequestTests(unittest.TestCase):
    def data(self):
        q=[{'case_key':str(i),'benchmark':'b','canonical_base_id':str(i%140),'source_file':'x','messages_sha256':'h','tools_sha256':'t','request':{'model':'Qwen/Qwen2.5-1.5B-Instruct','messages':[{'role':'user','content':'x'}],'temperature':.001}} for i in range(1728)]
        l=copy.deepcopy(q)
        for r in l:r['request']['model']='meta-llama/Llama-3.2-3B-Instruct'
        return q,l
    def test_full_same_requests(self):same_requests(*self.data())
    def test_count(self):
        q,l=self.data()
        with self.assertRaises(ValueError):same_requests(q[:-1],l)
    def test_order(self):
        q,l=self.data();l.reverse()
        with self.assertRaises(ValueError):same_requests(q,l)
    def test_duplicate_identity(self):
        q,l=self.data();q[-1]=copy.deepcopy(q[0]);l[-1]=copy.deepcopy(l[0])
        with self.assertRaises(ValueError):same_requests(q,l)
    def test_lineage(self):
        q,l=self.data();l[0]['canonical_base_id']='other'
        with self.assertRaises(ValueError):same_requests(q,l)
    def test_prompt_difference(self):
        q,l=self.data();l[0]['request']['messages'][0]['content']='other'
        with self.assertRaises(ValueError):same_requests(q,l)
    def test_sampling_difference(self):
        q,l=self.data();l[0]['request']['temperature']=.5
        with self.assertRaises(ValueError):same_requests(q,l)
    def test_wrong_model(self):
        q,l=self.data();l[0]['request']['model']='other'
        with self.assertRaises(ValueError):same_requests(q,l)

class Qwen7BRequestTests(unittest.TestCase):
    def data(self):
        q,l=RequestTests().data()
        for r in l:r['request']['model']='Qwen/Qwen2.5-7B-Instruct'
        return q,l
    def test_qwen7b_full_selection(self):same_requests(*self.data(),second_model='Qwen/Qwen2.5-7B-Instruct')
    def test_qwen7b_prompt_change_rejected(self):
        q,l=self.data();l[0]['request']['messages'][0]['content']='changed'
        with self.assertRaises(ValueError):same_requests(q,l,'Qwen/Qwen2.5-7B-Instruct')
    def test_qwen7b_wrong_role_rejected(self):
        q,l=self.data()
        with self.assertRaises(ValueError):same_requests(q,l)

if __name__=='__main__':unittest.main()
