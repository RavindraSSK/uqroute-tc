"""Development-only CPU diagnostics; official labels are immutable."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import re
import zipfile
from collections import Counter
from pathlib import Path
from replay_review import replay


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_config(config):
    if config.get('config_version')!='uqroute-analysis-policy-1.0.0':
        raise ValueError('Unsupported policy version')
    if config.get('main_experiment_ready') is not False:
        raise ValueError('This development implementation cannot enable main experiments')
    labels=config['official_labels'];diag=config['diagnostics'];uncertainty=config['uncertainty']
    if labels['immutable'] is not True or labels['ambiguity_exclusions'] is not False:
        raise ValueError('Official labels must be retained without ambiguity exclusions')
    if set(labels['primary_benchmarks'])!={'apibank','bfcl_v3','rotbench','toolalpaca'} or labels['separate_relevance_benchmarks']!=['tooleyes']:
        raise ValueError('Unsupported benchmark stratification')
    if diag['label_effect']!='none' or any(diag[k] for k in ('coerce_values','datetime_normalization','case_insensitive_reference_matching','invented_aliases')):
        raise ValueError('Diagnostic normalization cannot change labels')
    if uncertainty['routing_execution_enabled'] or uncertainty['impute_missing'] or uncertainty['smoke_scores_eligible']:
        raise ValueError('Smoke uncertainty/routing is unavailable in this policy')
    if config['reference_review']['change_official_scores'] or config['reference_review']['sensitivity_exclusion_policy']!='none':
        raise ValueError('Reference review cannot rewrite or exclude outcomes')


def type_compatibility(value,declared,aliases):
    if isinstance(declared,list):
        results=[type_compatibility(value,t,aliases) for t in declared]
        return 'compatible' if 'compatible' in results else ('unknown' if 'unknown' in results else 'incompatible')
    if not isinstance(declared,str):return 'unknown'
    declared=aliases.get(declared,declared)
    checks={
        'string':lambda v:isinstance(v,str),
        'integer':lambda v:not isinstance(v,bool) and isinstance(v,(int,float)) and math.isfinite(v) and int(v)==v,
        'number':lambda v:not isinstance(v,bool) and isinstance(v,(int,float)) and math.isfinite(v),
        'boolean':lambda v:isinstance(v,bool),
        'object':lambda v:isinstance(v,dict),
        'array':lambda v:isinstance(v,list),
        'null':lambda v:v is None,
    }
    if declared not in checks:return 'unknown'
    return 'compatible' if checks[declared](value) else 'incompatible'


def combine(states):
    if 'incompatible' in states:return 'incompatible'
    if 'unknown' in states:return 'unknown'
    return 'compatible'


def schema_occurrence(arguments,schema,aliases):
    if not isinstance(arguments,dict):
        return {'declared_argument_checks':'incompatible','reason':'arguments_not_a_mapping','full_json_schema_validity':'not_assessed'}
    if not isinstance(schema,dict) or not isinstance(schema.get('properties'),dict):
        return {'declared_argument_checks':'unknown','reason':'property_metadata_unavailable','full_json_schema_validity':'not_assessed'}
    props=schema['properties'];unknown=sorted(set(arguments)-set(props))
    required=schema.get('required')
    required_known=isinstance(required,list) and all(isinstance(k,str) for k in required)
    missing=sorted(set(required)-set(arguments)) if required_known else None
    required_status=('incompatible' if missing else 'compatible') if required_known else 'unknown'
    types={k:type_compatibility(v,props[k].get('type') if isinstance(props[k],dict) else None,aliases) for k,v in arguments.items() if k in props}
    membership='incompatible' if unknown else 'compatible'
    return {
        'declared_argument_checks':combine([membership,required_status,*types.values()]),
        'argument_key_membership':membership,'undeclared_argument_keys':unknown,
        'required_key_presence':required_status,'missing_required_keys':missing,
        'argument_type_compatibility':types,'full_json_schema_validity':'not_assessed',
        'note':'Key membership is a declared-interface check, not the JSON Schema additionalProperties default. No coercion, nested/enum/format/semantic validation.',
    }


def inspect_call(call,tools,aliases):
    if not isinstance(call,dict):return {'name_available':False,'declared_argument_checks':'incompatible','reason':'call_not_a_mapping','matching_name_occurrences':0}
    name=call.get('name');matches=[(i,t) for i,t in enumerate(tools) if t.get('name')==name]
    arguments=call.get('parameters',call.get('arguments',{}))
    checks=[{'tool_occurrence_index':i,**schema_occurrence(arguments,t.get('parameters'),aliases)} for i,t in matches]
    states=[c['declared_argument_checks'] for c in checks]
    result='compatible' if 'compatible' in states else ('unknown' if 'unknown' in states else 'incompatible')
    return {'name':name,'name_available':bool(matches),'matching_name_occurrences':len(matches),
            'duplicate_name_ambiguity':len(matches)>1,'declared_argument_checks':result,'occurrence_checks':checks}


def aggregate(rows):
    n=len(rows);correct=sum(r['official_score']['correct'] for r in rows)
    return {'n':n,'official_correct':correct,'official_reference_match_fraction':correct/n if n else None}


def analyze_record(record,candidate,annotation,config):
    official=copy.deepcopy(record['official_score'])
    calls=record['prediction']['tool_calls'];tools=candidate['tools']
    if not isinstance(calls,list):raise ValueError('Saved parser output must be a list')
    raw=record['prediction']['raw_output']
    user='\n'.join(m['content'] for m in record['request']['messages'] if m['role']=='user')
    one_call_requested='please only make one tool call' in user.lower()
    markers=len(re.findall(r'^\s*(?:Action|ActionCode)\s*:',raw,re.M))
    checks=[inspect_call(c,tools,config['diagnostics']['type_aliases']) for c in calls]
    benchmark=candidate['benchmark']
    if benchmark not in config['official_labels']['scorer_methods']:raise ValueError('Unknown benchmark')
    if official['method']!=config['official_labels']['scorer_methods'][benchmark]:raise ValueError('Unexpected saved scoring method')
    return {
        'case_key':record['case_key'],'benchmark':benchmark,
        'analysis_stratum':'tool_name_relevance_only' if benchmark=='tooleyes' else 'official_reference_compliance',
        'official_score':official,'response_status':record['status'],'finish_reason':record['finish_reason'],
        'parser_call_count':len(calls),'raw_react_action_marker_count':markers,
        'raw_action_markers_exceed_parsed_calls':markers>len(calls),
        'explicit_one_call_request_detected':one_call_requested,
        'explicit_one_call_violation':one_call_requested and len(calls)!=1,
        'extra_parsed_calls_beyond_one':max(0,len(calls)-1),
        'literal_unknown_tool_call_count':sum(not c['name_available'] for c in checks),
        'per_call_diagnostics':checks,
        'reference_review':copy.deepcopy(annotation) if annotation is not None else {'review_status':'unknown','flags':[]},
        'reference_review_status':'reviewed_post_hoc_development' if annotation is not None else 'unknown',
        'reference_ambiguity_status':('flagged' if set(annotation.get('flags',[])) & set(config['reference_review']['ambiguity_flag_names']) else 'not_flagged_in_this_review') if annotation is not None else 'unknown',
        'uncertainty':{'score_eligible':False,'scores':None,'reason':'smoke_token_alignment_and_uncertainty_not_validated'},
        'execution_success':'not_measured',
    }


def analyze(config,annotations,records,candidates):
    validate_config(config)
    if annotations.get('changes_labels') is not False or annotations.get('excludes_cases') is not False:
        raise ValueError('Annotations cannot change labels or exclusions')
    originals={r['case_key']:copy.deepcopy(r['official_score']) for r in records}
    if len(originals)!=len(records):raise ValueError('Duplicate case identities')
    rows=[]
    for record in records:
        key=record['case_key']
        if key not in candidates:raise ValueError('Candidate missing for saved response')
        candidate=candidates[key]
        if record['request']['messages']!=candidate['messages']:raise ValueError('Request differs from candidate')
        rows.append(analyze_record(record,candidate,annotations['annotations'].get(key),config))
    if {r['case_key']:r['official_score'] for r in rows}!=originals:
        raise ValueError('Official labels changed')
    primary=[r for r in rows if r['benchmark'] in config['official_labels']['primary_benchmarks']]
    relevance=[r for r in rows if r['benchmark']=='tooleyes']
    return {
        'config_version':config['config_version'],'scope':config['scope'],
        'status':'implemented_development_diagnostics_only','main_experiment_ready':False,
        'official_labels_unchanged':True,'ambiguity_exclusions_applied':False,
        'primary_reference_compliance':aggregate(primary),
        'separate_tooleyes_name_relevance':aggregate(relevance),
        'supplementary_all_benchmark_official_matches':aggregate(rows),
        'by_benchmark':{b:aggregate([r for r in rows if r['benchmark']==b]) for b in sorted({r['benchmark'] for r in rows})},
        'counts':{'responses':len(rows),'uncertainty_eligible':0,'uncertainty_unavailable':len(rows),
                  'literal_unknown_tool_calls':sum(r['literal_unknown_tool_call_count'] for r in rows),
                  'explicit_one_call_violations':sum(r['explicit_one_call_violation'] for r in rows),
                  'reference_cases_with_review_flags':sum(bool(r['reference_review'].get('flags')) for r in rows),
                  'reference_ambiguity_flagged_cases':sum(r['reference_ambiguity_status']=='flagged' for r in rows)},
        'denominator_note':'Reference flags are overlapping annotations; no exclusions. Smoke selection is not population-weighted or independent. No CI, ranking, gate or routing result is computed.',
        'pending_before_main_experiments':config['pending_before_main_experiments'],'cases':rows,
    }


def run(archive,audit_path,config_path,annotations_path):
    config_raw=config_path.read_bytes();annotation_raw=annotations_path.read_bytes()
    config=json.loads(config_raw);annotations=json.loads(annotation_raw);validate_config(config)
    # Strict content allowlist before parsing any dataset content. No glob,
    # network, split traversal, or held-out path is used.
    archive_raw=archive.read_bytes();audit_raw=audit_path.read_bytes()
    if sha(archive_raw)!=config['allowed_inputs']['archive_sha256'] or sha(audit_raw)!=config['allowed_inputs']['audit_sha256']:
        raise ValueError('Input is not the approved development smoke evidence')
    verified=replay(archive,audit_path)
    with zipfile.ZipFile(archive) as z:
        metadata=json.loads(z.read('metadata.json'));preview=json.loads(z.read('preview.json'))
        records=[json.loads(z.read(e['record_file'])) for e in metadata['records']]
    candidates={r['case_key']:r for r in preview['cases']}
    result=analyze(config,annotations,records,candidates)
    if verified['official_correct']!=result['supplementary_all_benchmark_official_matches']['official_correct']:
        raise ValueError('Replay and diagnostic totals differ')
    result['provenance']={'config_sha256':sha(config_raw),'annotations_sha256':sha(annotation_raw),
                          'archive_sha256':sha(archive_raw),'audit_sha256':sha(audit_raw),
                          'diagnostics_sha256':sha(Path(__file__).read_bytes()),
                          'held_out_accessed':False,'approved_development_inputs_only':True,
                          'validation_boundary':verified['validation_boundary']}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--config',type=Path,default=Path(__file__).with_name('analysis_config_v1.json'))
    p.add_argument('--annotations',type=Path,default=Path(__file__).with_name('reference_flags_v1.json'))
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    protected=[a.archive,a.audit,a.config,a.annotations,Path(__file__),Path(__file__).with_name('official_runner.py'),Path(__file__).with_name('official_scorer.py'),Path(__file__).with_name('replay_review.py')]
    if a.output.resolve() in [x.resolve() for x in protected]:raise ValueError('Output would overwrite source evidence or implementation')
    result=run(a.archive,a.audit,a.config,a.annotations)
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:result[k] for k in ['official_labels_unchanged','primary_reference_compliance','separate_tooleyes_name_relevance','supplementary_all_benchmark_official_matches','counts']},indent=2))
