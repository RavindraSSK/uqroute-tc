"""One CPU run for full-development intervals, calibration, categories and failure bands."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import reporting
HERE=Path(__file__).resolve().parent
ROOT='artifacts/local_development_audits'


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def run(repo,output):
    for p in (repo,output):
        if any(x.is_symlink() for x in (p,*p.parents)):raise ValueError('Symlink path rejected')
    repo=repo.resolve();output=output.absolute();root=repo/ROOT
    if output.exists() or not output.resolve().is_relative_to(root) or output.resolve()==root:raise ValueError('Fresh development output required')
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor','d0fe407','HEAD'],check=True)
    policy=json.loads((HERE/'policy.json').read_text())
    for name,wanted in policy['source_sha256_lf'].items():
        p=repo/name
        if any(x.is_symlink() for x in (p,*p.parents)) or hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=wanted:raise ValueError('Source fingerprint differs: '+name)
    previous=repo/'tools/development_audits/three_model_uncertainty_v1'
    sys.path.insert(0,str(previous));import engine;import metrics
    cfg=engine.loads(engine.regular(previous/'policy.json'))
    stat_folder=repo/'tools/development_audits/development_statistics_v1'
    statistics=module('_full_report_cluster',stat_folder/'statistics.py')
    graphics=module('_full_report_graphics',stat_folder/'run_statistics.py')
    calibration=module('_full_report_calibration',repo/'tools/development_audits/development_calibration_v1/calibration.py')
    categories=module('_full_report_categories',repo/'tools/development_audits/development_categories_v1/categories.py')
    full_policy=engine.loads(engine.regular(repo/'tools/development_audits/three_model_full_development_v1/policy.json'))
    sample_path=root/'full_primary_export_v1/samples.jsonl';sample_raw=engine.regular(sample_path)
    if engine.sha(sample_raw)!=policy['development_samples_sha256']:raise ValueError('Development samples differ')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='full-development-reporting-') as directory:
        temp=Path(directory).resolve();fresh=temp/'three_model_revalidation'
        print('Revalidating all three evidence-bound full-development analyses...',flush=True)
        subprocess.run([sys.executable,str(repo/'tools/development_audits/three_model_full_development_v1/run_comparison.py'),'--repo-root',str(repo),'--output',str(fresh)],check=True,stdout=subprocess.DEVNULL)
        old=root/'three_model_full_development_v1';ledger={}
        for name in ('summary.json','matched_comparison.json','paired_summaries.json'):
            raw=engine.regular(old/name);ledger[old/name]=engine.sha(raw)
            if engine.loads(raw)!=engine.loads(engine.regular(fresh/name)):raise ValueError('Existing three-model analysis differs')
        models={m:engine.loads(engine.regular(fresh/(m+'_scoring_recomputed/scores.json'))) for m in full_policy['models']}
        tax=reporting.taxonomy([engine.loads(line) for line in sample_raw.splitlines() if line.strip()],models,categories.metadata)
        assignment=calibration.folds(models['qwen15b']);calibrated={};bands={};category_results={}
        for model,rows in models.items():
            print('Calibration, categories and failure bands:',model,flush=True)
            for scope in ['official_reference_compliance','tooleyes_relevance']+sorted({r['benchmark'] for r in rows}):
                subset=[r for r in rows if r['panel']==scope or r['benchmark']==scope]
                train=[{'case_key':r['case_key'],'benchmark':r['benchmark'],'canonical_base_id':r['canonical_base_id'],'score':r['whole_output_scores']['mean_token_nll'],'error':not r['official_score']['correct']} for r in subset if r['whole_output_scores'] is not None]
                value=calibration.crossfit(train,assignment)
                value['original_rows']=len(subset)
                value['evidence_unavailable_case_keys']=[r['case_key'] for r in subset if r['whole_output_scores'] is None]
                calibrated[model+'/'+scope]=value
                bands[model+'/'+scope]={'calibrated_oof_band':reporting.calibrated_band(value)}
                if scope not in ('official_reference_compliance','tooleyes_relevance'):
                    bands[model+'/'+scope]['low_uncertainty_band']=reporting.low_uncertainty_band(subset)
            for kind in ('clean','observation','action','reward'):
                subset=[r for r in rows if tax[r['case_key']]['category']==kind]
                a=engine.analyze(subset,cfg);a['scope']='constructed-full-development-category-diagnostics';a['version']=policy['version']
                a['limits']=[x for x in a['limits'] if not x.startswith('Retrospective development diagnostics on one hash-selected')]
                a['limits'].append('Descriptive full-development category subset; benchmark and group mixture differ. Reward membership is not preference success.')
                category_results[model+'/'+kind]=a
        intervals={};plot_count=0
        scopes=['official_reference_compliance','tooleyes_relevance']+sorted({r['benchmark'] for r in models['qwen15b']})
        for scope in scopes:
            for cohort in ('whole_output_shared','all_measures_shared'):
                names=['mean_token_nll'] if cohort=='whole_output_shared' else list(cfg['measures'])
                selected,total=reporting.common_rows(models,names,cfg,engine.measured,scope)
                for measure in names:
                    label=scope+'/'+cohort+'/'+measure
                    print('Bootstrap:',label,'rows:',len(selected),flush=True)
                    visits=[0]
                    def evaluate(draw):
                        visits[0]+=1
                        if visits[0]%500==0:print('  Bootstrap metric evaluations:',visits[0],flush=True)
                        return graphics.evaluate(draw,measure,metrics)
                    result=statistics.bootstrap(selected,evaluate,policy['replicates'],statistics.stable_seed('full-development/'+scope+'/'+cohort))
                    curves={m:metrics.risk_coverage([r['models'][m]['error'] for r in selected],[r['models'][m][measure] for r in selected],total)['points'] for m in models}
                    intervals[label]={'original_rows':total,'shared_eligible_rows':len(selected),'case_keys':[r['case_key'] for r in selected],'metrics':result,'risk_coverage':curves}
                    (temp/(label.replace('/','__')+'.svg')).write_text(graphics.svg(curves,label),encoding='utf-8');plot_count+=1
        index={m:{r['case_key']:r for r in rows} for m,rows in models.items()};failures=[]
        for label,value in bands.items():
            model,scope=label.split('/',1)
            for kind,band in value.items():
                for key in band['failure_case_keys']:
                    row=index[model][key]
                    failures.append({'model':model,'scope':scope,'band':kind,'case_key':key,'benchmark':row['benchmark'],'canonical_base_id':row['canonical_base_id'],'source_file':row['source_file'],'released_category':tax[key]['category'],'official_score':row['official_score'],'reference_review_flags':row['reference_review_flags'],'evidence_status':row['evidence_status']})
        summary={'version':policy['version'],'rows_per_model':1728,'bootstrap_entries':len(intervals),'svg_plots':plot_count,'bootstrap_replicates':policy['replicates'],'calibration_scopes':len(calibrated),'category_scopes':len(category_results),'released_category_counts':dict(Counter(v['category'] for v in tax.values())),
                 'failure_catalogue_entries':len(failures),'failure_catalogue_unique_model_cases':len({(r['model'],r['case_key']) for r in failures}),
                 'held_out_access_enabled':False,'main_experiment_ready':False,'prior_files_modified':False}
        report=['# Full-development statistical and diagnostic reporting','',
                'Retrospective development diagnostics only. No final protocol freeze, held-out access or inference.',
                'Bootstrap: 2000 draws, canonical groups resampled within benchmark; same cohort draws across models/measures.',
                'Case-weighted metrics; 95% percentile intervals, withheld below 10 groups or 90% valid draws. No multiplicity or superiority claim.',
                'Calibration: fixed five group-separated folds, training-only scaling, ridge logistic error mapping and smoothed training-fold constant baseline.',
                'Failure bands: lowest mean-NLL 20% target per model/benchmark with full boundary ties; OOF estimated compliance >=0.9 reported separately.',
                'Bands are retrospective descriptive choices, not validated confidence guarantees or deployment thresholds. Catalogue rows overlap; use unique model/case counts.', '',
                '## Reference panel mean-token AUROC intervals','',
                '| Metric | Point | 95% interval or reason |','|---|---:|---|']
        for key,value in intervals['official_reference_compliance/whole_output_shared/mean_token_nll']['metrics'].items():
            if key.endswith('/auroc'):report.append(f'| {key} | {value["point"]} | {value["interval_95_percentile"] or value["interval_unavailable_reason"]} |')
        report+=['','## Out-of-fold reference calibration','','| Model | OOF rows | Brier | Baseline Brier | Log loss | Baseline log loss | ECE |','|---|---:|---:|---:|---:|---:|---:|']
        for model in models:
            c=calibrated[model+'/official_reference_compliance'];a=c['logistic'];b=c['training_fold_constant_baseline']
            report.append(f'| {model} | {c["oof_rows"]} | {a["brier_score"]} | {b["brier_score"]} | {a["log_loss_clipped_1e_minus_15"]} | {b["log_loss_clipped_1e_minus_15"]} | {a["ece_10_equal_width_bins"]} |')
        report+=['','Category results remain separated by panel and benchmark in category_results.json. Reward is released metadata, not measured preference success.',
                 'Reference flags never relabel or exclude outcomes. Repeated clean/perturbed variants remain dependent; no causal drop is inferred.',
                 'SVGs show discrete exact-tie-block points at original-panel coverage, without interpolated lines, origin risk or bootstrap bands.',
                 'Compare measures on all-measure intersections, inspect benchmark results, and retain unavailable cases in original denominators.',
                 'Bootstrap assumptions and calibration estimates condition on observed development groups. Full applicability and held-out performance are not established.',
                 'This package does not supply paired-change confidence intervals, simultaneous bands, or a final semantic adjudication of the catalogue.']
        values={'summary.json':summary,'bootstrap.json':intervals,'calibration.json':calibrated,'category_results.json':category_results,'failure_bands.json':bands,'failure_catalogue.json':failures,'taxonomy.json':tax,
                'provenance.json':{'policy':policy,'prior_analysis_sha256':{p.relative_to(repo).as_posix():h for p,h in ledger.items()},'network_requests':0,'held_out_access_enabled':False}}
        for name,value in values.items():(temp/name).write_text(engine.canonical(value)+'\n',encoding='utf-8')
        (temp/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
        if engine.sha(engine.regular(sample_path))!=policy['development_samples_sha256']:raise ValueError('Samples changed')
        for p,h in ledger.items():
            if engine.sha(engine.regular(p))!=h:raise ValueError('Prior analysis changed')
        engine.publish(temp,output)
    print(json.dumps(summary,indent=2));print('Review:',output/'REPORT.md')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo-root',type=Path,default=Path('.'));p.add_argument('--output',type=Path,default=Path(ROOT)/'full_development_reporting_v1');a=p.parse_args();run(a.repo_root,a.output)
