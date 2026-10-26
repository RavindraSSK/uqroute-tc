"""Revalidate full-development scoring and analyze immutable saved outcomes."""
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


def run(repo,output):
    for p in (repo,output):
        if any(x.is_symlink() for x in (p,*p.parents)):raise ValueError('Symlink path')
    repo=repo.resolve();output=output.absolute();root=repo/ROOT
    if output.exists() or not output.resolve().is_relative_to(root) or output.resolve()==root:raise ValueError('Fresh development output required')
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor','f76cadc','HEAD'],check=True)
    policy=json.loads((HERE/'policy.json').read_text())
    for name,wanted in policy['source_sha256_lf'].items():
        p=repo/name
        if hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=wanted:raise ValueError('Source fingerprint differs: '+name)
    folder=repo/'tools/development_audits/three_model_uncertainty_v1'
    sys.path.insert(0,str(folder));import engine
    cfg=engine.loads(engine.regular(folder/'policy.json'))
    prior=root/'corrected_qwen15b_full_development_official_scoring_v1'
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='full-development-analysis-') as directory:
        temp=Path(directory).resolve();verified=temp/'scoring_recomputed'
        command=[sys.executable,str(repo/'tools/development_audits/full_development_scoring_v1/score_full.py'),'--repo-root',str(repo),'--evidence-dir',str(root/'corrected_qwen15b_full_development_import_8517fd5d'),'--bundle',str(root/'full_primary_export_v1'),'--audit-dir',str(root/'full_primary_audit_v1'),'--output',str(verified)]
        subprocess.run(command,check=True,stdout=subprocess.DEVNULL)
        hashes={}
        for name in ('scores.json','summary.json'):
            raw=engine.regular(prior/name);hashes[name]=engine.sha(raw)
            if engine.loads(raw)!=engine.loads(engine.regular(verified/name)):raise ValueError('Existing full-development scores differ')
        rows=engine.loads(engine.regular(verified/'scores.json'))
        if len(rows)!=1728:raise ValueError('Full population differs')
        analysis=engine.analyze(rows,cfg);pair_rows=pairs.paired(rows)
        if len(pair_rows)!=1588:raise ValueError('Constructed pairing differs')
        summary={'rows':len(rows),'pairs':len(pair_rows),'by_panel':{p:pairs.summarize([r for r in pair_rows if r['panel']==p]) for p in ('official_reference_compliance','tooleyes_relevance')},
                 'by_benchmark':{b:pairs.summarize([r for r in pair_rows if r['benchmark']==b]) for b in sorted({r['benchmark'] for r in rows})},
                 'by_source_and_panel':{s:{p:pairs.summarize([r for r in pair_rows if r['source_file']==s and r['panel']==p]) for p in ('official_reference_compliance','tooleyes_relevance')} for s in sorted({r['source_file'] for r in pair_rows})},
                 'held_out_access_enabled':False,'main_experiment_ready':False,'prior_files_modified':False}
        # Correct inherited selected-69 scope/limitations without altering metric calculations.
        analysis['version']=policy['version']
        analysis['scope']='all-1728-constructed-primary-development-candidates-only'
        analysis['limits']=[v for v in analysis['limits'] if not v.startswith('Retrospective development diagnostics on one hash-selected')]
        analysis['limits'].append('All constructed development candidates; 26 blocked inventory rows have no outcome. Earlier coverage responses are not pooled.')
        report=['# Qwen 1.5B full-development uncertainty and pairing','',
                'All 1728 constructed development cases; 26 source construction blocks remain outside model-outcome denominators.',
                'Higher uncertainty predicts official error. AP is noninterpolated score-block average precision.', '',
                '| Panel | Measure | Eligible | Errors | AUROC | AP |','|---|---|---:|---:|---:|---:|']
        for panel,c in analysis['by_panel'].items():
            for name,m in c['available_case_analysis'].items():
                d=m['discrimination'];report.append(f'| {panel} | {name} | {d["eligible_rows"]} | {d["error_positive_rows"]} | {d["auroc"]} | {d["average_precision"]} |')
        report+=['','Compare measures using common_eligible_case_analysis in analysis.json; inspect per-benchmark results.',
                 'paired_summary.json reports C/I transitions, pair-weighted and equal-group-weighted changes separately.',
                 'The same clean response is reused across variants; pairs are dependent and not independent trials.',
                 'Changes are reference-compliance/name-relevance differences, not proven causal or executable-success changes.',
                 'NLL changes use joint evidence eligibility only. Unavailable evidence is not imputed.',
                 'Reference flags remain separate and never exclude cases. Changed references and schemas can affect comparisons.',
                 'No bootstrap, calibrated probability fitting, threshold selection, routing or held-out evaluation occurs.']
        for name,value in {'analysis.json':analysis,'paired_rows.json':pair_rows,'paired_summary.json':summary,'provenance.json':{'policy':policy,'prior_scoring_sha256':hashes,'held_out_access_enabled':False,'network_requests':0}}.items():
            (temp/name).write_text(engine.canonical(value)+'\n',encoding='utf-8')
        (temp/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
        for name,wanted in hashes.items():
            if engine.sha(engine.regular(prior/name))!=wanted:raise ValueError('Input changed')
        engine.publish(temp,output)
    print(json.dumps({'rows':1728,'pairs':1588,'panels':{p:{n:m['discrimination'] for n,m in c['available_case_analysis'].items()} for p,c in analysis['by_panel'].items()},'paired_by_panel':summary['by_panel'],'held_out_access_enabled':False,'prior_files_modified':False},indent=2))
    print('Report:',output/'REPORT.md')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo-root',type=Path,default=Path('.'));p.add_argument('--output',type=Path,default=Path(ROOT)/'qwen15b_full_development_analysis_v1');a=p.parse_args();run(a.repo_root,a.output)
