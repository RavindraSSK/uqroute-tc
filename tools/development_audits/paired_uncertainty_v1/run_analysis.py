"""One CPU subtask: verify saved evidence, recompute Llama scoring and compare models."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import engine as e

HERE=Path(__file__).resolve().parent
POLICY_SHA='ab402f69136018eaa10fb75025eb22090fc429451cdb10bcc7e4a0c4ae089a92'
PANELS=('official_reference_compliance','tooleyes_relevance')
ROOT='artifacts/local_development_audits'
QWEN='corrected_qwen15b_coverage_official_scoring_v1'
LLAMA='corrected_llama3b_coverage_official_scoring_v1'
QI='corrected_qwen15b_coverage_import_217d4a47'
LI='corrected_llama3b_coverage_import_08f32900'

def read_json(path):return e.loads(e.regular(path))
def hash_file(path):return e.sha(e.regular(path))
def checked(path,expected,ledger):
    raw=e.regular(path)
    if e.sha(raw)!=expected:raise ValueError('Fingerprint differs: '+path.name)
    ledger[path]=expected
    return e.loads(raw)

def unique(rows):return e.index(rows)

def same_requests(q,l):
    a,b=unique(q),unique(l)
    if len(a)!=69 or set(a)!=set(b):raise ValueError('Expected same 69 unique cases')
    if [r['case_key'] for r in q]!=[r['case_key'] for r in l]:raise ValueError('Request order differs')
    for k,x in a.items():
        y=b[k]
        if any(x[n]!=y[n] for n in ('benchmark','source_file','canonical_base_id')):raise ValueError('Request identity differs')
        if x['request']['model']!='Qwen/Qwen2.5-1.5B-Instruct' or y['request']['model']!='meta-llama/Llama-3.2-3B-Instruct':raise ValueError('Model differs')
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
                'qwen':e.one_measure([a[k] for k in selected],name,cfg,len(keys)),
                'llama':e.one_measure([b[k] for k in selected],name,cfg,len(keys))}
    all_common=[k for k in keys if all(e.measured(r,loc) is not None for r in (a[k],b[k]) for loc in cfg['measures'].values())]
    return {'original_rows':len(keys),'case_keys':keys,
            'paired_correctness_transitions_qwen_to_llama':dict(sorted(transitions.items())),
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

def run(repo,output):
    for p in (repo,output):
        if any(x.is_symlink() for x in (p,*p.parents)):raise ValueError('Symlink path rejected')
    repo=repo.resolve();output=output.absolute();root=repo/ROOT
    if not output.resolve().is_relative_to(root) or output.resolve()==root:raise ValueError('Output must be child of local development artifacts')
    if output.exists():raise ValueError('Output exists; preserve it')
    cfg=checked(HERE/'policy.json',POLICY_SHA,{})
    for n,h in cfg['own_source_sha256_lf'].items():
        if e.sha(e.regular(HERE/n).replace(b'\r\n',b'\n'))!=h:raise ValueError('Analysis source changed: '+n)
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',cfg['baseline_commit'],'HEAD'],capture_output=True,check=True)
    ledger={}
    paths={'scores.json':root/QWEN/'scores.json','provenance.json':root/QWEN/'provenance.json',
           'prepared/requests.json':root/QI/'prepared/requests.json','prepared/manifest.json':root/QI/'prepared/manifest.json'}
    for source in (root/QWEN,root/LLAMA,root/QI,root/LI,root/'full_primary_export_v1',root/'full_primary_audit_v1'):
        if any(x.is_symlink() for x in (source,*source.parents)):raise ValueError('Symlink source rejected')
        if output.resolve()==source or output.resolve() in source.parents or source in output.resolve().parents:raise ValueError('Output overlaps input')
    qdata={n:checked(p,cfg['qwen_input_sha256'][n],ledger) for n,p in paths.items()}
    q=e.validate_rows(qdata['scores.json'],qdata['prepared/requests.json'],cfg)
    scorer=repo/'tools/development_audits/llama_coverage_scoring_v1'
    for n,h in cfg['llama_scoring_source_sha256_lf'].items():
        if e.sha(e.regular(scorer/n).replace(b'\r\n',b'\n'))!=h:raise ValueError('Llama scoring source differs: '+n)
    # A full fresh recomputation validates Llama policy-bound archive and development lineage.
    # Existing Llama scores/provenance are opened only after that verification.
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='paired-analysis-') as temp:
        temp=Path(temp).resolve();recomputed=temp/'llama_scoring_recomputed'
        command=[sys.executable,str(scorer/'score_llama.py'),'--repo-root',str(repo),
                 '--evidence-dir',str(root/LI),'--bundle',str(root/'full_primary_export_v1'),
                 '--audit-dir',str(root/'full_primary_audit_v1'),'--output',str(recomputed)]
        result=subprocess.run(command,capture_output=True,text=True)
        if result.returncode:raise ValueError('Llama evidence-bound recomputation failed: '+result.stderr[-1500:])
        recomputed_rows=read_json(recomputed/'scores.json')
        for name in ('scores.json','summary.json'):
            original=root/LLAMA/name
            raw=e.regular(original);ledger[original]=e.sha(raw)
            if e.canonical(e.loads(raw))!=e.canonical(read_json(recomputed/name)):raise ValueError('Existing Llama '+name+' differs from fresh scoring')
        for name in ('manifest.json','requests.json'):
            p=root/LI/'prepared'/name;ledger[p]=hash_file(p)
        lr=read_json(root/LI/'prepared/requests.json')
        same_requests(qdata['prepared/requests.json'],lr)
        l=e.validate_rows(recomputed_rows,lr,cfg)
        qa=e.analyze(sorted(q,key=lambda r:r['case_key']),cfg)
        la=e.analyze(sorted(l,key=lambda r:r['case_key']),cfg)
        paired=compare(q,l,cfg)
        compact={'version':cfg['version'],'scope':cfg['scope'],'qwen':summarize(qa),'llama':summarize(la),
                 'matched_panel_cohorts':{p:{'original_rows':v['original_rows'],
                     'per_measure_joint_rows':{n:x['rows'] for n,x in v['per_measure_joint_eligible'].items()},
                     'all_measures_both_models_rows':v['all_measures_both_models_common']['rows'],
                     'correctness_transitions':v['paired_correctness_transitions_qwen_to_llama']} for p,v in paired['by_panel'].items()},
                 'held_out_access_enabled':False,'prior_files_modified':False,'main_experiment_ready':False,
                 'calibration':'not_fitted','routing_threshold':'not_selected','group_bootstrap':'not_performed',
                 'limits':['Retrospective selected development diagnostics, not population estimates.',
                           'ToolEyes relevance is separate from reference compliance; neither establishes execution success.',
                           'Llama ToolEyes has no error positives: AUROC and AP undefined, not perfect detection.',
                           'Truncation remains in correctness but not uncertainty denominators.',
                           'Same requests do not ensure identical tokenizer rendering or inherited sampling defaults.',
                           'No significance, model superiority, routing or cost benefit established.']}
        for p,h in ledger.items():
            if hash_file(p)!=h:raise ValueError('Input changed during analysis')
        provenance={'policy_sha256':POLICY_SHA,'input_sha256':{p.relative_to(repo).as_posix():h for p,h in ledger.items()},
                    'new_recomputed_scoring_provenance':'llama_scoring_recomputed/provenance.json',
                    'source_sha256_lf':{n:e.sha(e.regular(HERE/n).replace(b'\r\n',b'\n')) for n in ('run_analysis.py','engine.py','metrics.py')},
                    'llama_verification':'Full evidence-bound scorer rerun; original scores and summary compared structurally without modification.',
                    'network_requests':0,'raw_benchmark_or_split_opened':False,'held_out_access_enabled':False}
        values={'summary.json':compact,'qwen_analysis.json':qa,'llama_analysis.json':la,'matched_comparison.json':paired,'provenance.json':provenance}
        for name,value in values.items():(temp/name).write_text(e.canonical(value)+'\n',encoding='utf-8')
        lines=['# Qwen and Llama development uncertainty comparison','','Retrospective selected development diagnostics; no population or routing claims.','',
               '| Model/panel | Correct/rows | Measure | Eligible | AUROC | AP |','|---|---:|---|---:|---:|---:|']
        for model,analysis in [('Qwen',qa),('Llama',la)]:
            for panel,data in analysis['by_panel'].items():
                for name,x in data['available_case_analysis'].items():
                    d=x['discrimination'];fmt=lambda v:'undefined' if v is None else f'{v:.4f}'
                    lines.append(f"| {model}/{panel} | {data['official_correct']}/{data['original_rows']} | {name} | {d['eligible_rows']} | {fmt(d['auroc'])} | {fmt(d['average_precision'])} |")
        lines+=['','## Matched cases per measure','','| Panel | Measure | Shared eligible | Qwen AUROC | Llama AUROC | Qwen AP | Llama AP |','|---|---|---:|---:|---:|---:|---:|']
        for panel,data in paired['by_panel'].items():
            for name,x in data['per_measure_joint_eligible'].items():
                qd=x['qwen']['discrimination'];ld=x['llama']['discrimination']
                lines.append(f"| {panel} | {name} | {x['rows']} | {fmt(qd['auroc'])} | {fmt(ld['auroc'])} | {fmt(qd['average_precision'])} | {fmt(ld['average_precision'])} |")
        lines+=['','## Both-model, all-measure intersection','','| Panel | Measure | Shared eligible | Qwen AUROC | Llama AUROC |','|---|---|---:|---:|---:|']
        for panel,data in paired['by_panel'].items():
            for name,x in data['all_measures_both_models_common']['measures'].items():
                lines.append(f"| {panel} | {name} | {x['rows']} | {fmt(x['qwen']['discrimination']['auroc'])} | {fmt(x['llama']['discrimination']['auroc'])} |")
        lines+=['','Available-case metrics use different cohorts. Use matched_comparison.json for same-case comparisons.',
                'Inspect per-benchmark results and both-model/all-measure intersection before comparing measures.',
                'Equal reference totals do not mean identical case outcomes. Empty and one-class AUROC are undefined.',
                'Risk curves retain entire exact-score tie blocks; zero-acceptance risk is undefined.',
                'No calibration, confidence interval, threshold selection or final protocol freeze is performed.']
        (temp/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        e.publish(temp,output)
    print(json.dumps(compact,indent=2))
    print('Report:',output/'REPORT.md')
    return compact

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo-root',type=Path,default=Path('.'))
    parser.add_argument('--output',type=Path,default=Path(ROOT)/'paired_qwen_llama_uncertainty_v1')
    a=parser.parse_args()
    try:run(a.repo_root,a.output)
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as exc:raise SystemExit('Analysis stopped; preserve existing evidence: '+str(exc)) from None
if __name__=='__main__':main()
