"""Exploratory stratified cluster bootstrap for saved development diagnostics."""
import hashlib
import math
import random
from collections import defaultdict


def percentile(values, probability):
    values = sorted(values)
    if not values:
        return None
    at = (len(values) - 1) * probability
    low = int(at)
    return values[low] + (values[min(low + 1, len(values)-1)] - values[low]) * (at-low)


def cluster_draw(rows, rng):
    strata = defaultdict(lambda: defaultdict(list))
    for row in rows:
        strata[row['benchmark']][row['canonical_base_id']].append(row)
    result = []
    for benchmark in sorted(strata):
        groups = strata[benchmark]
        keys = sorted(groups)
        for _ in keys:
            result.extend(groups[rng.choice(keys)])
    return result


def interval(point, samples, repetitions, groups, minimum_groups=10):
    valid = [x for x in samples if x is not None and math.isfinite(x)]
    reason = None
    if point is None:
        reason = 'point_metric_undefined'
    elif groups < minimum_groups:
        reason = 'fewer_than_10_canonical_groups'
    elif len(valid) < math.ceil(.9 * repetitions):
        reason = 'fewer_than_90_percent_valid_replicates'
    return {'point': point, 'interval_95_percentile': None if reason else
            [percentile(valid, .025), percentile(valid, .975)],
            'interval_unavailable_reason': reason, 'valid_replicates': len(valid),
            'undefined_replicates': repetitions-len(valid), 'canonical_groups': groups}


def bootstrap(rows, evaluate, repetitions=2000, seed=1729):
    if type(repetitions) is not int or repetitions < 1:
        raise ValueError('Positive replicate count required')
    point = evaluate(rows)
    rng = random.Random(seed)
    samples = {key: [] for key in point}
    for _ in range(repetitions):
        value = evaluate(cluster_draw(rows, rng))
        if set(value) != set(point):
            raise ValueError('Metric identities changed')
        for key in point:
            samples[key].append(value[key])
    groups = len({(r['benchmark'], r['canonical_base_id']) for r in rows})
    return {key: interval(point[key], samples[key], repetitions, groups) for key in point}


def stable_seed(label):
    return 1729 + int(hashlib.sha256(label.encode()).hexdigest()[:8], 16)
