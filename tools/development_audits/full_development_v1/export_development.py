"""Trusted mixed-source partitioning step; exports development content only."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile
from collections import Counter
from common import (BASE_COMMIT,BENCHMARK_REVISION,BENCHMARKS,SPLIT_SHA,VERSION,SOURCE_FILES,SAMPLE_FIELDS,canonical,code_hashes,decode,json_bytes,lines_bytes,loads,read_regular,sha)
from identity_v1 import canonical_base_id,is_multi_turn


def git(root,*args):
    p=subprocess.run(['git','-C',str(root),*args],capture_output=True)
    if p.returncode:raise ValueError('Required Git provenance check failed')
    return p.stdout


def validate_assignments(split,population):
    if population not in ('primary','sensitivity_only'):raise ValueError('Unsupported population')
    if split.get('benchmark_revision')!=BENCHMARK_REVISION or split.get('excludes_multi_turn') is not True:
        raise ValueError('Unsupported split provenance')
    assignments=split.get('assignments')
    if not isinstance(assignments,dict) or not assignments:raise ValueError('Split assignments missing')
    for group,label in assignments.items():
        if not isinstance(group,str) or not group or set(label)!={'benchmark','population','split'} or label['benchmark'] not in BENCHMARKS or label['population'] not in ('primary','sensitivity_only') or label['split'] not in ('development','test'):
            raise ValueError('Invalid split assignment metadata')
    allowed={g:a for g,a in assignments.items() if a['split']=='development' and a['population']==population}
    expected_groups=split['group_counts'][population]['development']
    expected_rows=split['row_counts'][population]['development']
    if len(allowed)!=expected_groups or expected_rows<1:raise ValueError('Development count metadata inconsistent')
    return assignments,allowed,expected_rows


def decode_development_sample(raw):
    # Called only after canonical assignment has been verified as development.
    sample={k:raw[k] for k in SAMPLE_FIELDS if k in raw}
    for key in ('perturbation','conversation','tools'):
        sample[key]=decode(sample.get(key))
    if not isinstance(sample['conversation'],list) or not isinstance(sample['tools'],list):raise ValueError('Invalid selected development input structure')
    refs=decode(raw.get('golden_answers'))
    cfg=decode(raw.get('eval_config'))
    if not isinstance(refs,list) or not isinstance(cfg,dict):raise ValueError('Invalid selected development reference structure')
    return sample,refs,cfg


def partition_sources(sources,split,population):
    assignments,allowed,expected_rows=validate_assignments(split,population)
    clean_ids={g for g,a in assignments.items() if a['population']=='primary'}
    inputs=[];references=[];seen=set();all_source_keys=set();counts=Counter()
    for file_name,lines in sources:
        if file_name not in SOURCE_FILES:raise ValueError('Unexpected source filename')
        for raw_line in lines:
            if not raw_line.strip():continue
            counts['mixed_source_rows_read']+=1
            try:
                raw=loads(raw_line)
                if not isinstance(raw,dict):raise ValueError('Invalid top-level object')
                if any(not isinstance(raw.get(field),str) for field in ('conversation','tools','golden_answers','eval_config')):
                    raise ValueError('Pinned release requires nested fields as encoded JSON strings')
                if any(field in raw and not isinstance(raw[field],str) for field in ('perturbation','source')):
                    raise ValueError('Optional nested fields must remain encoded JSON strings')
                if is_multi_turn(raw):
                    counts['multi_turn_rows_not_exported']+=1;continue
                row_id=raw.get('id');benchmark=raw.get('benchmark')
                if not isinstance(row_id,str) or not row_id:raise ValueError('Missing row identifier')
                group=canonical_base_id(row_id,clean_ids)
                assignment=assignments.get(group)
                if assignment is None or assignment['benchmark']!=benchmark:raise ValueError('Identity assignment mismatch')
                source_key=file_name+':'+row_id
                if source_key in all_source_keys:raise ValueError('Duplicate source identity')
                all_source_keys.add(source_key)
                # No nested conversations/tools/references are decoded before this guard.
                if group not in allowed:
                    counts['unselected_single_turn_rows_not_exported']+=1;continue
                if source_key in seen:raise ValueError('Duplicate selected identity')
                sample,refs,cfg=decode_development_sample(raw)
                seen.add(source_key)
                inputs.append({'case_key':source_key,'source_file':file_name,'row_id':row_id,'canonical_base_id':group,'benchmark':benchmark,'population':population,'split':'development','source_line_sha256':sha(raw_line.rstrip(b'\r\n') if isinstance(raw_line,bytes) else raw_line.rstrip('\r\n').encode()),'sample':sample})
                references.append({'case_key':source_key,'golden_answers':refs,'eval_config':cfg})
            except (ValueError,TypeError,KeyError) as exc:
                # Never include unknown/test IDs, prompts or reference payloads in errors.
                raise ValueError('Source partition validation failed; inspect trusted partition implementation and source provenance') from None
    if len(inputs)!=expected_rows or {r['canonical_base_id'] for r in inputs}!=set(allowed):raise ValueError('Export does not cover expected development rows/groups')
    inputs.sort(key=lambda r:r['case_key']);references.sort(key=lambda r:r['case_key'])
    membership={'population':population,'split':'development','groups':allowed,'expected_rows':expected_rows,'expected_groups':len(allowed)}
    return inputs,references,membership,dict(counts)


def export(project_root,benchmark_root,output,population):
    project_root=Path(project_root).resolve();benchmark_root=Path(benchmark_root).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Output must be a new directory')
    for protected in (benchmark_root,project_root/'docs',project_root/'src',project_root/'tools',project_root/'.git'):
        if output==protected or protected in output.parents:raise ValueError('Output cannot overwrite source/code paths')
    git(project_root,'merge-base','--is-ancestor',BASE_COMMIT,'HEAD')
    if git(benchmark_root,'rev-parse','HEAD').decode().strip()!=BENCHMARK_REVISION:raise ValueError('Benchmark revision mismatch')
    if git(benchmark_root,'status','--porcelain','--','hf_data/datasets/api_eval'):raise ValueError('Benchmark source data has local changes')
    freeze=loads(git(project_root,'show',BASE_COMMIT+':docs/config/task1_single_sample_v1.json'))
    if freeze['benchmark']['split_sha256']!=SPLIT_SHA or freeze['benchmark']['revision']!=BENCHMARK_REVISION:raise ValueError('Frozen provenance mismatch')
    # The split is read from the pinned Git object, never regenerated or overwritten.
    split_raw=git(project_root,'show',BASE_COMMIT+':'+freeze['benchmark']['split_manifest'])
    if sha(split_raw)!=SPLIT_SHA:raise ValueError('Frozen split hash mismatch')
    split=loads(split_raw)
    data=benchmark_root/'hf_data/datasets/api_eval'
    if data.is_symlink():raise ValueError('Dataset symlink not allowed')
    tree=git(benchmark_root,'ls-tree','-r',BENCHMARK_REVISION,'--','hf_data/datasets/api_eval').decode()
    tracked={}
    for line in tree.splitlines():
        metadata,path=line.split('\t',1);mode,kind,blob=metadata.split()
        if kind!='blob' or mode!='100644':raise ValueError('Unexpected source object')
        name=Path(path).name
        if name not in SOURCE_FILES:raise ValueError('Unexpected tracked evaluation source')
        tracked[name]=blob
    if set(tracked)!=set(SOURCE_FILES) or {p.name for p in data.glob('*.jsonl')}!=set(SOURCE_FILES):raise ValueError('Evaluation source file set differs')
    sources=[];source_hashes={}
    for name in SOURCE_FILES:
        raw=read_regular(data/name)
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if blob!=tracked[name]:raise ValueError('Raw source bytes differ from pinned Git blob; use an unchanged LF checkout')
        source_hashes[name]=sha(raw);sources.append((name,raw.splitlines(keepends=True)))
    inputs,references,membership,counts=partition_sources(sources,split,population)
    payloads={'samples.jsonl':lines_bytes(inputs),'references.jsonl':lines_bytes(references),'membership.json':json_bytes(membership)}
    attestation={'format_version':VERSION,'exporter_base_commit':BASE_COMMIT,'project_head':git(project_root,'rev-parse','HEAD').decode().strip(),'benchmark_revision':BENCHMARK_REVISION,'split_sha256':SPLIT_SHA,'population':population,'partition':'development','row_count':len(inputs),'group_count':len(membership['groups']),'case_key_digest':sha(canonical([r['case_key'] for r in inputs]).encode()),'source_file_hashes':source_hashes,'payload_hashes':{n:sha(v) for n,v in payloads.items()},'code_hashes':code_hashes(),'implementation_hash_scheme':'sha256_source_bytes_with_CRLF_normalized_to_LF','held_out_content_exported':False,'unselected_nested_payloads_decoded':0,'trusted_stage_counts':counts,'access_boundary':'Trusted exporter reads mixed raw bytes/top-level identity metadata; nested input/reference payloads are decoded only for selected development assignments. Auditor receives development-only bundle.','integrity_limit':'Hashes establish consistency, not a cryptographically authenticated partition proof. Trust requires reviewing this exporter and frozen split provenance.'}
    payloads['attestation.json']=json_bytes(attestation)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='dev-export-') as temp:
        temp=Path(temp)
        for name,payload in payloads.items():(temp/name).write_bytes(payload)
        if output.exists():raise ValueError('Output directory appeared during export')
        temp.rename(output)
    return {'rows':len(inputs),'groups':len(membership['groups']),'population':population,'held_out_content_exported':False,'attestation_sha256':sha(payloads['attestation.json'])}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project-root',type=Path,required=True);p.add_argument('--benchmark-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--population',choices=['primary','sensitivity_only'],default='primary');args=p.parse_args()
    try:result=export(args.project_root,args.benchmark_root,args.output,args.population)
    except (ValueError,OSError,KeyError,TypeError):raise SystemExit('Export failed validation; no audit-ready bundle should be used. Check pinned sources, split and local paths. No record contents are printed.')
    import json
    print(json.dumps(result,indent=2))
