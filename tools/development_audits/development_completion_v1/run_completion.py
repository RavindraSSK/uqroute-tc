"""Fresh development-only monotonic calibration and paired intervals."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import calibration
import paired_intervals

HERE=Path(__file__).resolve().parent
ROOT=Path('artifacts/local_development_audits')


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def run(repo,output):
    repo=repo.absolute();output=output.absolute()
    if any(p.is_symlink() for v in (repo,output) for p in (v,*v.parents)):raise ValueError('Symlink path rejected')
    repo=repo.resolve();output=output.resolve();root=repo/ROOT
    if output.exists() or not output.is_relative_to(root) or output==root:raise ValueError('Fresh development output required')
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor','ff277c8','HEAD'],check=True)
    policy=json.loads((HERE/'policy.json').read_text())
    for name,wanted in policy['source_sha256_lf'].items():
        path=repo/name
        if any(p.is_symlink() for p in (path,*path.parents)) or hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=wanted:raise ValueError('Source differs: '+name)
    core=repo/'tools/development_audits/three_model_uncertainty_v1'
    sys.path.insert(0,str(core));import engine
    stats=load_module('_completion_stats',repo/'tools/development_audits/development_statistics_v1/statistics.py')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='development-completion-') as folder:
        temp=Path(folder).resolve();fresh=temp/'evidence_revalidation'
        print('Revalidating all three full-development scorers and comparisons...',flush=True)
        subprocess.run([sys.executable,str(repo/'tools/development_audits/three_model_full_development_v1/run_comparison.py'),'--repo-root',str(repo),'--output',str(fresh)],check=True,stdout=subprocess.DEVNULL)
        ledger={}
        for name in ('summary.json','matched_comparison.json','paired_summaries.json'):
            path=root/'three_model_full_development_v1'/name;raw=engine.regular(path);ledger[path]=engine.sha(raw)
            if engine.loads(raw)!=engine.loads(engine.regular(fresh/name)):raise ValueError('Saved comparison differs')
        models={m:engine.loads(engine.regular(fresh/(m+'_scoring_recomputed/scores.json'))) for m in policy['models']}
        assignment=calibration.folds(models['qwen15b'])
        scopes=policy['scopes'];calibrated={};intervals={}
        pairs={m:engine.loads(engine.regular(fresh/(m+'_paired_rows.json'))) for m in models}
        if any(len(v)!=1588 for v in pairs.values()):raise ValueError('Expected 1588 pairs/model')
        for scope in scopes:
            print('Calibrating and bootstrapping:',scope,flush=True)
            for model,rows in models.items():
                selected=[r for r in rows if r['panel']==scope or r['benchmark']==scope]
                eligible=[{'case_key':r['case_key'],'benchmark':r['benchmark'],'canonical_base_id':r['canonical_base_id'],'score':r['whole_output_scores']['mean_token_nll'],'error':not r['official_score']['correct']} for r in selected if r['whole_output_scores'] is not None]
                result=calibration.crossfit(eligible,assignment)
                result['original_rows']=len(selected);result['method']='nonnegative_slope_ridge_logistic_error_mapping'
                calibrated[model+'/'+scope]=result
            subset={m:[r for r in v if r['panel']==scope or r['benchmark']==scope] for m,v in pairs.items()}
            intervals[scope]=paired_intervals.bootstrap(paired_intervals.units(subset),sorted(models),stats.interval,stats.stable_seed('paired-completion/'+scope),policy['bootstrap_replicates'])
        for path,wanted in ledger.items():
            if engine.sha(engine.regular(path))!=wanted:raise ValueError('Input changed')
        summary={'version':policy['version'],'rows_per_model':1728,'pairs_per_model':1588,'calibration_scopes':len(calibrated),'paired_interval_scopes':len(intervals),'bootstrap_replicates':policy['bootstrap_replicates'],'held_out_access_enabled':False,'main_experiment_ready':False,'prior_files_modified':False,'inference_requests':0}
        report=['# Development completion diagnostics','','New retrospective development analysis; not a final freeze or Task 3 completion.','Error probability is nondecreasing with NLL; compliance probability is nonincreasing.','Five group-separated folds, training-only scaling, ridge slope penalty 1; boundary slope zero refits the intercept at the training error fraction.','Previous unconstrained diagnostics remain unchanged. No final all-development mapping is fitted.','','| Model | OOF reference rows | Brier | Baseline Brier | Log loss |','|---|---:|---:|---:|---:|']
        for model in models:
            c=calibrated[model+'/official_reference_compliance'];report.append(f"| {model} | {c['oof_rows']} | {c['logistic']['brier_score']} | {c['training_fold_constant_baseline']['brier_score']} | {c['logistic']['log_loss_clipped_1e_minus_15']} |")
        report+=['','## Reference-panel paired changes','','Changes are perturbed minus clean reference compliance. Negative values indicate lower compliance on perturbed variants.','Groups are resampled within benchmark, retaining all pairs and all models; repeated clean anchors are dependent.','Pair-weighted and equal-group estimates are separate. Pairwise model differences use the same draws.','','| Metric | Point | 95% interval or reason |','|---|---:|---|']
        for key,value in intervals['official_reference_compliance']['metrics'].items():report.append(f"| {key} | {value['point']} | {value['interval_95_percentile'] or value['interval_unavailable_reason']} |")
        report+=['','Intervals: 2000 draws, percentile 95%, minimum 10 groups, minimum 90% valid draws; exploratory, no multiplicity correction.','ToolEyes panel and benchmark are duplicate views, not independent evidence.','No causal, executable-success, model-superiority or deployment-confidence guarantee.','Repeated sampling, sensitivity extension, final protocol decisions, held-out evaluation and Task 4 remain unresolved.']
        for name,value in {'summary.json':summary,'calibration.json':calibrated,'paired_intervals.json':intervals,'provenance.json':{'policy':policy,'input_sha256':{p.relative_to(repo).as_posix():h for p,h in ledger.items()},'held_out_access_enabled':False}}.items():(temp/name).write_text(engine.canonical(value)+'\n',encoding='utf-8')
        (temp/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
        engine.publish(temp,output)
    print(json.dumps(summary,indent=2));print('Report:',output/'REPORT.md')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,default=Path('.'))
    parser.add_argument('--output',type=Path,default=ROOT/'development_completion_v1')
    args=parser.parse_args();run(args.repo_root,args.output)
