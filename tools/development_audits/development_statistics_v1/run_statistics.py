"""Revalidate development evidence, bootstrap shared cohorts and render SVG plots."""
import argparse
import hashlib
import html
import importlib.util
import json
from itertools import combinations
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('development_cluster_statistics', HERE/'statistics.py')
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)
ROOT = 'artifacts/local_development_audits'
BASE = '37430ea'


def svg(curves, title):
    colors = ['#0072B2', '#D55E00', '#009E73']
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="840" height="540" viewBox="0 0 840 540">',
             '<rect width="840" height="540" fill="white"/>',
             '<g font-family="sans-serif" font-size="13" fill="#222">',
             '<text x="70" y="30">'+html.escape(title)+'</text>']
    for i in range(6):
        v = i/5
        x, y = 70+650*v, 430-350*v
        parts += [f'<path d="M{x},80 V430 M70,{y} H720" stroke="#ddd" fill="none"/>',
                  f'<text x="{x}" y="450">{v:.1f}</text>', f'<text x="35" y="{y+4}">{v:.1f}</text>']
    for (model, points), color in zip(sorted(curves.items()), colors):
        # Discrete attainable tie-block points; no interpolation or origin risk.
        for p in points:
            if p['risk'] is not None:
                parts.append(f'<circle cx="{70+650*p["panel_coverage"]}" cy="{430-350*p["risk"]}" r="3" fill="{color}"/>')
        idx = sorted(curves).index(model)
        parts.append(f'<text x="{75+210*idx}" y="490" fill="{color}">{html.escape(model)}</text>')
    parts += ['<text x="220" y="475">Coverage of original panel (unavailable cases retained)</text>',
              '<text x="75" y="65">Risk = fraction of accepted calls officially noncompliant / irrelevant</text>',
              '<text x="70" y="520">Observed tie-block points only; no fitted threshold or confidence bands.</text>', '</g></svg>']
    return '\n'.join(parts)+'\n'


def evaluate(rows, measure, metrics):
    result = {}
    for model in sorted(rows[0]['models']) if rows else []:
        values = [r['models'][model] for r in rows]
        d = metrics.discrimination([v['error'] for v in values], [v[measure] for v in values])
        rc = metrics.risk_coverage([v['error'] for v in values], [v[measure] for v in values], len(rows))
        result.update({model+'/auroc': d['auroc'], model+'/average_precision': d['average_precision'],
                       model+'/tie_block_area': rc['tie_block_right_step_area_on_eligible_coverage']})
    for first, second in combinations(sorted(rows[0]['models']) if rows else [], 2):
        for metric in ('auroc', 'average_precision', 'tie_block_area'):
            a, b = result[first+'/'+metric], result[second+'/'+metric]
            result[first+'-minus-'+second+'/'+metric] = None if a is None or b is None else a-b
    return result


def run(repo, output):
    for path in (repo, output):
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('Symlink path rejected')
    repo, output = repo.resolve(), output.absolute()
    root = repo/ROOT
    if output.exists() or not output.resolve().is_relative_to(root) or output.resolve() == root:
        raise ValueError('A new development artifact directory is required')
    subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', BASE, 'HEAD'], check=True)
    policy = json.loads((HERE/'policy.json').read_text())
    for name, wanted in policy['source_sha256_lf'].items():
        if hashlib.sha256((HERE/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != wanted:
            raise ValueError('Statistics source fingerprint differs')
    prior = repo/'tools/development_audits/three_model_uncertainty_v1'
    for name, wanted in policy['prior_source_sha256_lf'].items():
        if hashlib.sha256((prior/name).read_bytes().replace(b'\r\n', b'\n')).hexdigest() != wanted:
            raise ValueError('Three-model source fingerprint differs')
    sys.path.insert(0, str(prior))
    import run_analysis as analysis
    import metrics
    import engine
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='development-statistics-') as directory:
        temporary = Path(directory).resolve()
        verified = temporary/'evidence_revalidation'
        analysis.run(repo, verified)
        paths = {'qwen15b':root/'corrected_qwen15b_coverage_official_scoring_v1/scores.json',
                 'llama3b':verified/'llama3b_scoring_recomputed/scores.json',
                 'qwen7b':verified/'qwen7b_scoring_recomputed/scores.json'}
        input_hashes = {m:analysis.hash_file(p) for m,p in paths.items()}
        models = {m:engine.index(analysis.read_json(p)) for m,p in paths.items()}
        cfg = analysis.read_json(prior/'policy.json')
        base = models['qwen15b']
        results = {}
        for scope in ['official_reference_compliance', 'tooleyes_relevance'] + sorted({r['benchmark'] for r in base.values()}):
            keys = sorted(k for k,r in base.items() if r['panel'] == scope or r['benchmark'] == scope)
            print('Processing development scope:',scope,flush=True)
            for cohort in ('whole_output_shared', 'all_measures_shared'):
                names = ['mean_token_nll'] if cohort == 'whole_output_shared' else list(cfg['measures'])
                required = ['mean_token_nll'] if cohort == 'whole_output_shared' else list(cfg['measures'])
                selected = [k for k in keys if all(engine.measured(models[m][k], cfg['measures'][n]) is not None for m in models for n in required)]
                rows = [{'case_key':k, 'benchmark':base[k]['benchmark'], 'canonical_base_id':base[k]['canonical_base_id'],
                         'models':{m:{'error':not models[m][k]['official_score']['correct'],
                                      **{n:engine.measured(models[m][k],cfg['measures'][n]) for n in names}} for m in models}} for k in selected]
                for measure in names:
                    label = scope+'/'+cohort+'/'+measure
                    result = st.bootstrap(rows, lambda draw:evaluate(draw,measure,metrics), policy['replicates'], st.stable_seed(scope+'/'+cohort))
                    curves = {m:metrics.risk_coverage([r['models'][m]['error'] for r in rows], [r['models'][m][measure] for r in rows],len(keys))['points'] for m in models}
                    results[label] = {'original_rows':len(keys), 'shared_eligible_rows':len(rows), 'case_keys':selected, 'metrics':result, 'risk_coverage':curves}
                    (temporary/(label.replace('/','__')+'.svg')).write_text(svg(curves,label), encoding='utf-8')
        report = ['# Development cluster-bootstrap diagnostics', '',
                  'Exploratory 95% percentile intervals conditional on the selected development cases.',
                  'Benchmarks are fixed strata; canonical groups are resampled with replacement within benchmark.',
                  'Each sampled group contributes all its selected eligible rows, including duplicate draws.',
                  'Metrics are case weighted; shared resampling preserves pairing across models and measures.',
                  'Each measure uses the same seed within a cohort, so bootstrap draws match across measures.',
                  'Intervals are withheld below 10 groups or 90% valid replicates; undefined metrics stay undefined.',
                  'These rules are prospective for this diagnostic only, not a final protocol freeze.', '',
                  '| Scope/cohort/measure | Rows | Metric | Point | 95% interval or reason |', '|---|---:|---|---:|---|']
        for label, result in results.items():
            for name, value in result['metrics'].items():
                report.append(f'| {label} | {result["shared_eligible_rows"]} | {name} | {value["point"]} | {value["interval_95_percentile"] or value["interval_unavailable_reason"]} |')
        report += ['', 'Intervals do not repair nonrandom selection, missingness or reference ambiguity. No multiple-comparison correction or significance claim is supplied.',
                   'Differences are first model minus second; lower tie-block area is better. AP differences also reflect model-specific error prevalence.',
                   'Plots show discrete attainable tie-block risks, without interpolation, bootstrap bands or threshold selection.',
                   'ToolEyes relevance is separate from reference compliance. No calibration, routing evaluation, held-out access or model inference occurs.']
        (temporary/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
        (temporary/'statistics.json').write_text(engine.canonical({'policy':policy,'results':results,'held_out_access_enabled':False,'main_experiment_ready':False,'prior_files_modified':False})+'\n',encoding='utf-8')
        for model,path in paths.items():
            if analysis.hash_file(path) != input_hashes[model]:
                raise ValueError('Saved scores changed during statistics')
        (temporary/'provenance.json').write_text(engine.canonical({'statistics_source_sha256_lf':policy['source_sha256_lf'], 'scored_input_sha256':input_hashes, 'prior_workflow_policy_sha256':analysis.POLICY_SHA, 'network_requests':0, 'held_out_access_enabled':False, 'main_experiment_ready':False})+'\n',encoding='utf-8')
        engine.publish(temporary,output)
    print('Development statistics complete:',output)
    return results


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path('.'))
    p.add_argument('--output',type=Path,default=Path(ROOT)/'development_statistics_v1')
    a = p.parse_args()
    run(a.repo_root,a.output)
