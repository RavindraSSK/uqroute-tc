"""Prepare corrected repeated-sample proposals; no dispatch or reference access."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
import selection

HERE=Path(__file__).resolve().parent
ROOT=Path('artifacts/local_development_audits')


def run(repo,output):
    repo=repo.absolute();output=output.absolute()
    if any(p.is_symlink() for v in (repo,output) for p in (v,*v.parents)):raise ValueError('Symlink path rejected')
    repo=repo.resolve();output=output.resolve();root=repo/ROOT
    if output.exists() or not output.is_relative_to(root) or output==root:raise ValueError('Fresh development output required')
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor','a2fb64d','HEAD'],check=True)
    policy=json.loads((HERE/'policy.json').read_text())
    for name,wanted in policy['source_sha256_lf'].items():
        path=repo/name
        if any(p.is_symlink() for p in (path,*path.parents)) or selection.sha(path.read_bytes().replace(b'\r\n',b'\n'))!=wanted:raise ValueError('Source fingerprint differs: '+name)
    workflow_dir=repo/'tools/development_audits/corrected_generation_v1';sys.path.insert(0,str(workflow_dir))
    import workflow
    plans={};ledger={}
    for model,item in policy['models'].items():
        prepared=root/item['prepared']
        for name in ('manifest.json','requests.json'):
            path=prepared/name
            if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('Symlink input')
            ledger[path]=selection.sha(path.read_bytes())
        manifest,rows=workflow.load_plan(repo,prepared,item['manifest_sha256'])
        if manifest['selection']!='full-development' or manifest['held_out_access_enabled'] is not False or len(rows)!=1728:raise ValueError('Not full development')
        plans[model]=(manifest,rows)
    reference=plans['qwen15b'][1]
    for model,(_,rows) in plans.items():
        if [r['case_key'] for r in rows]!=[r['case_key'] for r in reference]:raise ValueError('Model identity/order differs')
        for a,b in zip(reference,rows):
            if any(a[f]!=b[f] for f in ('benchmark','source_file','canonical_base_id')):raise ValueError('Model lineage differs')
            if {k:v for k,v in a['request'].items() if k!='model'}!={k:v for k,v in b['request'].items() if k!='model'}:raise ValueError('Prompt/settings differ')
    chosen,pairs=selection.select(reference);keys=[r['case_key'] for r in chosen]
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent,prefix='corrected-repeated-preparation-') as folder:
        temp=Path(folder).resolve();transfers={}
        for model,(old,rows) in plans.items():
            index={r['case_key']:r for r in rows};slots=selection.expand([index[k] for k in keys])
            raw=(selection.canonical(slots)+'\n').encode()
            manifest={'version':policy['version'],'scope':'corrected-primary-development-repeated-sampling-proposal','model_settings':old['model_settings'],'server_settings':old['server_settings'],'source_prepared_manifest_sha256':policy['models'][model]['manifest_sha256'],'cases':30,'pairs':15,'groups':15,'requests':300,'requests_sha256':selection.sha(raw),'sample_seeds':list(range(1729,1739)),'held_out_access_enabled':False,'main_experiment_ready':False,'dispatch_authorized':False,'case_keys':keys,'pairs_manifest':pairs,'selection':'Original hash ranking applied to constructed full-development candidates; three disjoint groups per benchmark; not the original frozen subset digest.','status_policy_authority':'docs/config/task2_repeated_sampling_v1.json','runner_status':'Dedicated resumable repeated-slot runner and review required; incompatible with single-sample workflow.run.'}
            manifest_raw=(selection.canonical(manifest)+'\n').encode();dest=temp/model;dest.mkdir()
            (dest/'manifest.json').write_bytes(manifest_raw);(dest/'requests.json').write_bytes(raw)
            archive=temp/(model+'_corrected_repeated_transfer_v1.zip')
            with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
                z.writestr('manifest.json',manifest_raw);z.writestr('requests.json',raw)
            with zipfile.ZipFile(archive) as z:
                if z.testzip() is not None:raise ValueError('ZIP integrity failed')
            transfers[model]={'file':archive.name,'sha256':selection.sha(archive.read_bytes()),'manifest_sha256':selection.sha(manifest_raw),'requests':300}
        for path,wanted in ledger.items():
            if selection.sha(path.read_bytes())!=wanted:raise ValueError('Input changed')
        summary={'version':policy['version'],'cases_per_model':30,'pairs_per_model':15,'groups_per_model':15,'requests_per_model':300,'total_proposed_requests':900,'transfers':transfers,'held_out_access_enabled':False,'main_experiment_ready':False,'dispatch_authorized':False,'generation_requests_sent':0,'prior_outputs_modified':False,'selection_case_keys':keys}
        (temp/'summary.json').write_text(selection.canonical(summary)+'\n',encoding='utf-8')
        (temp/'provenance.json').write_text(selection.canonical({'policy':policy,'input_sha256':{p.relative_to(repo).as_posix():h for p,h in ledger.items()}})+'\n',encoding='utf-8')
        # Same no-replace publication helper used by the existing analysis tools.
        core=repo/'tools/development_audits/three_model_uncertainty_v1';sys.path.insert(0,str(core));import engine
        engine.publish(temp,output)
    print(json.dumps(summary,indent=2));print('Preparation complete:',output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo-root',type=Path,default=Path('.'));p.add_argument('--output',type=Path,default=ROOT/'corrected_repeated_preparation_v1');a=p.parse_args();run(a.repo_root,a.output)
