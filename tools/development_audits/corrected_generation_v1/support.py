"""Checked source loading and write-once local artifact helpers."""
from __future__ import annotations
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
from typing import Any

BASE = '85de7822d768d71548a1fbb7ceb45e65a2a5792e'
HERE = Path(__file__).resolve().parent
SOURCE_MANIFEST_SHA = '3c6d9aa632951d5a82bc6ae1679f6bbda8884d5938d0997b5f7fc4d5cf699387'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(canonical(value).encode())


def loads(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError('Duplicate JSON key')
            out[key] = value
        return out
    def invalid(_):
        raise ValueError('Nonfinite JSON value')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('Expected regular file')
    return path.read_bytes()


def write_once(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def json_once(path, value):
    write_once(path, (canonical(value) + '\n').encode())


def fresh_directory(output, values):
    if output.exists() or output.is_symlink():
        raise ValueError('Output already exists')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent, prefix='corrected-dev-') as tmp:
        for name, value in values.items():
            json_once(Path(tmp) / name, value)
        if output.exists():
            raise ValueError('Output appeared while writing')
        Path(tmp).rename(output)


def artifact_path(repo, output, inputs=()):
    result = output.resolve()
    root = repo.resolve() / 'artifacts/local_development_audits'
    if result == root or not result.is_relative_to(root):
        raise ValueError('Output must be a child of local development artifacts')
    for item in inputs:
        source = item.resolve()
        if source == result or source in result.parents or result in source.parents:
            raise ValueError('Output overlaps prior input')
    return result


def source_bytes(repo):
    manifest_raw = read(HERE / 'source_manifest.json').replace(b'\r\n', b'\n')
    if sha(manifest_raw) != SOURCE_MANIFEST_SHA:
        raise ValueError('Source manifest differs; version any amendment')
    manifest = loads(manifest_raw)
    if manifest['baseline_commit'] != BASE:
        raise ValueError('Unexpected baseline')
    result = {}
    for path, expected in manifest['source_files'].items():
        raw = read(repo / path).replace(b'\r\n', b'\n')
        if sha(raw) != expected['sha256_lf']:
            raise ValueError('Pinned source fingerprint differs')
        result[path] = raw
    return result


def verify_baseline(repo):
    subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', BASE, 'HEAD'],
                   check=True, capture_output=True)
    source_bytes(repo)
    return subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()


def implementation_hashes():
    return {name: sha(read(HERE / name).replace(b'\r\n', b'\n')) for name in
            ('support.py', 'workflow.py', 'workflow_config.json', 'source_manifest.json')}


def module_from_ast(name, tree, injected=None):
    module = types.ModuleType(name)
    module.__dict__.update(injected or {})
    sys.modules[name] = module
    exec(compile(ast.fix_missing_locations(tree), name, 'exec'), module.__dict__)
    return module


def methods(repo):
    """Compile checked definitions with source methods unchanged, no project imports.

    Only pilot.token_evidence is extracted; single/alignment project imports
    are supplied with the same checked functions. The pinned released parser
    module omits optional OpenAI/tqdm imports and never runs its main function.
    """
    sources = source_bytes(repo)
    def load(relative, name, injected=None, remove_prefix=None):
        tree = ast.parse(sources[relative])
        if remove_prefix:
            tree.body = [n for n in tree.body if not (
                isinstance(n, ast.ImportFrom) and n.module and n.module.startswith(remove_prefix))]
        return module_from_ast(name, tree, injected)
    pilot = ast.parse(sources['src/uqroute_tc/inference/pilot.py'])
    pilot.body = [n for n in pilot.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 'token_evidence']
    token = module_from_ast('_corrected_dev_pilot', pilot, {'math': math, 'Any': Any}).token_evidence
    canonical_module = load('src/uqroute_tc/parsing/canonical.py', '_corrected_dev_canonical')
    single = load('src/uqroute_tc/uncertainty/single.py', '_corrected_dev_single', {'token_evidence': token}, 'uqroute_tc')
    alignment = load('src/uqroute_tc/uncertainty/alignment.py', '_corrected_dev_alignment',
                     {'token_evidence': token, 'canonical_key': canonical_module.canonical_key}, 'uqroute_tc')
    parser_tree = ast.parse(sources['tools/development_audits/full_development_v1/official_runner.py'])
    parser_tree.body = [ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0)] + [n for n in parser_tree.body if not (isinstance(n, ast.ImportFrom) and n.module in {'openai', 'tqdm'})]
    parser = module_from_ast('_corrected_dev_reference_parser', parser_tree).parse_tool_calls
    population = load('tools/development_audits/population_policy_v1/plan_population.py', '_corrected_dev_population')
    return {'token_evidence': token, 'single': single.single_sample_scores,
            'meaningful': alignment.meaningful_token_score,
            'parse': lambda raw, benchmark: canonical_module.parse_prediction(raw, benchmark, parser),
            'population_plan': population.plan}
