"""Replay saved smoke requests, parser outputs and official scoring; never infer."""
import argparse
import ast
import hashlib
import importlib.util
import json
import zipfile
from collections import Counter
from pathlib import Path


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replay(archive,audit_path):
    folder=Path(__file__).parent
    runner_bytes=(folder/'official_runner.py').read_bytes()
    scorer_bytes=(folder/'official_scorer.py').read_bytes()
    assert sha(runner_bytes)=='e305a816c96ed574ad18ca90871775721fd79fcf3533a60077b26d1fdeef20d8'
    assert sha(scorer_bytes)=='2e29741b3fe7c46d5cc99da1a0a6c75ff52d9d8c4d6156db21cdc55ef115a894'
    tree=ast.parse(runner_bytes)
    body=[n for n in tree.body if not (isinstance(n,ast.ImportFrom) and n.module in {'openai','tqdm'})]
    tree=ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),*body],type_ignores=[]))
    ns={'__name__':'pinned_parser_replay'}
    exec(compile(tree,'pinned_runner_replay','exec'),ns)
    spec=importlib.util.spec_from_file_location('pinned_scorer',folder/'official_scorer.py')
    scorer=importlib.util.module_from_spec(spec);spec.loader.exec_module(scorer)
    raw=audit_path.read_bytes();audit=json.loads(raw);index={r['case_key']:r for r in audit['cases']}
    rows=[]
    with zipfile.ZipFile(archive) as z:
        metadata=json.loads(z.read('metadata.json'));preview=json.loads(z.read('preview.json'))
        assert sha(raw)==metadata['audit_sha256']
        assert sha(z.read('adapter_source.py'))==metadata['adapter_sha256']
        candidates={r['case_key']:r for r in preview['cases']}
        assert len(candidates)==69 and set(candidates)==set(index)
        seen=set()
        for item in metadata['records']:
            record=json.loads(z.read(item['record_file']));key=record['case_key'];assert key not in seen;seen.add(key)
            assert key==item['case_key'] and record['status']==item['status']
            request=record['request'];assert request['messages']==candidates[key]['messages']
            assert sha(canonical(request).encode())==record['request_sha256']
            assert sha(canonical(request['messages']).encode())==record['candidate_messages_sha256']
            assert record['prediction']['raw_output']==record['response']['choices'][0]['message']['content']
            original=index[key];parsed=ns['parse_tool_calls'](record['prediction']['raw_output'],original['benchmark'])
            assert parsed==record['prediction']['tool_calls']
            method=record['official_score']['method']
            # Replay each saved benchmark-specific calculation. This does not
            # independently reconstruct the original sample's eval_config dispatch.
            if method=='name_match':result=scorer.score_relevance(parsed,original['golden_answers'])
            elif method=='rule_based':result=scorer.score_rule_based(parsed,original['golden_answers'])
            elif method=='exact_match':result=scorer.score_exact_match(parsed,original['golden_answers'],benchmark=original['benchmark'])
            else:raise ValueError('Unexpected scoring method')
            assert result==record['official_score']
            rows.append({'case_key':key,'benchmark':original['benchmark'],'official_score':result,'status':record['status'],'finish_reason':record['finish_reason'],'record_sha256':sha(z.read(item['record_file']))})
    assert len(rows)==8
    return {'scope':'CPU-only smoke scoring review; official labels unchanged; no inference',
            'source_archive_sha256':sha(archive.read_bytes()),'source_audit_sha256':sha(raw),
            'parser_sha256':sha(runner_bytes),'scorer_sha256':sha(scorer_bytes),
            'scored_records':len(rows),'official_correct':sum(r['official_score']['correct'] for r in rows),
            'response_status_counts':dict(Counter(r['status'] for r in rows)),
            'finish_reason_counts':dict(Counter(r['finish_reason'] for r in rows)),
            'requested_temperature':0.001,'effective_temperature_reported_by_server':metadata['effective_temperature_reported_by_server'],
            'validation_boundary':'Replayed saved request fingerprints, parser outputs and saved-method score calculations. Full source eval_config dispatch not independently reconstructed here. No tools executed, no token alignment/uncertainty validated.',
            'freeze_status':'PROPOSED_RULES_NOT_YET_IMPLEMENTED_OR_FINALIZED','cases':rows}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--audit',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.resolve() in (args.archive.resolve(),args.audit.resolve()):raise ValueError('Do not overwrite input evidence')
    result=replay(args.archive,args.audit)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['scored_records','official_correct','response_status_counts','finish_reason_counts','freeze_status']},indent=2))
