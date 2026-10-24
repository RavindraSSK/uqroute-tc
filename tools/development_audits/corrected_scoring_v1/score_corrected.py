"""Score the reviewed five-response development run without changing prior artifacts."""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
POLICY_SHA = 'd23e7175616dc61817e84e65bfe257241586dd96ec2a4e395b262e2e4173c1b9'
SCORER_PATH = 'tools/development_audits/analysis_policy_v1/official_scorer.py'
BENCHMARKS = {'apibank', 'bfcl_v3', 'rotbench', 'toolalpaca', 'tooleyes'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def loads(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def invalid(_):
        raise ValueError('Nonfinite JSON value')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def regular(path):
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError('Expected regular input without symlink ancestors')
    return path.read_bytes()


def checked(path, expected, ledger):
    raw = regular(path)
    if sha(raw) != expected:
        raise ValueError('Input fingerprint differs: ' + path.name)
    ledger[path] = expected
    return raw


def policy():
    raw = regular(HERE / 'scoring_policy_v1.json').replace(b'\r\n', b'\n')
    if sha(raw) != POLICY_SHA:
        raise ValueError('Versioned scoring policy differs')
    return loads(raw)


def load_dependencies(repo, rules):
    folder = repo / 'tools/development_audits/corrected_generation_v1'
    for name, expected in rules['workflow_hashes'].items():
        if sha(regular(folder / name).replace(b'\r\n', b'\n')) != expected:
            raise ValueError('Frozen generation implementation differs')
    sys.path.insert(0, str(folder))
    try:
        import support
        import workflow
        if Path(support.__file__).resolve().parent != folder.resolve() or Path(workflow.__file__).resolve().parent != folder.resolve():
            raise ValueError('Conflicting Python module import')
        support.verify_baseline(repo)
        frozen = support.methods(repo)
    finally:
        sys.path.pop(0)
    scorer_raw = regular(repo / SCORER_PATH).replace(b'\r\n', b'\n')
    if sha(scorer_raw) != rules['scorer_sha256_lf']:
        raise ValueError('Pinned official scorer differs')
    scorer = {'__name__': '_corrected_dev_official_scorer'}
    exec(compile(scorer_raw, SCORER_PATH, 'exec'), scorer)
    # Same pinned parser source and definitions as generation; omit optional
    # OpenAI/tqdm imports only. Reparse original text, preserving tuples/types.
    runner = support.source_bytes(repo)['tools/development_audits/full_development_v1/official_runner.py']
    tree = ast.parse(runner)
    tree.body = [ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)] + [
        n for n in tree.body if not (isinstance(n, ast.ImportFrom) and n.module in {'openai', 'tqdm'})]
    namespace = {'__name__': '_corrected_dev_official_parser'}
    exec(compile(ast.fix_missing_locations(tree), 'pinned_parser', 'exec'), namespace)
    return workflow, frozen, namespace['parse_tool_calls'], scorer['score_record']


def unique_index(rows):
    result = {}
    for row in rows:
        key = row['case_key']
        if key in result:
            raise ValueError('Duplicate case identity')
        result[key] = row
    return result


def development_inputs(bundle, inventory_path, rules, ledger):
    att = loads(checked(bundle / 'attestation.json', rules['attestation_sha256'], ledger))
    if (att['partition'] != 'development' or att['population'] != 'primary'
            or att['held_out_content_exported'] is not False
            or att['unselected_nested_payloads_decoded'] != 0
            or att['benchmark_revision'] != 'd5d03180de41eb30a6c796d04a9bfbd9dad85c1d'
            or att['split_sha256'] != '688c1013d8fe9d5c1b454d14d4cbe215659e48adc7bdfd63175580e83e2eb0db'):
        raise ValueError('Not the approved primary development export')
    membership = loads(checked(bundle / 'membership.json', att['payload_hashes']['membership.json'], ledger))
    if membership['split'] != 'development' or membership['population'] != 'primary':
        raise ValueError('Non-development membership')
    groups = membership['groups']
    if len(groups) != membership['expected_groups'] or len(groups) != att['group_count']:
        raise ValueError('Development group counts differ')
    for label in groups.values():
        if label['split'] != 'development' or label['population'] != 'primary' or label['benchmark'] not in BENCHMARKS:
            raise ValueError('Non-development group')
    # The pinned attestation is checked before opening the reference sidecar.
    raw = checked(bundle / 'references.jsonl', att['payload_hashes']['references.jsonl'], ledger)
    refs = unique_index([loads(line) for line in raw.splitlines() if line.strip()])
    inventory = unique_index(loads(checked(inventory_path, rules['inventory_sha256'], ledger)))
    if set(refs) != set(inventory) or len(refs) != att['row_count'] or len(refs) != membership['expected_rows']:
        raise ValueError('Reference/inventory coverage differs')
    if sha(canonical(sorted(refs)).encode()) != att['case_key_digest']:
        raise ValueError('Reference identity digest differs')
    for key, row in inventory.items():
        label = groups.get(row['canonical_base_id'])
        if (label is None or row['split'] != 'development' or row['population'] != 'primary'
                or row['benchmark'] != label['benchmark'] or row['official_labels_changed'] is not False):
            raise ValueError('Unapproved inventory membership')
        if sha(canonical(refs[key]).encode()) != row['source_reference_sha256']:
            raise ValueError('Reference lineage differs')
    return refs, inventory


def score_case(request, response, reference, row, parser, scorer, workflow, frozen, saved):
    key = request['case_key']; benchmark = request['benchmark']
    if (row['case_key'] != key or reference['case_key'] != key
            or row['canonical_base_id'] != request['canonical_base_id'] or row['benchmark'] != benchmark
            or row['construction_status'] != 'candidate' or row['split'] != 'development'
            or row['population'] != 'primary' or row['source_file'] != 'clean.jsonl'
            or row['corrected_messages_sha256'] != request['messages_sha256']):
        raise ValueError('Selected development case lineage differs')
    if row['reference_audit_status'] != 'completed_bounded_signals_only':
        raise ValueError('Reference audit unavailable')
    result = workflow.evaluate(response, benchmark, frozen)
    if canonical(result) != canonical(saved) or result['status'] != 'complete':
        raise ValueError('Response revalidation differs or is incomplete')
    cfg = reference['eval_config']
    method = cfg.get('method', 'exact_match')
    metric = (cfg.get('metrics') or ['complete_accuracy'])[0]
    allowed = {'apibank': {'exact_match'}, 'bfcl_v3': {'exact_match'}, 'rotbench': {'rule_based'},
               'toolalpaca': {'gpt_judge', 'exact_match'}, 'tooleyes': {'gpt_judge'}}
    if method not in allowed[benchmark] or (benchmark == 'tooleyes' and metric != 'relevance') or (benchmark == 'toolalpaca' and method == 'gpt_judge' and metric != 'complete_accuracy'):
        raise ValueError('Unexpected benchmark evaluation dispatch')
    raw = response['choices'][0]['message']['content']
    calls = parser(raw, benchmark)
    official = scorer({'benchmark': benchmark, 'eval_config': cfg,
                       'golden_answers': reference['golden_answers'], 'prediction': {'tool_calls': calls}})
    audit = row['reference_audit']
    if audit.get('changes_official_labels') is not False or audit.get('excluded') is not False:
        raise ValueError('Reference flags must not change labels or exclude cases')
    return {'case_key': key, 'canonical_base_id': request['canonical_base_id'], 'benchmark': benchmark,
            'panel': 'tooleyes_relevance' if benchmark == 'tooleyes' else 'official_reference_compliance',
            'official_score': official, 'original_eval_config': cfg,
            'official_parser_call_count': len(calls), 'evidence_status': result['status'],
            'whole_output_scores': result['whole_output_scores'],
            'meaningful_token_score': result['meaningful_token_score'],
            'meaningful_token_unavailable': result['meaningful_token_unavailable'],
            'reference_review_flags': audit['review_flags'],
            'reference_review_status': audit['review_status'],
            'objective_detection': audit['objective_detection'],
            'cost_latency_preference': {'status': 'not_assessed_clean_feasibility',
                'reward_kind': audit['reward_kind'],
                'interpretation': 'Objective-detection diagnostics are not preference success or measured cost/latency.'},
            'ambiguity_exclusion_applied': False, 'official_labels_changed': False}


def panel(rows):
    n = len(rows)
    return {'rows': n, 'correct': sum(r['official_score']['correct'] for r in rows),
            'accuracy': sum(r['official_score']['correct'] for r in rows) / n if n else None,
            'mean_official_score': sum(r['official_score']['score'] for r in rows) / n if n else None,
            'flagged_rows_retained': sum(bool(r['reference_review_flags']) for r in rows)}


def score(repo, evidence, bundle, audit_dir, output):
    for path in (repo, evidence, bundle, audit_dir, output):
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('Symlink paths are not accepted')
    repo, evidence, bundle, audit_dir, output = (
        path.resolve() for path in (repo, evidence, bundle, audit_dir, output)
    )
    rules = policy(); ledger = {}
    root = repo / 'artifacts/local_development_audits'
    for path in (evidence, bundle, audit_dir, output):
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.resolve().is_relative_to(root) or path.resolve() == root:
            raise ValueError('Paths must be children of local development artifacts without symlinks')
    for source in (evidence, bundle, audit_dir):
        a, b = output.resolve(), source.resolve()
        if a == b or a in b.parents or b in a.parents:
            raise ValueError('Output overlaps existing input')
    if output.exists():
        raise ValueError('Output already exists; preserve it')
    subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', rules['baseline_commit'], 'HEAD'], check=True, capture_output=True)
    workflow, frozen, parser, scorer = load_dependencies(repo, rules)
    actual_files = set()
    for path in evidence.rglob('*'):
        if path.is_symlink():
            raise ValueError('Symlink evidence')
        if path.is_file():
            actual_files.add(path.relative_to(evidence).as_posix())
    if actual_files != set(rules['evidence_file_sha256']):
        raise ValueError('Evidence file set differs from reviewed five-response archive')
    for name, fingerprint in rules['evidence_file_sha256'].items():
        checked(evidence / name, fingerprint, ledger)
    manifest, requests = workflow.load_plan(repo, evidence / 'prepared', rules['prepared_manifest_sha256'])
    if len(requests) != 5 or manifest['selection'] != 'feasibility-five' or {r['benchmark'] for r in requests} != BENCHMARKS:
        raise ValueError('Not the five-benchmark feasibility selection')
    refs, inventory = development_inputs(bundle, audit_dir / 'inventory.json', rules, ledger)
    rows = []
    for request in requests:
        key = request['case_key']; folder = evidence / 'run/cases' / sha(key.encode())
        response = loads(regular(folder / 'http_response.bin'))
        rows.append(score_case(request, response, refs[key], inventory[key], parser, scorer,
                               workflow, frozen, loads(regular(folder / 'validation.json'))))
    summary = {'version': rules['version'], 'scope': 'five-clean-primary-development-feasibility-cases-only',
               'rows': len(rows), 'held_out_access_enabled': False, 'main_experiment_ready': False,
               'official_labels_changed': False, 'ambiguity_exclusions_applied': False,
               'official_reference_compliance': panel([r for r in rows if r['benchmark'] != 'tooleyes']),
               'tooleyes_relevance': panel([r for r in rows if r['benchmark'] == 'tooleyes']),
               'by_benchmark': {b: panel([r for r in rows if r['benchmark'] == b]) for b in sorted(BENCHMARKS)},
               'reference_flag_counts': dict(Counter(f for r in rows for f in r['reference_review_flags'])),
               'cost_latency_preference': 'not_assessed_clean_feasibility',
               'raw_benchmark_or_split_opened': False, 'development_samples_opened': False,
               'network_requests': 0, 'prior_files_modified': False,
               'limits': ['Official reference compliance is not semantic correctness or tool execution success.',
                          'ToolEyes is deterministic name-only relevance, not executable argument correctness.',
                          'Reference flags are bounded signals; no signal is not semantic clearance.',
                          'Regex nondetection is not evidence of absent intent.',
                          'Five selected clean cases do not estimate population accuracy, uncertainty discrimination or routing benefit.',
                          'Bundle consistency trusts the reviewed exporter; hashes are not authenticated partition proofs.']}
    inputs = {p.resolve().relative_to(repo).as_posix(): h for p, h in ledger.items()}
    provenance = {'baseline_commit': rules['baseline_commit'], 'head': subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
                  'policy_sha256': POLICY_SHA, 'adapter_sha256_lf': sha(regular(Path(__file__)).replace(b'\r\n', b'\n')),
                  'scorer_sha256_lf': rules['scorer_sha256_lf'], 'input_sha256': inputs,
                  'source_policy': 'Frozen generation workflow verifies its source/implementation hashes and baseline.',
                  'official_scoring_input': 'Pinned parser reparses original raw text; JSON replay calls are never scored.'}
    for path, fingerprint in ledger.items():
        if sha(regular(path)) != fingerprint:
            raise ValueError('Input changed during scoring')
    # Publish only a fresh directory after every validation and computation passes.
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='corrected-scoring-') as tmp:
        for name, value in {'scores.json': rows, 'summary.json': summary, 'provenance.json': provenance}.items():
            with (Path(tmp) / name).open('x', encoding='utf-8') as stream:
                stream.write(canonical(value) + '\n')
        if output.exists():
            raise ValueError('Output appeared during scoring')
        Path(tmp).rename(output)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('repo-root', 'evidence-dir', 'bundle', 'audit-dir', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    try:
        result = score(args.repo_root, args.evidence_dir, args.bundle, args.audit_dir, args.output)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        raise SystemExit('CPU scoring stopped (' + type(exc).__name__ + '). Preserve inputs; do not bypass fingerprints.') from None
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
