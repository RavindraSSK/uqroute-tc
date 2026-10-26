"""Verify existing corrected development evidence and compare three small models on CPU."""
from __future__ import annotations
import argparse
from collections import Counter
from itertools import combinations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import engine as e
HERE=Path(__file__).resolve().parent
POLICY_SHA='aa68f1523869665798b6092a9be14f835a0b352bf96f117df16084a81f4f7166'
PANELS=('official_reference_compliance','tooleyes_relevance')
ROOT='artifacts/local_development_audits'
QWEN='corrected_qwen15b_coverage_official_scoring_v1'
QI='corrected_qwen15b_coverage_import_217d4a47'
def read_json(path):return e.loads(e.regular(path))
def hash_file(path):return e.sha(e.regular(path))
def checked(path,expected,ledger):
    raw=e.regular(path)
    if e.sha(raw)!=expected:raise ValueError('Fingerprint differs: '+path.name)
    ledger[path]=expected
    return e.loads(raw)

def unique(rows):return e.index(rows)

def same_requests(q,l,model_id='meta-llama/Llama-3.2-3B-Instruct'):
    a,b=unique(q),unique(l)
    if len(a)!=69 or set(a)!=set(b):raise ValueError('Expected same 69 unique cases')
    if [r['case_key'] for r in q]!=[r['case_key'] for r in l]:raise ValueError('Request order differs')
    for k,x in a.items():
        y=b[k]
        if any(x[n]!=y[n] for n in ('benchmark','source_file','canonical_base_id')):raise ValueError('Request identity differs')
        if x['request']['model']!='Qwen/Qwen2.5-1.5B-Instruct' or y['request']['model']!=model_id:raise ValueError('Model differs')
        if {n:v for n,v in x['request'].items() if n!='model'}!={n:v for n,v in y['request'].items() if n!='model'}:raise ValueError('Prompts or request settings differ')

def paired_cohort(q,l,cfg):
    a,b=unique(q),unique(l)
    if set(a)!=set(b):raise ValueError('Outcome case sets differ')
    keys=sorted(a)
    for k in keys:
        if any(a[k][n]!=b[k][n] for n in ('benchmark','canonical_base_id','source_file','panel','reference_review_flags')):
            raise ValueError('Outcome lineage/flags differ')
    transitions=Counter()
    for k in keys:
        transitions[('correct' if a[k]['official_score']['correct'] else 'incorrect')+'_to_'+('correct' if b[k]['official_score']['correct'] else 'incorrect')]+=1
    def one(name,selected):
        return {'rows':len(selected),'case_keys':selected,
                'canonical_groups':len({a[k]['canonical_base_id'] for k in selected}),
                'first_model':e.one_measure([a[k] for k in selected],name,cfg,len(keys)),
                'second_model':e.one_measure([b[k] for k in selected],name,cfg,len(keys))}
    all_common=[k for k in keys if all(e.measured(r,loc) is not None for r in (a[k],b[k]) for loc in cfg['measures'].values())]
    return {'original_rows':len(keys),'case_keys':keys,
            'paired_correctness_transitions_first_to_second':dict(sorted(transitions.items())),
            'correctness_denominator_includes_unavailable_and_truncated':True,
            'per_measure_joint_eligible':{name:one(name,[k for k in keys if e.measured(a[k],loc) is not None and e.measured(b[k],loc) is not None]) for name,loc in cfg['measures'].items()},
            'all_measures_both_models_common':{'rows':len(all_common),'case_keys':all_common,'measures':{name:one(name,all_common) for name in cfg['measures']}},
            'limits':['Joint eligibility is nonrandom; it does not repair exclusions or represent the population.',
                      'Outcomes are model-specific reference/relevance labels on shared cases; no raw uncertainty-scale pooling.',
                      'No group independence, confidence interval or significance claim. Clean/perturbed causal pairing is not established.']}

def compare(q,l,cfg):
    return {'by_panel':{p:paired_cohort([r for r in q if r['panel']==p],[r for r in l if r['panel']==p],cfg) for p in PANELS},
            'by_benchmark':{b:paired_cohort([r for r in q if r['benchmark']==b],[r for r in l if r['benchmark']==b],cfg) for b in sorted({r['benchmark'] for r in q})}}

def summarize(analysis):
    return {p:{'rows':v['original_rows'],'correct':v['official_correct'],
               'available_metrics':{n:x['discrimination'] for n,x in v['available_case_analysis'].items()},
               'all_measures_common_rows':v['common_eligible_case_analysis']['rows']} for p,v in analysis['by_panel'].items()}


def joint_cohort(models,cfg):
    indexes={name:unique(rows) for name,rows in models.items()}
    names=sorted(indexes);base=indexes[names[0]];keys=sorted(base)
    if any(set(x)!=set(keys) for x in indexes.values()):raise ValueError('Joint case sets differ')
    for k in keys:
        for name in names:
            if any(indexes[name][k][f]!=base[k][f] for f in ('benchmark','canonical_base_id','source_file','panel','reference_review_flags')):raise ValueError('Joint lineage or flags differ')
    def one(measure,selected):
        return {'rows':len(selected),'case_keys':selected,
                'canonical_groups':len({base[k]['canonical_base_id'] for k in selected}),
                'models':{name:e.one_measure([indexes[name][k] for k in selected],measure,cfg,len(keys)) for name in names}}
    common=[k for k in keys if all(e.measured(indexes[name][k],loc) is not None for name in names for loc in cfg['measures'].values())]
    patterns=Counter(''.join('C' if indexes[name][k]['official_score']['correct'] else 'I' for name in names) for k in keys)
    return {'original_rows':len(keys),'model_order_for_outcome_patterns':names,'outcome_patterns_C_correct_I_incorrect':dict(sorted(patterns.items())),
            'per_measure_all_models_joint':{n:one(n,[k for k in keys if all(e.measured(indexes[name][k],loc) is not None for name in names)]) for n,loc in cfg['measures'].items()},
            'all_measures_all_models_common':{'rows':len(common),'case_keys':common,'measures':{n:one(n,common) for n in cfg['measures']}},
            'limits':['Same-case eligibility intersection, not representative sampling or causal clean/perturbed pairing.',
                      'Each model retains its own official outcomes; identical case sets do not imply identical error labels.',
                      'No oracle routing policy, confidence interval or significance test is inferred from these patterns.']}

def comparisons(models,cfg):
    pairs={first+'__'+second:{'first_model':first,'second_model':second,'comparison':compare(models[first],models[second],cfg)} for first,second in combinations(sorted(models),2)}
    joint={'by_panel':{p:joint_cohort({m:[r for r in rows if r['panel']==p] for m,rows in models.items()},cfg) for p in PANELS},
           'by_benchmark':{b:joint_cohort({m:[r for r in rows if r['benchmark']==b] for m,rows in models.items()},cfg) for b in sorted({r['benchmark'] for r in next(iter(models.values()))})}}
    return {'pairwise':pairs,'three_model_joint':joint}

def fmt(value):return 'undefined' if value is None else f'{value:.4f}'

def render_report(analyses,comparison):
    lines=['# Three-model corrected development uncertainty comparison','',
           'Selected development diagnostics only. Reference compliance and ToolEyes relevance are separate.',
           'No population, significance, model-superiority, routing-benefit or execution-success claims.','',
           '## Available cases per model','','| Model/panel | Correct/rows | Measure | Eligible | Error positives | AUROC | AP |','|---|---:|---|---:|---:|---:|---:|']
    for model,analysis in analyses.items():
        for panel,c in analysis['by_panel'].items():
            for n,m in c['available_case_analysis'].items():
                d=m['discrimination'];lines.append(f"| {model}/{panel} | {c['official_correct']}/{c['original_rows']} | {n} | {d['eligible_rows']} | {d['error_positive_rows']} | {fmt(d['auroc'])} | {fmt(d['average_precision'])} |")
    for label,key in [('Same measure, shared eligible cases across all models','per_measure_all_models_joint'),('All measures, shared eligible cases across all models','all_measures_all_models_common')]:
        lines+=['','## '+label,'','| Panel | Measure | Shared eligible | Model | Errors | AUROC | AP |','|---|---|---:|---|---:|---:|---:|']
        for panel,data in comparison['three_model_joint']['by_panel'].items():
            measures=data[key] if key=='per_measure_all_models_joint' else data[key]['measures']
            for n,m in measures.items():
                for model,v in m['models'].items():
                    d=v['discrimination'];lines.append(f"| {panel} | {n} | {m['rows']} | {model} | {d['error_positive_rows']} | {fmt(d['auroc'])} | {fmt(d['average_precision'])} |")
    lines+=['','## Interpretation limits','',
            '- Compare measures using the all-measure common cohort, and inspect per-benchmark results in the JSON files.',
            '- Missingness is nonrandom; shrinking to a shared cohort does not establish population performance.',
            '- Official outcome labels differ across models even on identical cases; AP also depends on error prevalence.',
            '- ToolEyes one-class AUROC/AP are undefined; 6/6 relevance does not show perfect error detection.',
            '- Truncated responses stay in correctness denominators but remain unavailable for probability metrics.',
            '- Explicit prompts/settings match; tokenizer rendering and inherited model sampling defaults can differ.',
            '- Risk curves accept complete exact-score tie blocks; zero-acceptance risk is undefined.',
            '- No calibration, group bootstrap, routing threshold, final freeze or held-out access is performed.',
            '- Pairwise model comparisons and three-model outcome patterns are descriptive, not an evaluated routing policy.']
    return '\n'.join(lines)+'\n'

def run(repo,output):
    for p in (repo,output):
        if any(x.is_symlink() for x in (p,*p.parents)):raise ValueError('Symlink path rejected')
    repo=repo.resolve();output=output.absolute();root=repo/ROOT
    if not output.resolve().is_relative_to(root) or output.resolve()==root:raise ValueError('Output must be child of local development artifacts')
    if output.exists():raise ValueError('Output exists; preserve it')
    cfg=checked(HERE/'policy.json',POLICY_SHA,{})
    for n,h in cfg['own_source_sha256_lf'].items():
        if e.sha(e.regular(HERE/n).replace(b'\r\n',b'\n'))!=h:raise ValueError('Analysis source differs: '+n)
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',cfg['baseline_commit'],'HEAD'],capture_output=True,check=True)
    ledger={}
    qpaths={'scores.json':root/QWEN/'scores.json','provenance.json':root/QWEN/'provenance.json',
            'prepared/requests.json':root/QI/'prepared/requests.json','prepared/manifest.json':root/QI/'prepared/manifest.json'}
    sources={root/QWEN,root/QI,root/'full_primary_export_v1',root/'full_primary_audit_v1'}
    for model in cfg['models'].values():sources.update({root/model['evidence'],root/model['scored']})
    for source in sources:
        if any(x.is_symlink() for x in (source,*source.parents)):raise ValueError('Symlink source')
        if output.resolve()==source or output.resolve() in source.parents or source in output.resolve().parents:raise ValueError('Output overlaps inputs')
    qdata={n:checked(p,cfg['qwen_input_sha256'][n],ledger) for n,p in qpaths.items()}
    models={'qwen15b':e.validate_rows(qdata['scores.json'],qdata['prepared/requests.json'],cfg)}
    for key,model in cfg['models'].items():
        folder=repo/'tools/development_audits'/model['folder']
        for n,h in model['source_sha256_lf'].items():
            if e.sha(e.regular(folder/n).replace(b'\r\n',b'\n'))!=h:raise ValueError('Scoring source differs: '+key+'/'+n)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='three-model-analysis-') as temp:
        temp=Path(temp).resolve()
        for key,model in cfg['models'].items():
            destination=temp/(key+'_scoring_recomputed')
            command=[sys.executable,str(repo/'tools/development_audits'/model['folder']/model['module']),
                     '--repo-root',str(repo),'--evidence-dir',str(root/model['evidence']),
                     '--bundle',str(root/'full_primary_export_v1'),'--audit-dir',str(root/'full_primary_audit_v1'),'--output',str(destination)]
            result=subprocess.run(command,capture_output=True,text=True)
            if result.returncode:raise ValueError('Evidence-bound scoring failed for '+key+': '+result.stderr[-1500:])
            for n in ('scores.json','summary.json'):
                p=root/model['scored']/n;raw=e.regular(p);ledger[p]=e.sha(raw)
                if e.canonical(e.loads(raw))!=e.canonical(read_json(destination/n)):raise ValueError('Existing '+key+' '+n+' differs from recomputation')
            for n in ('manifest.json','requests.json'):
                p=root/model['evidence']/'prepared'/n;ledger[p]=hash_file(p)
            requests=read_json(root/model['evidence']/'prepared/requests.json')
            same_requests(qdata['prepared/requests.json'],requests,model['model_id'])
            models[key]=e.validate_rows(read_json(destination/'scores.json'),requests,cfg)
        analyses={key:e.analyze(sorted(rows,key=lambda r:r['case_key']),cfg) for key,rows in sorted(models.items())}
        comparison=comparisons(models,cfg)
        summary={'version':cfg['version'],'scope':cfg['scope'],
                 'models':{key:{'by_panel':summarize(analysis),
                     'evidence_status_counts':dict(Counter(r['evidence_status'] for r in models[key]))} for key,analysis in analyses.items()},
                 'three_model_shared_cohorts':{p:{'original_rows':data['original_rows'],
                     'per_measure_joint_rows':{n:m['rows'] for n,m in data['per_measure_all_models_joint'].items()},
                     'all_measures_joint_rows':data['all_measures_all_models_common']['rows'],
                     'outcome_pattern_model_order':data['model_order_for_outcome_patterns'],
                     'outcome_patterns':data['outcome_patterns_C_correct_I_incorrect']} for p,data in comparison['three_model_joint']['by_panel'].items()},
                 'held_out_access_enabled':False,'main_experiment_ready':False,'prior_files_modified':False,
                 'calibration':'not_fitted','routing_threshold':'not_selected','group_bootstrap':'not_performed',
                 'limits':['Selected development diagnostics, not population estimates or final protocol freeze.',
                           'Reference compliance and deterministic ToolEyes relevance are separate proxies, not tool execution success.',
                           'No independence assumption, confidence interval, statistical significance, superiority or routing-benefit claim.',
                           'Identical explicit requests do not imply identical tokenizer rendering or inherited sampling defaults.']}
        for p,h in ledger.items():
            if hash_file(p)!=h:raise ValueError('Input changed during analysis')
        provenance={'baseline_commit':cfg['baseline_commit'],'policy_sha256':POLICY_SHA,
                    'source_sha256_lf':{n:e.sha(e.regular(HERE/n).replace(b'\r\n',b'\n')) for n in ('run_analysis.py','engine.py','metrics.py')},
                    'input_sha256':{p.relative_to(repo).as_posix():h for p,h in ledger.items()},
                    'fresh_scoring_provenance':{key:key+'_scoring_recomputed/provenance.json' for key in cfg['models']},
                    'verification':'Both evidence-bound scorers rerun; old scores/summary compared structurally and not rewritten.',
                    'network_requests':0,'raw_benchmark_or_split_opened':False,'held_out_access_enabled':False}
        values={'summary.json':summary,'matched_comparison.json':comparison,'provenance.json':provenance,
                **{key+'_analysis.json':analysis for key,analysis in analyses.items()}}
        for n,v in values.items():(temp/n).write_text(e.canonical(v)+'\n',encoding='utf-8')
        (temp/'REPORT.md').write_text(render_report(analyses,comparison),encoding='utf-8')
        e.publish(temp,output)
    compact={'models':{key:{p:{'correct':v['official_correct'],'rows':v['original_rows'],
                  'whole_output_eligible':v['available_case_analysis']['mean_token_nll']['discrimination']['eligible_rows'],
                  'meaningful_token_eligible':v['available_case_analysis']['meaningful_mean_token_nll']['discrimination']['eligible_rows'],
                  'mean_token_auroc':v['available_case_analysis']['mean_token_nll']['discrimination']['auroc']} for p,v in analysis['by_panel'].items()} for key,analysis in analyses.items()},
             'three_model_shared_cohorts':summary['three_model_shared_cohorts'],
             'held_out_access_enabled':False,'prior_files_modified':False,'main_experiment_ready':False}
    print(json.dumps(compact,indent=2));print('Report:',output/'REPORT.md')
    return summary

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo-root',type=Path,default=Path('.'))
    parser.add_argument('--output',type=Path,default=Path(ROOT)/'three_model_uncertainty_v1');a=parser.parse_args()
    try:run(a.repo_root,a.output)
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as exc:raise SystemExit('Analysis stopped; preserve existing evidence: '+str(exc)) from None
if __name__=='__main__':main()
