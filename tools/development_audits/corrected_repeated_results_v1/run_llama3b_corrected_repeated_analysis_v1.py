"""Score 300 verified Llama 3B development responses and compare 30 case-level signals."""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import argparse
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path('artifacts/local_development_audits')
REPEATED = ROOT / 'corrected_llama3b_repeated_import_91340333'
SINGLE = ROOT / 'corrected_llama3b_full_development_import_0a9a8a9b'
OUTPUT = ROOT / 'llama3b_corrected_repeated_analysis_v1'
SCORER = 'tools/development_audits/llama_full_development_scoring_v1/score_llama_full.py'
METHOD = 'src/uqroute_tc/uncertainty/repeated.py'
METRICS = 'tools/development_audits/three_model_uncertainty_v1/metrics.py'
SOURCE_PINS = {
    SCORER: '875ff9b4e93a602d04d892e790d30277f7f3b73c5f3fa038b33fbd04e7e09190',
    METHOD: 'df58714c586dafd7b816ef04c59046972c9c45b5c77217a835e09da2067ebdd9',
    METRICS: 'c42316319649629378b968915ed3cfeb366f5ce785364948c5c5a507d6d248ff',
}
INVENTORY = '8861ce9cfa3ad3365db3814750b0d6f5b96155b12852d93869371adcc5fb93c2'
SUMMARY = '667d768a0e3b8726d9db1705a629111347419d4bcda529f4b123d7de1f4f6142'
RECORDS = 'feb885e5e2ceabaab156564c7a872128b403ceec5539dbdda62d5d08735fa40d'
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
    exec(compile(path.read_bytes(), str(path), 'exec'), result.__dict__)
    return result


ZIP='500f9784b4db5733a4168b19370eaa5ebd194c4c3e7537537a9b19c117f4105d'
CLIENT='c6a9b226ab89b7f2652133161aedc5bd83b7d141db5a5747aa98edf4fd1f2307'
MANIFEST='4055b39bea20b3bfde8a188505a4251ebd64f9d2b23c0c9e87576c16b32cf12b'



def validate(source):
    if sha(source.read_bytes())!=ZIP:raise ValueError('ZIP fingerprint differs')
    with zipfile.ZipFile(source) as z:
        entries=z.infolist();names=[e.filename for e in entries]
        if len(names)!=929 or len({n.casefold() for n in names})!=929 or z.testzip() is not None:raise ValueError('Archive inventory/integrity differs')
        for e in entries:
            p=PurePosixPath(e.filename)
            if p.is_absolute() or not p.parts or '..' in p.parts or '\\' in e.filename or ':' in e.filename or p.parts[0] not in {'prepared','metadata','run','replay'} or stat.S_ISLNK(e.external_attr>>16) or any(part.endswith((' ','.')) for part in p.parts):raise ValueError('Unsafe archive member')
        data={e.filename:z.read(e) for e in entries if not e.is_dir()}
    if sha(data['metadata/export_file_hashes.json']) != INVENTORY:
        raise ValueError('Export hash manifest differs')
    hashes=json.loads(data['metadata/export_file_hashes.json'])
    if len(hashes)!=928 or set(hashes)!=set(data)-{'metadata/export_file_hashes.json'}:raise ValueError('Evidence inventory differs')
    for n,h in hashes.items():
        if sha(data[n])!=h:raise ValueError('Member differs: '+n)
    if sha(data['metadata/repeated_client.py'])!=CLIENT or sha(data['prepared/manifest.json'])!=MANIFEST:raise ValueError('Code/plan binding differs')
    binding=json.loads(data['run/run_manifest.json'])
    if binding['client_sha256']!=CLIENT or binding['prepared_manifest_sha256']!=MANIFEST or binding['runtime_sha256']!=sha(data['metadata/runtime.json']) or binding['held_out_access_enabled'] is not False or binding['main_experiment_ready'] is not False or binding['automatic_retries']!=0 or binding['request_count']!=300:raise ValueError('Run binding differs')
    return data,binding



REPLAY = ROOT / 'corrected_llama3b_repeated_local_replay_v1'
ARCHIVE_NAME = 'uqroute_llama3b_corrected_repeated_91340333.zip'
STATUSES = {'complete': 298, 'invalid_evidence': 1, 'truncated': 1}


def import_and_replay(repo, archive, sc, workflow, frozen):
    target, replay = repo / REPEATED, repo / REPLAY
    for path in (target, replay):
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('Output has a symlink ancestor; preserve it')
    data, binding = validate(archive)
    with tempfile.TemporaryDirectory(dir=repo / ROOT, prefix='llama-repeated-import-') as tmp:
        stage = Path(tmp) / 'evidence'
        candidate = target if target.exists() else stage
        if candidate == stage:
            stage.mkdir()
            for name, raw in data.items():
                path = stage.joinpath(*PurePosixPath(name).parts)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as stream:
                    stream.write(raw)
        else:
            for name, raw in data.items():
                if sc.regular(target / name) != raw:
                    raise ValueError('Previously imported evidence differs; preserve it: ' + name)
        client = module('_verified_repeat_import_client', candidate / 'metadata/repeated_client.py')
        manifest, requests = client.load(candidate / 'prepared')
        workflow.check_runtime(sc.loads(data['metadata/runtime.json']), manifest)
        trial = Path(tmp) / 'replay'
        result = client.replay(requests, candidate / 'run', trial, binding,
                               lambda response, bench: workflow.evaluate(response, bench, frozen))
        if result['status_counts'] != STATUSES:
            raise ValueError('Unexpected replay status counts')
        for name in ('records.json', 'summary.json'):
            actual = sc.regular(trial / name)
            if actual != data['replay/' + name]:
                raise ValueError('Local replay differs: ' + name)
            if replay.exists() and sc.regular(replay / name) != actual:
                raise ValueError('Previously saved replay differs; preserve it: ' + name)
        if candidate == stage:
            sc.publish_directory(stage, target)
        if not replay.exists():
            sc.publish_directory(trial, replay)
    print('Archive, 928 member hashes, local replay records and summary: MATCH', flush=True)


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


def run(repo, archive):
    out = repo / OUTPUT
    if out.exists() or any(p.is_symlink() for p in (out, *out.parents)):
        raise ValueError('Output exists or path has a symlink; preserve it')
    for path, pin in SOURCE_PINS.items():
        p = repo / path
        if any(x.is_symlink() for x in (p, *p.parents)) or sha(p.read_bytes().replace(b'\r\n', b'\n')) != pin:
            raise ValueError('Source fingerprint differs: ' + path)
    subprocess.run(['git', 'merge-base', '--is-ancestor', '0bf4fe6', 'HEAD'], cwd=repo, check=True)
    for path in (OUTPUT / 'summary.json', REPEATED / 'prepared/manifest.json', REPLAY / 'summary.json'):
        subprocess.run(['git', 'check-ignore', str(path)], cwd=repo, check=True)
    if not (repo / SINGLE / 'prepared/manifest.json').is_file():
        raise ValueError('Verified Llama full-development import is required for the matched baseline')
    sc = module('_verified_full_scorer', repo / SCORER)
    metrics = module('_verified_rank_metrics', repo / METRICS)
    rules = sc.policy()
    workflow, frozen, parser, official = sc.load_dependencies(repo, rules)
    support = sys.modules['support']
    repeated_scores = load_repeated(repo, support, sys.modules['_corrected_dev_canonical'])
    import_and_replay(repo, archive, sc, workflow, frozen)
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
    repeat_replay = repo / REPLAY
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
        if any(r[k] != validation[k] for k in (*IDENTITY, 'slot_id', 'sample_index')) or validation['http_status'] != 200 or validation['status'] not in STATUSES:
            raise ValueError('Unexpected response slot in reviewed run')
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
        if list(scores.statuses) != [r['parser_status'] if r['evidence_status'] != 'truncated'
                                    else 'truncated' for r, _ in samples]:
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
        'scope': 'llama3b_corrected_repeated_primary_development_diagnostic',
        'cases': len(cases), 'sample_slots': len(slots),
        'samples_per_case': 10,
        'canonical_groups': len({r['canonical_base_id'] for r in cases}),
        'evidence_status_counts': dict(Counter(r['evidence_status'] for r in slots)),
        'parser_status_counts': dict(Counter(r['parser_status'] for r in slots)),
        'panels': summarize(cases, slots, metrics.discrimination),
        'ranking_target': 'mismatch of the separately generated matched single response',
        'limits': ['Exploratory 30-case diagnostic; repeated slots and clean/perturbed variants are dependent.',
                   'Sample-level reference outcomes are descriptive; ToolEyes name relevance stays separate.',
                   'Agreement measures variation in sampled outcomes and can be high even when every call is wrong.',
                   'Unparsed/no-call outputs share a frozen canonical outcome; unanimity need not imply ten parsed calls.',
                   'Truncation has its own clustering status; invalid log probabilities do not prevent clustering saved text.',
                   'All 300 saved texts are scored under the same raw-output reference rules, including the truncated response.',
                   'Reference matching does not measure execution or cost/latency preference.'],
        'held_out_access_enabled': False, 'main_experiment_ready': False,
        'official_labels_changed': False, 'inference_requests': 0,
    }
    provenance = {'inputs_sha256': {p.relative_to(repo).as_posix(): h for p, h in ledger.items()},
                  'sources_sha256_lf': SOURCE_PINS, 'tool_sha256': sha(Path(__file__).read_bytes())}
    for p, pin in ledger.items():
        if sha(sc.regular(p)) != pin:
            raise ValueError('Input changed during scoring: ' + p.name)
    with tempfile.TemporaryDirectory(dir=out.parent, prefix='llama-repeated-analysis-') as tmp:
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
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('archive', nargs='?', type=Path, default=Path.home() / 'Downloads' / ARCHIVE_NAME)
    run(Path.cwd().resolve(), cli.parse_args().archive)
