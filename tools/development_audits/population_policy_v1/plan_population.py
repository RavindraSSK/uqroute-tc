"""Development-only construction denominator diagnostics; no inference or scoring.

Reads only an explicitly hash-approved prior summary and inventory. Existing
reference diagnostics may occur in inventory; only flags/status/booleans are
used here. Hashes establish consistency, not authenticated partition membership.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

POLICY_SHA = 'd3168b2fb511d71c2867f2badd2f8d1cfb2381ccfb911bf93cef002e4c3f322b'
BASE = 'd8f70b64f0c2cc3e4757fe0c4ffd2387f8200bd8'
BENCHMARK = 'd5d03180de41eb30a6c796d04a9bfbd9dad85c1d'
SPLIT = '688c1013d8fe9d5c1b454d14d4cbe215659e48adc7bdfd63175580e83e2eb0db'
ATTESTATION = '77071dc342a19b0f32995fed9f9f9e25840294e633ef5368830f07a3ccf3ccb9'
OFFICIAL = {'apibank', 'bfcl_v3', 'rotbench', 'toolalpaca'}
REWARD = {'CD.jsonl', 'CD_AB.jsonl', 'CD_NT.jsonl', 'TD.jsonl', 'TD_AB.jsonl', 'TD_NT.jsonl'}
BLOCKED_STATUS = 'not_assessed_due_to_construction_block'
COMPLETED = 'completed_bounded_signals_only'
ALLOWED = {'case_key', 'source_file', 'row_id', 'canonical_base_id', 'benchmark',
           'population', 'split', 'source_line_sha256', 'source_file_sha256',
           'source_reference_sha256', 'construction_status', 'excluded_from_inventory',
           'official_labels_changed', 'uncertainty_eligibility', 'original_messages_sha256',
           'corrected_messages_sha256', 'repair_edits', 'tool_occurrence_schema_sha256',
           'construction_reason', 'reference_audit_status', 'reference_audit',
           'reference_schema_diagnostics', 'reference_audit_reason'}
SOURCE_FILES = REWARD | {'clean.jsonl', 'paraphrase_parameter_description.jsonl',
    'paraphrase_tool_description.jsonl', 'query_paraphrase.jsonl', 'realistic_typos.jsonl',
    'redundant.jsonl', 'same_name_A.jsonl', 'same_name_B.jsonl', 'same_name_C.jsonl',
    'same_name_D.jsonl', 'same_name_E.jsonl'}

def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def loads(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('Duplicate JSON key')
            out[key] = value
        return out
    def invalid(_):
        raise ValueError('Nonfinite JSON value')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def read_file(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected regular input file')
    return path.read_bytes()


def summarize(rows):
    flags = Counter()
    for r in rows:
        flags.update(r.get('reference_audit', {}).get('review_flags', []))
    return {'rows': len(rows), 'canonical_groups': len({r['canonical_base_id'] for r in rows}),
            'construction_status_counts': dict(Counter(r['construction_status'] for r in rows)),
            'review_signal_cases': sum(bool(r.get('reference_audit', {}).get('review_flags')) for r in rows),
            'review_signal_counts': dict(flags),
            'objective_cost_detected': sum(r.get('reference_audit', {}).get('objective_detection', {}).get('cost_explicit_detected', False) for r in rows),
            'objective_latency_detected': sum(r.get('reference_audit', {}).get('objective_detection', {}).get('latency_explicit_detected', False) for r in rows)}


def plan(rows, summary):
    """Pure structural checks; CLI adds expected full counts and provenance."""
    if not rows or not isinstance(rows, list):
        raise ValueError('Missing inventory')
    if summary.get('format_version') != 'uqroute-development-pipeline-1.0.0' or summary.get('readiness') != 'DEVELOPMENT_AUDIT_ONLY_MAIN_EXPERIMENT_NOT_READY':
        raise ValueError('Prior audit version/readiness differs')
    for field in ('official_labels_changed', 'reference_corrections_applied', 'ambiguity_exclusions_applied'):
        if summary.get(field) is not False:
            raise ValueError('Prior audit label/exclusion boundary differs')
    if summary.get('all_input_rows_retained') is not True or summary.get('population') != 'primary' or summary.get('partition') != 'development':
        raise ValueError('Non-development or incomplete summary')
    for field in ('held_out_bundle_rows_accepted', 'raw_benchmark_files_opened_by_auditor'):
        if type(summary.get(field)) is not int or summary[field] != 0:
            raise ValueError('Prior access boundary differs')
    groups = defaultdict(list)
    keys = set()
    for r in rows:
        if not isinstance(r, dict) or set(r) - ALLOWED:
            raise ValueError('Unexpected inventory fields')
        if r.get('population') != 'primary' or r.get('split') != 'development':
            raise ValueError('Non-development inventory')
        if r.get('benchmark') not in OFFICIAL | {'tooleyes'}:
            raise ValueError('Unknown benchmark')
        if r.get('excluded_from_inventory') is not False or r.get('official_labels_changed') is not False:
            raise ValueError('Inventory exclusion/label change')
        if r.get('uncertainty_eligibility') != 'not_assessed_before_inference':
            raise ValueError('Unexpected outcome eligibility')
        key, source, row_id, group = (r.get(k) for k in ('case_key', 'source_file', 'row_id', 'canonical_base_id'))
        if not all(isinstance(v, str) and v for v in (key, source, row_id, group)) or source not in SOURCE_FILES or key != source + ':' + row_id or key in keys:
            raise ValueError('Invalid/duplicate identity')
        keys.add(key)
        status = r.get('construction_status')
        audit_status = r.get('reference_audit_status')
        if status not in {'candidate', 'blocked'}:
            raise ValueError('Invalid construction status')
        if status == 'blocked':
            if audit_status != BLOCKED_STATUS or 'reference_audit' in r or not r.get('construction_reason'):
                raise ValueError('Invalid blocked assessment')
        elif audit_status not in {COMPLETED, 'unresolved_audit_error'}:
            raise ValueError('Invalid candidate assessment')
        a = r.get('reference_audit')
        if audit_status == COMPLETED:
            if not isinstance(a, dict) or a.get('case_key') != key or a.get('benchmark') != r['benchmark'] or a.get('changes_official_labels') is not False or a.get('excluded') is not False:
                raise ValueError('Invalid reference audit metadata')
            flags = a.get('review_flags')
            if not isinstance(flags, list) or not all(isinstance(f, str) for f in flags) or len(flags) != len(set(flags)):
                raise ValueError('Invalid review signals')
            objectives = a.get('objective_detection', {})
            if any(type(objectives.get(k)) is not bool for k in ('cost_explicit_detected', 'latency_explicit_detected')):
                raise ValueError('Invalid objective status')
        elif status == 'candidate' and not r.get('reference_audit_reason'):
            raise ValueError('Unresolved audit reason missing')
        groups[group].append(r)
    pairs = []
    for group, items in sorted(groups.items()):
        if len({r['benchmark'] for r in items}) != 1:
            raise ValueError('Cross-benchmark group')
        clean = [r for r in items if r['source_file'] == 'clean.jsonl']
        if len(clean) != 1:
            raise ValueError('Primary group needs unique clean anchor')
        for r in items:
            if r is clean[0]:
                continue
            pairs.append({'canonical_base_id': group, 'clean_case_key': clean[0]['case_key'],
                          'perturbed_case_key': r['case_key'], 'pair_available': True,
                          'both_constructed': all(x['construction_status'] == 'candidate' for x in (clean[0], r))})
    pair_counts = {'perturbed_rows': len(pairs), 'with_unique_clean_anchor': len(pairs),
                   'both_constructed': sum(p['both_constructed'] for p in pairs)}
    official = [r for r in rows if r['benchmark'] in OFFICIAL]
    eyes = [r for r in rows if r['benchmark'] == 'tooleyes']
    reward = [r for r in rows if r['source_file'] in REWARD]
    checks = {'totals': summarize(rows), 'reference_audit_status_counts': dict(Counter(r['reference_audit_status'] for r in rows)),
              'clean_anchor_pairing': pair_counts,
              'reference_compliance_candidate_inventory': summarize(official),
              'separate_tooleyes_relevance_candidate_inventory': summarize(eyes),
              'by_benchmark': {b: summarize([r for r in rows if r['benchmark'] == b]) for b in sorted({r['benchmark'] for r in rows})},
              'by_source_file': {f: summarize([r for r in rows if r['source_file'] == f]) for f in sorted({r['source_file'] for r in rows})}}
    for key, value in checks.items():
        if summary.get(key) != value:
            raise ValueError('Summary/inventory reconciliation failed')
    assessed = [r for r in reward if r['reference_audit_status'] == COMPLETED]
    nondetected = [r for r in assessed if not any(r['reference_audit']['objective_detection'][k] for k in ('cost_explicit_detected', 'latency_explicit_detected'))]
    reward_summary = {**summarize(reward), 'objective_detection_assessed_rows': len(assessed), 'objective_not_detected_rows': len(nondetected)}
    if summary.get('reward_panel') != reward_summary:
        raise ValueError('Reward summary differs')
    index = []
    for r in sorted(rows, key=lambda x: x['case_key']):
        assessed_row = r['reference_audit_status'] == COMPLETED
        obj = r.get('reference_audit', {}).get('objective_detection', {})
        index.append({k: r[k] for k in ('case_key', 'canonical_base_id', 'benchmark', 'source_file', 'construction_status')} | {
            'panel': 'tooleyes_relevance' if r['benchmark'] == 'tooleyes' else 'official_reference_compliance',
            'reward_overlap': r['source_file'] in REWARD,
            'reference_review_signal': bool(r.get('reference_audit', {}).get('review_flags')) if assessed_row else None,
            'reference_audit_status': r['reference_audit_status'],
            'cost_objective_detected': obj.get('cost_explicit_detected') if assessed_row else None,
            'latency_objective_detected': obj.get('latency_explicit_detected') if assessed_row else None,
            'construction_candidate_only': r['construction_status'] == 'candidate'})
    report = {'policy_version': 'uqroute-development-population-policy-1.0.0',
              'status': 'DEVELOPMENT_DENOMINATORS_ONLY_NOT_FINAL_FREEZE',
              'main_experiment_ready': False, 'held_out_access_enabled': False, 'inference_enabled': False,
              'official_labels_changed': False, 'ambiguity_exclusions_applied': False,
              'source_inventory': checks['totals'], 'reference_audit_status_counts': checks['reference_audit_status_counts'], 'official_reference_compliance': checks['reference_compliance_candidate_inventory'],
              'tooleyes_relevance': checks['separate_tooleyes_relevance_candidate_inventory'],
              'reward_overlap': reward_summary, 'construction_pairs': pair_counts,
              'reward_objective_unassessed': len(reward) - len(assessed),
              'metric_denominators': 'not_assigned; require future model outcomes and frozen metric rules',
              'limitations': ['Prior development audit provenance is trusted, not cryptographically authenticated.',
                             'Source/block counts are not model correctness labels.',
                             'Regex nondetection is not evidence of absent intent.',
                             'Reward overlaps reference panels; flags do not exclude rows.']}
    return report, index, pairs


def run(repo, audit, expected_summary, expected_inventory, output):
    if output.exists() or output.is_symlink():
        raise ValueError('Output already exists')
    repo, audit, target = repo.resolve(), audit.resolve(), output.resolve()
    if audit == target or audit in target.parents or target == repo or target in audit.parents:
        raise ValueError('Output overlaps input/repository')
    if not target.is_relative_to(repo / 'artifacts/local_development_audits'):
        raise ValueError('Output must be inside local development artifacts')
    cfg_raw = read_file(Path(__file__).with_name('population_policy_v1.json'))
    if digest(cfg_raw.replace(b'\r\n', b'\n')) != POLICY_SHA:
        raise ValueError('Policy source differs; version any policy amendment')
    cfg = loads(cfg_raw)
    if cfg['baseline_commit'] != BASE or cfg['main_experiment_ready'] is not False or cfg['held_out_access_enabled'] is not False or cfg['inference_enabled'] is not False:
        raise ValueError('Policy readiness boundary differs')
    manifest = loads(read_file(Path(__file__).with_name('source_manifest.json')))
    if manifest.get('baseline_commit') != BASE:
        raise ValueError('Source manifest baseline differs')
    subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', BASE, 'HEAD'], check=True, capture_output=True)
    for path, expected in manifest['source_git_blobs'].items():
        actual = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', BASE + ':' + path], text=True).strip()
        if actual != expected:
            raise ValueError('Baseline source identity differs')
    raw = {}
    for name, expected in [('summary.json', expected_summary), ('inventory.json', expected_inventory)]:
        if not re.fullmatch('[0-9a-f]{64}', expected):
            raise ValueError('Expected SHA256 required')
        raw[name] = read_file(audit / name)
        if digest(raw[name]) != expected:
            raise ValueError('Prior audit hash mismatch')
    summary, rows = loads(raw['summary.json']), loads(raw['inventory.json'])
    p = summary.get('provenance', {})
    if p.get('benchmark_revision') != BENCHMARK or p.get('split_sha256') != SPLIT or p.get('attestation_sha256') != ATTESTATION:
        raise ValueError('Unexpected original audit provenance')
    report, index, pairs = plan(rows, summary)
    totals = report['source_inventory']
    if (totals['rows'], totals['canonical_groups'], totals['construction_status_counts']) != (1754, 140, {'candidate': 1728, 'blocked': 26}):
        raise ValueError('Original primary-development counts differ')
    for key, expected in [('official_reference_compliance', (1538, 1512, 26)), ('tooleyes_relevance', (216, 216, 0)), ('reward_overlap', (498, 486, 12))]:
        panel = report[key]
        actual = (panel['rows'], panel['construction_status_counts'].get('candidate', 0), panel['construction_status_counts'].get('blocked', 0))
        if actual != expected:
            raise ValueError('Original panel counts differ')
    if report['construction_pairs'] != {'perturbed_rows': 1614, 'with_unique_clean_anchor': 1614, 'both_constructed': 1588}:
        raise ValueError('Original pair counts differ')
    report['provenance'] = {'baseline_commit': BASE, 'prior_summary_sha256': expected_summary,
        'prior_inventory_sha256': expected_inventory, 'policy_sha256': digest(cfg_raw),
        'planner_sha256': digest(read_file(Path(__file__)).replace(b'\r\n', b'\n')),
        'original_attestation_sha256': ATTESTATION,
        'files_read_from_audit': ['summary.json', 'inventory.json'],
        'prior_outputs_modified': False, 'raw_benchmark_or_split_opened': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='population-plan-') as tmp:
        for name, data in [('denominators.json', report), ('case_index.json', index), ('construction_pairs.json', pairs)]:
            (Path(tmp) / name).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
        if output.exists():
            raise ValueError('Output appeared during planning')
        Path(tmp).rename(output)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, required=True)
    parser.add_argument('--audit-dir', type=Path, required=True)
    parser.add_argument('--expected-summary-sha256', required=True)
    parser.add_argument('--expected-inventory-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    a = parser.parse_args()
    try:
        result = run(a.repo_root, a.audit_dir, a.expected_summary_sha256, a.expected_inventory_sha256, a.output)
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError):
        raise SystemExit('Development denominator validation failed; preserve inputs and investigate. No record content printed.')
    print(json.dumps(result, indent=2))
