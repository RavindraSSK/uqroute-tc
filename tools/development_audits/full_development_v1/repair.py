"""Deterministic research-track tool rendering; no inference or gold-based repairs."""
import ast
import copy
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
import base_adapter as base

POLICY='uqroute-structured-vocabulary-research-preview-v2'

def norm(text):
    text=re.sub(r'\[(?:Cost|Latency|Response time):[^\]]*\]','',text,flags=re.I)
    text=re.sub(r'\((?:costs approximately \$[^)]* per call|typically responds in [^)]*)\)','',text,flags=re.I)
    return ' '.join(text.split()).strip()


def apibank_definitions(system):
    if '**Available Tools**' not in system or '**Steps for Each Turn**' not in system:
        raise ValueError('API-Bank tool section boundary absent')
    section=system.split('**Available Tools**',1)[1].split('**Steps for Each Turn**',1)[0]
    starts=list(re.finditer(r'^\d+\.\s+(?:Name:\s*([^\n]+)|([^:\n]+):\s*([^\n]*))',section,re.M))
    rows=[]
    for i,m in enumerate(starts):
        block=section[m.end():starts[i+1].start() if i+1<len(starts) else len(section)]
        desc=re.search(r'^Description:\s*(.*)',block,re.M)
        pm=re.search(r'^Parameters:\s*(\{[^\n]*\})',block,re.M)
        # Inline Parameters occurs in synthetic duplicate-name cases.
        if pm is None:
            pm=re.search(r'Parameters:\s*(\{[^\n]*\})',m.group(0))
        if pm is None:raise ValueError('API-Bank parameter declaration absent')
        props=ast.literal_eval(pm[1])
        if not isinstance(props,dict):raise ValueError('API-Bank parameters are not a mapping')
        rows.append({'name':(m[1] or m[2]).strip(),'description':desc[1] if desc else (m[3] or ''),'properties':props})
    if not rows:raise ValueError('No API-Bank declarations parsed')
    return rows


def repair_apibank(system,tools):
    sources=apibank_definitions(system)
    tools=copy.deepcopy(tools)
    edits=[]
    # Exact spurious instruction entry only; not a general name filter.
    tools=[t for t in tools if not (t['name']=='**Think' and norm(t.get('description',''))=='** Recall relevant context and analyze the current user goal.' and not t['parameters'].get('properties'))]
    edits.append({'kind':'exclude_exact_instruction_artifact','name':'**Think'})
    consumed=set()
    # Match existing nonempty schemas first to distinguish same-name occurrences.
    for t in tools:
        props=t['parameters'].get('properties',{})
        if not props:continue
        matches=[i for i,s in enumerate(sources) if i not in consumed and s['name']==t['name'] and s['properties']==props]
        if len(matches)==1:consumed.add(matches[0])
    for t in tools:
        if t['parameters'].get('properties'):continue
        candidates=[(i,s) for i,s in enumerate(sources) if i not in consumed and s['name']==t['name']]
        by_desc=[(i,s) for i,s in candidates if norm(s['description'])==norm(t.get('description',''))]
        if by_desc:candidates=by_desc
        if not candidates:
            candidates=[(i,s) for i,s in enumerate(sources) if norm(s['description'])==norm(t.get('description',''))]
        # A synthetic entry's malformed description sometimes contains its own schema.
        inline=re.fullmatch(r'Parameters:\s*(\{.*\})',t.get('description',''))
        if inline:
            props=ast.literal_eval(inline[1])
            matches=[(i,s) for i,s in candidates if s['properties']==props]
            if not matches:
                matches=[(i,s) for i,s in enumerate(sources) if s['name']==t['name'] and s['properties']==props]
            candidates=matches
        unique={base.canonical(s['properties']) for _,s in candidates}
        if not unique:
            raise ValueError('No matching schema declaration for '+t['name'])
        if len(unique)>1:
            raise ValueError('Conflicting schema declarations for '+t['name'])
        chosen=candidates[0]
        props=copy.deepcopy(chosen[1]['properties'])
        if chosen[0] not in consumed:consumed.add(chosen[0])
        if props:
            t['parameters']['properties']=props
            edits.append({'kind':'restore_missing_properties','tool_name':t['name'],'source_name':chosen[1]['name'],'source_occurrence':chosen[0],'properties':props})
        else:
            edits.append({'kind':'retain_explicit_empty_schema','tool_name':t['name'],'source_occurrence':chosen[0]})
    return tools,edits


def replace_tools(benchmark,messages,tools):
    messages=copy.deepcopy(messages)
    text=messages[0]['content']
    rendered=json.dumps(tools,ensure_ascii=False,indent=2)
    if benchmark=='apibank':
        a=text.index('**Available Tools**'); b=text.index('**Steps for Each Turn**',a)
        text=text[:a]+'**Available Tools**\n'+rendered+'\n\n'+text[b:]
    elif benchmark=='rotbench':
        marker='Specifically, you have access of the following tools:'
        start=text.index(marker)+len(marker)
        offset=start+len(text[start:])-len(text[start:].lstrip())
        existing,end=json.JSONDecoder().raw_decode(text[offset:])
        if not isinstance(existing,list):raise ValueError('RoTBench tools are not an array')
        text=text[:offset]+rendered+text[offset+end:]
        messages=messages[:-1]
    elif benchmark=='toolalpaca':
        # Original ToolAlpaca prompt is API documentation. Replace the whole stale
        # documentation with the released structured vocabulary and retain user input.
        text=('Use the available tools to answer the user request. Tool names below are the exact callable identifiers.\n'
              'Return the next tool call in this format:\nAction: tool_name\nAction Input: {"parameter": "value"}\n'
              'Do not invent tool results.\nAvailable tools:\n'+rendered)
    else:
        return messages
    messages[0]['content']=text
    return messages


def build(benchmark,messages,tools):
    roles=[m['role'] for m in messages]
    expected=['system','user','assistant'] if benchmark=='rotbench' else ['system','user']
    if roles!=expected:raise ValueError('Unsupported prediction boundary')
    tools=copy.deepcopy(tools)
    edits=[]
    if benchmark=='apibank':tools,edits=repair_apibank(messages[0]['content'],tools)
    elif benchmark not in ('rotbench','toolalpaca','bfcl_v3','tooleyes'):raise ValueError('Unsupported benchmark')
    for t in tools:
        if not isinstance(t.get('name'),str) or not isinstance(t.get('parameters',{}).get('properties'),dict):
            raise ValueError('Invalid structured tool schema')
    result=replace_tools(benchmark,messages,tools)
    # Exact tool list agreement, preserving order and duplicates.
    arrays=base.tool_sets(result)
    if len(arrays)!=1 or base.canonical(arrays[0])!=base.canonical(tools):
        # Existing BFCL/ToolEyes renderings may differ only in ordering.
        if benchmark not in ('bfcl_v3','tooleyes') or len(arrays)!=1 or base.tool_multiset(arrays[0])!=base.tool_multiset(tools):
            raise ValueError('Rendered tool list does not match schema')
    return {'messages':result,'tools':tools,'edits':edits,'messages_sha256':base.digest(result),'tools_sha256':base.digest(tools)}


def prepare(audit):
    if audit.get('benchmark_revision')!=base.REVISION or audit.get('official_runner_sha256')!=base.RUNNER_SHA:
        raise ValueError('Unsupported source provenance')
    rows=audit['cases']
    if len(rows)!=69 or len({r['case_key'] for r in rows})!=69:raise ValueError('Expected 69 unique development cases')
    result=[]
    for r in rows:
        if base.digest(r['messages'])!=r['prompt_sha256']:raise ValueError('Source prompt fingerprint mismatch')
        out={'case_key':r['case_key'],'benchmark':r['benchmark'],'source_prompt_sha256':r['prompt_sha256']}
        try:
            out.update(build(r['benchmark'],r['messages'],r['structured_tools']))
            out['status']='candidate'
        except (ValueError,SyntaxError,KeyError) as exc:
            out.update(status='blocked',reason=str(exc))
        result.append(out)
    return {'policy':POLICY,'readiness':'RESEARCH_TRACK_CANDIDATES_ONLY','inference_enabled':False,'summary':dict(Counter(r['status'] for r in result)),'cases':result}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.input.resolve()==a.output.resolve():raise ValueError('Do not overwrite the source audit')
    raw=a.input.read_bytes();report=prepare(json.loads(raw));report['source_audit_sha256']=hashlib.sha256(raw).hexdigest()
    a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(report['summary'])
    for r in report['cases']:
        if r['status']=='blocked':print(r['case_key'],r['reason'])
