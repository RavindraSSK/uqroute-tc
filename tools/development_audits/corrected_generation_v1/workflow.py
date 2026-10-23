"""Prepare corrected development requests, explicitly dispatch, or replay on CPU.

No raw benchmark/split or reference-sidecar arguments. No official scoring.
Old outputs and every prior durable request intent are preserved.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import math
from pathlib import Path
import re
import time
from urllib import error, request
from urllib.parse import urlsplit
import uuid

from support import (BASE, HERE, artifact_path, canonical, digest, fresh_directory,
                     implementation_hashes, json_once, loads, methods, read,
                     sha, source_bytes, verify_baseline, write_once)

MODELS = {'qwen15b': 'Qwen/Qwen2.5-1.5B-Instruct', 'llama3b': 'meta-llama/Llama-3.2-3B-Instruct',
          'qwen7b': 'Qwen/Qwen2.5-7B-Instruct', 'qwen14b_awq': 'Qwen/Qwen2.5-14B-Instruct-AWQ'}
CONFIG_SHA = '1c47a993d664e8431926a6257eff96a834671eeccf87409f1fc9cd824d37063b'
ATTESTATION = '77071dc342a19b0f32995fed9f9f9e25840294e633ef5368830f07a3ccf3ccb9'


def now():
    return datetime.now(timezone.utc).isoformat()


def config():
    raw = read(HERE / 'workflow_config.json').replace(b'\r\n', b'\n')
    if sha(raw) != CONFIG_SHA: raise ValueError('Workflow configuration differs')
    cfg = loads(raw)
    if cfg['baseline_commit'] != BASE or cfg['held_out_access_enabled'] is not False or cfg['main_experiment_ready'] is not False or cfg['automatic_retries'] != 0:
        raise ValueError('Development workflow boundary differs')
    return cfg


def approved_file(path, expected):
    if not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('Explicit expected SHA256 required')
    raw = read(path)
    if sha(raw) != expected:
        raise ValueError('Approved input hash differs')
    return loads(raw)


def validate_candidates(candidates, inventory):
    by_key = {r['case_key']: r for r in inventory if r['construction_status'] == 'candidate'}
    if not isinstance(candidates, list) or len(candidates) != len(by_key):
        raise ValueError('Candidate coverage differs')
    seen = set()
    for c in candidates:
        if set(c) != {'case_key', 'canonical_base_id', 'benchmark', 'messages', 'tools', 'messages_sha256'}:
            raise ValueError('Unexpected candidate fields')
        key = c['case_key']; r = by_key.get(key)
        if r is None or key in seen or c['canonical_base_id'] != r['canonical_base_id'] or c['benchmark'] != r['benchmark']:
            raise ValueError('Candidate membership differs')
        if r['split'] != 'development' or r['population'] != 'primary':
            raise ValueError('Non-development candidate')
        seen.add(key)
        messages = c['messages']
        if not isinstance(messages, list) or [m.get('role') for m in messages] != ['system', 'user'] or any(set(m) != {'role', 'content'} or not isinstance(m['content'], str) for m in messages):
            raise ValueError('Unexpected corrected prediction boundary')
        if digest(messages) != c['messages_sha256'] or c['messages_sha256'] != r['corrected_messages_sha256']:
            raise ValueError('Corrected prompt hash differs')
        if not isinstance(c['tools'], list) or [digest(t) for t in c['tools']] != r['tool_occurrence_schema_sha256']:
            raise ValueError('Corrected tool schema hash differs')
    return by_key


def select(candidates, by_key, selection):
    rank = lambda c: (sha(('uqroute-corrected-generation-v1/1729/' + c['case_key']).encode()), c['case_key'])
    if selection == 'full-development':
        return sorted(candidates, key=lambda c: c['case_key'])
    strata = defaultdict(list)
    for c in candidates:
        source = by_key[c['case_key']]['source_file']
        if selection == 'feasibility-five':
            if source == 'clean.jsonl': strata[c['benchmark']].append(c)
        elif selection == 'coverage': strata[(c['benchmark'], source)].append(c)
        else: raise ValueError('Unsupported selection')
    if selection == 'feasibility-five' and set(strata) != {'apibank', 'bfcl_v3', 'rotbench', 'toolalpaca', 'tooleyes'}:
        raise ValueError('Five-benchmark feasibility selection incomplete')
    return sorted([min(items, key=rank) for items in strata.values()], key=lambda c: c['case_key'])


def make_requests(selected, by_key, model, generation):
    result = []
    for c in selected:
        body = {'model': model['model_id'], 'messages': c['messages'],
                'temperature': generation['temperature'], 'max_tokens': generation['max_tokens'],
                'logprobs': True, 'top_logprobs': generation['top_logprobs'], 'stream': False}
        result.append({'case_key': c['case_key'], 'canonical_base_id': c['canonical_base_id'],
                       'benchmark': c['benchmark'], 'source_file': by_key[c['case_key']]['source_file'],
                       'messages_sha256': c['messages_sha256'], 'tools_sha256': digest(c['tools']),
                       'request_sha256': digest(body), 'request': body})
    return result


def prepare(repo, audit, denominators, candidates_hash, denominators_hash, model_key, selection, output):
    output = artifact_path(repo, output, (audit, denominators.parent))
    if output.exists(): raise ValueError('Prepared output already exists')
    head = verify_baseline(repo); src = source_bytes(repo); cfg = config(); frozen = methods(repo)
    summary = approved_file(audit / 'summary.json', cfg['prior_summary_sha256'])
    inventory = approved_file(audit / 'inventory.json', cfg['prior_inventory_sha256'])
    candidates = approved_file(audit / 'candidates.json', candidates_hash)
    denominator_report = approved_file(denominators, denominators_hash)
    p = summary.get('provenance', {})
    if p.get('attestation_sha256') != ATTESTATION or p.get('benchmark_revision') != 'd5d03180de41eb30a6c796d04a9bfbd9dad85c1d' or p.get('split_sha256') != '688c1013d8fe9d5c1b454d14d4cbe215659e48adc7bdfd63175580e83e2eb0db':
        raise ValueError('Unexpected original audit provenance')
    report, _, _ = frozen['population_plan'](inventory, summary)
    if {k: v for k, v in denominator_report.items() if k != 'provenance'} != report:
        raise ValueError('Population sidecar differs from prior inventory')
    provenance = denominator_report['provenance']
    if provenance['prior_summary_sha256'] != cfg['prior_summary_sha256'] or provenance['prior_inventory_sha256'] != cfg['prior_inventory_sha256']:
        raise ValueError('Population sidecar source hashes differ')
    if (len(inventory), len(candidates), len({r['canonical_base_id'] for r in inventory})) != (1754, 1728, 140):
        raise ValueError('Original population coverage differs')
    by_key = validate_candidates(candidates, inventory)
    selected = select(candidates, by_key, selection)
    task1 = loads(src['docs/config/task1_single_sample_v1.json'])
    model = next(m for m in task1['models'] if m['model_id'] == MODELS[model_key])
    requests = make_requests(selected, by_key, model, task1['single_sample'])
    manifest = {'version': cfg['version'], 'scope': 'corrected-primary-development-only',
        'main_experiment_ready': False, 'held_out_access_enabled': False,
        'selection': selection, 'selection_seed': 1729, 'model_settings': model,
        'prompt_authority': 'Corrected research-track candidates bound to prior audit; Task 1 prompt-builder field is historical',
        'server_settings': task1['single_sample']['server'], 'generation_settings': task1['single_sample'],
        'request_count': len(requests), 'requests_sha256': digest(requests),
        'case_keys': [c['case_key'] for c in requests], 'baseline_commit': BASE, 'prepared_project_head': head,
        'source_hashes': {p: sha(v) for p, v in src.items()}, 'implementation_hashes': implementation_hashes(),
        'input_hashes': {'summary.json': cfg['prior_summary_sha256'], 'inventory.json': cfg['prior_inventory_sha256'],
                         'candidates.json': candidates_hash, 'denominators.json': denominators_hash},
        'source_inventory_rows': 1754, 'construction_blocks_retained': 26,
        'automatic_retries': 0, 'request_seed': None, 'official_scoring': 'not_performed',
        'source_trust': 'Reviewed prior development exporter/auditor; local hashes are not authentication',
        'old_outputs_modified': False, 'raw_benchmark_or_split_opened': False}
    fresh_directory(output, {'manifest.json': manifest, 'requests.json': requests})
    return {'prepared_requests': len(requests), 'selection': selection,
            'manifest_sha256': sha(read(output / 'manifest.json')), 'network_requests': 0,
            'held_out_access_enabled': False, 'official_scoring': 'not_performed'}


def load_plan(repo, folder, expected):
    verify_baseline(repo)
    m = approved_file(folder / 'manifest.json', expected)
    records = loads(read(folder / 'requests.json'))
    src = source_bytes(repo)
    if m.get('version') != config()['version'] or m.get('scope') != 'corrected-primary-development-only' or m.get('held_out_access_enabled') is not False or m.get('main_experiment_ready') is not False:
        raise ValueError('Invalid prepared scope')
    if m['source_hashes'] != {p: sha(v) for p, v in src.items()} or m['implementation_hashes'] != implementation_hashes():
        raise ValueError('Prepared code/source fingerprints differ')
    if digest(records) != m['requests_sha256'] or len(records) != m['request_count'] or [r['case_key'] for r in records] != m['case_keys'] or len(set(m['case_keys'])) != len(records):
        raise ValueError('Prepared requests differ')
    task1 = loads(src['docs/config/task1_single_sample_v1.json'])
    model = next((x for x in task1['models'] if x == m['model_settings']), None)
    if model is None or m['generation_settings'] != task1['single_sample'] or m['server_settings'] != task1['single_sample']['server']:
        raise ValueError('Prepared model/settings differ')
    for r in records:
        b = r['request']
        expected_body = {'model': model['model_id'], 'messages': b['messages'], 'temperature': task1['single_sample']['temperature'],
                         'max_tokens': task1['single_sample']['max_tokens'], 'logprobs': True,
                         'top_logprobs': task1['single_sample']['top_logprobs'], 'stream': False}
        if b != expected_body or digest(b) != r['request_sha256'] or digest(b['messages']) != r['messages_sha256'] or [x['role'] for x in b['messages']] != ['system', 'user']:
            raise ValueError('Frozen request body differs')
    return m, records


def evaluate(response, benchmark, frozen):
    result = {'official_correctness': None, 'official_scoring': 'not_performed',
              'whole_output_scores': None, 'whole_output_unavailable': None,
              'meaningful_token_score': None, 'meaningful_token_unavailable': None}
    if not isinstance(response, dict) or not isinstance(response.get('choices'), list) or len(response['choices']) != 1:
        return result | {'status': 'malformed_response', 'whole_output_unavailable': 'expected exactly one choice', 'meaningful_token_unavailable': 'invalid response shape'}
    choice = response['choices'][0]
    raw = (choice.get('message') or {}).get('content')
    if not isinstance(raw, str):
        return result | {'status': 'malformed_response', 'whole_output_unavailable': 'non-text output', 'meaningful_token_unavailable': 'non-text output'}
    parsed = frozen['parse'](raw, benchmark)
    result.update(parser_status=parsed.status, canonical_key=parsed.key,
                  parsed_calls_json_view=list(parsed.calls), finish_reason=choice.get('finish_reason'))
    try: evidence = frozen['token_evidence'](choice)
    except (ValueError, TypeError, KeyError, OverflowError):
        evidence = {'valid': False, 'reason': 'malformed token evidence'}
    result['evidence'] = evidence
    if choice.get('finish_reason') == 'length': status = 'truncated'
    elif choice.get('finish_reason') != 'stop': status = 'unsupported_finish'
    elif not raw.strip(): status = 'empty_output'
    elif not evidence.get('valid'): status = 'invalid_evidence'
    else: status = 'complete'
    result['status'] = status
    if status == 'complete':
        try: result['whole_output_scores'] = asdict(frozen['single']({'uqroute': {'status': status, 'response': response, 'evidence': evidence}}))
        except (ValueError, TypeError, KeyError, OverflowError): result['whole_output_unavailable'] = 'frozen single-sample revalidation rejected evidence'
        if parsed.status == 'parse_failure': result['meaningful_token_unavailable'] = 'pinned parser failure'
        else:
            try:
                result['meaningful_token_score'] = asdict(frozen['meaningful'](raw, list(parsed.calls), choice['logprobs']['content'], choice.get('finish_reason'), benchmark))
            except (ValueError, TypeError, KeyError, SyntaxError, OverflowError):
                result['meaningful_token_unavailable'] = 'frozen format/alignment rule unavailable; ToolAlpaca remains excluded'
    else:
        result['whole_output_unavailable'] = status
        result['meaningful_token_unavailable'] = status
    return result


def endpoint_url(endpoint):
    u = urlsplit(endpoint)
    if u.scheme != 'http' or u.hostname not in {'127.0.0.1', 'localhost', '::1'} or u.username or u.password or u.query or u.fragment or u.path.rstrip('/') != '/v1':
        raise ValueError('Only local unauthenticated HTTP /v1 endpoint is supported')
    return endpoint.rstrip('/')


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def transport(endpoint, path, body=None, timeout=300):
    url = endpoint_url(endpoint) + path
    opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
    req = request.Request(url, data=None if body is None else canonical(body).encode(),
                          headers={'Content-Type': 'application/json'}, method='GET' if body is None else 'POST')
    try:
        with opener.open(req, timeout=timeout) as response:
            return response.status, response.read()
    except error.HTTPError as exc:
        return exc.code, exc.read()


def check_runtime(runtime, manifest):
    model = manifest['model_settings']; server = manifest['server_settings']
    required = {'model_id', 'model_revision', 'tokenizer_revision', 'dtype', 'quantization',
                'vllm_version', 'max_model_len', 'gpu_memory_utilization', 'chat_template',
                'effective_temperature', 'gpu_name', 'gpu_memory_mib', 'platform', 'quota_note',
                'launch_command_sha256', 'server_log_sha256'}
    if set(runtime) != required: raise ValueError('Runtime attestation fields differ')
    if any(runtime[k] != model[k] for k in ('model_id', 'model_revision', 'tokenizer_revision', 'dtype', 'quantization')):
        raise ValueError('Runtime model settings differ')
    if runtime['vllm_version'] != server['version'] or any(runtime[k] != server[k] for k in ('max_model_len', 'gpu_memory_utilization', 'chat_template')):
        raise ValueError('Runtime server settings differ')
    if type(runtime['effective_temperature']) not in (int, float) or not math.isfinite(runtime['effective_temperature']) or runtime['effective_temperature'] < 0:
        raise ValueError('Effective temperature must be observed and finite')
    if type(runtime['gpu_memory_mib']) is not int or runtime['gpu_memory_mib'] <= 0:
        raise ValueError('GPU allocation metadata missing')
    if any(not isinstance(runtime[k], str) or not runtime[k].strip() for k in ('gpu_name', 'platform', 'quota_note')):
        raise ValueError('Runtime context missing')
    if any(not re.fullmatch('[0-9a-f]{64}', runtime[k]) for k in ('launch_command_sha256', 'server_log_sha256')):
        raise ValueError('Runtime source hashes missing')


def slot(output, case):
    return output / 'cases' / sha(case['case_key'].encode())


def dispatch(records, manifest, output, binding, frozen, caller):
    """No retries. An existing intent permanently occupies that case slot."""
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / 'run_manifest.json'
    if manifest_path.exists():
        if loads(read(manifest_path)) != binding: raise ValueError('Resume binding differs')
    else:
        if any(output.iterdir()): raise ValueError('Nonempty output without run manifest')
        json_once(manifest_path, binding)
    lock = output / '.writer.lock'
    write_once(lock, b'single writer\n')
    session = uuid.uuid4().hex; started = time.perf_counter(); processed = 0; skipped = 0
    try:
        expected_folders = {slot(output, c).name: c for c in records}
        if any(p.name not in {'run_manifest.json', 'cases', 'sessions', '.writer.lock'} or p.is_symlink() for p in output.iterdir()):
            raise ValueError('Unexpected run output entry')
        case_root = output / 'cases'
        if case_root.exists():
            for folder in case_root.iterdir():
                if folder.name not in expected_folders or folder.is_symlink() or not folder.is_dir():
                    raise ValueError('Unexpected prior case folder')
                prior = loads(read(folder / 'intent.json'))
                expected = expected_folders[folder.name]
                if prior['case_key'] != expected['case_key'] or prior['request_sha256'] != expected['request_sha256']:
                    raise ValueError('Prior intent differs')
        json_once(output / 'sessions' / (session + '.started.json'), {'session': session, 'started_utc': now()})
        for c in records:
            folder = slot(output, c)
            intent_path = folder / 'intent.json'
            if intent_path.exists():
                old = loads(read(intent_path))
                if old['request_sha256'] != c['request_sha256'] or old['case_key'] != c['case_key']:
                    raise ValueError('Prior intent differs')
                skipped += 1
                continue
            if folder.exists() and any(folder.iterdir()): raise ValueError('Orphan case files')
            json_once(intent_path, {'case_key': c['case_key'], 'request_sha256': c['request_sha256'],
                                   'session': session, 'started_utc': now()})
            began = time.perf_counter()
            try: http_status, body = caller(c['request'])
            except Exception as exc:
                json_once(folder / 'transport_error.json', {'exception_type': type(exc).__name__,
                    'elapsed_seconds': time.perf_counter() - began, 'outcome': 'unknown; no automatic retry'})
                processed += 1
                continue
            elapsed = time.perf_counter() - began
            write_once(folder / 'http_response.bin', body)
            json_once(folder / 'response_metadata.json', {'http_status': http_status, 'body_sha256': sha(body),
                       'elapsed_seconds': elapsed, 'received_utc': now()})
            try:
                response = loads(body)
                if http_status != 200:
                    validation = {'status': 'http_error', 'official_correctness': None, 'whole_output_scores': None, 'meaningful_token_score': None}
                else: validation = evaluate(response, c['benchmark'], frozen)
            except Exception as exc:
                validation = {'status': 'validation_error', 'exception_type': type(exc).__name__,
                              'official_correctness': None, 'whole_output_scores': None, 'meaningful_token_score': None}
            json_once(folder / 'validation.json', validation)
            processed += 1
        result = {'session': session, 'processed': processed, 'resumed_without_request': skipped,
                  'batch_wall_seconds': time.perf_counter() - started, 'finished_utc': now()}
        json_once(output / 'sessions' / (session + '.finished.json'), result)
        return result
    finally:
        lock.unlink()


def run(repo, prepared, expected, runtime_path, endpoint, output, execute=False):
    if not execute: raise ValueError('Explicit --execute-development flag required')
    endpoint = endpoint_url(endpoint)
    output = artifact_path(repo, output, (prepared,))
    manifest, records = load_plan(repo, prepared, expected)
    runtime_raw = read(runtime_path); runtime = loads(runtime_raw); check_runtime(runtime, manifest)
    http_status, raw = transport(endpoint, '/models', timeout=30)
    if http_status != 200 or manifest['model_settings']['model_id'] not in {x['id'] for x in loads(raw)['data']}:
        raise ValueError('Local server model ID differs')
    binding = {'prepared_manifest_sha256': expected, 'runtime_attestation_sha256': sha(runtime_raw), 'runtime_canonical_sha256': digest(runtime),
               'runtime_attestation': runtime, 'endpoint': endpoint, 'request_count': len(records),
               'implementation_hashes': implementation_hashes(), 'held_out_access_enabled': False,
               'main_experiment_ready': False, 'automatic_retries': 0,
               'runtime_identity_limit': 'Operator-attested revisions/settings; /models checks model ID only, not loaded weights'}
    return dispatch(records, manifest, output, binding, methods(repo),
                    lambda body: transport(endpoint, '/chat/completions', body))


def replay(repo, prepared, expected, run_dir, output):
    output = artifact_path(repo, output, (prepared, run_dir))
    if output.exists(): raise ValueError('Replay output already exists')
    manifest, records = load_plan(repo, prepared, expected); frozen = methods(repo)
    if (run_dir / '.writer.lock').exists(): raise ValueError('Run has an active or stale writer lock')
    binding_raw = read(run_dir / 'run_manifest.json'); binding = loads(binding_raw)
    if binding['prepared_manifest_sha256'] != expected or binding['implementation_hashes'] != implementation_hashes() or binding['held_out_access_enabled'] is not False:
        raise ValueError('Run binding differs')
    if binding['request_count'] != len(records) or binding['main_experiment_ready'] is not False or binding['automatic_retries'] != 0 or digest(binding['runtime_attestation']) != binding['runtime_canonical_sha256']:
        raise ValueError('Runtime binding differs')
    check_runtime(binding['runtime_attestation'], manifest)
    endpoint_url(binding['endpoint'])
    expected_folders = {slot(run_dir, c).name for c in records}
    case_root = run_dir / 'cases'
    if case_root.exists() and any(p.name not in expected_folders or p.is_symlink() for p in case_root.iterdir()):
        raise ValueError('Unexpected case folder')
    rows = []; file_hashes = {'run_manifest.json': sha(binding_raw)}; tokens = Counter(); missing_usage = Counter(); elapsed = 0.0
    for c in records:
        folder = slot(run_dir, c); row = {'case_key': c['case_key'], 'benchmark': c['benchmark'],
             'canonical_base_id': c['canonical_base_id'], 'official_correctness': None,
             'whole_output_scores': None, 'meaningful_token_score': None}
        def grab(name):
            raw = read(folder / name); file_hashes[folder.name + '/' + name] = sha(raw); return raw
        if not folder.exists(): row['status'] = 'not_attempted'
        else:
            allowed = {'intent.json', 'transport_error.json', 'http_response.bin', 'response_metadata.json', 'validation.json'}
            if any(p.name not in allowed or p.is_symlink() for p in folder.iterdir()): raise ValueError('Unexpected case evidence file')
            intent = loads(grab('intent.json'))
            if intent['case_key'] != c['case_key'] or intent['request_sha256'] != c['request_sha256']: raise ValueError('Intent differs')
            if (folder / 'transport_error.json').exists():
                if (folder / 'http_response.bin').exists(): raise ValueError('Conflicting request outcomes')
                err = loads(grab('transport_error.json')); row['status'] = 'transport_error_outcome_unknown'
                if type(err['elapsed_seconds']) not in (int, float) or not math.isfinite(err['elapsed_seconds']) or err['elapsed_seconds'] < 0: raise ValueError('Invalid elapsed time')
                elapsed += err['elapsed_seconds']
            elif not (folder / 'http_response.bin').exists(): row['status'] = 'interrupted_outcome_unknown'
            elif not (folder / 'response_metadata.json').exists():
                grab('http_response.bin'); row['status'] = 'interrupted_response_metadata_missing'
            else:
                body = grab('http_response.bin'); meta = loads(grab('response_metadata.json'))
                if meta['body_sha256'] != sha(body): raise ValueError('Response fingerprint differs')
                if type(meta['elapsed_seconds']) not in (int, float) or not math.isfinite(meta['elapsed_seconds']) or meta['elapsed_seconds'] < 0: raise ValueError('Invalid elapsed time')
                elapsed += meta['elapsed_seconds']
                try:
                    response = loads(body)
                    if meta['http_status'] != 200:
                        checked = {'status': 'http_error', 'official_correctness': None, 'whole_output_scores': None, 'meaningful_token_score': None}
                    else: checked = evaluate(response, c['benchmark'], frozen)
                    usage = response.get('usage', {}) if isinstance(response, dict) else {}
                    if not isinstance(usage, dict): usage = {}
                except Exception as exc:
                    checked = {'status': 'validation_error', 'exception_type': type(exc).__name__, 'official_correctness': None, 'whole_output_scores': None, 'meaningful_token_score': None}
                    usage = {}
                if (folder / 'validation.json').exists():
                    if canonical(loads(grab('validation.json'))) != canonical(checked): raise ValueError('Saved/replayed validation differs')
                    row.update(checked)
                else:
                    row.update(checked); row['validation_recovered_on_cpu'] = True
                for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
                    value = usage.get(key)
                    if type(value) is int and value >= 0: tokens[key] += value
                    else: missing_usage[key] += 1
                row['usage'] = usage
        if row['status'] in {'transport_error_outcome_unknown', 'interrupted_outcome_unknown', 'interrupted_response_metadata_missing'}:
            for key in ('prompt_tokens', 'completion_tokens', 'total_tokens'): missing_usage[key] += 1
        rows.append(row)
    sessions = {}; finished = {}
    session_root = run_dir / 'sessions'
    if session_root.exists():
        for path in session_root.iterdir():
            match = re.fullmatch(r'([0-9a-f]{32})\.(started|finished)\.json', path.name)
            if not match: raise ValueError('Unexpected session file')
            raw = read(path); record = loads(raw)
            if record['session'] != match[1]: raise ValueError('Session identity differs')
            file_hashes['sessions/' + path.name] = sha(raw)
            (sessions if match[2] == 'started' else finished)[match[1]] = record
    if not set(finished) <= set(sessions): raise ValueError('Finished session without start')
    for record in finished.values():
        if any(type(record[k]) is not int or record[k] < 0 for k in ('processed', 'resumed_without_request')) or record['processed'] + record['resumed_without_request'] != len(records) or not math.isfinite(record['batch_wall_seconds']) or record['batch_wall_seconds'] < 0:
            raise ValueError('Session accounting differs')
    summary = {'scope': 'corrected-development-evidence-replay-only', 'rows': len(rows),
        'status_counts': dict(Counter(r['status'] for r in rows)),
        'whole_output_eligible': sum(r['whole_output_scores'] is not None for r in rows),
        'meaningful_token_eligible': sum(r['meaningful_token_score'] is not None for r in rows),
        'known_token_totals': {k: tokens[k] for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')},
        'missing_usage_attempts': {k: missing_usage[k] for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')},
        'usage_not_applicable_unattempted': sum(r['status'] == 'not_attempted' for r in rows),
        'attempted_slots': sum(r['status'] != 'not_attempted' for r in rows),
        'session_count': len(sessions), 'unfinished_sessions': len(sessions) - len(finished),
        'known_finished_session_wall_seconds': sum(r['batch_wall_seconds'] for r in finished.values()),
        'resumed_slot_visits': sum(r['resumed_without_request'] for r in finished.values()),
        'known_request_elapsed_seconds': elapsed,
        'official_scoring': 'not_performed', 'held_out_access_enabled': False, 'main_experiment_ready': False,
        'prepared_manifest_sha256': expected, 'prior_files_modified': False,
        'request_outcome_file_sha256': file_hashes,
        'limits': ['Eligibility and parser extraction are not correctness.', 'Unknown outcomes are never automatically retried.',
                   'Request elapsed time is not GPU active time; runtime/setup/idle costs remain separate.',
                   'Parsed calls are a JSON view; official scoring must reparse original raw output to preserve Python value types.']}
    fresh_directory(output, {'summary.json': summary, 'records.json': rows})
    return {k: v for k, v in summary.items() if k != 'request_outcome_file_sha256'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check-sources')
    p = sub.add_parser('prepare')
    p.add_argument('--audit-dir', type=Path, required=True); p.add_argument('--denominators', type=Path, required=True)
    p.add_argument('--expected-candidates-sha256', required=True); p.add_argument('--expected-denominators-sha256', required=True)
    p.add_argument('--model-key', choices=MODELS, required=True)
    p.add_argument('--selection', choices=('feasibility-five', 'coverage', 'full-development'), default='feasibility-five')
    p.add_argument('--output', type=Path, required=True)
    for name in ('run', 'replay'):
        p = sub.add_parser(name)
        p.add_argument('--prepared', type=Path, required=True); p.add_argument('--expected-manifest-sha256', required=True)
        p.add_argument('--output', type=Path, required=True)
        if name == 'run':
            p.add_argument('--runtime-json', type=Path, required=True); p.add_argument('--endpoint', default='http://127.0.0.1:8000/v1')
            p.add_argument('--execute-development', action='store_true')
        else: p.add_argument('--run-dir', type=Path, required=True)
    a = parser.parse_args()
    try:
        if a.command == 'check-sources':
            config(); head = verify_baseline(a.repo_root)
            result = {'source_fingerprints_valid': True, 'head': head, 'baseline_commit': BASE, 'dataset_files_opened': 0,
                      'network_requests': 0, 'held_out_access_enabled': False, 'main_experiment_ready': False}
        elif a.command == 'prepare': result = prepare(a.repo_root, a.audit_dir, a.denominators, a.expected_candidates_sha256,
            a.expected_denominators_sha256, a.model_key, a.selection, a.output)
        elif a.command == 'run': result = run(a.repo_root, a.prepared, a.expected_manifest_sha256, a.runtime_json,
            a.endpoint, a.output, a.execute_development)
        else: result = replay(a.repo_root, a.prepared, a.expected_manifest_sha256, a.run_dir, a.output)
    except Exception as exc:
        raise SystemExit('Corrected-development validation failed (' + type(exc).__name__ + '). Preserve outputs; do not bypass hashes or retry unknown requests.') from None
    print(canonical(result))


if __name__ == '__main__': main()
