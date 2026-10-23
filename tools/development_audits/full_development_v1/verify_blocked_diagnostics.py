"""Replay a development-only blocked-input extract without reading references.

Checks diagnostic categories and nonmutation; writes no output files.
The extract must originate from the reviewed development export.
"""
import argparse
import copy
import json
from collections import Counter
from pathlib import Path
from repair import build


def verify(path):
    rows = json.loads(path.read_text(encoding='utf-8'))
    if len(rows) != 26 or len({r['case_key'] for r in rows}) != 26:
        raise ValueError('Expected 26 unique development diagnostic cases')
    counts = Counter()
    for row in rows:
        if set(row) != {'case_key', 'source_file', 'construction_reason', 'sample'}:
            raise ValueError('Unexpected extract fields')
        sample = row['sample']
        if set(sample) - {'benchmark', 'category', 'conversation', 'id', 'level', 'perturbation', 'tools'}:
            raise ValueError('Unexpected sample fields; reference/outcome inputs prohibited')
        if sample['benchmark'] != 'apibank':
            raise ValueError('Unexpected benchmark')
        before = copy.deepcopy(row)
        try:
            build(sample['benchmark'], sample['conversation'], sample['tools'])
        except ValueError as exc:
            reason = str(exc)
            if reason.startswith('No matching schema declaration for '):
                category = 'missing_declaration'
            elif reason.startswith('Conflicting schema declarations for '):
                category = 'conflicting_schemas'
            else:
                raise ValueError('Unexpected diagnostic category') from exc
            expected = ('missing_declaration' if row['source_file'] in
                        {'CD.jsonl', 'CD_NT.jsonl', 'TD.jsonl', 'TD_NT.jsonl'}
                        else 'conflicting_schemas' if row['source_file'] in
                        {'same_name_B.jsonl', 'same_name_D.jsonl'} else None)
            if category != expected:
                raise ValueError('Unexpected source/category pairing')
            counts[category] += 1
        else:
            raise ValueError('Previously blocked case became a candidate')
        if row != before:
            raise ValueError('Input mutated')
    if counts != Counter(missing_declaration=12, conflicting_schemas=14):
        raise ValueError('Unexpected classification counts')
    return {'blocked': 26, 'new_candidates': 0, 'categories': dict(counts),
            'inputs_unchanged': True, 'reference_sidecar_read': False,
            'scope': 'Uploaded development-only diagnostic extract; not full-population rerun'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.input), indent=2))
