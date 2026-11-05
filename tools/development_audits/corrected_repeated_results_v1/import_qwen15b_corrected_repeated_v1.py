"""Import pinned Qwen repeated evidence and reproduce its CPU replay; no inference."""
from pathlib import Path,PurePosixPath
import hashlib
import importlib.util
import json
import stat
import subprocess
import sys
import zipfile

ZIP='3487190ea5c1f8b20928207910c00ecf8c2cab913acf684c8f051b0ca47eb3bc'
CLIENT='7838fb504edd2a3cdf369d1e5f8dfe4093acedae69e5b778454f4cacdc0abc2c'
MANIFEST='dcc66fe09db0db00adc860d6b1b0f4e19f2fbbaa225e2b0bc648c93b26d08b07'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def validate(source):
    if sha(source.read_bytes())!=ZIP:raise ValueError('ZIP fingerprint differs')
    with zipfile.ZipFile(source) as z:
        entries=z.infolist();names=[e.filename for e in entries]
        if len(names)!=929 or len({n.casefold() for n in names})!=929 or z.testzip() is not None:raise ValueError('Archive inventory/integrity differs')
        for e in entries:
            p=PurePosixPath(e.filename)
            if p.is_absolute() or not p.parts or '..' in p.parts or '\\' in e.filename or ':' in e.filename or p.parts[0] not in {'prepared','metadata','run','replay'} or stat.S_ISLNK(e.external_attr>>16) or any(part.endswith((' ','.')) for part in p.parts):raise ValueError('Unsafe archive member')
        data={e.filename:z.read(e) for e in entries if not e.is_dir()}
    hashes=json.loads(data['metadata/export_file_hashes.json'])
    if len(hashes)!=928 or set(hashes)!=set(data)-{'metadata/export_file_hashes.json'}:raise ValueError('Evidence inventory differs')
    for n,h in hashes.items():
        if sha(data[n])!=h:raise ValueError('Member differs: '+n)
    if sha(data['metadata/repeated_client.py'])!=CLIENT or sha(data['prepared/manifest.json'])!=MANIFEST:raise ValueError('Code/plan binding differs')
    binding=json.loads(data['run/run_manifest.json'])
    if binding['client_sha256']!=CLIENT or binding['prepared_manifest_sha256']!=MANIFEST or binding['runtime_sha256']!=sha(data['metadata/runtime.json']) or binding['held_out_access_enabled'] is not False or binding['main_experiment_ready'] is not False or binding['automatic_retries']!=0 or binding['request_count']!=300:raise ValueError('Run binding differs')
    return data,binding


def main():
    repo=Path.cwd().resolve();source=Path(sys.argv[1]) if len(sys.argv)>1 else Path.home()/'Downloads/uqroute_qwen15b_corrected_repeated_6e710e52.zip'
    root=repo/'artifacts/local_development_audits';target=root/'corrected_qwen15b_repeated_import_6e710e52';replay=root/'corrected_qwen15b_repeated_local_replay_v1'
    for path in (target,replay):
        if path.exists() or any(p.is_symlink() for p in (path,*path.parents)):raise SystemExit('Output exists or symlink ancestor; preserve it.')
    data,binding=validate(source)
    subprocess.run(['git','merge-base','--is-ancestor','0bf4fe6','HEAD'],check=True)
    subprocess.run([sys.executable,'tools/development_audits/corrected_generation_v1/workflow.py','--repo-root',str(repo),'check-sources'],check=True)
    target.mkdir(parents=True,exist_ok=False)
    for name,raw in data.items():
        dest=target.joinpath(*PurePosixPath(name).parts);dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb') as stream:stream.write(raw)
    print('ZIP and 928 evidence member fingerprints verified; imported:',target,flush=True)
    spec=importlib.util.spec_from_file_location('_pinned_qwen_repeated_client',target/'metadata/repeated_client.py');client=importlib.util.module_from_spec(spec);spec.loader.exec_module(client)
    manifest,rows=client.load(target/'prepared')
    sys.path.insert(0,str(repo/'tools/development_audits/corrected_generation_v1'));import workflow
    workflow.check_runtime(json.loads((target/'metadata/runtime.json').read_bytes()),manifest)
    frozen=workflow.methods(repo)
    result=client.replay(rows,target/'run',replay,binding,lambda response,bench:workflow.evaluate(response,bench,frozen))
    expected=json.loads((target/'replay/summary.json').read_bytes())
    if result!=expected:raise ValueError('Local replay summary differs; preserve evidence for review')
    if json.loads((replay/'records.json').read_bytes())!=json.loads((target/'replay/records.json').read_bytes()):raise ValueError('Local replay records differ')
    for name,raw in data.items():
        if target.joinpath(*PurePosixPath(name).parts).read_bytes()!=raw:raise ValueError('Imported input changed')
    subprocess.run(['git','check-ignore',str((target/'prepared/manifest.json').relative_to(repo)),str((replay/'summary.json').relative_to(repo))],check=True)
    print('FULL LOCAL REPLAY SUMMARY, RECORDS AND EVIDENCE HASHES: MATCH')
    print('No inference, scoring, model retries, Git staging, commit or push performed.')
    print('Held-out access remains disabled. Existing outputs preserved.')


if __name__=='__main__':main()
