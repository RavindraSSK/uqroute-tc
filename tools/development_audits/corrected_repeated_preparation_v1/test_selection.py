import copy
import unittest
import selection as s


def records():
    rows=[]
    for bench in s.BENCHMARKS:
        for g in range(7):
            for stem in ('clean','query_paraphrase','redundant','CD_AB','realistic_typos'):
                rows.append({'case_key':f'{stem}.jsonl:{bench}__{g}','benchmark':bench,'canonical_base_id':f'{bench}__{g}','source_file':stem+'.jsonl','request':{'model':'m','messages':[{'role':'user','content':'task'}],'temperature':.001,'max_tokens':1024,'logprobs':True,'top_logprobs':5,'stream':False}})
    return rows


class Selection(unittest.TestCase):
    def test_counts(self):
        rows,pairs=s.select(records())
        self.assertEqual((len(rows),len(pairs)),(30,15))
        self.assertEqual(len({r['canonical_base_id'] for r in rows}),15)
        self.assertEqual(sum(r['source_file']=='clean.jsonl' for r in rows),15)
    def test_order_independent(self):
        self.assertEqual(s.select(records()),s.select(list(reversed(records()))))
    def test_uses_original_hash(self):
        _,pairs=s.select(records())
        for b in s.BENCHMARKS:
            group=min([f'{b}__{i}' for i in range(7)],key=lambda g:(s.sha(f'uqroute-tc/repeated-subset-v1\0{1729}\0{b}\0query_paraphrase\0{g}'.encode()),g))
            self.assertEqual(next(p['canonical_base_id'] for p in pairs if p['benchmark']==b),group)
    def test_no_mutation(self):
        rows=records();old=copy.deepcopy(rows);s.expand(s.select(rows)[0]);self.assertEqual(rows,old)
    def test_duplicates(self):
        rows=records();rows.append(rows[0])
        with self.assertRaises(ValueError):s.select(rows)
    def test_missing_stratum(self):
        rows=[r for r in records() if not(r['benchmark']=='bfcl_v3' and r['source_file']=='CD_AB.jsonl')]
        with self.assertRaises(ValueError):s.select(rows)
    def test_missing_clean(self):
        with self.assertRaises(ValueError):s.select([r for r in records() if r['source_file']!='clean.jsonl'])
    def test_tooleyes_no_reward(self):
        _,pairs=s.select(records());sources={p['source_file'] for p in pairs if p['benchmark']=='tooleyes'}
        self.assertEqual(sources,{'query_paraphrase.jsonl','redundant.jsonl','realistic_typos.jsonl'})
    def test_distinct_groups(self):
        _,pairs=s.select(records())
        for b in s.BENCHMARKS:self.assertEqual(len({p['canonical_base_id'] for p in pairs if p['benchmark']==b}),3)
    def test_slots(self):
        selected,_=s.select(records());slots=s.expand(selected)
        self.assertEqual(len(slots),300);self.assertEqual(len({r['slot_id'] for r in slots}),300)
        for row in slots:
            body=row['request'];i=row['sample_index']
            self.assertEqual(body['seed'],1729+i)
            self.assertEqual((body['temperature'],body['top_p'],body['n']),(.7,1.0,1))
            self.assertEqual(row['request_sha256'],s.sha(s.canonical(body).encode()))
    def test_model_comparison(self):
        selected,_=s.select(records());other=copy.deepcopy(selected)
        for r in other:r['request']['model']='other'
        a,b=s.expand(selected),s.expand(other)
        self.assertEqual([r['slot_id'] for r in a],[r['slot_id'] for r in b])
        self.assertNotEqual(a[0]['request_sha256'],b[0]['request_sha256'])


if __name__=='__main__':unittest.main()
