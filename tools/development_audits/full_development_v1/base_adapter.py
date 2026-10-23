"""Build conservative development prompt previews; never dispatch inference."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from collections import Counter
from pathlib import Path

POLICY = 'uqroute-development-prompt-preview-v1'
REVISION = 'd5d03180de41eb30a6c796d04a9bfbd9dad85c1d'
RUNNER_SHA = 'e305a816c96ed574ad18ca90871775721fd79fcf3533a60077b26d1fdeef20d8'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def tool_sets(messages):
    """Read JSON tool arrays, preserving order and duplicate-name entries."""
    decoder = json.JSONDecoder()
    found = []
    for message in messages:
        if message['role'] != 'system':
            continue
        content = message['content']
        for offset, char in enumerate(content):
            if char != '[':
                continue
            try:
                value, _ = decoder.raw_decode(content[offset:])
            except ValueError:
                continue
            if isinstance(value, list) and value and all(
                isinstance(tool, dict) and isinstance(tool.get('name'), str)
                and isinstance(tool.get('parameters'), dict) for tool in value
            ):
                found.append(value)
    return found


def tool_multiset(tools):
    return Counter(canonical(tool) for tool in tools)


def build_preview(benchmark, messages, tools):
    """No gold labels, outcomes, scores or model identities are accepted here."""
    messages = copy.deepcopy(messages)
    tools = copy.deepcopy(tools)
    reasons = []
    roles = [message.get('role') for message in messages]
    if benchmark not in ('bfcl_v3', 'rotbench', 'tooleyes'):
        reasons.append('source_schema_and_name_reconciliation_required')
    wanted_roles = ['system', 'user', 'assistant'] if benchmark == 'rotbench' else ['system', 'user']
    if roles != wanted_roles:
        reasons.append('prediction_boundary_not_supported_by_v1')
    arrays = tool_sets(messages)
    if len(arrays) != 1:
        reasons.append('requires_exactly_one_embedded_json_tool_array')
    elif tool_multiset(arrays[0]) != tool_multiset(tools):
        reasons.append('embedded_and_structured_tool_definitions_differ')
    if not tools:
        reasons.append('empty_tool_list_requires_separate_review')
    for tool in tools:
        if not isinstance(tool.get('name'), str) or not isinstance(tool.get('parameters'), dict):
            reasons.append('malformed_structured_tool')
            break
    if reasons:
        return {'status': 'blocked', 'reasons': list(dict.fromkeys(reasons)), 'messages': None}
    # RoTBench single-turn next-action boundary is defined without looking at gold.
    # No historical messages are removed: only this exact supported role pattern.
    if benchmark == 'rotbench':
        messages = messages[:-1]
    return {
        'status': 'preview_only', 'reasons': [], 'messages': messages,
        'transformation': 'remove_terminal_assistant_target' if benchmark == 'rotbench' else 'unchanged',
        'after_messages_sha256': digest(messages),
    }


def prepare(audit):
    if audit.get('benchmark_revision') != REVISION or audit.get('official_runner_sha256') != RUNNER_SHA:
        raise ValueError('Unsupported benchmark/runner provenance')
    cases = audit['cases']
    if len(cases) != 69 or len({row['case_key'] for row in cases}) != 69:
        raise ValueError('Expected 69 distinct development case identities')
    rows = []
    for row in sorted(cases, key=lambda row: row['case_key']):
        if digest(row['messages']) != row['prompt_sha256']:
            raise ValueError('Prompt fingerprint differs: ' + row['case_key'])
        preview = build_preview(row['benchmark'], row['messages'], row['structured_tools'])
        rows.append({
            'case_key': row['case_key'], 'benchmark': row['benchmark'],
            'before_messages_sha256': digest(row['messages']),
            'structured_tools_sha256': digest(row['structured_tools']), **preview,
        })
    counts = Counter(row['status'] for row in rows)
    return {
        'policy_version': POLICY, 'benchmark_revision': REVISION,
        'readiness': 'CPU_PREVIEW_VALIDATED_GPU_BLOCKED',
        'inference_enabled': False, 'held_out_accessed': False,
        'summary': {'total': len(rows), **counts},
        'limitations': [
            'Matching embedded and structured tools establishes internal agreement only, not upstream semantic validity.',
            'Preview subset is not an approved evaluation population; all 69 rows remain in this report.',
            'No aliases, schemas, references, parser, scorer, model roles or thresholds are changed.',
            'Prompt-changing cases require new generations; old uncertainty scores and labels cannot be transferred.',
            'Original HTTP requests are not available; source prompts were reconstructed using the pinned runner.',
            'GPU execution remains disabled pending population, source and scoring reconciliation.',
        ], 'cases': rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        raise ValueError('Output must not overwrite the source audit')
    raw = args.input.read_bytes()
    report = prepare(json.loads(raw))
    report['source_audit_sha256'] = hashlib.sha256(raw).hexdigest()
    report['adapter_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'readiness': report['readiness'], 'summary': report['summary']}, indent=2))


if __name__ == '__main__':
    main()
