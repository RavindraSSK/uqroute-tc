"""Outcome-independent review signals for the 69 corrected development cases."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
from collections import Counter,defaultdict
from pathlib import Path

VERSION='uqroute-development-reference-audit-1.0.0'
AUDIT_HASH='669eee55ea13f2e683d5fa7bdf914a62dc96b4603df5f3a32c1c0b5f54ad19e9'
CANDIDATES_HASH='498728420b2bf837f2b54d215be30fde31d766c7205632e5fd46de091b9ae365'
COST_OBJECTIVE=r'\b(?:cost[- ]effective|most economical|cheapest|least expensive|lowest[- ]cost|minimi[sz]e (?:the )?cost|(?:reduce|save) (?:the )?cost)\b'
LATENCY_OBJECTIVE=r'\b(?:fastest|quickest|lowest[- ]latency|shortest (?:response )?time|minimi[sz]e (?:the )?(?:latency|response time)|(?:reduce|avoid) (?:the )?latency)\b'


def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def sha(raw):return hashlib.sha256(raw).hexdigest()

def user_segments(messages):
    segments=[]
    for m in messages:
        if m['role']!='user':continue
        content=m['content']
        embedded=re.findall(r'<user>\s*(.*?)\s*</user>',content,re.S|re.I)
        segments.extend(embedded if embedded else [content])
    return segments


def instruction_without_tool_arrays(messages):
    output=[];decoder=json.JSONDecoder()
    for m in messages:
        if m['role']!='system':continue
        text=m['content'];spans=[]
        for i,char in enumerate(text):
            if char!='[':continue
            try:value,end=decoder.raw_decode(text[i:])
            except ValueError:continue
            if isinstance(value,list) and value and all(isinstance(t,dict) and 'name' in t and 'parameters' in t for t in value):spans.append((i,i+end))
        for a,b in sorted(spans,reverse=True):text=text[:a]+' [TOOL DEFINITIONS OMITTED] '+text[b:]
        output.append(text)
    return output


def objective_hits(segments,pattern):
    return [{'segment_index':i,'matched_text':m.group(0),'excerpt':s[max(0,m.start()-70):min(len(s),m.end()+70)]}
            for i,s in enumerate(segments) for m in re.finditer(pattern,s,re.I)]


def strip_metadata(text):
    text=re.sub(r'\[(?:Cost|Latency|Response time):[^\]]*\]','',text,flags=re.I)
    text=re.sub(r'\((?:costs approximately \$[^)]* per call|typically responds in [^)]*)\)','',text,flags=re.I)
    return ' '.join(text.split()).strip()


def metadata(description):
    cost=re.search(r'(?:Cost:\s*|costs approximately\s*)\$([0-9]+(?:\.[0-9]+)?)',description,re.I)
    latency=re.search(r'(?:Latency:\s*|Response time:\s*~?|typically responds in\s*)([0-9]+(?:\.[0-9]+)?)\s*ms',description,re.I)
    return {'declared_cost_per_call':float(cost[1]) if cost else None,'declared_latency_ms':float(latency[1]) if latency else None}


def advertised_groups(tools):
    groups=defaultdict(list)
    for i,t in enumerate(tools):
        key=canonical({'description':strip_metadata(t.get('description','')),'parameters':t.get('parameters')})
        groups[key].append({'occurrence':i,'name':t['name'],**metadata(t.get('description',''))})
    return [v for v in groups.values() if len(v)>1]


def audit_case(source,candidate):
    # Only reference calls and candidate prompts/tools enter this function.
    # Model responses, official correctness and uncertainty are not read.
    messages=candidate['messages'];tools=candidate['tools'];users=user_segments(messages)
    system=instruction_without_tool_arrays(messages)
    cost_user=objective_hits(users,COST_OBJECTIVE);lat_user=objective_hits(users,LATENCY_OBJECTIVE)
    cost_system=objective_hits(system,COST_OBJECTIVE);lat_system=objective_hits(system,LATENCY_OBJECTIVE)
    cost_explicit=bool(cost_user or cost_system);lat_explicit=bool(lat_user or lat_system)
    file=source['case_key'].split(':',1)[0];perturbation=file.removesuffix('.jsonl')
    reward_kind='cost' if perturbation in ('CD','CD_AB','CD_NT') else ('latency' if perturbation in ('TD','TD_AB','TD_NT') else None)
    refs=source['golden_answers'];flags=[];checks=[]
    groups=advertised_groups(tools)
    all_user_text='\n'.join(users)
    for ref in refs:
        name=ref.get('name') or ref.get('Action')
        args=ref.get('parameters') or ref.get('arguments') or ref.get('Action_Input') or {}
        occurrences=[(i,t) for i,t in enumerate(tools) if t['name']==name]
        compatible=[i for i,t in occurrences if isinstance(t.get('parameters',{}).get('properties'),dict) and set(args)<=set(t['parameters']['properties'])]
        if not occurrences:flags.append('reference_name_not_declared')
        elif not compatible:flags.append('reference_argument_keys_not_declared')
        if len(occurrences)>1:flags.append('reference_name_has_multiple_schema_occurrences')
        years=[]
        for key,value in args.items():
            if isinstance(value,str):
                for y in re.findall(r'\b(?:19|20)\d{2}(?=[-/])',value):
                    if y not in all_user_text:years.append({'argument':key,'year':y,'value':value})
        if years:flags.append('reference_date_year_not_literal_in_user_turns')
        preferences=[]
        for group in groups:
            if not any(g['name']==name for g in group):continue
            for kind,field in [('cost','declared_cost_per_call'),('latency','declared_latency_ms')]:
                if not all(g[field] is not None for g in group):continue
                values={g[field] for g in group}
                if len(values)<2:continue
                minima=[g['name'] for g in group if g[field]==min(values)]
                selected=[g[field] for g in group if g['name']==name]
                preferences.append({'kind':kind,'advertised_identical_description_schema':True,'group':group,'minimum_names':minima,'reference_name_at_minimum':any(v==min(values) for v in selected),'explicit_objective_detected':cost_explicit if kind=='cost' else lat_explicit})
                if not (cost_explicit if kind=='cost' else lat_explicit):flags.append('reference_preference_without_detected_'+kind+'_objective')
        checks.append({'reference_name':name,'matching_name_occurrence_indices':[i for i,_ in occurrences],'argument_key_compatible_occurrences':compatible,'reference_date_year_literal_gaps':years,'advertised_preference_checks':preferences})
    # Literal evidence only: not a general time-range/intent solver. This rule
    # flags a stronger conflict if the reference's two HH:MM times are absent
    # from every explicit HH:MM AM/PM user range in the dialogue.
    ranges=[]
    for i,s in enumerate(users):
        for m in re.finditer(r'\b(\d{1,2}):(\d{2})\s*(AM|PM)\s+to\s+(\d{1,2}):(\d{2})\s*(AM|PM)\b',s,re.I):
            cv=lambda h,mi,ap:f'{int(h)%12+(12 if ap.upper()=="PM" else 0):02d}:{mi}'
            ranges.append({'user_segment_index':i,'times':[cv(m[1],m[2],m[3]),cv(m[4],m[5],m[6])],'excerpt':m.group(0)})
    range_checks=[]
    if ranges:
        latest=ranges[-1]
        for ref in refs:
            args=ref.get('parameters') or ref.get('arguments') or {}
            if 'from_time' in args and 'to_time' in args:
                times=[re.search(r'\b(\d{2}:\d{2})(?::\d{2})?\b',str(args[k])) for k in ['from_time','to_time']]
                if all(times):
                    actual=[x[1] for x in times]
                    range_checks.append({'latest_explicit_user_range':latest,'reference_times':actual,'literal_range_agreement':actual==latest['times']})
                    if actual!=latest['times']:flags.append('reference_latest_explicit_time_range_mismatch')
    if reward_kind and not (cost_explicit if reward_kind=='cost' else lat_explicit):flags.append('reward_cell_without_detected_explicit_objective')
    return {'case_key':source['case_key'],'benchmark':source['benchmark'],'perturbation':perturbation,'reward_kind':reward_kind,
            'objective_detection':{'cost_explicit_detected':cost_explicit,'latency_explicit_detected':lat_explicit,'cost_user_hits':cost_user,'cost_system_hits':cost_system,'latency_user_hits':lat_user,'latency_system_hits':lat_system,'interpretation':'No regex hit means not detected, not proof that no implicit or differently worded objective exists.'},
            'reference_checks':checks,'latest_time_range_checks':range_checks,'review_flags':sorted(set(flags)),
            'review_status':'requires_review' if flags else 'no_signal_detected_not_semantic_clearance',
            'changes_official_labels':False,'excluded':False}


def analyze(audit,candidates):
    source={r['case_key']:r for r in audit['cases']};candidate={r['case_key']:r for r in candidates['cases']}
    if len(source)!=69 or len(candidate)!=69 or set(source)!=set(candidate):raise ValueError('Expected matching 69-case development populations')
    if any(r.get('status')!='candidate' for r in candidate.values()):raise ValueError('Unresolved candidate construction')
    rows=[audit_case(source[k],candidate[k]) for k in sorted(source)]
    reward=[r for r in rows if r['reward_kind']]
    def summary(items):
        return {'n':len(items),'cost_objective_detected':sum(r['objective_detection']['cost_explicit_detected'] for r in items),'latency_objective_detected':sum(r['objective_detection']['latency_explicit_detected'] for r in items),'with_review_signals':sum(bool(r['review_flags']) for r in items),'flag_counts':dict(Counter(f for r in items for f in r['review_flags']))}
    return {'rules_version':VERSION,'scope':'69 selected corrected development cases; outcome-independent automated review signals, not full development/held-out population','summary':summary(rows),'reward_cells':summary(reward),'by_benchmark':{b:summary([r for r in rows if r['benchmark']==b]) for b in sorted({r['benchmark'] for r in rows})},'changes_official_labels':False,'exclusions_applied':False,'held_out_accessed':False,'model_outputs_used':False,'limitations':['No-match is not semantic clearance; regex detection is bounded by documented literal forms.','Dates may be grounded outside explicit user turns; missing literal year is a review signal, not proof of wrong reference.','Identical advertised descriptions/schemas do not prove equivalent execution.','No task execution, model scoring, threshold selection or uncertainty calculation is performed.','The 69-case coverage-stratified diagnostic is not the full corrected development population.'],'cases':rows}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--audit',type=Path,required=True);p.add_argument('--candidates',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.resolve() in [args.audit.resolve(),args.candidates.resolve(),Path(__file__).resolve()]:raise ValueError('Do not overwrite source files')
    a=args.audit.read_bytes();c=args.candidates.read_bytes()
    if sha(a)!=AUDIT_HASH or sha(c)!=CANDIDATES_HASH:raise ValueError('Unsupported development audit or candidate snapshot')
    candidate_data=json.loads(c)
    if candidate_data.get('source_audit_sha256')!=AUDIT_HASH:raise ValueError('Candidate source provenance mismatch')
    result=analyze(json.loads(a),candidate_data);result['provenance']={'audit_sha256':sha(a),'candidates_sha256':sha(c),'implementation_sha256':sha(Path(__file__).read_bytes())}
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:result[k] for k in ['summary','reward_cells','by_benchmark']},indent=2))
