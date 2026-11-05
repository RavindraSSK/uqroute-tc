"""Paired group-bootstrap changes; fixed observed benchmark mixture."""
from collections import defaultdict
import itertools
import random


def aggregate(groups, models):
    result = {}
    for model in models:
        count = sum(g[model][1] for g in groups)
        result[model+'/pair_weighted_change'] = sum(g[model][0] for g in groups)/count if count else None
        result[model+'/equal_group_change'] = sum(g[model][0]/g[model][1] for g in groups)/len(groups) if groups else None
    for a,b in itertools.combinations(models,2):
        for measure in ('pair_weighted_change','equal_group_change'):
            x,y = result[a+'/'+measure],result[b+'/'+measure]
            result[a+'-minus-'+b+'/'+measure] = None if x is None or y is None else x-y
    return result


def units(paired):
    models = sorted(paired)
    indexes = {}
    for model,rows in paired.items():
        index = {r['perturbed_case_key']:r for r in rows}
        if len(index)!=len(rows):raise ValueError('Duplicate perturbed identity')
        indexes[model] = index
    base = indexes[models[0]]
    if any(set(v)!=set(base) for v in indexes.values()):raise ValueError('Pair sets differ')
    groups = {}
    for key,row in base.items():
        group = (row['benchmark'],row['canonical_base_id'])
        unit = groups.setdefault(group,{'benchmark':group[0],'canonical_base_id':group[1],'models':{m:[0,0] for m in models}})
        for model,index in indexes.items():
            r = index[key]
            if any(r[f]!=row[f] for f in ('benchmark','canonical_base_id','panel','source_file','clean_case_key')):raise ValueError('Pair lineage differs')
            a,b = r['clean_correct'],r['perturbed_correct']
            if type(a) is not bool or type(b) is not bool:raise ValueError('Boolean outcomes required')
            change = int(b)-int(a)
            if r['correctness_change_perturbed_minus_clean']!=change:raise ValueError('Change arithmetic differs')
            unit['models'][model][0] += change
            unit['models'][model][1] += 1
    return [v for _,v in sorted(groups.items())]


def bootstrap(group_units, models, interval, seed=1729, replicates=2000):
    strata = defaultdict(list)
    for g in group_units:strata[g['benchmark']].append(g['models'])
    point = aggregate([g['models'] for g in group_units],models)
    samples = {k:[] for k in point};rng=random.Random(seed)
    for _ in range(replicates):
        drawn = [rng.choice(values) for _,values in sorted(strata.items()) for _ in values]
        values = aggregate(drawn,models)
        for k,v in values.items():samples[k].append(v)
    return {'canonical_groups':len(group_units),'replicates':replicates,'seed':seed,
            'metrics':{k:interval(v,samples[k],replicates,len(group_units)) for k,v in point.items()}}
