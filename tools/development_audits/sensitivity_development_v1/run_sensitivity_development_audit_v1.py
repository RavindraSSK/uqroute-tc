"""Run the pinned UQRoute-TC sensitivity-only development construction audit."""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path('artifacts/local_development_audits')
DEFAULT_BENCHMARK = ROOT / 'benchmark_pinned_d5d0318'
OUTPUT = ROOT / 'sensitivity_development_audit_v1'
PIPELINE = Path('tools/development_audits/full_development_v1')
CODE_PINS = {
    'common.py': '4837affabe38879233a63e02b134eb97e55a62264ec7f3de7d9724986cbfc686',
    'export_development.py': 'ec96bd4800ef42da0d23862ec70180433c7f50416db932a3113b1e9e48b2ef5b',
    'audit_development.py': 'c9e85b6e10bed5bfc57975aa7abad30d05af9725af4780b86b4ecd5879b5cb23',
    'identity_v1.py': '9d2daefa9de97785ba6a50881206f683894e155a1f9782d6bc043449acc2ccf1',
    'repair.py': '5be0388f7b8dadd413679e727e6fcad3536ebb0bec123a4e302ee158560c271b',
    'base_adapter.py': '65f4457e843cd92f53535e4e98455cd34d522926ebe1b092ce54c2caa600c265',
    'reference_rules.py': '1a5d133612f13fda966676269c334e5dd112bc87ddaf78465d6228ad9a12c71c',
    'schema_rules.py': '4fee14e67b2d73de9d8e763eb09c82ed694b8155efa08760a9876d38c1f9713b',
    'official_runner.py': 'e305a816c96ed574ad18ca90871775721fd79fcf3533a60077b26d1fdeef20d8',
}
SPLIT_SHA = '688c1013d8fe9d5c1b454d14d4cbe215659e48adc7bdfd63175580e83e2eb0db'
BENCHMARK_REVISION = 'd5d03180de41eb30a6c796d04a9bfbd9dad85c1d'


def sha(raw):
    return sha256(raw).hexdigest()


def no_symlinks(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Unexpected symlink in input or output path')


def raw_file(path):
    no_symlinks(path)
    if not path.is_file():
        raise ValueError('Missing expected file: ' + path.name)
    return path.read_bytes()


def verify_code(repo):
    for name, expected in CODE_PINS.items():
        if sha(raw_file(repo / PIPELINE / name).replace(b'\r\n', b'\n')) != expected:
            raise ValueError('Reviewed development pipeline source differs: ' + name)


def cli(repo, name, *args):
    result = subprocess.run(
        [sys.executable, '-E', '-s', '-B', str(repo / PIPELINE / name), *map(str, args)],
        cwd=repo, capture_output=True, encoding='utf-8', errors='replace')
    if result.returncode:
        # Underlying commands may handle mixed source data. Only report the stage.
        raise ValueError(name + ' failed. Verify the pinned benchmark checkout, LF data and project history.')
    return json.loads(result.stdout)


def bundle_check(bundle, export_result):
    att_raw = raw_file(bundle / 'attestation.json')
    digest = sha(att_raw)
    att = json.loads(att_raw)
    if (export_result != {'rows':35, 'groups':34, 'population':'sensitivity_only',
                          'held_out_content_exported':False, 'attestation_sha256':digest}
            or att['population'] != 'sensitivity_only' or att['partition'] != 'development'
            or (att['row_count'],att['group_count']) != (35,34)
            or att['split_sha256'] != SPLIT_SHA or att['benchmark_revision'] != BENCHMARK_REVISION
            or att['code_hashes'] != CODE_PINS or att['held_out_content_exported'] is not False
            or att['unselected_nested_payloads_decoded'] != 0):
        raise ValueError('Sensitivity export does not match the frozen development scope')
    membership = json.loads(raw_file(bundle / 'membership.json'))
    groups = membership['groups']
    if (len(groups) != 34 or membership['expected_rows'] != 35 or membership['expected_groups'] != 34
            or membership['population'] != 'sensitivity_only' or membership['split'] != 'development'
            or any(a != {'benchmark':'bfcl_v3','population':'sensitivity_only','split':'development'}
                   for a in groups.values())):
        raise ValueError('Sensitivity membership does not match the frozen development scope')
    return digest, groups


def summarize(audit, groups, digest):
    def load(name):
        return json.loads(raw_file(audit / name))

    s = load('summary.json')
    rows = load('inventory.json')
    candidates = load('candidates.json')
    pairs = load('clean_perturbed_pairs.json')
    by_key = {r['case_key']:r for r in rows}
    keys = set(by_key)
    if (s['population'] != 'sensitivity_only' or s['partition'] != 'development'
            or s['all_input_rows_retained'] is not True or s['official_labels_changed'] is not False
            or s['held_out_bundle_rows_accepted'] != 0 or s['raw_benchmark_files_opened_by_auditor'] != 0
            or s['provenance']['attestation_sha256'] != digest
            or s['provenance']['code_hashes'] != CODE_PINS
            or (s['totals']['rows'],s['totals']['canonical_groups']) != (35,34)
            or len(rows) != 35 or len(keys) != 35
            or {r['canonical_base_id'] for r in rows} != set(groups)
            or any(r['split'] != 'development' or r['population'] != 'sensitivity_only'
                   or r['benchmark'] != 'bfcl_v3' or r['source_file'] == 'clean.jsonl' for r in rows)):
        raise ValueError('Audit did not retain the separate development inventory')
    counts = Counter(r['construction_status'] for r in rows)
    candidate_index = {r['case_key']:r for r in candidates}
    if (not set(counts) <= {'candidate','blocked'} or dict(counts) != s['totals']['construction_status_counts']
            or len(candidate_index) != len(candidates) or len(candidates) != counts['candidate']
            or set(candidate_index) != {r['case_key'] for r in rows if r['construction_status']=='candidate'}
            or any(r['messages_sha256'] != sha(json.dumps(r['messages'],sort_keys=True,
                        ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())
                   or [v['role'] for v in r['messages']] != ['system','user']
                   or r['benchmark'] != 'bfcl_v3'
                   or r['messages_sha256'] != by_key[r['case_key']]['corrected_messages_sha256']
                   or r['canonical_base_id'] != by_key[r['case_key']]['canonical_base_id'] for r in candidates)):
        raise ValueError('Construction candidate evidence differs')
    pairing = {'perturbed_rows':35,'with_unique_clean_anchor':0,'both_constructed':0}
    if (s['clean_anchor_pairing'] != pairing or len(pairs) != 35
            or {r['perturbed_case_key'] for r in pairs} != keys
            or any(r['pair_available'] or r['both_constructed'] or r['clean_case_key'] is not None for r in pairs)):
        raise ValueError('Sensitivity-only population must not have clean anchors')
    return {
        'scope':'sensitivity_only_development_construction_audit',
        'benchmark':'bfcl_v3',
        'benchmark_revision':BENCHMARK_REVISION,
        'split_sha256':SPLIT_SHA,
        'source_rows':35,
        'canonical_groups':34,
        'constructed_candidates':counts['candidate'],
        'construction_blocks_retained':counts['blocked'],
        'clean_perturbed_pairs':0,
        'rows_by_source':dict(sorted(Counter(r['source_file'] for r in rows).items())),
        'reference_audit_status_counts':s['reference_audit_status_counts'],
        'three_small_models_request_count_if_approved':3 * counts['candidate'],
        'held_out_content_exported':False,
        'unselected_nested_payloads_decoded':0,
        'generation_requests_sent':0,
        'official_scoring':'not_performed',
        'main_experiment_ready':False,
        'export_attestation_sha256':digest,
        'candidate_file_sha256':sha(raw_file(audit / 'candidates.json')),
    }


def run(repo, benchmark):
    out = repo / OUTPUT
    no_symlinks(out)
    no_symlinks(benchmark)
    no_symlinks(benchmark / 'hf_data/datasets/api_eval')
    if out.exists():
        raise ValueError('Sensitivity audit already exists; preserve it')
    if not (benchmark / '.git').exists():
        raise ValueError('Pinned local benchmark checkout missing. Supply its path with --benchmark-root.')
    ignored = subprocess.run(['git','check-ignore','-q','--',str(OUTPUT / 'summary.json')],
                             cwd=repo).returncode
    if ignored != 0:
        raise ValueError('Audit output must be inside the Git-ignored local artifacts directory')
    verify_code(repo)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent, prefix='sensitivity-audit-stage-') as tmp:
        stage = Path(tmp) / 'result'
        stage.mkdir()
        bundle, audit = stage / 'export', stage / 'audit'
        print('Exporting sensitivity-only development cases with the pinned split...', flush=True)
        exported = cli(repo, 'export_development.py', '--project-root', repo,
                       '--benchmark-root', benchmark, '--population', 'sensitivity_only', '--output', bundle)
        digest, groups = bundle_check(bundle, exported)
        print('Auditing corrected prompt construction on 35 rows across 34 groups...', flush=True)
        cli(repo, 'audit_development.py', '--bundle', bundle,
            '--expected-attestation-sha256', digest, '--output', audit)
        report = summarize(audit, groups, digest)
        verify_code(repo)
        (stage / 'summary.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n', encoding='utf-8')
        if out.exists() or out.is_symlink():
            raise ValueError('Output appeared during the audit; preserve it')
        stage.rename(out)
    print(json.dumps(report,indent=2,sort_keys=True))
    print('Summary:', out / 'summary.json')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark-root', type=Path, default=DEFAULT_BENCHMARK)
    args = parser.parse_args()
    repo = Path.cwd().resolve()
    if not (repo / '.git').exists() or not (repo / 'docs/PROJECT_TASKS.md').is_file():
        raise SystemExit('Run from the root of your uqroute-tc checkout.')
    try:
        run(repo, args.benchmark_root.absolute())
    except (ValueError,OSError,KeyError,TypeError) as exc:
        # Only controlled validation messages may surface. Never print record contents.
        msg = str(exc) if type(exc) is ValueError else 'Audit I/O or structure validation failed.'
        raise SystemExit(msg) from None


if __name__ == '__main__':
    main()
