"""Shared development-bundle format; no network or inference operations."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

BASE_COMMIT='05a95bfb0d18755a834819862da46c014b4ccae2'
BENCHMARK_REVISION='d5d03180de41eb30a6c796d04a9bfbd9dad85c1d'
SPLIT_SHA='688c1013d8fe9d5c1b454d14d4cbe215659e48adc7bdfd63175580e83e2eb0db'
RUNNER_SHA='e305a816c96ed574ad18ca90871775721fd79fcf3533a60077b26d1fdeef20d8'
VERSION='uqroute-development-pipeline-1.0.0'
SOURCE_FILES=tuple(sorted(stem+'.jsonl' for stem in ('clean','CD','CD_AB','CD_NT','TD','TD_AB','TD_NT','paraphrase_parameter_description','paraphrase_tool_description','query_paraphrase','realistic_typos','redundant','same_name_A','same_name_B','same_name_C','same_name_D','same_name_E')))
BENCHMARKS={'apibank','bfcl_v3','rotbench','toolalpaca','tooleyes'}
BUNDLE_FILES={'samples.jsonl','references.jsonl','membership.json','attestation.json'}
SAMPLE_FIELDS={'id','benchmark','category','level','perturbation','conversation','tools'}

def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)

def sha(raw):return hashlib.sha256(raw).hexdigest()

def _pairs(items):
    result={}
    for key,value in items:
        if key in result:raise ValueError('Duplicate JSON key')
        result[key]=value
    return result

def loads(raw):
    return json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Nonfinite JSON value')))

def decode(value):return loads(value) if isinstance(value,str) else value

def json_bytes(value):return (json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()

def lines_bytes(rows):return ''.join(canonical(row)+'\n' for row in rows).encode()

def code_hashes():
    folder=Path(__file__).parent
    names=['common.py','export_development.py','audit_development.py','identity_v1.py','repair.py','base_adapter.py','reference_rules.py','schema_rules.py','official_runner.py']
    return {name:sha((folder/name).read_bytes().replace(b'\r\n',b'\n')) for name in names}

def read_regular(path):
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('Expected a regular non-symlink file')
    return path.read_bytes()
