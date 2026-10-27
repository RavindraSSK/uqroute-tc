"""Revalidate three full-development runs; compare saved uncertainty and paired outcomes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import pairs
HERE=Path(__file__).resolve().parent
ROOT='artifacts/local_development_audits'


def same_requests(a,b,second_model='meta-llama/Llama-3.2-3B-Instruct'):
    if len(a)!=1728 or len(b)!=1728 or len({r['case_key'] for r in a})!=1728:
        raise ValueError('Expected two full-development selections')
    if [r['case_key'] for r in a]!=[r['case_key'] for r in b]:raise ValueError('Case order differs')
    for x,y in zip(a,b):
        if any(x[f]!=y[f] for f in ('benchmark','canonical_base_id','source_file','messages_sha256','tools_sha256')):
            raise ValueError('Prompt lineage differs')
        if x['request']['model']!='Qwen/Qwen2.5-1.5B-Instruct' or y['request']['model']!=second_model:
            raise ValueError('Model identity differs')
        if {k:v for k,v in x['request'].items() if k!='model'}!={k:v for k,v in y['request'].items() if k!='model'}:
            raise ValueError('Explicit request settings differ')


def joint_summary(matched):
    return {panel:{'original_rows':value['original_rows'],
                   'shared_by_measure':{name:cohort['rows'] for name,cohort in value['per_measure_all_models_joint'].items()},
                   'all_models_all_measures':value['all_measures_all_models_common']['rows'],
                   'outcome_pattern_model_order':value['model_order_for_outcome_patterns'],
                   'outcome_patterns':value['outcome_patterns_C_correct_I_incorrect']}
            for panel,value in matched['three_model_joint']['by_panel'].items()}


def run(repo,output):
    for p in (repo,output):
        if any(x.is_symlink() for x in (p,*p.parents)):raise ValueError('Symlink path rejected')
    repo=repo.resolve();output=output.absolute();root=repo/ROOT
    if output.exists() or not output.resolve().is_relative_to(root) or output.resolve()==root:raise ValueError('Fresh output under development artifacts required')
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor','d734311','HEAD'],check=True)
    policy=json.loads((HERE/'policy.json').read_text())
    for name,wanted in policy['source_sha256_lf'].items():
        p=repo/name
        if any(x.is_symlink() for x in (p,*p.parents)) or hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=wanted:
            raise ValueError('Source fingerprint differs: '+name)
    prior=repo/'tools/development_audits/three_model_uncertainty_v1'
    sys.path.insert(0,str(prior))
    import engine
    import run_analysis as comparison
    cfg=engine.loads(engine.regular(prior/'policy.json'))
    output.parent.mkdir(parents=True,exist_ok=True)
    hashes={};models={};requests={};analyses={};paired={};paired_summaries={}
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='full-development-comparison-') as directory:
        temp=Path(directory).resolve()
        for model,settings in policy['models'].items():
            print('Revalidating full-development scoring:',model,flush=True)
            evidence=root/settings['evidence'];previous=root/settings['scored'];fresh=temp/(model+'_scoring_recomputed')
            subprocess.run([sys.executable,str(repo/settings['scorer']),'--repo-root',str(repo),'--evidence-dir',str(evidence),'--bundle',str(root/'full_primary_export_v1'),'--audit-dir',str(root/'full_primary_audit_v1'),'--output',str(fresh)],check=True,stdout=subprocess.DEVNULL)
            for name in ('scores.json','summary.json'):
                p=previous/name;raw=engine.regular(p);hashes[p]=engine.sha(raw)
                if engine.loads(raw)!=engine.loads(engine.regular(fresh/name)):raise ValueError('Existing scoring differs: '+model+'/'+name)
            models[model]=engine.loads(engine.regular(fresh/'scores.json'))
            p=evidence/'prepared/requests.json';raw=engine.regular(p);hashes[p]=engine.sha(raw);requests[model]=engine.loads(raw)
            analyses[model]=engine.analyze(models[model],cfg)
            analyses[model]['version']=policy['version'];analyses[model]['scope']='all-1728-constructed-primary-development-candidates-only'
            analyses[model]['limits']=[x for x in analyses[model]['limits'] if not x.startswith('Retrospective development diagnostics on one hash-selected')]
            analyses[model]['limits'].append('All constructed development candidates; 26 blocked prompts have no outcomes. Earlier coverage responses are not pooled.')
            paired[model]=pairs.paired(models[model])
            if len(paired[model])!=1588:raise ValueError('Constructed pairing differs')
            paired_summaries[model]={'by_panel':{p:pairs.summarize([r for r in paired[model] if r['panel']==p]) for p in ('official_reference_compliance','tooleyes_relevance')},
                'by_benchmark':{b:pairs.summarize([r for r in paired[model] if r['benchmark']==b]) for b in sorted({r['benchmark'] for r in models[model]})},
                'by_source_and_panel':{s:{p:pairs.summarize([r for r in paired[model] if r['source_file']==s and r['panel']==p]) for p in ('official_reference_compliance','tooleyes_relevance')} for s in sorted({r['source_file'] for r in paired[model]})}}
        same_requests(requests['qwen15b'],requests['llama3b'])
        same_requests(requests['qwen15b'],requests['qwen7b'],'Qwen/Qwen2.5-7B-Instruct')
        matched=comparison.comparisons(models,cfg)
        summary={'version':policy['version'],'rows_per_model':1728,'pairs_per_model':1588,
                 'panels':{m:{p:{'rows':c['original_rows'],'correct':c['official_correct'],'available_case_metrics':{n:v['discrimination'] for n,v in c['available_case_analysis'].items()},'all_measure_common_rows':c['common_eligible_case_analysis']['rows']} for p,c in a['by_panel'].items()} for m,a in analyses.items()},
                 'matched_panel_cohorts':joint_summary(matched),
                 'held_out_access_enabled':False,'main_experiment_ready':False,'prior_files_modified':False}
        report=['# Three-model full-development uncertainty comparison','',
                'Development only; reference compliance and ToolEyes name relevance remain separate.',
                'Metric outcomes are model-specific. Shared cases do not imply shared error labels.', '',
                '| Panel | Shared cohort | Measure | Model | Eligible | Errors | AUROC | AP |','|---|---|---|---|---:|---:|---:|---:|']
        for panel,c in matched['three_model_joint']['by_panel'].items():
            for cohort,measures in [('same_measure',c['per_measure_all_models_joint']),('all_models_all_measures',c['all_measures_all_models_common']['measures'])]:
                for name,value in measures.items():
                    for model,entry in value['models'].items():
                        d=entry['discrimination'];report.append(f'| {panel} | {cohort} | {name} | {model} | {d["eligible_rows"]} | {d["error_positive_rows"]} | {d["auroc"]} | {d["average_precision"]} |')
        report+=['','Inspect per-benchmark matched results and all-measure common cohorts before comparing measures.',
                 'Missingness is nonrandom; intersections do not repair format exclusions or establish population-wide applicability.',
                 'AP depends on model-specific error prevalence. Empty and one-class metrics retain explicit undefined reasons.',
                 'Clean responses are reused across variants. Paired correctness changes are descriptive reference/relevance changes, not independent trials or causal degradation.',
                 'Reference flags remain attached and never exclude cases. Model-specific paired summaries report pair and equal-group weights separately.',
                 'Explicit request bodies match except model ID; tokenizer rendering, inherited sampling defaults and output length can differ.',
                 'No bootstrap, calibration refitting, uncertainty threshold, routing benefit or held-out evaluation is established. No model-superiority or oracle-routing claim follows from outcome patterns.']
        values={'summary.json':summary,'matched_comparison.json':matched,'paired_summaries.json':paired_summaries,
                **{m+'_analysis.json':a for m,a in analyses.items()},**{m+'_paired_rows.json':v for m,v in paired.items()},
                'provenance.json':{'policy':policy,'input_sha256':{p.relative_to(repo).as_posix():h for p,h in hashes.items()},'network_requests':0,'held_out_access_enabled':False}}
        for name,value in values.items():(temp/name).write_text(engine.canonical(value)+'\n',encoding='utf-8')
        (temp/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
        for p,h in hashes.items():
            if engine.sha(engine.regular(p))!=h:raise ValueError('Input changed during analysis')
        engine.publish(temp,output)
    compact={'models':{m:{p:{'rows':c['rows'],'correct':c['correct'],'mean_nll_auroc':c['available_case_metrics']['mean_token_nll']['auroc'],'mean_nll_eligible':c['available_case_metrics']['mean_token_nll']['eligible_rows'],'meaningful_eligible':c['available_case_metrics']['meaningful_mean_token_nll']['eligible_rows']} for p,c in panels.items()} for m,panels in summary['panels'].items()},'rows_per_model':1728,'pairs_per_model':1588,'shared_cohorts':summary['matched_panel_cohorts'],'held_out_access_enabled':False,'main_experiment_ready':False,'prior_files_modified':False}
    print(json.dumps(compact,indent=2));print('Report:',output/'REPORT.md')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo-root',type=Path,default=Path('.'));parser.add_argument('--output',type=Path,default=Path(ROOT)/'three_model_full_development_v1');a=parser.parse_args();run(a.repo_root,a.output)
