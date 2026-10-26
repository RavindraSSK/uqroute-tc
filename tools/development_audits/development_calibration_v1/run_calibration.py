"""Revalidate saved evidence and run fixed development-only calibration diagnostics."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import calibration

HERE = Path(__file__).resolve().parent
ROOT = 'artifacts/local_development_audits'


def run(repo,output):
    for p in (repo,output):
        if any(x.is_symlink() for x in (p,*p.parents)):
            raise ValueError('Symlink path rejected')
    repo,output = repo.resolve(),output.absolute()
    root = repo/ROOT
    if output.exists() or not output.resolve().is_relative_to(root) or output.resolve()==root:
        raise ValueError('New development output directory required; preserve existing files')
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor','78522c9','HEAD'],check=True)
    policy = json.loads((HERE/'policy.json').read_text())
    prior = repo/'tools/development_audits/three_model_uncertainty_v1'
    for folder,locked in ((HERE,policy['source_sha256_lf']),(prior,policy['prior_source_sha256_lf'])):
        for name,wanted in locked.items():
            if hashlib.sha256((folder/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=wanted:
                raise ValueError('Source fingerprint differs: '+name)
    sys.path.insert(0,str(prior))
    import run_analysis as analysis
    import engine
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='development-calibration-') as directory:
        temp = Path(directory).resolve()
        verified = temp/'evidence_revalidation'
        analysis.run(repo,verified)
        paths = {'qwen15b':root/'corrected_qwen15b_coverage_official_scoring_v1/scores.json',
                 'llama3b':verified/'llama3b_scoring_recomputed/scores.json',
                 'qwen7b':verified/'qwen7b_scoring_recomputed/scores.json'}
        hashes = {m:analysis.hash_file(p) for m,p in paths.items()}
        models = {m:analysis.read_json(p) for m,p in paths.items()}
        assignment = calibration.folds(models['qwen15b'])
        results = {}
        for model,rows in sorted(models.items()):
            print('Calibrating development model:',model,flush=True)
            for scope in ['official_reference_compliance','tooleyes_relevance']+sorted({r['benchmark'] for r in rows}):
                original = [r for r in rows if r['panel']==scope or r['benchmark']==scope]
                eligible = [r for r in original if r['whole_output_scores'] is not None]
                prepared = [{'case_key':r['case_key'],'benchmark':r['benchmark'],'canonical_base_id':r['canonical_base_id'],
                             'score':r['whole_output_scores']['mean_token_nll'],'error':not r['official_score']['correct']} for r in eligible]
                result = calibration.crossfit(prepared,assignment)
                result.update({'original_rows':len(original),'whole_output_unavailable_case_keys':[r['case_key'] for r in original if r['whole_output_scores'] is None]})
                results[model+'/'+scope] = result
        report = ['# Exploratory development calibration', '',
                  'Five group-separated folds; fixed mean-token NLL feature, log1p transform, training-only standardization.',
                  'Ridge logistic regression has an unpenalized intercept and slope penalty 1 on the summed log loss.',
                  'No model/feature/hyperparameter selection or tuning occurs. Predictions estimate official error probability.',
                  'Scopes are fitted independently. Baseline is the smoothed training-fold error rate on identical validation rows.', '',
                  '| Model/scope | Original | OOF eligible | Brier | Baseline Brier | Log loss | Baseline log loss | ECE |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|']
        for key,r in results.items():
            a,b = r['logistic'],r['training_fold_constant_baseline']
            report.append(f'| {key} | {r["original_rows"]} | {r["oof_rows"]} | {a["brier_score"]} | {b["brier_score"]} | {a["log_loss_clipped_1e_minus_15"]} | {b["log_loss_clipped_1e_minus_15"]} | {a["ece_10_equal_width_bins"]} |')
        report += ['', 'Every validation group is excluded from its calibrator training; no in-sample calibration metric is reported.',
                   'Missing probability evidence, small training cohorts and one-class training folds remain unavailable.',
                   'Ten fixed equal-width bins describe reliability. ECE is sample- and bin-dependent; it is not a guarantee.',
                   'These retrospective selected-case diagnostics do not establish population calibration, routing thresholds or superiority.',
                   'Pooled reference calibration can reflect benchmark mixtures. Inspect independent benchmark results.',
                   'Model-specific eligible cohorts differ. Baseline comparisons are same-case within model, not controlled cross-model rankings.',
                   'No held-out access, inference, final calibrator fit, final protocol freeze or change to official outcomes occurs.']
        value = {'version':policy['version'],'policy':policy,'results':results,
                 'fold_assignment':[{'benchmark':b,'canonical_base_id':g,'fold':f} for (b,g),f in sorted(assignment.items())],
                 'held_out_access_enabled':False,'main_experiment_ready':False,'prior_files_modified':False}
        (temp/'calibration.json').write_text(engine.canonical(value)+'\n',encoding='utf-8')
        (temp/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
        for model,path in paths.items():
            if analysis.hash_file(path)!=hashes[model]:raise ValueError('Input changed during calibration')
        (temp/'provenance.json').write_text(engine.canonical({'input_score_sha256':hashes,'source_sha256_lf':policy['source_sha256_lf'],
             'prior_policy_sha256':analysis.POLICY_SHA,'network_requests':0,'held_out_access_enabled':False})+'\n',encoding='utf-8')
        engine.publish(temp,output)
    print('Calibration subtask complete:',output/'REPORT.md')
    return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,default=Path('.'))
    p.add_argument('--output',type=Path,default=Path(ROOT)/'development_calibration_v1')
    a=p.parse_args();run(a.repo_root,a.output)
