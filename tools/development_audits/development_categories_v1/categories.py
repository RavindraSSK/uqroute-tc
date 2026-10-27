"""Join released development taxonomy to existing scored cases without relabeling."""
from collections import Counter

EXPECTED = {
 'CD.jsonl':('reward','CD',3),'CD_AB.jsonl':('reward','CD_AB',4),
 'CD_NT.jsonl':('reward','CD_NT',3),'TD.jsonl':('reward','TD',3),
 'TD_AB.jsonl':('reward','TD_AB',4),'TD_NT.jsonl':('reward','TD_NT',3),
 'clean.jsonl':('clean',None,5),
 'paraphrase_parameter_description.jsonl':('observation','paraphrase_parameter_description',5),
 'paraphrase_tool_description.jsonl':('observation','paraphrase_tool_description',5),
 'query_paraphrase.jsonl':('observation','query_paraphrase',5),
 'realistic_typos.jsonl':('observation','realistic_typos',5),
 'redundant.jsonl':('action','redundant',5),
 'same_name_A.jsonl':('action','same_name_A',4),'same_name_B.jsonl':('action','same_name_B',4),
 'same_name_C.jsonl':('action','same_name_C',3),'same_name_D.jsonl':('action','same_name_D',4),
 'same_name_E.jsonl':('action','same_name_E',4)}


def metadata(record):
    source = record['source_file']
    if source not in EXPECTED:
        raise ValueError('Unrecognized selected source')
    raw = record['sample'].get('perturbation')
    if not isinstance(raw,dict) or 'mdp_category' not in raw or 'type' not in raw:
        raise ValueError('Released category/type fields required')
    category,kind = raw['mdp_category'],raw['type']
    wanted_category,wanted_kind,_ = EXPECTED[source]
    if source == 'clean.jsonl':
        # The inspection rendered Python None and literal "None" identically.
        # Either explicit clean-null representation is retained in provenance.
        if category not in (None,'None') or kind not in (None,'None'):
            raise ValueError('Unexpected clean metadata')
        return 'clean'
    if (category,kind)!=(wanted_category,wanted_kind):
        raise ValueError('Released taxonomy differs from reviewed metadata')
    return category


def taxonomy(records,requests):
    req = {r['case_key']:r for r in requests}
    if len(req)!=69 or len(requests)!=69:
        raise ValueError('Expected 69 unique prepared cases')
    out = {}
    for record in records:
        key = record['case_key']
        if key not in req:
            continue
        if key in out:
            raise ValueError('Duplicate selected development case')
        if record.get('split')!='development' or record.get('population')!='primary':
            raise ValueError('Expected primary development records')
        if any(record[f]!=req[key][f] for f in ('source_file','benchmark','canonical_base_id')):
            raise ValueError('Taxonomy lineage differs')
        out[key] = {'case_key':key,'source_file':record['source_file'],
                    'benchmark':record['benchmark'],'canonical_base_id':record['canonical_base_id'],
                    'analysis_category':metadata(record),
                    'released_perturbation':record['sample']['perturbation']}
    if set(out)!=set(req):
        raise ValueError('Selected taxonomy coverage differs')
    if Counter(r['source_file'] for r in out.values())!=Counter({s:v[2] for s,v in EXPECTED.items()}):
        raise ValueError('Selected source counts differ')
    return out


def join(rows,tax):
    if len(rows)!=len(tax) or len({r['case_key'] for r in rows})!=len(rows) or {r['case_key'] for r in rows}!=set(tax):
        raise ValueError('Scored identities differ from taxonomy')
    result = []
    for row in rows:
        t = tax[row['case_key']]
        if any(row[f]!=t[f] for f in ('source_file','benchmark','canonical_base_id')):
            raise ValueError('Scored taxonomy lineage differs')
        result.append({**row,'analysis_category':t['analysis_category']})
    return result
