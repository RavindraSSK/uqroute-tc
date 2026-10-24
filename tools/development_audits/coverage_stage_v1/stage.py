"""Prepare a bounded outcome-independent development coverage run; no inference."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

BASE = '6dfed208793f0061b79dba76359b91d6ea484fcf'
CANDIDATES = '177b0409bb6f2f0e116fa6b924e46807c9c30a3305a5fd6e15bfa30cf0f3d060'
DENOMINATORS = '14a59d3da30d715675271dd05ad6384c3f6c7421db52e86630b828e8651c44f6'
WORKFLOW_HASHES = {
    'source_manifest.json': '3c6d9aa632951d5a82bc6ae1679f6bbda8884d5938d0997b5f7fc4d5cf699387',
    'support.py': '4aac9f16ed6a03fa833ab3fbaf321127c3043194273c91f79c4f2bda167dbc47',
    'workflow.py': '01a881a67e9b80c81f09268e878502b48bb640398c9729f5eed1ffc47b843831',
    'workflow_config.json': '1c47a993d664e8431926a6257eff96a834671eeccf87409f1fc9cd824d37063b',
}
VERSION = 'uqroute-development-coverage-stage-1.0.0'
BENCHMARKS = {'apibank','bfcl_v3','rotbench','toolalpaca','tooleyes'}
SOURCES = {'clean.jsonl','CD.jsonl','CD_AB.jsonl','CD_NT.jsonl','TD.jsonl','TD_AB.jsonl','TD_NT.jsonl',
           'paraphrase_parameter_description.jsonl','paraphrase_tool_description.jsonl','query_paraphrase.jsonl',
           'realistic_typos.jsonl','redundant.jsonl','same_name_A.jsonl','same_name_B.jsonl',
           'same_name_C.jsonl','same_name_D.jsonl','same_name_E.jsonl'}


def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(x): return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def regular(path):
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError('Expected a regular file without symlink ancestors')
    return path.read_bytes()


def dependencies(repo):
    folder = repo / 'tools/development_audits/corrected_generation_v1'
    for name, expected in WORKFLOW_HASHES.items():
        if sha(regular(folder / name).replace(b'\r\n', b'\n')) != expected:
            raise ValueError('Frozen generation source differs')
    sys.path.insert(0, str(folder))
    try:
        import workflow
        import support
        if Path(workflow.__file__).resolve().parent != folder or Path(support.__file__).resolve().parent != folder:
            raise ValueError('Conflicting module import')
    finally:
        sys.path.pop(0)
    return workflow, support


def coverage_report(manifest, requests, candidates, inventory, workflow):
    index = workflow.validate_candidates(candidates, inventory)
    expected = workflow.select(candidates, index, 'coverage')
    actual_keys = [r['case_key'] for r in requests]
    if actual_keys != [c['case_key'] for c in expected] or len(set(actual_keys)) != len(actual_keys):
        raise ValueError('Coverage selection differs from frozen outcome-independent rule')
    if not requests or len(requests) > 85 or manifest['selection'] != 'coverage' or manifest['request_count'] != len(requests):
        raise ValueError('Coverage request bound or manifest differs')
    if manifest['held_out_access_enabled'] is not False or manifest['main_experiment_ready'] is not False:
        raise ValueError('Scope/readiness differs')
    strata = Counter((r['benchmark'], r['source_file']) for r in requests)
    if any(n != 1 or b not in BENCHMARKS or f not in SOURCES for (b,f),n in strata.items()):
        raise ValueError('Unexpected or duplicated benchmark/source stratum')
    if {r['benchmark'] for r in requests} != BENCHMARKS:
        raise ValueError('Missing benchmark')
    candidate_strata = {(c['benchmark'], index[c['case_key']]['source_file']) for c in candidates}
    if set(strata) != candidate_strata:
        raise ValueError('Constructed stratum omitted')
    prior = workflow.select(candidates, index, 'feasibility-five')
    prior_keys = {c['case_key'] for c in prior}
    repeat_keys = sorted(set(actual_keys) & prior_keys)
    clean_by_group = Counter(r['canonical_base_id'] for r in requests if r['source_file'] == 'clean.jsonl')
    perturbed = [r for r in requests if r['source_file'] != 'clean.jsonl']
    selected_pairs = sum(clean_by_group[r['canonical_base_id']] == 1 for r in perturbed)
    return {'version': VERSION, 'scope': 'bounded-development-coverage-diagnostic',
            'rows': len(requests), 'canonical_groups': len({r['canonical_base_id'] for r in requests}),
            'selection': 'frozen hash minimum per constructed benchmark/source stratum',
            'by_benchmark': dict(sorted(Counter(r['benchmark'] for r in requests).items())),
            'by_source_file': dict(sorted(Counter(r['source_file'] for r in requests).items())),
            'covered_strata': [{'benchmark': b, 'source_file': f} for b,f in sorted(strata)],
            'candidate_empty_strata': [{'benchmark': b, 'source_file': f} for b in sorted(BENCHMARKS) for f in sorted(SOURCES) if (b,f) not in strata],
            'source_inventory_rows': len(inventory),
            'construction_blocks_retained': sum(r['construction_status'] == 'blocked' for r in inventory),
            'prior_feasibility_cases_deliberately_repeated': len(repeat_keys),
            'repeated_case_keys': repeat_keys,
            'repeat_policy': 'Separate planned coverage run; no retries of prior slots and no pooling with prior five-case outcomes.',
            'selected_perturbed_rows': len(perturbed), 'selected_perturbed_rows_with_selected_clean_anchor': selected_pairs,
            'pairing_limit': 'Per-stratum selection is not a clean/perturbed paired population design.',
            'maximum_completion_tokens': len(requests) * 1024,
            'prompt_utf8_bytes_max': max(sum(len(m['content'].encode()) for m in r['request']['messages']) for r in requests),
            'context_preflight': 'pending pinned-tokenizer rendering in GPU notebook; byte counts are not token counts',
            'runtime_and_quota': 'pending local preparation review and Colab availability; no extrapolation from five clean calls',
            'automatic_retries': 0, 'official_scoring': 'not_performed',
            'held_out_access_enabled': False, 'main_experiment_ready': False,
            'network_requests': 0, 'raw_benchmark_or_split_opened': False,
            'official_labels_changed': False, 'prior_outputs_modified': False,
            'limits': ['Source-file coverage is not O/A/R taxonomy validation.',
                       'One selected case per stratum does not estimate population accuracy or uncertainty discrimination.',
                       'ToolEyes relevance must remain separate from reference compliance.',
                       'Reference ambiguity and cost/latency preference remain separate analysis dimensions.',
                       'New coverage scoring requires a new reviewed evidence-bound adapter; the five-case scorer is not generalized.']}


def prepare(repo, audit, denominators, output):
    for p in (repo, audit, denominators, output):
        if any(q.is_symlink() for q in (p, *p.parents)):
            raise ValueError('Symlink paths are not accepted')
    repo, audit, denominators, output = (p.resolve() for p in (repo, audit, denominators, output))
    root = repo / 'artifacts/local_development_audits'
    for p in (audit, denominators, output):
        if not p.is_relative_to(root) or p == root:
            raise ValueError('Data paths must be children of local development artifacts')
    for source in (audit, denominators.parent):
        if output == source or source in output.parents or output in source.parents:
            raise ValueError('Output overlaps inputs')
    if output.exists(): raise ValueError('Output exists; preserve it')
    subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',BASE,'HEAD'], check=True, capture_output=True)
    workflow, support = dependencies(repo)
    # Explicit previously reviewed fingerprints: never approve inputs by hashing
    # whatever happens to be present. No references or model outcomes are opened.
    candidates = workflow.approved_file(audit / 'candidates.json', CANDIDATES)
    inventory = workflow.approved_file(audit / 'inventory.json', workflow.config()['prior_inventory_sha256'])
    ledger = {p: sha(regular(p)) for p in (audit/'candidates.json', audit/'inventory.json', audit/'summary.json', denominators)}
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='coverage-stage-') as temp:
        temp = Path(temp).resolve(); prepared = temp / 'prepared'
        workflow.prepare(repo, audit, denominators, CANDIDATES, DENOMINATORS, 'qwen15b', 'coverage', prepared)
        manifest_hash = sha(regular(prepared / 'manifest.json'))
        manifest, requests = workflow.load_plan(repo, prepared, manifest_hash)
        report = coverage_report(manifest, requests, candidates, inventory, workflow)
        report.update(baseline_commit=BASE, prepared_manifest_sha256=manifest_hash,
                      input_sha256={p.relative_to(repo).as_posix():h for p,h in ledger.items()})
        transfer = temp / 'corrected_qwen15b_coverage_transfer_v1.zip'
        with zipfile.ZipFile(transfer, 'x', zipfile.ZIP_DEFLATED) as archive:
            for name in ('manifest.json','requests.json'):
                archive.writestr(name, regular(prepared / name))
        report['transfer_zip_sha256'] = sha(regular(transfer))
        (temp/'coverage_report.json').write_text(canonical(report)+'\n', encoding='utf-8')
        (temp/'MANIFEST_SHA256.txt').write_text(manifest_hash+'\n', encoding='utf-8')
        for p,h in ledger.items():
            if sha(regular(p)) != h: raise ValueError('Input changed during preparation')
        if output.exists(): raise ValueError('Output appeared during preparation')
        temp.rename(output)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo-root',type=Path,required=True)
    p.add_argument('--audit-dir',type=Path,required=True)
    p.add_argument('--denominators',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try: result=prepare(a.repo_root,a.audit_dir,a.denominators,a.output)
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        raise SystemExit('Coverage preparation stopped ('+type(exc).__name__+'). Preserve inputs and report this error: '+str(exc)) from None
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
