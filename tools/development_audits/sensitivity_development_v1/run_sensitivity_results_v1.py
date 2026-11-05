"""Verify/import the completed sensitivity bundle, replay and score on CPU."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import importlib.util
import io
import json
from pathlib import Path,PurePosixPath
import shutil
import stat
import sys
import tempfile
import zipfile

ROOT=Path('artifacts/local_development_audits')
OUTPUT=ROOT/'sensitivity_development_results_v1'
AUDIT=ROOT/'sensitivity_development_audit_v1'
ARCHIVE='uqroute_sensitivity_development_evidence_b5718d0f.zip'
ZIP_SHA='699d80a6441fbec37669857ee23cf0b5c6f7d969280e4a838b7d0d42281b57cf'
CLIENT_SHA='4bb85c817c76fd41f2c05255ba772730d1cc44271771853ecaba096102a5b951'
RUNNER_SHA='75dde7b0014b546e2aa39f230f2db6e14f434d129ecc59c5a7db4516c7fbecc2'
ATTESTATION_SHA='b23c8fb207558c65867ebcb737566a677d41e867436d039cc898f9ef67f41092'
CANDIDATES_SHA='747d9feca7c79629873b9f43468d9db3d2e8b586f211994d7c94dece8dcf7d13'
SCORER='tools/development_audits/full_development_scoring_v1/score_full.py'
METRICS='tools/development_audits/three_model_uncertainty_v1/metrics.py'
SOURCE_PINS={
 SCORER:'af44aee3371f62ba6d0ba5ec6b31764d46d4a21e61c30fb21b15ccb82ef880e8',
 METRICS:'c42316319649629378b968915ed3cfeb366f5ce785364948c5c5a507d6d248ff',
}
MODELS=('qwen15b','llama3b','qwen7b')
MEASURES=('max_token_surprisal','mean_token_nll','sequence_nll','meaningful_mean_token_nll')
IDENTITY=('case_key','benchmark','canonical_base_id','source_file')
sys.dont_write_bytecode=True


def sha(raw):
 return hashlib.sha256(raw).hexdigest()


def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path)
 obj=importlib.util.module_from_spec(spec)
 exec(compile(path.read_bytes(),str(path),'exec'),obj.__dict__)
 return obj


def unpack(raw,roots):
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  entries=z.infolist()
  names=[r.filename for r in entries]
  if len({n.casefold() for n in names})!=len(names) or z.testzip() is not None:
   raise ValueError('Duplicate or corrupt archive members')
  if sum(r.file_size for r in entries)>100_000_000:
   raise ValueError('Unexpected archive size')
  for e in entries:
   p=PurePosixPath(e.filename)
   if (p.is_absolute() or not p.parts or '..' in p.parts or '\\' in e.filename or ':' in e.filename
       or p.parts[0] not in roots or stat.S_ISLNK(e.external_attr>>16)
       or any(t.endswith((' ','.')) for t in p.parts)):
    raise ValueError('Unsafe archive member')
  return {e.filename:z.read(e) for e in entries if not e.is_dir()}


def verify_archive(path):
 raw=path.read_bytes()
 if sha(raw)!=ZIP_SHA:
  raise ValueError('Completed evidence ZIP SHA-256 differs')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  if z.testzip() is not None:
   raise ValueError('Outer archive is corrupt')
  inventory=json.loads(z.read('archives.json'))
  if set(inventory)!=set(MODELS) or len(z.namelist())!=4:
   raise ValueError('Expected three model archives')
  payloads={}
  for model in MODELS:
   entry=inventory[model];name=entry['archive']
   if name!=PurePosixPath(name).name or not name.startswith('uqroute_'+model+'_sensitivity_development_'):
    raise ValueError('Unexpected model archive name')
   data=z.read(name)
   if sha(data)!=entry['sha256']:
    raise ValueError('Nested archive SHA-256 differs')
   members=unpack(data,{'prepared','metadata','run','replay'})
   hashes=json.loads(members['metadata/export_file_hashes.json'])
   if len(hashes)!=168 or set(hashes)!=set(members)-{'metadata/export_file_hashes.json'}:
    raise ValueError('Expected 168 fingerprinted evidence members per model')
   for n,h in hashes.items():
    if sha(members[n])!=h:
     raise ValueError('Evidence member fingerprint differs')
   if (sha(members['metadata/sensitivity_client.py'])!=CLIENT_SHA
       or sha(members['metadata/execution_source.py'])!=RUNNER_SHA):
    raise ValueError('Reviewed execution source differs')
   payloads[model]=members
 return payloads


def audit_inputs(repo,sc,ledger):
 base=repo/AUDIT
 def checked(name,pin=None):
  path=base/name
  raw=sc.regular(path)
  digest=sha(raw)
  if pin is not None and digest!=pin:
   raise ValueError('Development audit fingerprint differs: '+name)
  ledger[path]=digest
  return sc.loads(raw)
 att=checked('export/attestation.json',ATTESTATION_SHA)
 if (att['population']!='sensitivity_only' or att['partition']!='development'
     or att['held_out_content_exported'] is not False or att['unselected_nested_payloads_decoded']!=0
     or (att['row_count'],att['group_count'])!=(35,34)):
  raise ValueError('Unexpected development reference boundary')
 member=checked('export/membership.json',att['payload_hashes']['membership.json'])
 groups=member['groups']
 if len(groups)!=34 or any(x!={'benchmark':'bfcl_v3','population':'sensitivity_only','split':'development'} for x in groups.values()):
  raise ValueError('Sensitivity membership differs')
 ref_path=base/'export/references.jsonl'
 raw=sc.checked(ref_path,att['payload_hashes']['references.jsonl'],ledger)
 refs=sc.unique_index([sc.loads(line) for line in raw.splitlines() if line.strip()])
 inventory=sc.unique_index(checked('audit/inventory.json'))
 candidates=sc.unique_index(checked('audit/candidates.json',CANDIDATES_SHA))
 keys=sorted(candidates)
 if (len(keys)!=35 or set(refs)!=set(keys) or set(inventory)!=set(keys)
     or sha(sc.canonical(keys).encode())!=att['case_key_digest']
     or {r['canonical_base_id'] for r in inventory.values()}!=set(groups)):
  raise ValueError('Audit and reference identities differ')
 for key,r in inventory.items():
  if (r['population']!='sensitivity_only' or r['split']!='development' or r['benchmark']!='bfcl_v3'
      or r['source_file']=='clean.jsonl' or r['construction_status']!='candidate'
      or r['reference_audit_status']!='completed_bounded_signals_only'
      or r['official_labels_changed'] is not False
      or r['source_reference_sha256']!=sha(sc.canonical(refs[key]).encode())):
   raise ValueError('Development reference lineage differs')
 return refs,inventory,candidates


def case_score(request,response,saved,row,ref,sc,w,frozen,parser,official):
 result=w.evaluate(response,'bfcl_v3',frozen)
 if sc.canonical(result)!=sc.canonical(saved) or result['status']!='complete':
  raise ValueError('Saved response validation differs')
 if (row['population']!='sensitivity_only' or row['split']!='development'
     or any(request[k]!=row[k] for k in IDENTITY)
     or request['messages_sha256']!=row['corrected_messages_sha256']
     or request['messages_sha256']!=w.digest(request['request']['messages'])):
  raise ValueError('Sensitivity response lineage differs')
 cfg=ref['eval_config']
 if cfg.get('method','exact_match')!='exact_match' or (cfg.get('metrics') or ['complete_accuracy'])[0]!='complete_accuracy':
  raise ValueError('Expected BFCL exact-match dispatch')
 raw=response['choices'][0]['message']['content']
 calls=parser(raw,'bfcl_v3')
 score=official({'benchmark':'bfcl_v3','eval_config':cfg,'golden_answers':ref['golden_answers'],
                 'prediction':{'tool_calls':calls}})
 audit=row['reference_audit']
 if audit['changes_official_labels'] is not False or audit['excluded'] is not False:
  raise ValueError('Reference flags cannot relabel or exclude outcomes')
 return {**{k:request[k] for k in IDENTITY},
         'population':'sensitivity_only','split':'development','panel':'official_reference_compliance',
         'official_score':score,'evidence_status':result['status'],'parser_status':result['parser_status'],
         'official_parser_call_count':len(calls),'whole_output_scores':result['whole_output_scores'],
         'whole_output_unavailable':result['whole_output_unavailable'],
         'meaningful_token_score':result['meaningful_token_score'],
         'meaningful_token_unavailable':result['meaningful_token_unavailable'],
         'reference_review_flags':audit['review_flags'],'official_labels_changed':False}


def signal(row,name):
 if name=='meaningful_mean_token_nll':
  v=row['meaningful_token_score']
  return None if v is None else v['mean_token_nll']
 v=row['whole_output_scores']
 return None if v is None else v[name]


def summarize(scores,metrics,session):
 def cohort(rows,measure):
  labels=[not r['official_score']['correct'] for r in rows]
  values=[signal(r,measure) for r in rows]
  return {'discrimination':metrics.discrimination(labels,values),
          'risk_coverage':metrics.risk_coverage(labels,values,len(scores))}
 n=len(scores);correct=sum(r['official_score']['correct'] for r in scores)
 return {'rows':n,'canonical_groups':len({r['canonical_base_id'] for r in scores}),
         'reference_matches':correct,'reference_compliance':correct/n,
         'mean_official_score':sum(r['official_score']['score'] for r in scores)/n,
         'whole_output_eligible':sum(r['whole_output_scores'] is not None for r in scores),
         'meaningful_token_eligible':sum(r['meaningful_token_score'] is not None for r in scores),
         'flagged_rows_retained':sum(bool(r['reference_review_flags']) for r in scores),
         'reference_flag_counts':dict(Counter(f for r in scores for f in r['reference_review_flags'])),
         'evidence_status_counts':dict(Counter(r['evidence_status'] for r in scores)),
         'batch_wall_seconds_excluding_setup':session['known_finished_session_wall_seconds'],
         'available_case_metrics':{m:cohort([r for r in scores if signal(r,m) is not None],m) for m in MEASURES}}


def make_report(summary):
 lines=['# Sensitivity-only development results','',
        '35 BFCL same-name perturbations from 34 development groups per model.',
        'This extension has no clean anchors. Reference matching is not execution success.',
        'All 105 responses completed. Every model replay matched the exported evidence.','',
        '| Model | Reference matches | Compliance | Whole eligible | Meaningful eligible | Flagged rows retained | Batch seconds |',
        '|---|---:|---:|---:|---:|---:|---:|']
 for model,r in summary['models'].items():
  lines.append(f'| {model} | {r["reference_matches"]}/{r["rows"]} | {r["reference_compliance"]:.1%} | '
               f'{r["whole_output_eligible"]} | {r["meaningful_token_eligible"]} | {r["flagged_rows_retained"]} | {r["batch_wall_seconds_excluding_setup"]:.2f} |')
 lines+=['','Reference-review flags are retained without exclusions or relabeling.',
         'The flags are structural review signals, not adjudicated reference errors.',
         'Inspect model scores.json and reference_flag_counts in summary.json.','',
         '## Matched cases across all three models','',
         'Each model uses its own reference-error labels; shared cases do not imply shared outcomes.',
         'AP is noninterpolated average precision; compare it with error prevalence.','',
         '| Measure | Cases | Model | Error AUROC | AP | Error prevalence |',
         '|---|---:|---|---:|---:|---:|']
 def fmt(x):return 'undefined' if x is None else f'{x:.3f}'
 for measure,cohort in summary['matched_by_measure'].items():
  for model,m in cohort['models'].items():
   lines.append(f'| {measure} | {cohort["rows"]} | {model} | {fmt(m["auroc"])} | '
                f'{fmt(m["average_precision"])} | {fmt(m["error_prevalence"])} |')
 lines+=['','Full measure comparisons belong on the all-model/all-measure intersection:',
         str(summary['all_models_all_measures_rows'])+' cases. See summary.json for those metrics.','',
         'Keep this extension separate from primary-development estimates. It contains',
         'additional BFCL groups, not a new five-benchmark experiment. No clean/perturbed',
         'paired change can be estimated for these cases. The observed success rates',
         'condition on this small selected source population and do not establish model superiority.',
         'No calibration refit, routing threshold, final freeze or held-out evaluation is performed.',
         'Generation timing excludes setup/model loading and is not online cascade latency.','']
 return '\n'.join(lines)


def run(repo,archive):
 out=repo/OUTPUT
 if out.exists() or any(p.is_symlink() for p in (out,*out.parents)):
  raise ValueError('Output already exists or has a symlink ancestor; preserve it')
 for p,h in SOURCE_PINS.items():
  if sha((repo/p).read_bytes().replace(b'\r\n',b'\n'))!=h:
   raise ValueError('Scoring source fingerprint differs')
 payloads=verify_archive(archive)
 sc=module('_sensitivity_scoring_helpers',repo/SCORER)
 metrics=module('_sensitivity_metrics',repo/METRICS)
 w,frozen,parser,official=sc.load_dependencies(repo,sc.policy())
 ledger={}
 refs,inventory,candidates=audit_inputs(repo,sc,ledger)
 out.parent.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(dir=out.parent,prefix='sensitivity-results-') as tmp:
  stage=Path(tmp)/'result';stage.mkdir()
  scores_by_model={};results={}
  original_loader=w.load_plan
  try:
   for model in MODELS:
    evidence=stage/model/'evidence';evidence.mkdir(parents=True)
    for name,raw in payloads[model].items():
     dest=evidence.joinpath(*PurePosixPath(name).parts)
     dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    client=module('_sensitivity_client_'+model,evidence/'metadata/sensitivity_client.py')
    pin=client.PINS[model][1]
    prepared=evidence/'prepared'
    manifest,requests=client.load_plan(repo,prepared,pin,model,w)
    if set(r['case_key'] for r in requests)!=set(refs):
     raise ValueError('Prepared cases differ from approved sensitivity references')
    if any(r['request']['messages']!=candidates[r['case_key']]['messages'] for r in requests):
     raise ValueError('Candidate prompts differ from generation inputs')
    for path in (evidence/'run',stage/model/'local_replay'):
     w.artifact_path(repo,path,(prepared,))
    w.load_plan=lambda rp,pr,ex,model=model,client=client:client.load_plan(rp,pr,ex,model,w)
    replay=stage/model/'local_replay'
    print('Replaying saved sensitivity evidence:',model,flush=True)
    w.replay(repo,prepared,pin,evidence/'run',replay)
    for name in ('records.json','summary.json'):
     if (replay/name).read_bytes()!=(evidence/'replay'/name).read_bytes():
      raise ValueError('Full local replay does not match exported bytes')
    session=sc.loads((replay/'summary.json').read_bytes())
    if session['status_counts']!={'complete':35}:
     raise ValueError('Unexpected outcome status inventory')
    scores=[]
    for request in requests:
     key=request['case_key'];folder=evidence/'run/cases'/w.sha(key.encode())
     ref=refs[key];row=inventory[key]
     score=case_score(request,sc.loads((folder/'http_response.bin').read_bytes()),
                      sc.loads((folder/'validation.json').read_bytes()),row,ref,sc,w,frozen,parser,official)
     scores.append(score)
    scores_by_model[model]=scores
    results[model]=summarize(scores,metrics,session)
    (stage/model/'scores.json').write_text(sc.canonical(scores)+'\n',encoding='utf-8')
  finally:
   w.load_plan=original_loader
  index={m:sc.unique_index(r) for m,r in scores_by_model.items()}
  keys=sorted(refs)
  matched={}
  all_joint=[k for k in keys if all(signal(index[m][k],s) is not None for m in MODELS for s in MEASURES)]
  for measure in MEASURES:
   joint=[k for k in keys if all(signal(index[m][k],measure) is not None for m in MODELS)]
   matched[measure]={'rows':len(joint),'case_keys':joint,'models':{
    m:metrics.discrimination([not index[m][k]['official_score']['correct'] for k in joint],
                             [signal(index[m][k],measure) for k in joint]) for m in MODELS}}
  summary={'scope':'sensitivity_only_development_results','models':results,
           'matched_by_measure':matched,'all_models_all_measures_rows':len(all_joint),
           'all_models_all_measures':{s:{m:metrics.discrimination(
                [not index[m][k]['official_score']['correct'] for k in all_joint],
                [signal(index[m][k],s) for k in all_joint]) for m in MODELS} for s in MEASURES},
           'all_models_all_measures_case_keys':all_joint,
           'held_out_access_enabled':False,'main_experiment_ready':False,
           'inference_requests':0,'official_labels_changed':False}
  for path,pin in ledger.items():
   if sha(sc.regular(path))!=pin:
    raise ValueError('Development reference inputs changed during scoring')
  hashes={p.relative_to(stage).as_posix():sha(p.read_bytes()) for p in stage.rglob('*') if p.is_file()}
  provenance={'completed_zip_sha256':ZIP_SHA,'sources_sha256_lf':SOURCE_PINS,
              'development_inputs_sha256':{p.relative_to(repo).as_posix():v for p,v in ledger.items()},
              'imported_and_generated_evidence_sha256':hashes,'analysis_source_sha256':sha(Path(__file__).read_bytes())}
  for name,value in [('summary.json',summary),('provenance.json',provenance)]:
   (stage/name).write_text(sc.canonical(value)+'\n',encoding='utf-8')
  (stage/'REPORT.md').write_text(make_report(summary),encoding='utf-8')
  shutil.copyfile(Path(__file__),stage/'analysis_source.py')
  sc.publish_directory(stage,out)
 print(json.dumps({m:{k:v for k,v in r.items() if k!='available_case_metrics'} for m,r in results.items()},indent=2))
 print('Scored 105 saved responses; local replays MATCH; no inference or Git mutation.')
 print('Report:',out/'REPORT.md')
 return summary


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('archive',nargs='?',type=Path,default=Path.home()/'Downloads'/ARCHIVE)
 a=p.parse_args()
 run(Path.cwd().resolve(),a.archive)
