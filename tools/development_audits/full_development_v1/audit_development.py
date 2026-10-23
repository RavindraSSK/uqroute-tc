"""Audit an explicitly approved development-only bundle; no raw-dataset access."""
from __future__ import annotations
import argparse
import ast
import copy
import json
from collections import Counter,defaultdict
from pathlib import Path
import tempfile
from common import (BASE_COMMIT,BENCHMARK_REVISION,BENCHMARKS,BUNDLE_FILES,RUNNER_SHA,SAMPLE_FIELDS,SOURCE_FILES,SPLIT_SHA,VERSION,canonical,code_hashes,json_bytes,loads,read_regular,sha)
from identity_v1 import canonical_base_id,is_multi_turn
from reference_rules import audit_case
from repair import build
from schema_rules import TYPE_ALIASES,schema_occurrence


def load_builder():
    raw=read_regular(Path(__file__).with_name('official_runner.py')).replace(b'\r\n',b'\n')
    if sha(raw)!=RUNNER_SHA:raise ValueError('Pinned message builder source differs')
    tree=ast.parse(raw)
    body=[n for n in tree.body if not (isinstance(n,ast.ImportFrom) and n.module in {'openai','tqdm'})]
    tree=ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),*body],type_ignores=[]))
    namespace={'__name__':'development_message_builder'}
    exec(compile(tree,'pinned_message_builder','exec'),namespace)
    return namespace['build_messages']


def validate_bundle(samples,references,membership,attestation):
    required_attestation={'format_version','exporter_base_commit','project_head','benchmark_revision','split_sha256','population','partition','row_count','group_count','case_key_digest','source_file_hashes','payload_hashes','code_hashes','implementation_hash_scheme','held_out_content_exported','unselected_nested_payloads_decoded','trusted_stage_counts','access_boundary','integrity_limit'}
    if set(attestation)!=required_attestation or attestation.get('exporter_base_commit')!=BASE_COMMIT or attestation.get('implementation_hash_scheme')!='sha256_source_bytes_with_CRLF_normalized_to_LF':
        raise ValueError('Attestation metadata boundary differs')
    if set(membership)!={'population','split','groups','expected_rows','expected_groups'}:raise ValueError('Unexpected membership metadata')
    if attestation.get('format_version')!=VERSION or attestation.get('benchmark_revision')!=BENCHMARK_REVISION or attestation.get('split_sha256')!=SPLIT_SHA or attestation.get('partition')!='development' or attestation.get('held_out_content_exported') is not False or attestation.get('unselected_nested_payloads_decoded')!=0:
        raise ValueError('Unsupported development attestation')
    population=attestation.get('population')
    if population not in ('primary','sensitivity_only') or membership.get('population')!=population or membership.get('split')!='development':raise ValueError('Population/membership mismatch')
    groups=membership.get('groups')
    if not isinstance(groups,dict) or not groups:raise ValueError('Development membership missing')
    for label in groups.values():
        if set(label)!={'benchmark','population','split'} or label['benchmark'] not in BENCHMARKS or label['population']!=population or label['split']!='development':raise ValueError('Non-development membership or invalid label')
    if len(groups)!=membership['expected_groups'] or len(samples)!=membership['expected_rows'] or len(samples)!=attestation['row_count'] or len(groups)!=attestation['group_count']:raise ValueError('Attested population counts differ')
    keys=[r['case_key'] for r in samples];refkeys=[r['case_key'] for r in references]
    if len(set(keys))!=len(keys) or len(set(refkeys))!=len(refkeys) or set(keys)!=set(refkeys):raise ValueError('Duplicate/missing case/reference identity')
    if sha(canonical(sorted(keys)).encode())!=attestation['case_key_digest']:raise ValueError('Case-key digest mismatch')
    if set(attestation.get('source_file_hashes',{}))!=set(SOURCE_FILES):raise ValueError('Source provenance incomplete')
    seen_groups=set();clean_counts=Counter()
    allowed_record={'case_key','source_file','row_id','canonical_base_id','benchmark','population','split','source_line_sha256','sample'}
    for record in samples:
        if set(record)!=allowed_record:raise ValueError('Unexpected input fields; audit does not accept model outcomes')
        group=record['canonical_base_id'];sample=record['sample'];label=groups.get(group)
        if label is None or record['split']!='development' or record['population']!=population or record['benchmark']!=label['benchmark']:raise ValueError('Unapproved group membership')
        if not isinstance(sample,dict) or not set(sample)<=SAMPLE_FIELDS or 'golden_answers' in sample:raise ValueError('Builder input sidecar boundary violated')
        if sample.get('id')!=record['row_id'] or sample.get('benchmark')!=record['benchmark'] or is_multi_turn(sample):raise ValueError('Sample identity/category mismatch')
        # Only exported development group IDs are used in this check.
        if canonical_base_id(record['row_id'],groups if population=='primary' else ())!=group:raise ValueError('Canonical identity mismatch')
        if record['source_file'] not in SOURCE_FILES or record['case_key']!=record['source_file']+':'+record['row_id']:raise ValueError('Qualified key mismatch')
        if len(record['source_line_sha256'])!=64:raise ValueError('Lineage fingerprint missing')
        seen_groups.add(group)
        if record['source_file']=='clean.jsonl':clean_counts[group]+=1
    if seen_groups!=set(groups):raise ValueError('Not all attested development groups represented')
    if population=='primary' and any(clean_counts[g]!=1 for g in groups):raise ValueError('Primary group missing unique clean anchor')
    if population=='sensitivity_only' and clean_counts:raise ValueError('Sensitivity-only bundle contains clean anchors')
    for ref in references:
        if set(ref)!={'case_key','golden_answers','eval_config'} or not isinstance(ref['golden_answers'],list) or not isinstance(ref['eval_config'],dict):raise ValueError('Invalid reference sidecar')
    return {r['case_key']:r for r in references}


def summarize_rows(rows):
    return {'rows':len(rows),'canonical_groups':len({r['canonical_base_id'] for r in rows}),
            'construction_status_counts':dict(Counter(r['construction_status'] for r in rows)),
            'review_signal_cases':sum(bool(r.get('reference_audit',{}).get('review_flags')) for r in rows),
            'review_signal_counts':dict(Counter(f for r in rows for f in r.get('reference_audit',{}).get('review_flags',[]))),
            'objective_cost_detected':sum(r.get('reference_audit',{}).get('objective_detection',{}).get('cost_explicit_detected',False) for r in rows),
            'objective_latency_detected':sum(r.get('reference_audit',{}).get('objective_detection',{}).get('latency_explicit_detected',False) for r in rows)}


def analyze(samples,references,membership,attestation,message_builder,repair_builder=build,reference_auditor=audit_case):
    ref_index=validate_bundle(samples,references,membership,attestation)
    inventory=[];candidates=[];groups=defaultdict(list)
    for record in samples:
        key=record['case_key'];sample=record['sample'];reference=ref_index[key]
        row={k:copy.deepcopy(record[k]) for k in ('case_key','source_file','row_id','canonical_base_id','benchmark','population','split','source_line_sha256')}
        row['source_file_sha256']=attestation['source_file_hashes'][record['source_file']]
        row['source_reference_sha256']=sha(canonical(reference).encode())
        row.update(construction_status='blocked',excluded_from_inventory=False,official_labels_changed=False,uncertainty_eligibility='not_assessed_before_inference')
        try:
            # Reference sidecar is not supplied to either builder.
            messages=message_builder(copy.deepcopy(sample))
            row['original_messages_sha256']=sha(canonical(messages).encode())
            candidate=repair_builder(sample['benchmark'],messages,copy.deepcopy(sample['tools']))
            corrected=candidate['messages']
            if [m['role'] for m in corrected]!=['system','user']:raise ValueError('Unexpected corrected prediction boundary')
            row.update(construction_status='candidate',corrected_messages_sha256=candidate['messages_sha256'],repair_edits=candidate['edits'],tool_occurrence_schema_sha256=[sha(canonical(t).encode()) for t in candidate['tools']])
            candidates.append({'case_key':key,'canonical_base_id':record['canonical_base_id'],'benchmark':sample['benchmark'],'messages':corrected,'tools':candidate['tools'],'messages_sha256':candidate['messages_sha256']})
        except (ValueError,TypeError,KeyError,SyntaxError,IndexError) as exc:
            row['construction_reason']=type(exc).__name__+': '+str(exc)
            row['reference_audit_status']='not_assessed_due_to_construction_block'
            inventory.append(row);groups[record['canonical_base_id']].append(row);continue
        try:
            row['reference_audit']=reference_auditor({'case_key':key,'benchmark':sample['benchmark'],'golden_answers':copy.deepcopy(reference['golden_answers'])},candidate)
            row['reference_audit_status']='completed_bounded_signals_only'
            schema=[]
            for call in reference['golden_answers']:
                name=call.get('name') or call.get('Action');args=call.get('parameters') or call.get('arguments') or call.get('Action_Input') or {}
                if sample['benchmark']=='tooleyes':
                    schema.append({'reference_name':name,'argument_validation':'not_applicable_name_only_reference','matching_name_occurrences':[i for i,t in enumerate(candidate['tools']) if t['name']==name],'interpretation':'ToolEyes reference supplies tool relevance, not a complete executable argument mapping.'})
                else:
                    occurrences=[{'occurrence':i,**schema_occurrence(args,t.get('parameters'),TYPE_ALIASES)} for i,t in enumerate(candidate['tools']) if t['name']==name]
                    schema.append({'reference_name':name,'occurrence_checks':occurrences,'interpretation':'Structural declaration diagnostics only; no reference correction or execution validation'})
            row['reference_schema_diagnostics']=schema
        except (ValueError,TypeError,KeyError,SyntaxError,IndexError) as exc:
            row['reference_audit_status']='unresolved_audit_error';row['reference_audit_reason']=type(exc).__name__+': '+str(exc)
        inventory.append(row);groups[record['canonical_base_id']].append(row)
    pairs=[]
    for group,items in sorted(groups.items()):
        clean=[r for r in items if r['source_file']=='clean.jsonl']
        for row in items:
            if row['source_file']=='clean.jsonl':continue
            pairs.append({'canonical_base_id':group,'perturbed_case_key':row['case_key'],'clean_case_key':clean[0]['case_key'] if len(clean)==1 else None,'pair_available':len(clean)==1,'both_constructed':len(clean)==1 and clean[0]['construction_status']=='candidate' and row['construction_status']=='candidate'})
    summary={'format_version':VERSION,'scope':'Full exported development population only; not a model-performance result',
             'population':membership['population'],'partition':'development','all_input_rows_retained':len(inventory)==len(samples),
             'official_labels_changed':False,'reference_corrections_applied':False,'ambiguity_exclusions_applied':False,
             'held_out_bundle_rows_accepted':0,'raw_benchmark_files_opened_by_auditor':0,
             'readiness':'DEVELOPMENT_AUDIT_ONLY_MAIN_EXPERIMENT_NOT_READY',
             'totals':summarize_rows(inventory),
             'by_benchmark':{b:summarize_rows([r for r in inventory if r['benchmark']==b]) for b in sorted({r['benchmark'] for r in inventory})},
             'by_source_file':{f:summarize_rows([r for r in inventory if r['source_file']==f]) for f in sorted({r['source_file'] for r in inventory})},
             'reference_audit_status_counts':dict(Counter(r['reference_audit_status'] for r in inventory)),
             'clean_anchor_pairing':{'perturbed_rows':len(pairs),'with_unique_clean_anchor':sum(p['pair_available'] for p in pairs),'both_constructed':sum(p['both_constructed'] for p in pairs)},
             'candidate_inference_count_scenario':{'model_roles':4,'one_request_per_candidate_per_model_calls':4*len(candidates),'maximum_completion_tokens_at_frozen_cap':4*len(candidates)*1024,'interpretation':'Counting scenario only; not a GPU-time estimate, quota check or main-experiment readiness decision'},
             'limits':['Construction blockers are quarantined from candidate output, never removed from source inventory.','Audit flags are bounded review signals, not new official labels or proof of semantic error.','Expected metadata counts are verified during export; actual repaired counts are measured here.','No inference, score eligibility, threshold, routing or confidence interval is produced.','Attestation integrity depends on reviewed trusted exporter; hashes are not a signature.']}
    reward=[r for r in inventory if r['source_file'].removesuffix('.jsonl') in {'CD','CD_AB','CD_NT','TD','TD_AB','TD_NT'}]
    summary['reference_compliance_candidate_inventory']=summarize_rows([r for r in inventory if r['benchmark']!='tooleyes'])
    summary['separate_tooleyes_relevance_candidate_inventory']=summarize_rows([r for r in inventory if r['benchmark']=='tooleyes'])
    summary['panel_interpretation']='Inventory counts only, no compliance/relevance scores; reward panel overlaps other panels.'
    summary['reward_panel']=summarize_rows(reward)
    summary['reward_panel']['objective_detection_assessed_rows']=sum(r.get('reference_audit_status')=='completed_bounded_signals_only' for r in reward)
    summary['reward_panel']['objective_not_detected_rows']=sum(r.get('reference_audit_status')=='completed_bounded_signals_only' and not r['reference_audit']['objective_detection']['cost_explicit_detected'] and not r['reference_audit']['objective_detection']['latency_explicit_detected'] for r in reward)
    return inventory,candidates,pairs,summary


def audit_bundle(bundle,expected_attestation_sha256,output):
    bundle=Path(bundle).resolve();output=Path(output).resolve()
    if output.exists() or output==bundle or bundle in output.parents:raise ValueError('Output must be a new directory outside the bundle')
    if {p.name for p in bundle.iterdir()}!=BUNDLE_FILES:raise ValueError('Bundle file set differs')
    attestation_raw=read_regular(bundle/'attestation.json')
    if sha(attestation_raw)!=expected_attestation_sha256:raise ValueError('Attestation not explicitly approved by hash')
    attestation=loads(attestation_raw)
    if attestation.get('code_hashes')!=code_hashes():raise ValueError('Export/audit implementation fingerprints differ')
    payloads={name:read_regular(bundle/name) for name in ('samples.jsonl','references.jsonl','membership.json')}
    if attestation.get('payload_hashes')!={n:sha(raw) for n,raw in payloads.items()}:raise ValueError('Bundle payload hashes differ')
    samples=[loads(line) for line in payloads['samples.jsonl'].splitlines() if line.strip()]
    references=[loads(line) for line in payloads['references.jsonl'].splitlines() if line.strip()]
    membership=loads(payloads['membership.json'])
    inventory,candidates,pairs,summary=analyze(samples,references,membership,attestation,load_builder())
    summary['provenance']={'attestation_sha256':sha(attestation_raw),'payload_hashes':attestation['payload_hashes'],'code_hashes':code_hashes(),'benchmark_revision':BENCHMARK_REVISION,'split_sha256':SPLIT_SHA}
    outputs={'inventory.json':inventory,'candidates.json':candidates,'clean_perturbed_pairs.json':pairs,'summary.json':summary,'unresolved.json':[r for r in inventory if r['construction_status']=='blocked' or r['reference_audit_status']=='unresolved_audit_error' or r.get('reference_audit',{}).get('review_flags')]}
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='dev-audit-') as temp:
        temp=Path(temp)
        for name,payload in outputs.items():(temp/name).write_bytes(json_bytes(payload))
        if output.exists():raise ValueError('Output directory appeared during audit')
        temp.rename(output)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--expected-attestation-sha256',required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    try:result=audit_bundle(args.bundle,args.expected_attestation_sha256,args.output)
    except (ValueError,OSError,KeyError,TypeError):raise SystemExit('Development audit failed provenance or structure validation; do not use partial outputs. No record contents are printed.')
    print(json.dumps({k:result[k] for k in ('readiness','totals','reference_audit_status_counts','clean_anchor_pairing','reward_panel')},indent=2))
