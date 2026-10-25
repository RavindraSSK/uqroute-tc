"""Separate bounded review signals; never change official scores or old detectors."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time

HERE=Path(__file__).resolve().parent
POLICY_SHA='90145bab9c13eddbfc92a9de87588b73c59408afc68dd35333227bcde9fa891e'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)


def loads(raw):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result:raise ValueError('Duplicate JSON key')
            result[k]=v
        return result
    def invalid(_):raise ValueError('Nonfinite JSON value')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)


def regular(path):
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file():
        raise ValueError('Expected regular file without symlink ancestors')
    return path.read_bytes()


def policy():
    raw=regular(HERE/'review_policy_v1.json').replace(b'\r\n',b'\n')
    if sha(raw)!=POLICY_SHA:raise ValueError('Versioned review policy differs')
    return loads(raw)


def index(rows):
    result={}
    for row in rows:
        key=row['case_key']
        if key in result:raise ValueError('Duplicate case identity')
        result[key]=row
    return result


def user_segments(messages):
    # Same extraction convention as the old audit. Assistant dialogue and
    # system/tool descriptions are not promoted to user objectives.
    segments=[]
    for m in messages:
        if m['role']!='user':continue
        embedded=re.findall(r'<user>\s*(.*?)\s*</user>',m['content'],re.S|re.I)
        segments.extend(embedded if embedded else [m['content']])
    return segments


def credential_signals(reference,messages,keys):
    result=[]
    for call_index,call in enumerate(reference['golden_answers']):
        args=call.get('parameters') or call.get('arguments') or call.get('Action_Input') or {}
        if not isinstance(args,dict):raise ValueError('Unexpected reference argument shape')
        for name,value in args.items():
            if name not in keys or not isinstance(value,str) or not value:continue
            present=[i for i,m in enumerate(messages) if value in m['content']]
            result.append({'reference_call_index':call_index,'argument_name':name,
                           'literal_present':bool(present),'message_indices_with_literal':present})
    # Values and hashes of credentials are intentionally not emitted.
    return result


def review_case(request,score,reference,cfg):
    key=request['case_key'];benchmark=request['benchmark']
    if score['case_key']!=key or reference['case_key']!=key or score['benchmark']!=benchmark or score['canonical_base_id']!=request['canonical_base_id'] or score['source_file']!=request['source_file']:
        raise ValueError('Case lineage mismatch')
    expected_panel='tooleyes_relevance' if benchmark=='tooleyes' else 'official_reference_compliance'
    if score['panel']!=expected_panel or score['official_labels_changed'] is not False or score['ambiguity_exclusion_applied'] is not False:
        raise ValueError('Official panel or label boundary differs')
    messages=request['request']['messages']
    if [m['role'] for m in messages]!=['system','user'] or any(not isinstance(m['content'],str) for m in messages):
        raise ValueError('Unexpected prediction boundary')
    if sha(canonical(messages).encode())!=request['messages_sha256'] or sha(canonical(request['request']).encode())!=request['request_sha256']:
        raise ValueError('Prepared prompt/body hash differs')
    credentials=credential_signals(reference,messages,set(cfg['credential_argument_keys']))
    segments=user_segments(messages);phrases={}
    old={}
    for kind,pattern in cfg['supplemental_user_phrase_patterns'].items():
        detected=score['objective_detection'][kind+'_explicit_detected']
        if type(detected) is not bool:raise ValueError('Invalid old detector value')
        old[kind+'_explicit_detected']=detected
        hits=[{'user_segment_index':i,'matched_text':m.group(0),'start':m.start(),'end':m.end()}
              for i,text in enumerate(segments) for m in re.finditer(pattern,text,re.I)]
        phrases[kind]={'hits':hits,'supplemental_phrase_present':bool(hits),
                       'old_detector_nondetection_with_new_phrase':bool(hits) and not detected}
    return {'case_key':key,'benchmark':benchmark,'source_file':score['source_file'],'panel':score['panel'],
            'official_score':score['official_score'],'original_reference_review_flags':score['reference_review_flags'],
            'original_objective_detection_flags':old,'credential_literal_checks':credentials,
            'reference_credential_literal_absence_signal':any(not c['literal_present'] for c in credentials),
            'supplemental_user_phrase_diagnostics':phrases,
            'semantic_adjudication':'not_performed','preference_success':'not_assessed',
            'official_labels_changed':False,'original_detector_changed':False,'excluded':False}


def summarize(rows,cfg):
    def counts(items):
        flagged=[r for r in items if r['reference_credential_literal_absence_signal']]
        return {'rows':len(items),'official_correct':sum(r['official_score']['correct'] for r in items),
                'credential_literal_absence_signal_rows':len(flagged),
                'credential_signal_official_correct':sum(r['official_score']['correct'] for r in flagged),
                'credential_signal_official_noncompliant':sum(not r['official_score']['correct'] for r in flagged),
                'new_phrase_with_old_nondetection':{kind:sum(r['supplemental_user_phrase_diagnostics'][kind]['old_detector_nondetection_with_new_phrase'] for r in items)
                    for kind in cfg['supplemental_user_phrase_patterns']}}
    return {'version':cfg['version'],'scope':cfg['scope'],'rows':len(rows),
            'by_panel':{p:counts([r for r in rows if r['panel']==p]) for p in ('official_reference_compliance','tooleyes_relevance')},
            'by_benchmark':{b:counts([r for r in rows if r['benchmark']==b]) for b in sorted({r['benchmark'] for r in rows})},
            'original_detector_changed':False,'official_labels_changed':False,'ambiguity_exclusions_applied':False,
            'semantic_adjudication':'not_performed','preference_success':'not_assessed',
            'held_out_access_enabled':False,'main_experiment_ready':False,'network_requests':0,'prior_files_modified':False,
            'limits':['Literal absence is not proof of semantic unavailability or an erroneous reference.',
                      'Literal presence may occur in a tool declaration or irrelevant dialogue; it is not proof the value should be used.',
                      'Credential-like keys are a fixed bounded list; no nested/encoded credential inference is performed.',
                      'Supplemental phrase matches are retrospective review signals, not corrected intent labels; negation, quotations and scope need manual review.',
                      'User-segment extraction retains the old audit convention and may require review for malformed role tags.',
                      'No-hit is not absent intent; flags overlap and never remove cases or change official scores.',
                      'Official compliance, ToolEyes relevance and cost/latency preference remain separate.',
                      'No metric calibration, threshold selection, AUROC/AP or main-experiment freeze is performed.']}


def publish(source,output):
    for attempt in range(6):
        if output.exists() or output.is_symlink():raise ValueError('Output exists; preserve it')
        try:source.rename(output);return
        except PermissionError:
            if attempt==5:raise
            time.sleep(0.1*(2**attempt))


def run(repo,output):
    for p in (repo,output):
        if any(q.is_symlink() for q in (p,*p.parents)):raise ValueError('Symlink path')
    repo,output=repo.resolve(),output.absolute();cfg=policy()
    root=repo/'artifacts/local_development_audits'
    paths={'scores.json':root/'corrected_qwen15b_coverage_official_scoring_v1/scores.json',
           'provenance.json':root/'corrected_qwen15b_coverage_official_scoring_v1/provenance.json',
           'coverage_reference_review_inputs_v1.json':root/'coverage_reference_review_inputs_v1.json',
           'prepared/manifest.json':root/'corrected_qwen15b_coverage_import_217d4a47/prepared/manifest.json',
           'prepared/requests.json':root/'corrected_qwen15b_coverage_import_217d4a47/prepared/requests.json'}
    if not output.resolve().is_relative_to(root) or output.resolve()==root:raise ValueError('Output must be inside local development artifacts')
    if output.exists():raise ValueError('Output already exists; preserve it')
    for p in paths.values():
        if output.resolve() in p.resolve().parents or output.resolve()==p.resolve() or (p.parent.resolve()!=root and p.parent.resolve() in output.resolve().parents):
            raise ValueError('Output overlaps inputs')
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',cfg['baseline_commit'],'HEAD'],capture_output=True,check=True)
    raw={}
    for name,p in paths.items():
        raw[name]=regular(p)
        if sha(raw[name])!=cfg['input_sha256'][name]:raise ValueError('Approved input fingerprint differs: '+name)
    scores=index(loads(raw['scores.json']));provenance=loads(raw['provenance.json'])
    reference_bundle=loads(raw['coverage_reference_review_inputs_v1.json'])
    if reference_bundle['scope']!='selected-primary-development-references-only' or reference_bundle['source_sha256']!='ec1bccc61aca1fb57eefd072fb81e3a9b37ed7aabc2575b161e4033abbe0df93':
        raise ValueError('Reference extract is not the approved development-only selection')
    refs=index(reference_bundle['references']);manifest=loads(raw['prepared/manifest.json']);requests=loads(raw['prepared/requests.json'])
    if manifest['scope']!='corrected-primary-development-only' or manifest['selection']!='coverage' or manifest['held_out_access_enabled'] is not False or manifest['main_experiment_ready'] is not False:
        raise ValueError('Prepared development boundary differs')
    if sha(canonical(requests).encode())!=manifest['requests_sha256'] or manifest['request_count']!=69:
        raise ValueError('Prepared request hash/count differs')
    if len(requests)!=69 or len(scores)!=69 or len(refs)!=69 or set(scores)!=set(refs) or set(index(requests))!=set(scores):
        raise ValueError('Selected identities differ')
    # Scoring provenance itself is approved by hash above. It predates the
    # publication-only fix, so do not rewrite it to pretend later code produced it.
    for suffix,expected in [('attestation.json','77071dc342a19b0f32995fed9f9f9e25840294e633ef5368830f07a3ccf3ccb9'),
                            ('references.jsonl',reference_bundle['source_sha256'])]:
        matching=[v for k,v in provenance['input_sha256'].items() if k.endswith('/full_primary_export_v1/'+suffix)]
        if matching!=[expected]:raise ValueError('Scoring reference provenance differs')
    rows=[review_case(r,scores[r['case_key']],refs[r['case_key']],cfg) for r in requests]
    report=summarize(rows,cfg)
    for name,p in paths.items():
        if regular(p)!=raw[name]:raise ValueError('Input changed during diagnostics')
    audit={'baseline_commit':cfg['baseline_commit'],'policy_sha256':POLICY_SHA,
           'implementation_sha256_lf':sha(regular(Path(__file__)).replace(b'\r\n',b'\n')),
           'input_sha256':{p.relative_to(repo).as_posix():sha(raw[n]) for n,p in paths.items()},
           'references':'Only the previously hash-approved 69-case development extract; no full reference sidecar or split opened.'}
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='reference-review-') as tmp:
        temp=Path(tmp).resolve()
        for name,value in {'diagnostics.json':rows,'summary.json':report,'provenance.json':audit}.items():
            with (temp/name).open('x',encoding='utf-8') as stream:stream.write(canonical(value)+'\n')
        publish(temp,output)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:report=run(a.repo_root,a.output)
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        raise SystemExit('Reference review stopped: '+str(exc)+'. Preserve all existing inputs/outputs.') from None
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
