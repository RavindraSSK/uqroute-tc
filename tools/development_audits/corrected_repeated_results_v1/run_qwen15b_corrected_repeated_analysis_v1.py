"""Score 300 verified Qwen development responses and compare 30 case-level signals."""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path('artifacts/local_development_audits')
REPEATED = ROOT / 'corrected_qwen15b_repeated_import_6e710e52'
SINGLE = ROOT / 'corrected_qwen15b_full_development_import_8517fd5d'
OUTPUT = ROOT / 'qwen15b_corrected_repeated_analysis_v1'
SCORER = 'tools/development_audits/full_development_scoring_v1/score_full.py'
METHOD = 'src/uqroute_tc/uncertainty/repeated.py'
METRICS = 'tools/development_audits/three_model_uncertainty_v1/metrics.py'
SOURCE_PINS = {
    SCORER: 'af44aee3371f62ba6d0ba5ec6b31764d46d4a21e61c30fb21b15ccb82ef880e8',
    METHOD: 'df58714c586dafd7b816ef04c59046972c9c45b5c77217a835e09da2067ebdd9',
    METRICS: 'c42316319649629378b968915ed3cfeb366f5ce785364948c5c5a507d6d248ff',
}
INVENTORY = '0adc05d685f3f562b0ab94d9a75d018c95204933fddbd5b1d302c47741d0b5ed'
SUMMARY = '90a72e13faa97837a700d52e96364ed0ad0fe769ac99f3593d4306477e0ffb3b'
RECORDS = '4ce9ee0aa7674f8d60e360117e81b6b44a9820c6d412d8a103391b9f8a162d97'
IDENTITY = ('case_key', 'benchmark', 'canonical_base_id', 'source_file')
REPLAY_FIELDS = (*IDENTITY, 'slot_id', 'sample_index', 'http_status', 'elapsed_seconds')
PANELS = ('official_reference_compliance', 'tooleyes_relevance')
SIGNALS = ('single_mean_token_nll', 'single_meaningful_token_nll',
           'canonical_entropy', 'canonical_disagreement', 'exact_string_entropy',
           'exact_string_disagreement')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def load_repeated(repo, support, canonical_module):
    raw = support.read(repo / METHOD).replace(b'\r\n', b'\n')
    if sha(raw) != SOURCE_PINS[METHOD]:
        raise ValueError('Maintained frozen repeated method differs')
    tree = ast.parse(raw)
    tree.body = [node for node in tree.body if not (
        isinstance(node, ast.ImportFrom) and node.module == 'uqroute_tc.parsing.canonical')]
    return support.module_from_ast('_verified_repeated', tree, {
        'CanonicalPrediction': canonical_module.CanonicalPrediction,
        'parse_prediction': canonical_module.parse_prediction,
    }).repeated_scores


def summarize(cases, slots, discrimination):
    panels = {}
    for panel in PANELS:
        group = [r for r in cases if r['panel'] == panel]
        samples = [r for r in slots if r['panel'] == panel]
        if not group or not samples:
            raise ValueError('Expected both separate scoring panels')
        joint = [r for r in group if all(r['signals'][k] is not None for k in SIGNALS)]
        def rank(rows, key):
            return discrimination([not r['single_official_score']['correct'] for r in rows],
                                  [r['signals'][key] for r in rows])
        panels[panel] = {
            'cases': len(group),
            'sample_slots': len(samples),
            'sample_slots_reference_match': sum(r['official_score']['correct'] for r in samples),
            'single_response_reference_match': sum(r['single_official_score']['correct'] for r in group),
            'canonical_unanimous_cases': sum(r['canonical']['cluster_count'] == 1 for r in group),
            'canonical_unanimous_but_single_response_mismatch': sum(
                r['canonical']['cluster_count'] == 1 and not r['single_official_score']['correct'] for r in group),
            'canonical_unanimous_and_all_ten_samples_mismatch': sum(
                r['canonical']['cluster_count'] == 1 and r['sample_slots_reference_match'] == 0 for r in group),
            'single_response_error_ranking_available_case': {
                key: rank([r for r in group if r['signals'][key] is not None], key) for key in SIGNALS},
            'single_response_error_ranking_all_signal_common': {key: rank(joint, key) for key in SIGNALS},
            'single_response_error_ranking_whole_and_repeated_common': {
                key: rank([r for r in group if r['signals']['single_mean_token_nll'] is not None], key)
                for key in SIGNALS if key != 'single_meaningful_token_nll'},
        }
    return panels


def run(repo):
    out = repo / OUTPUT
    if out.exists() or any(p.is_symlink() for p in (out, *out.parents)):
        raise ValueError('Output exists or path has a symlink; preserve it')
    for path, pin in SOURCE_PINS.items():
        p = repo / path
        if any(x.is_symlink() for x in (p, *p.parents)) or sha(p.read_bytes().replace(b'\r\n', b'\n')) != pin:
            raise ValueError('Source fingerprint differs: ' + path)
    subprocess.run(['git', 'merge-base', '--is-ancestor', '0bf4fe6', 'HEAD'], cwd=repo, check=True)
    subprocess.run(['git', 'check-ignore', str(OUTPUT / 'summary.json')], cwd=repo, check=True)
    sc = module('_verified_full_scorer', repo / SCORER)
    metrics = module('_verified_rank_metrics', repo / METRICS)
    rules = sc.policy()
    workflow, frozen, parser, official = sc.load_dependencies(repo, rules)
    support = sys.modules['support']
    repeated_scores = load_repeated(repo, support, sys.modules['_corrected_dev_canonical'])
    evidence = repo / REPEATED
    ledger = {}
    hashes = sc.loads(sc.checked(evidence / 'metadata/export_file_hashes.json', INVENTORY, ledger))
    if len(hashes) != 928:
        raise ValueError('Repeated export inventory differs')
    for name, digest in hashes.items():
        sc.checked(evidence / name, digest, ledger)
    client = module('_verified_repeat_client', evidence / 'metadata/repeated_client.py')
    manifest, requests = client.load(evidence / 'prepared')
    workflow.check_runtime(sc.loads(sc.regular(evidence / 'metadata/runtime.json')), manifest)
    repeat_replay = repo / ROOT / 'corrected_qwen15b_repeated_local_replay_v1'
    local = sc.loads(sc.checked(repeat_replay / 'records.json', RECORDS, ledger))
    sc.checked(repeat_replay / 'summary.json', SUMMARY, ledger)
    if len(local) != 300 or len({r['slot_id'] for r in local}) != 300:
        raise ValueError('Repeated replay denominator differs')
    saved = {r['slot_id']: r for r in local}

    single_dir = repo / SINGLE
    def read_single(name):
        return sc.checked(single_dir / name, rules['evidence_file_sha256'][name], ledger)
    for name in ('prepared/manifest.json', 'prepared/requests.json'):
        read_single(name)
    _, singles = workflow.load_plan(repo, single_dir / 'prepared', rules['prepared_manifest_sha256'])
    single_index = sc.unique_index(singles)
    refs, inventory = sc.development_inputs(repo / ROOT / 'full_primary_export_v1',
        repo / ROOT / 'full_primary_audit_v1/inventory.json', rules, ledger)
    print('Pinned sources, 928 export fingerprints, local replay and development references verified.', flush=True)
    slots = []
    grouped = defaultdict(list)
    for r in requests:
        key, slot = r['case_key'], r['slot_id']
        single = single_index[key]
        validation = saved[slot]
        if any(r[k] != single[k] for k in IDENTITY) or r['request']['messages'] != single['request']['messages']:
            raise ValueError('Repeated prompt does not match the single-response case')
        if any(r[k] != validation[k] for k in (*IDENTITY, 'slot_id', 'sample_index')) or validation['http_status'] != 200 or validation['status'] != 'complete':
            raise ValueError('Unexpected response slot for the reviewed 300-complete run')
        response = sc.loads(sc.regular(evidence / f'run/cases/{slot}/http_response.bin'))
        score = sc.score_case(single, response, refs[key], inventory[key], parser, official,
                              workflow, frozen, {k: v for k, v in validation.items() if k not in REPLAY_FIELDS})
        score.update(slot_id=slot, sample_index=r['sample_index'], parser_status=validation['parser_status'])
        slots.append(score)
        grouped[key].append((score, response['choices'][0]['message']['content']))
    cases = []
    for key, samples in grouped.items():
        if [r['sample_index'] for r, _ in samples] != list(range(10)):
            raise ValueError('Expected ten ordered slots')
        single = single_index[key]
        single_slot = sha(key.encode())
        path = f'run/cases/{single_slot}'
        baseline = sc.score_case(single, sc.loads(read_single(path + '/http_response.bin')),
            refs[key], inventory[key], parser, official, workflow, frozen,
            sc.loads(read_single(path + '/validation.json')))
        scores = repeated_scores([raw for _, raw in samples], single['benchmark'], parser,
                                 generation_statuses=[r['evidence_status'] for r, _ in samples])
        if list(scores.statuses) != [r['parser_status'] for r, _ in samples]:
            raise ValueError('Frozen clustering parser statuses differ from replay')
        count_correct = sum(r['official_score']['correct'] for r, _ in samples)
        whole, meaningful = baseline['whole_output_scores'], baseline['meaningful_token_score']
        cases.append({**{k: single[k] for k in IDENTITY}, 'panel': baseline['panel'],
            'single_official_score': baseline['official_score'],
            'single_evidence_status': baseline['evidence_status'],
            'sample_slots_reference_match': count_correct,
            'sample_slots': len(samples), **asdict(scores),
            'signals': {'single_mean_token_nll': whole['mean_token_nll'] if whole else None,
                        'single_meaningful_token_nll': meaningful['mean_token_nll'] if meaningful else None,
                        'canonical_entropy': scores.canonical.entropy_nats,
                        'canonical_disagreement': scores.canonical.disagreement,
                        'exact_string_entropy': scores.exact_string.entropy_nats,
                        'exact_string_disagreement': scores.exact_string.disagreement}})
    if len(cases) != 30 or len(slots) != 300:
        raise ValueError('Unexpected case/sample denominators')
    summary = {
        'scope': 'qwen15b_corrected_repeated_primary_development_diagnostic',
        'cases': len(cases), 'sample_slots': len(slots),
        'samples_per_case': 10,
        'canonical_groups': len({r['canonical_base_id'] for r in cases}),
        'parser_status_counts': dict(Counter(r['parser_status'] for r in slots)),
        'panels': summarize(cases, slots, metrics.discrimination),
        'ranking_target': 'mismatch of the separately generated matched single response',
        'limits': ['Exploratory 30-case diagnostic; repeated slots and clean/perturbed variants are dependent.',
                   'Sample-level reference outcomes are descriptive; ToolEyes name relevance stays separate.',
                   'Agreement measures variation in sampled outcomes and can be high even when every call is wrong.',
                   'Unparsed/no-call outputs share a frozen canonical outcome; unanimity need not imply ten parsed calls.',
                   'Reference matching does not measure execution or cost/latency preference.'],
        'held_out_access_enabled': False, 'main_experiment_ready': False,
        'official_labels_changed': False, 'inference_requests': 0,
    }
    provenance = {'inputs_sha256': {p.relative_to(repo).as_posix(): h for p, h in ledger.items()},
                  'sources_sha256_lf': SOURCE_PINS, 'tool_sha256': sha(Path(__file__).read_bytes())}
    for p, pin in ledger.items():
        if sha(sc.regular(p)) != pin:
            raise ValueError('Input changed during scoring: ' + p.name)
    with tempfile.TemporaryDirectory(dir=out.parent, prefix='qwen-repeated-analysis-') as tmp:
        stage = Path(tmp) / 'output'
        stage.mkdir()
        for filename, value in [('summary.json', summary), ('slots.json', slots),
                                ('cases.json', cases), ('provenance.json', provenance)]:
            (stage / filename).write_text(sc.canonical(value) + '\n', encoding='utf-8')
        shutil.copyfile(Path(__file__), stage / 'analysis_source.py')
        sc.publish_directory(stage, out)
    for panel, data in summary['panels'].items():
        brief = {k: v for k, v in data.items() if 'ranking' not in k}
        brief['matched_whole_output_auroc'] = {
            k: v['auroc'] for k, v in data['single_response_error_ranking_whole_and_repeated_common'].items()}
        print(panel, json.dumps(brief, sort_keys=True))
    print('ANALYSIS COMPLETE: 300 slot scores, 30 repeated-sample cases. No generation or Git changes.')
    print('Results:', out)


if __name__ == '__main__':
    run(Path.cwd().resolve())
