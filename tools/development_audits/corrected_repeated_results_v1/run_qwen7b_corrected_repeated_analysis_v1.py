"""Score 300 verified Qwen 7B development responses and compare 30 case-level signals."""
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
REPEATED = ROOT / 'corrected_qwen7b_repeated_import_de99cdcc'
SINGLE = ROOT / 'corrected_qwen7b_full_development_import_cee21586'
OUTPUT = ROOT / 'qwen7b_corrected_repeated_analysis_v1'
SCORER = 'tools/development_audits/qwen7b_full_development_scoring_v1/score_qwen7b_full.py'
METHOD = 'src/uqroute_tc/uncertainty/repeated.py'
METRICS = 'tools/development_audits/three_model_uncertainty_v1/metrics.py'
SOURCE_PINS = {
    SCORER: '61e7c590a5bafece6c95cf562b078f7e9a771b08112f7606813ee83adf606508',
    METHOD: 'df58714c586dafd7b816ef04c59046972c9c45b5c77217a835e09da2067ebdd9',
    METRICS: 'c42316319649629378b968915ed3cfeb366f5ce785364948c5c5a507d6d248ff',
}
INVENTORY = 'fa2f2cb3251ce950f5abd1302dcff3a28a0a5717ac6298c4ed30d1f99e682336'
SUMMARY = 'dea28373f4efaaa8348bc424436c2168f87f59037e9d9bb7d22015c22f67132a'
RECORDS = '48c068c96396ad033156d4bfe9447db9b1842d44bf8ac65a64b5cf9e943148f5'
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


ZIP='b760086abb05d383f09cf126ae5472fc6d735d0a9d424c76a43e3718e0a3d6cf'
CLIENT='0bfa4dda855c669d102e23359ef8ed8b9818995647a79e1d467b33cec566861f'
MANIFEST='0468034b1a302dfba56b294e69d09fe68aaa85132c6aa3069d61eae0a3e565ba'



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



REPLAY = ROOT / 'corrected_qwen7b_repeated_local_replay_v1'
ARCHIVE_NAME = 'uqroute_qwen7b_corrected_repeated_de99cdcc.zip'
STATUSES = {'complete': 300}


def import_and_replay(repo, archive, sc, workflow, frozen):
    target, replay = repo / REPEATED, repo / REPLAY
    for path in (target, replay):
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('Output has a symlink ancestor; preserve it')
    data, binding = validate(archive)
    with tempfile.TemporaryDirectory(dir=repo / ROOT, prefix='qwen7b-repeated-import-') as tmp:
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


PRIOR = {
    'qwen15b': '3d3ef620b68dc3b4c5da0878f904eaf8e94fa78a4c3cd7a748328abc1bcfef8e',
    'llama3b': 'e17603a3adc4bd568534c0b812ed726b69bd00b97baed6059314f076ac8838d6',
}


def prior_cases(repo, sc, metrics, ledger):
    result = {}
    for model, expected in PRIOR.items():
        folder = repo / ROOT / (model + '_corrected_repeated_analysis_v1')
        if not folder.is_dir():
            raise ValueError('Missing completed development analysis: ' + model)
        sc.checked(folder / 'analysis_source.py', expected, ledger)
        def load(name):
            path = folder / (name + '.json')
            raw = sc.regular(path)
            ledger[path] = sha(raw)
            return sc.loads(raw)
        cases, slots, summary, provenance = [load(n) for n in ('cases','slots','summary','provenance')]
        if (summary['scope'] != model + '_corrected_repeated_primary_development_diagnostic'
                or summary['held_out_access_enabled'] is not False
                or summary['main_experiment_ready'] is not False
                or summary['official_labels_changed'] is not False
                or summary['inference_requests'] != 0
                or summary['cases'] != 30 or summary['sample_slots'] != 300
                or provenance['tool_sha256'] != expected):
            raise ValueError('Prior analysis scope or source differs: ' + model)
        by_case = defaultdict(list)
        seen = set()
        for slot in slots:
            sample = slot['sample_index']
            key = slot['case_key']
            if type(sample) is not int or sample not in range(10) or (key,sample) in seen:
                raise ValueError('Prior slot identity differs: ' + model)
            seen.add((key,sample))
            by_case[key].append(slot)
        if len(by_case) != 30 or len(seen) != 300 or len(cases) != 30 or {r['case_key'] for r in cases} != set(by_case):
            raise ValueError('Prior analysis denominators differ: ' + model)
        for r in cases:
            group = by_case[r['case_key']]
            if (len(group) != 10 or any(any(s[k] != r[k] for k in (*IDENTITY,'panel')) for s in group)
                    or sum(s['official_score']['correct'] for s in group) != r['sample_slots_reference_match']
                    or any(r['signals'][kind + '_' + metric] != r[kind][field]
                           for kind in ('canonical','exact_string')
                           for metric,field in (('entropy','entropy_nats'),('disagreement','disagreement')))):
                raise ValueError('Prior case and slot results disagree: ' + model)
        if summary['panels'] != summarize(cases, slots, metrics.discrimination):
            raise ValueError('Prior panel metrics disagree: ' + model)
        result[model] = cases
    return result


def compare(cases_by_model, metrics):
    identity = (*IDENTITY, 'panel')
    indices = {model:{r['case_key']:r for r in rows} for model,rows in cases_by_model.items()}
    baseline = indices['qwen7b']
    for model, rows in indices.items():
        if len(cases_by_model[model]) != len(rows) or set(rows) != set(baseline):
            raise ValueError('Model case keys differ: ' + model)
        if any(any(r[k] != baseline[key][k] for k in identity) for key,r in rows.items()):
            raise ValueError('Model case lineage differs: ' + model)
    out = {}
    for panel in PANELS:
        keys = [k for k,r in baseline.items() if r['panel'] == panel]
        if len(keys) != (6 if panel == 'tooleyes_relevance' else 24):
            raise ValueError('Unexpected panel denominator')
        panel_result = {'original_cases': len(keys), 'cohorts': {}}
        for name, signals in (
            ('shared_whole_and_repeated', tuple(k for k in SIGNALS if k != 'single_meaningful_token_nll')),
            ('shared_all_signals', SIGNALS),
        ):
            common = [k for k in keys if all(rows[k]['signals'][s] is not None
                                              for rows in indices.values() for s in signals)]
            results = {}
            for model, rows in indices.items():
                labels = []
                for key in common:
                    label = rows[key]['single_official_score']['correct']
                    if type(label) is not bool:
                        raise ValueError('Non-boolean reference label: ' + model)
                    labels.append(not label)
                measures = {s:metrics.discrimination(labels,[rows[k]['signals'][s] for k in common])
                            for s in signals}
                results[model] = {
                    'measures': measures,
                    'repeated_minus_single_mean_nll_auroc': {
                        s: measures[s]['auroc'] - measures['single_mean_token_nll']['auroc']
                        if measures[s]['auroc'] is not None and measures['single_mean_token_nll']['auroc'] is not None else None
                        for s in signals if s.startswith(('canonical_', 'exact_string_'))},
                }
            panel_result['cohorts'][name] = {
                'cases':len(common),
                'canonical_groups':len({(baseline[k]['benchmark'],baseline[k]['canonical_base_id']) for k in common}),
                'case_keys':common,
                'models':results,
            }
        panel_result['model_outcomes'] = {
            model:{
                'sample_slots':sum(rows[k]['sample_slots'] for k in keys),
                'sample_slots_reference_match':sum(rows[k]['sample_slots_reference_match'] for k in keys),
                'canonical_unanimous_all_ten_mismatch':sum(
                    rows[k]['canonical']['cluster_count'] == 1 and rows[k]['sample_slots_reference_match'] == 0 for k in keys),
            } for model,rows in indices.items()}
        out[panel] = panel_result
    return {'scope':'three_model_corrected_repeated_development_comparison',
            'ranking_target':'reference mismatch of each model’s own separately generated single response',
            'held_out_access_enabled':False, 'main_experiment_ready':False,
            'inference_requests':0, 'routing_threshold_selected':False,
            'limitations':[
                'Retrospective diagnostic: 30 cases in 15 groups per model. Slots are dependent.',
                'Shared case identities do not imply identical outcomes across models.',
                'ToolEyes name relevance is separate; AUROC is undefined with one outcome class.',
                'The earlier Qwen 1.5B and Llama analyses are reused and checked for internal consistency; their source scripts are fingerprinted.',
                'This comparison does not measure execution, calibrate a routing threshold, or establish statistical superiority.',
            ], 'panels':out}


def report(joint):
    lines = ['# Corrected repeated sampling: three-model development comparison', '',
             'Each AUROC ranks errors of the same model’s separately generated single response.',
             'Rows within a panel use the same case identities across models and measures.', '']
    def fmt(x):
        return 'undefined' if x is None else f'{x:.3f}'
    for panel, data in joint['panels'].items():
        lines += [f'## {panel}', '']
        for name, cohort in data['cohorts'].items():
            lines += [f'{name}: {cohort["cases"]}/{data["original_cases"]} cases, {cohort["canonical_groups"]} groups.', '',
                      '| Model | Measure | Errors | AUROC | AP | Error prevalence |',
                      '|---|---|---:|---:|---:|---:|']
            for model, result in cohort['models'].items():
                for signal,m in result['measures'].items():
                    lines.append(f'| {model} | {signal} | {m["error_positive_rows"]} | {fmt(m["auroc"])} | '
                                 f'{fmt(m["average_precision"])} | {fmt(m["error_prevalence"])} |')
            lines.append('')
        lines += ['| Model | Reference-matching samples | Unanimous cases with ten reference mismatches |',
                  '|---|---:|---:|']
        for model,m in data['model_outcomes'].items():
            lines.append(f'| {model} | {m["sample_slots_reference_match"]}/{m["sample_slots"]} | {m["canonical_unanimous_all_ten_mismatch"]} |')
        lines.append('')
    lines += ['## Limits', ''] + ['- '+s for s in joint['limitations']]
    return '\n'.join(lines)+'\n'


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
        raise ValueError('Verified Qwen 7B full-development import is required for the matched baseline')
    sc = module('_verified_full_scorer', repo / SCORER)
    metrics = module('_verified_rank_metrics', repo / METRICS)
    ledger = {}
    previous = prior_cases(repo, sc, metrics, ledger)
    rules = sc.policy()
    workflow, frozen, parser, official = sc.load_dependencies(repo, rules)
    support = sys.modules['support']
    repeated_scores = load_repeated(repo, support, sys.modules['_corrected_dev_canonical'])
    import_and_replay(repo, archive, sc, workflow, frozen)
    evidence = repo / REPEATED
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
        'scope': 'qwen7b_corrected_repeated_primary_development_diagnostic',
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
                   'Reference matching does not measure execution or cost/latency preference.'],
        'held_out_access_enabled': False, 'main_experiment_ready': False,
        'official_labels_changed': False, 'inference_requests': 0,
    }
    joint = compare({**previous, 'qwen7b':cases}, metrics)
    provenance = {'inputs_sha256': {p.relative_to(repo).as_posix(): h for p, h in ledger.items()},
                  'sources_sha256_lf': SOURCE_PINS, 'tool_sha256': sha(Path(__file__).read_bytes())}
    for p, pin in ledger.items():
        if sha(sc.regular(p)) != pin:
            raise ValueError('Input changed during scoring: ' + p.name)
    with tempfile.TemporaryDirectory(dir=out.parent, prefix='qwen7b-repeated-analysis-') as tmp:
        stage = Path(tmp) / 'output'
        stage.mkdir()
        for filename, value in [('summary.json', summary), ('slots.json', slots),
                                ('cases.json', cases), ('provenance.json', provenance),
                                ('three_model_comparison.json', joint)]:
            (stage / filename).write_text(sc.canonical(value) + '\n', encoding='utf-8')
        (stage / 'THREE_MODEL_REPORT.md').write_text(report(joint), encoding='utf-8')
        shutil.copyfile(Path(__file__), stage / 'analysis_source.py')
        sc.publish_directory(stage, out)
    for panel, data in summary['panels'].items():
        brief = {k: v for k, v in data.items() if 'ranking' not in k}
        brief['matched_whole_output_auroc'] = {
            k: v['auroc'] for k, v in data['single_response_error_ranking_whole_and_repeated_common'].items()}
        print(panel, json.dumps(brief, sort_keys=True))
    print('ANALYSIS COMPLETE: 300 slot scores, 30 repeated-sample cases. No generation or Git changes.')
    print('Results:', out)
    print('Three-model comparison:', out / 'THREE_MODEL_REPORT.md')


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('archive', nargs='?', type=Path, default=Path.home() / 'Downloads' / ARCHIVE_NAME)
    run(Path.cwd().resolve(), cli.parse_args().archive)
