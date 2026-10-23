"""Validate the protocol proposal and its Git baseline without reading datasets."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess

BASE='344234f156dd4ea2fc1f6713330cf02ded38d5f1'
DOCS=Path('docs/research_track_v1')
REQUIRED_DECISIONS={'development_export','full_prompt_repair','reference_objectives','population_pairing','generation_evidence','gate_measure','gate_missing_acceptance','threshold_objective','baselines','statistics_calibration','cost_feasibility','repeated_recovery_scope','final_freeze'}
ALLOWED_BASELINE_PATHS={
    'docs/PROTOCOL.md','docs/PROGRESS.md','docs/config/task1_single_sample_v1.json',
    'docs/config/task2_uncertainty_v1.json','docs/config/task2_repeated_sampling_v1.json',
    'tools/development_audits/analysis_policy_v1/analysis_config_v1.json',
    'tools/development_audits/development_reference_audit_v1/audit_rules_v1.json',
    'docs/literature/EVIDENCE_MATRIX.md',
}

def validate(plan,manifest):
    errors=[]
    if plan.get('plan_version')!='uqroute-main-experiment-plan-1.0.0':errors.append('Unsupported plan version')
    if plan.get('baseline_commit')!=BASE or manifest.get('baseline_commit')!=BASE:errors.append('Baseline differs from reviewed commit')
    if plan.get('status')!='proposal_not_frozen':errors.append('This version must remain a proposal')
    for field in ('main_experiment_ready','inference_enabled','held_out_access_enabled','training_enabled'):
        if plan.get(field) is not False:errors.append(field+' must be false')
    for field in ('existing_official_labels_immutable','existing_split_unchanged'):
        if plan.get(field) is not True:errors.append(field+' must be true')
    if plan.get('data_access_for_this_package')!='none':errors.append('Plan verifier cannot access datasets')
    panels=plan.get('reporting_panels',{})
    if set(panels.get('official_reference_compliance',{}).get('benchmarks',[]))!={'apibank','bfcl_v3','rotbench','toolalpaca'}:errors.append('Reference panel changed')
    relevance=panels.get('tool_name_relevance',{})
    if relevance.get('benchmarks')!=['tooleyes'] or relevance.get('pooled_into_primary_compliance') is not False:errors.append('ToolEyes must remain separate')
    reward=panels.get('cost_latency_preference',{})
    if set(reward.get('source_file_stems',[]))!={'CD','CD_AB','CD_NT','TD','TD_AB','TD_NT'} or reward.get('objective_detected_and_not_detected_separate') is not True or reward.get('overlaps_reference_panel') is not True:errors.append('Reward panel boundary changed')
    for name in ('official_reference_compliance','tool_name_relevance'):
        if panels.get(name,{}).get('semantic_execution_claim') is not False:errors.append('No execution-success claim is supported')
    if plan.get('proposed_analysis',{}).get('impute_missing_scores') is not False:errors.append('Missing scores cannot be imputed')
    decisions=plan.get('decisions',[]);ids=[d.get('id') for d in decisions]
    if len(ids)!=len(set(ids)) or set(ids)!=REQUIRED_DECISIONS:errors.append('Decision register incomplete or duplicated')
    for decision in decisions:
        if decision.get('status')!='pending' or not decision.get('requires'):errors.append('Proposal decisions cannot be marked resolved without a new reviewed freeze')
    sources=manifest.get('sources',[])
    if len(sources)!=len(ALLOWED_BASELINE_PATHS) or {s.get('path') for s in sources}!=ALLOWED_BASELINE_PATHS:errors.append('Source manifest contains unexpected paths')
    for source in sources:
        blob=source.get('git_blob_sha','')
        if len(blob)!=40 or any(c not in '0123456789abcdef' for c in blob):errors.append('Invalid baseline Git blob hash')
    return errors


def verify_git(repo,manifest):
    def git(*args):
        return subprocess.run(['git','-C',str(repo),*args],text=True,capture_output=True)
    head=git('rev-parse','HEAD')
    if head.returncode:raise ValueError('Repository HEAD is unavailable')
    ancestry=git('merge-base','--is-ancestor',BASE,'HEAD')
    if ancestry.returncode:raise ValueError('Reviewed baseline must be an ancestor of HEAD')
    for source in manifest['sources']:
        path=source['path']
        if path not in ALLOWED_BASELINE_PATHS:raise ValueError('Unexpected source path')
        blob=git('rev-parse',BASE+':'+path)
        if blob.returncode or blob.stdout.strip()!=source['git_blob_sha']:
            raise ValueError('Baseline source object differs: '+path)
    return head.stdout.strip()


def verify(repo,check_git=True):
    repo=Path(repo).resolve();folder=repo/DOCS
    plan=json.loads((folder/'main_experiment_plan_v1.json').read_text(encoding='utf-8'))
    manifest=json.loads((folder/'source_manifest.json').read_text(encoding='utf-8'))
    errors=validate(plan,manifest)
    for name in ('MAIN_EXPERIMENT_PROTOCOL_V1.md','DEVELOPMENT_POPULATION_AUDIT_PLAN_V1.md'):
        if not (folder/name).is_file():errors.append('Missing proposal document: '+name)
    if errors:raise ValueError('; '.join(errors))
    head=verify_git(repo,manifest) if check_git else None
    return {'package_valid':True,'baseline_commit':BASE,'head':head,
            'git_baseline_verified':check_git,'main_experiment_ready':False,
            'inference_enabled':False,'held_out_access_enabled':False,
            'dataset_files_opened':0,'scope':'plan/configuration and source Git object IDs only',
            'pending_decisions':[d['id'] for d in plan['decisions']]}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,default=Path.cwd())
    parser.add_argument('--package-only',action='store_true',help='Validate extracted package before integration; does not verify Git ancestry')
    parser.add_argument('--require-main-ready',action='store_true',help='Exit 2 because this proposal does not enable main experiments')
    args=parser.parse_args()
    try:result=verify(args.repo_root,check_git=not args.package_only)
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as exc:
        print(json.dumps({'package_valid':False,'error':str(exc)},indent=2));raise SystemExit(1)
    print(json.dumps(result,indent=2))
    if args.require_main_ready:raise SystemExit(2)
