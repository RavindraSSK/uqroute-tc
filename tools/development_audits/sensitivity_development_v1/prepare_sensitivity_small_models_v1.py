"""Prepare three corrected sensitivity-only development transfer ZIPs; no inference."""
from __future__ import annotations

from collections import Counter
import hashlib
import importlib
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path('artifacts/local_development_audits')
AUDIT = ROOT / 'sensitivity_development_audit_v1'
OUTPUT = ROOT / 'sensitivity_small_models_preparation_v1'
WORKFLOW = Path('tools/development_audits/corrected_generation_v1')
CODE = {
    'support.py': '4aac9f16ed6a03fa833ab3fbaf321127c3043194273c91f79c4f2bda167dbc47',
    'workflow.py': '01a881a67e9b80c81f09268e878502b48bb640398c9729f5eed1ffc47b843831',
}
CANDIDATES_SHA = '747d9feca7c79629873b9f43468d9db3d2e8b586f211994d7c94dece8dcf7d13'
ATTESTATION_SHA = 'b23c8fb207558c65867ebcb737566a677d41e867436d039cc898f9ef67f41092'
SPLIT_SHA = '688c1013d8fe9d5c1b454d14d4cbe215659e48adc7bdfd63175580e83e2eb0db'
BENCHMARK_REVISION = 'd5d03180de41eb30a6c796d04a9bfbd9dad85c1d'
SCOPE = 'corrected-sensitivity-only-development'
VERSION = 'uqroute-corrected-sensitivity-preparation-1.0.0'
MODELS = ('qwen15b', 'llama3b', 'qwen7b')
COUNTS = {'same_name_A.jsonl': 11, 'same_name_B.jsonl': 2, 'same_name_C.jsonl': 8,
          'same_name_D.jsonl': 7, 'same_name_E.jsonl': 7}
LABEL = {'benchmark':'bfcl_v3', 'population':'sensitivity_only', 'split':'development'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlink paths are unsupported')


def regular(path):
    safe(path)
    if not path.is_file():
        raise ValueError('Required file missing: ' + path.name)
    return path.read_bytes()


def load_workflow(repo):
    folder = repo / WORKFLOW
    for name,pin in CODE.items():
        if sha(regular(folder / name).replace(b'\r\n',b'\n')) != pin:
            raise ValueError('Reviewed generation implementation differs: ' + name)
    sys.path.insert(0, str(folder))
    try:
        workflow = importlib.import_module('workflow')
        for name in ('workflow','support'):
            if Path(sys.modules[name].__file__).resolve().parent != folder.resolve():
                raise ValueError('Conflicting local generation module: ' + name)
    finally:
        sys.path.pop(0)
    return workflow


def load_audit(repo, workflow):
    ledger = {}
    def load(relative, pin=None):
        name = AUDIT / relative
        raw = regular(repo / name)
        digest = sha(raw)
        if pin is not None and digest != pin:
            raise ValueError('Reviewed audit fingerprint differs: ' + name.name)
        ledger[name.as_posix()] = digest
        return workflow.loads(raw)

    summary = load('summary.json')
    if any(summary.get(k) != v for k,v in {
        'scope':'sensitivity_only_development_construction_audit', 'benchmark':'bfcl_v3',
        'benchmark_revision':BENCHMARK_REVISION, 'split_sha256':SPLIT_SHA,
        'candidate_file_sha256':CANDIDATES_SHA, 'export_attestation_sha256':ATTESTATION_SHA,
        'source_rows':35, 'canonical_groups':34, 'constructed_candidates':35,
        'construction_blocks_retained':0, 'clean_perturbed_pairs':0, 'rows_by_source':COUNTS,
        'generation_requests_sent':0, 'unselected_nested_payloads_decoded':0,
        'official_scoring':'not_performed',
    }.items()) or summary.get('held_out_content_exported') is not False or summary.get('main_experiment_ready') is not False:
        raise ValueError('Sensitivity audit summary differs from the reviewed result')
    att = load('export/attestation.json', ATTESTATION_SHA)
    if (att['population'] != 'sensitivity_only' or att['partition'] != 'development'
            or att['benchmark_revision'] != BENCHMARK_REVISION or att['split_sha256'] != SPLIT_SHA
            or (att['row_count'],att['group_count']) != (35,34)
            or att['held_out_content_exported'] is not False or att['unselected_nested_payloads_decoded'] != 0):
        raise ValueError('Sensitivity export scope differs')
    member = load('export/membership.json', att['payload_hashes']['membership.json'])
    groups = member['groups']
    if (member['population'] != 'sensitivity_only' or member['split'] != 'development'
            or (member['expected_rows'],member['expected_groups'],len(groups)) != (35,34,34)
            or any(a != LABEL for a in groups.values())):
        raise ValueError('Sensitivity membership differs')
    inv = load('audit/inventory.json')
    candidates = load('audit/candidates.json', CANDIDATES_SHA)
    by_key = {r['case_key']:r for r in inv}
    keys = sorted(by_key)
    if (len(inv) != 35 or len(keys) != 35 or len(candidates) != 35
            or sorted(c['case_key'] for c in candidates) != keys
            or workflow.digest(keys) != att['case_key_digest']
            or {r['canonical_base_id'] for r in inv} != set(groups)
            or Counter(r['source_file'] for r in inv) != COUNTS):
        raise ValueError('Sensitivity candidate coverage differs')
    for c in candidates:
        r = by_key[c['case_key']]
        if (set(c) != {'case_key','canonical_base_id','benchmark','messages','tools','messages_sha256'}
                or c['benchmark'] != 'bfcl_v3' or c['canonical_base_id'] != r['canonical_base_id']
                or any(r.get(k) != v for k,v in LABEL.items())
                or r['case_key'] != r['source_file']+':'+r['row_id']
                or r['construction_status'] != 'candidate'
                or r['reference_audit_status'] != 'completed_bounded_signals_only'
                or r['official_labels_changed'] is not False or r['excluded_from_inventory'] is not False
                or not isinstance(c['messages'],list)
                or [m['role'] for m in c['messages']] != ['system','user']
                or any(set(m) != {'role','content'} or not isinstance(m['content'],str) for m in c['messages'])
                or workflow.digest(c['messages']) != c['messages_sha256']
                or r['corrected_messages_sha256'] != c['messages_sha256']
                or [workflow.digest(t) for t in c['tools']] != r['tool_occurrence_schema_sha256']):
            raise ValueError('Candidate prompt or lineage differs')
    return sorted(candidates,key=lambda r:r['case_key']), by_key, ledger


def run(repo):
    out = repo / OUTPUT
    safe(out)
    if out.exists():
        raise ValueError('Preparation output already exists; preserve it')
    if subprocess.run(['git','check-ignore','-q','--',str(OUTPUT / 'summary.json')],cwd=repo).returncode:
        raise ValueError('Preparation must stay in the Git-ignored local artifacts folder')
    w = load_workflow(repo)
    head = w.verify_baseline(repo)
    src = w.source_bytes(repo)
    w.config()
    task = w.loads(src['docs/config/task1_single_sample_v1.json'])
    if (task['benchmark']['revision'],task['benchmark']['split_sha256']) != (BENCHMARK_REVISION,SPLIT_SHA):
        raise ValueError('Frozen Task 1 authority differs')
    candidates,by_key,ledger = load_audit(repo,w)
    generation = task['single_sample']
    if generation['request_seed'] is not None or generation['tool_call_mode'] != 'prompt-based; no native tools argument':
        raise ValueError('Unexpected single-sample settings')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out.parent,prefix='sensitivity-prep-stage-') as temp:
        stage=Path(temp)/'output';stage.mkdir()
        transfers = {}
        prompt_records = None
        for key in MODELS:
            model = next(m for m in task['models'] if m['model_id'] == w.MODELS[key])
            if model['role'] != 'small':
                raise ValueError('Only the three small models belong in this sensitivity run')
            records = w.make_requests(candidates,by_key,model,generation)
            comparable = [{**r, 'request':{k:v for k,v in r['request'].items() if k!='model'}}
                          for r in records]
            for r in comparable:
                del r['request_sha256']
            if prompt_records is None:
                prompt_records = comparable
            elif comparable != prompt_records:
                raise ValueError('Non-model request settings differ across models')
            manifest = {
                'version':VERSION, 'scope':SCOPE, 'population':'sensitivity_only', 'split':'development',
                'benchmark_revision':BENCHMARK_REVISION, 'split_sha256':SPLIT_SHA, 'model_key':key,
                'prepared_project_head':head, 'source_baseline_commit':w.BASE,
                'source_hashes':{p:sha(v) for p,v in src.items()},
                'implementation_hashes':w.implementation_hashes(), 'input_sha256':ledger,
                'model_settings':model, 'generation_settings':generation, 'server_settings':generation['server'],
                'request_count':len(records), 'canonical_groups':34, 'source_rows':35,
                'case_keys':[r['case_key'] for r in records], 'requests_sha256':w.digest(records),
                'construction_blocks_retained':0, 'clean_perturbed_pairs':0,
                'held_out_access_enabled':False, 'main_experiment_ready':False,
                'automatic_retries':0, 'official_scoring':'not_performed',
                'dispatch_authorized_by_preparation':False,
            }
            mraw,rraw = [(w.canonical(v)+'\n').encode() for v in (manifest,records)]
            dest=stage/key;dest.mkdir()
            (dest/'manifest.json').write_bytes(mraw)
            (dest/'requests.json').write_bytes(rraw)
            archive=stage/f'{key}_sensitivity_development_transfer_v1.zip'
            with zipfile.ZipFile(archive,'x') as z:
                # Fixed timestamp and byte storage produce reproducible transfer hashes.
                for name,data in [('manifest.json',mraw),('requests.json',rraw)]:
                    entry=zipfile.ZipInfo(name)
                    entry.create_system=3
                    entry.external_attr=0o100644<<16
                    z.writestr(entry,data)
            with zipfile.ZipFile(archive) as z:
                if z.namelist()!=['manifest.json','requests.json'] or z.testzip() is not None:
                    raise ValueError('Transfer integrity check failed')
            transfers[key]={'file':archive.name,'sha256':sha(archive.read_bytes()),
                            'manifest_sha256':sha(mraw),'requests':len(records)}
        for name,pin in ledger.items():
            if sha(regular(repo / name)) != pin:
                raise ValueError('Audit input changed during preparation')
        result = {
            'scope':SCOPE,'source_rows':35,'canonical_groups':34,'clean_perturbed_pairs':0,
            'requests_per_model':35,'total_prepared_requests':105,'transfers':transfers,
            'held_out_access_enabled':False,'main_experiment_ready':False,
            'generation_requests_sent':0,'official_scoring':'not_performed',
        }
        (stage/'summary.json').write_text(w.canonical(result)+'\n',encoding='utf-8',newline='\n')
        if out.exists() or out.is_symlink():
            raise ValueError('Output appeared during preparation; preserve it')
        stage.rename(out)
    print(w.canonical(result))
    print('Prepared transfers:', out)
    return result


if __name__=='__main__':
    try:
        run(Path.cwd().resolve())
    except (ValueError, OSError, subprocess.CalledProcessError, TypeError, KeyError, StopIteration) as exc:
        raise SystemExit(str(exc) if type(exc) is ValueError else
                         'Preparation validation failed; no generation or prior-output changes.') from None
