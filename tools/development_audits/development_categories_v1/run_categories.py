"""Revalidate saved development evidence and compare released static categories."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import categories

HERE = Path(__file__).resolve().parent
ROOT = 'artifacts/local_development_audits'


def run(repo,output):
    for p in (repo,output):
        if any(x.is_symlink() for x in (p,*p.parents)):
            raise ValueError('Symlink path rejected')
    repo,output = repo.resolve(),output.absolute()
    root = repo/ROOT
    if output.exists() or not output.resolve().is_relative_to(root) or output.resolve()==root:
        raise ValueError('New development output directory required')
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor','38cb695','HEAD'],check=True)
    policy = json.loads((HERE/'policy.json').read_text())
    prior = repo/'tools/development_audits/three_model_uncertainty_v1'
    for folder,locked in ((HERE,policy['source_sha256_lf']),(prior,policy['prior_source_sha256_lf'])):
        for name,wanted in locked.items():
            if hashlib.sha256((folder/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=wanted:
                raise ValueError('Source fingerprint differs: '+name)
    sys.path.insert(0,str(prior))
    import engine
    import run_analysis as analysis
    sample_path = root/'full_primary_export_v1/samples.jsonl'
    sample_raw = engine.regular(sample_path)
    if engine.sha(sample_raw)!=policy['development_samples_sha256']:
        raise ValueError('Reviewed development sample fingerprint differs')
    request_path = root/'corrected_qwen15b_coverage_import_217d4a47/prepared/requests.json'
    request_raw = engine.regular(request_path)
    if engine.sha(request_raw)!=policy['prepared_requests_sha256']:
        raise ValueError('Prepared request fingerprint differs')
    tax = categories.taxonomy([engine.loads(line) for line in sample_raw.splitlines() if line.strip()],engine.loads(request_raw))
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='development-categories-') as directory:
        temp = Path(directory).resolve()
        verified = temp/'evidence_revalidation'
        analysis.run(repo,verified)
        paths = {'qwen15b':root/'corrected_qwen15b_coverage_official_scoring_v1/scores.json',
                 'llama3b':verified/'llama3b_scoring_recomputed/scores.json',
                 'qwen7b':verified/'qwen7b_scoring_recomputed/scores.json'}
        hashes = {m:analysis.hash_file(p) for m,p in paths.items()}
        models = {m:categories.join(analysis.read_json(p),tax) for m,p in paths.items()}
        cfg = analysis.read_json(prior/'policy.json')
        results = {}; matched = {}
        # Each source type is exploratory; categories and benchmarks can overlap.
        scopes = [('category',c) for c in ('clean','observation','action','reward')]
        scopes += [('source_file',s) for s in sorted(categories.EXPECTED)]
        report = ['# Development static category diagnostics','',
                  'Released perturbation metadata; selected development cases only.',
                  'Reference compliance and deterministic ToolEyes relevance remain separate.',
                  'Unpaired condition summaries are not causal degradation estimates.', '',
                  '| Scope | Model | Panel | Rows | Correct | Mean-NLL eligible | AUROC | AP |',
                  '|---|---|---|---:|---:|---:|---:|---:|']
        for kind,value in scopes:
            selected = {m:[r for r in rows if r['analysis_category' if kind=='category' else kind]==value] for m,rows in models.items()}
            label = kind+'/'+value
            results[label] = {m:engine.analyze(rows,cfg) for m,rows in selected.items()}
            matched[label] = analysis.comparisons(selected,cfg)
            for model,data in results[label].items():
                for panel,cohort in data['by_panel'].items():
                    d = cohort['available_case_analysis']['mean_token_nll']['discrimination']
                    report.append(f'| {label} | {model} | {panel} | {cohort["original_rows"]} | {cohort["official_correct"]} | {d["eligible_rows"]} | {d["auroc"]} | {d["average_precision"]} |')
        counts = dict(Counter(t['analysis_category'] for t in tax.values()))
        summary = {'version':policy['version'],'selected_rows':len(tax),'category_counts':counts,
                   'scope_count':len(scopes),'held_out_access_enabled':False,'main_experiment_ready':False,
                   'official_labels_changed':False,'prior_files_modified':False,
                   'preference_success':'not_assessed; reward is released taxonomy, not observed preference success',
                   'inference_requests':0,'calibration':'not_refitted','routing_threshold':'not_selected'}
        report += ['', '## Interpretation', '',
                   '- Five clean cases cannot serve as a matched clean baseline for the 64 perturbed cases.',
                   '- Category composition differs by benchmark and canonical group. Inspect per-benchmark results in category_results.json.',
                   '- matched_comparison.json holds same-case model/measure comparisons within each scope; this is not clean-to-perturbed pairing.',
                   '- Available-case and all-measure-common cohorts differ. Missingness and reference flags are retained.',
                   '- Reward class membership does not establish an explicit user objective, measured tool cost/latency or preference success.',
                   '- One-class and empty discrimination metrics remain undefined. Small source-type results are exploratory.',
                   '- No category bootstrap, significance claim, population accuracy, executable task success or final freeze is established.',
                   '- Full-population construction blocks are outside this 69-response selection; no blocked case is repaired or newly generated.']
        for name,value in {'summary.json':summary,'taxonomy.json':list(tax.values()),'category_results.json':results,'matched_comparison.json':matched,
                           'provenance.json':{'policy':policy,'scored_input_sha256':hashes,'prior_policy_sha256':analysis.POLICY_SHA,'raw_benchmark_or_split_opened':False,'network_requests':0}}.items():
            (temp/name).write_text(engine.canonical(value)+'\n',encoding='utf-8')
        (temp/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
        if analysis.hash_file(sample_path)!=policy['development_samples_sha256'] or analysis.hash_file(request_path)!=policy['prepared_requests_sha256']:
            raise ValueError('Development inputs changed during analysis')
        for model,path in paths.items():
            if analysis.hash_file(path)!=hashes[model]:raise ValueError('Saved scores changed during analysis')
        engine.publish(temp,output)
    print(json.dumps(summary,indent=2));print('Review:',output/'REPORT.md')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path('.'))
    p.add_argument('--output',type=Path,default=Path(ROOT)/'development_categories_v1')
    a=p.parse_args();run(a.repo_root,a.output)
