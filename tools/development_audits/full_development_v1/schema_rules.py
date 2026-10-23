"""Shallow declaration diagnostics copied from analysis policy v1; no scoring."""
from __future__ import annotations
import math

TYPE_ALIASES={"str":"string","int":"integer","float":"number","bool":"boolean","dict":"object","list":"array"}

def type_compatibility(value,declared,aliases):
    if isinstance(declared,list):
        results=[type_compatibility(value,t,aliases) for t in declared]
        return 'compatible' if 'compatible' in results else ('unknown' if 'unknown' in results else 'incompatible')
    if not isinstance(declared,str):return 'unknown'
    declared=aliases.get(declared,declared)
    checks={
        'string':lambda v:isinstance(v,str),
        'integer':lambda v:not isinstance(v,bool) and isinstance(v,(int,float)) and math.isfinite(v) and int(v)==v,
        'number':lambda v:not isinstance(v,bool) and isinstance(v,(int,float)) and math.isfinite(v),
        'boolean':lambda v:isinstance(v,bool),
        'object':lambda v:isinstance(v,dict),
        'array':lambda v:isinstance(v,list),
        'null':lambda v:v is None,
    }
    if declared not in checks:return 'unknown'
    return 'compatible' if checks[declared](value) else 'incompatible'

def combine(states):
    if 'incompatible' in states:return 'incompatible'
    if 'unknown' in states:return 'unknown'
    return 'compatible'

def schema_occurrence(arguments,schema,aliases):
    if not isinstance(arguments,dict):
        return {'declared_argument_checks':'incompatible','reason':'arguments_not_a_mapping','full_json_schema_validity':'not_assessed'}
    if not isinstance(schema,dict) or not isinstance(schema.get('properties'),dict):
        return {'declared_argument_checks':'unknown','reason':'property_metadata_unavailable','full_json_schema_validity':'not_assessed'}
    props=schema['properties'];unknown=sorted(set(arguments)-set(props))
    required=schema.get('required')
    required_known=isinstance(required,list) and all(isinstance(k,str) for k in required)
    missing=sorted(set(required)-set(arguments)) if required_known else None
    required_status=('incompatible' if missing else 'compatible') if required_known else 'unknown'
    types={k:type_compatibility(v,props[k].get('type') if isinstance(props[k],dict) else None,aliases) for k,v in arguments.items() if k in props}
    membership='incompatible' if unknown else 'compatible'
    return {
        'declared_argument_checks':combine([membership,required_status,*types.values()]),
        'argument_key_membership':membership,'undeclared_argument_keys':unknown,
        'required_key_presence':required_status,'missing_required_keys':missing,
        'argument_type_compatibility':types,'full_json_schema_validity':'not_assessed',
        'note':'Key membership is a declared-interface check, not the JSON Schema additionalProperties default. No coercion, nested/enum/format/semantic validation.',
    }

def inspect_call(call,tools,aliases):
    if not isinstance(call,dict):return {'name_available':False,'declared_argument_checks':'incompatible','reason':'call_not_a_mapping','matching_name_occurrences':0}
    name=call.get('name');matches=[(i,t) for i,t in enumerate(tools) if t.get('name')==name]
    arguments=call.get('parameters',call.get('arguments',{}))
    checks=[{'tool_occurrence_index':i,**schema_occurrence(arguments,t.get('parameters'),aliases)} for i,t in matches]
    states=[c['declared_argument_checks'] for c in checks]
    result='compatible' if 'compatible' in states else ('unknown' if 'unknown' in states else 'incompatible')
    return {'name':name,'name_available':bool(matches),'matching_name_occurrences':len(matches),
            'duplicate_name_ambiguity':len(matches)>1,'declared_argument_checks':result,'occurrence_checks':checks}
