"""Descriptive constructed clean/perturbed pairing; no causal or independence claim."""
from collections import Counter,defaultdict


def paired(rows):
    if len({r['case_key'] for r in rows})!=len(rows):raise ValueError('Duplicate case')
    clean={}
    for r in rows:
        if r['source_file']=='clean.jsonl':
            group=(r['benchmark'],r['canonical_base_id'])
            if group in clean:raise ValueError('Duplicate clean anchor')
            clean[group]=r
    result=[]
    for r in rows:
        if r['source_file']=='clean.jsonl':continue
        c=clean.get((r['benchmark'],r['canonical_base_id']))
        if c is None:raise ValueError('Missing clean anchor')
        if c['panel']!=r['panel']:raise ValueError('Panel mismatch')
        a,b=c['official_score']['correct'],r['official_score']['correct']
        if type(a) is not bool or type(b) is not bool:raise ValueError('Nonboolean outcome')
        ca,cb=c['whole_output_scores'],r['whole_output_scores']
        result.append({'clean_case_key':c['case_key'],'perturbed_case_key':r['case_key'],
                       'benchmark':r['benchmark'],'canonical_base_id':r['canonical_base_id'],
                       'panel':r['panel'],'source_file':r['source_file'],
                       'clean_correct':a,'perturbed_correct':b,'correctness_change_perturbed_minus_clean':int(b)-int(a),
                       'mean_nll_change_perturbed_minus_clean':None if ca is None or cb is None else cb['mean_token_nll']-ca['mean_token_nll'],
                       'clean_reference_flags':c['reference_review_flags'],'perturbed_reference_flags':r['reference_review_flags']})
    return result


def summarize(rows):
    groups=defaultdict(list)
    for r in rows:groups[(r['benchmark'],r['canonical_base_id'])].append(r['correctness_change_perturbed_minus_clean'])
    changes=[r['correctness_change_perturbed_minus_clean'] for r in rows]
    nll=[r['mean_nll_change_perturbed_minus_clean'] for r in rows if r['mean_nll_change_perturbed_minus_clean'] is not None]
    return {'pairs':len(rows),'canonical_groups':len(groups),
            'transitions':dict(Counter(('C' if r['clean_correct'] else 'I')+('C' if r['perturbed_correct'] else 'I') for r in rows)),
            'pair_weighted_correctness_change':sum(changes)/len(changes) if changes else None,
            'equal_group_weighted_correctness_change':sum(sum(v)/len(v) for v in groups.values())/len(groups) if groups else None,
            'joint_mean_nll_pairs':len(nll),'mean_nll_change_on_joint_eligible_pairs':sum(nll)/len(nll) if nll else None}
