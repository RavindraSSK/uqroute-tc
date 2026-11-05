"""Outcome-independent corrected-candidate subset and ten-slot expansion."""
import hashlib
import json

BENCHMARKS=('apibank','bfcl_v3','rotbench','toolalpaca','tooleyes')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def sha(value):return hashlib.sha256(value).hexdigest()


def select(rows):
    if len({r['case_key'] for r in rows})!=len(rows):raise ValueError('Duplicate case')
    clean={}
    for r in rows:
        if r['source_file']=='clean.jsonl':
            group=(r['benchmark'],r['canonical_base_id'])
            if group in clean:raise ValueError('Duplicate clean group')
            clean[group]=r
    selected=[];pair_manifest=[]
    for benchmark in BENCHMARKS:
        used=set()
        stems=('query_paraphrase','redundant','realistic_typos') if benchmark=='tooleyes' else ('query_paraphrase','redundant','CD_AB')
        for stem in stems:
            candidates=[r for r in rows if r['benchmark']==benchmark and r['source_file']==stem+'.jsonl' and (benchmark,r['canonical_base_id']) in clean]
            if len({r['canonical_base_id'] for r in candidates})!=len(candidates):raise ValueError('Duplicate group in source')
            candidates.sort(key=lambda r:(sha(f"uqroute-tc/repeated-subset-v1\0{1729}\0{benchmark}\0{stem}\0{r['canonical_base_id']}".encode()),r['canonical_base_id']))
            choice=next((r for r in candidates if r['canonical_base_id'] not in used),None)
            if choice is None:raise ValueError('No distinct candidate: '+benchmark+'/'+stem)
            group=choice['canonical_base_id'];used.add(group)
            anchor=clean[(benchmark,group)];selected.extend([anchor,choice])
            pair_manifest.append({'benchmark':benchmark,'canonical_base_id':group,'clean_case_key':anchor['case_key'],'perturbed_case_key':choice['case_key'],'source_file':choice['source_file']})
    if len(selected)!=30 or len({r['case_key'] for r in selected})!=30:raise ValueError('Expected 30 unique cases')
    return selected,pair_manifest


def expand(rows):
    slots=[]
    for row in rows:
        for index in range(10):
            body={**row['request'],'temperature':.7,'top_p':1.0,'max_tokens':1024,'logprobs':True,'top_logprobs':5,'seed':1729+index,'n':1,'stream':False}
            slot_id=sha(canonical([row['case_key'],index]).encode())
            slots.append({'case_key':row['case_key'],'benchmark':row['benchmark'],'canonical_base_id':row['canonical_base_id'],'source_file':row['source_file'],'sample_index':index,'slot_id':slot_id,'request_sha256':sha(canonical(body).encode()),'request':body})
    return slots
