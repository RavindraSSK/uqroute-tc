"""Saved-score-only descriptive development uncertainty diagnostics; no fitting."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile
import time
from metrics import discrimination,risk_coverage

HERE=Path(__file__).resolve().parent
POLICY_SHA='3ddb3454a4e3ace3b90306c8ec26b5b9ccd0e9b3ce8b17a73603bd76d32fe51f'


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)


def loads(raw):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('Duplicate JSON key')
            out[k]=v
        return out
    def invalid(_):raise ValueError('Nonfinite JSON value')
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)


def regular(path):
    if any(p.is_symlink() for p in (path,*path.parents)) or not path.is_file():raise ValueError('Expected regular file without symlink ancestors')
    return path.read_bytes()


def policy():
    raw=regular(HERE/'analysis_policy_v1.json').replace(b'\r\n',b'\n')
    if sha(raw)!=POLICY_SHA:raise ValueError('Versioned analysis policy differs')
    return loads(raw)


def index(rows):
    out={}
    for row in rows:
        if row['case_key'] in out:raise ValueError('Duplicate case key')
        out[row['case_key']]=row
    return out


def measured(row,location):
    parent=row.get(location[0])
    if parent is None:return None
    if not isinstance(parent,dict) or location[1] not in parent:raise ValueError('Malformed saved measure')
    value=parent[location[1]]
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Nonfinite or malformed saved measure')
    return value


def validate_rows(rows,requests,cfg):
    cases=index(rows);prepared=index(requests)
    if len(rows)!=69 or set(cases)!=set(prepared):raise ValueError('Not the selected 69 development cases')
    if Counter(r['benchmark'] for r in rows)!=Counter({'apibank':17,'bfcl_v3':12,'rotbench':17,'toolalpaca':17,'tooleyes':6}):
        raise ValueError('Benchmark coverage differs')
    for row in rows:
        req=prepared[row['case_key']]
        if any(row[k]!=req[k] for k in ('benchmark','source_file','canonical_base_id')):raise ValueError('Case lineage differs')
        expected='tooleyes_relevance' if row['benchmark']=='tooleyes' else 'official_reference_compliance'
        if row['panel']!=expected or row['official_labels_changed'] is not False or row['ambiguity_exclusion_applied'] is not False:
            raise ValueError('Panel or label boundary differs')
        if row['evidence_status'] not in {'complete','truncated'} or type(row['official_score']['correct']) is not bool:
            raise ValueError('Invalid official outcome or incomplete evidence')
        if row['evidence_status']=='truncated' and (row['whole_output_scores'] is not None or row['meaningful_token_score'] is not None):
            raise ValueError('Truncated uncertainty must remain unavailable')
        for location in cfg['measures'].values():measured(row,location)
    return rows


def one_measure(rows,name,cfg,original_rows):
    location=cfg['measures'][name]
    eligible=[r for r in rows if measured(r,location) is not None]
    labels=[not r['official_score']['correct'] for r in eligible]
    scores=[measured(r,location) for r in eligible]
    unavailable=[r for r in rows if measured(r,location) is None]
    return {'eligible_case_keys':[r['case_key'] for r in eligible],
            'unavailable_case_keys':[r['case_key'] for r in unavailable],
            'unavailable_reasons':dict(Counter(r.get('alignment_diagnostic',{}).get('category','saved_measure_unavailable')
                if location[0]=='meaningful_token_score' else 'saved_measure_unavailable' for r in unavailable)),
            'discrimination':discrimination(labels,scores),
            'risk_coverage':risk_coverage(labels,scores,original_rows)}


def cohort(rows,cfg):
    total=len(rows);correct=sum(r['official_score']['correct'] for r in rows)
    common=[r for r in rows if all(measured(r,loc) is not None for loc in cfg['measures'].values())]
    return {'original_rows':total,'canonical_groups':len({r['canonical_base_id'] for r in rows}),
            'official_correct':correct,'official_noncompliant_or_irrelevant':total-correct,
            'official_accuracy':correct/total if total else None,
            'reference_flagged_rows_retained':sum(bool(r['reference_review_flags']) for r in rows),
            'available_case_analysis':{name:one_measure(rows,name,cfg,total) for name in cfg['measures']},
            'common_eligible_case_analysis':{'rows':len(common),'case_keys':[r['case_key'] for r in common],
                'canonical_groups':len({r['canonical_base_id'] for r in common}),
                'measures':{name:one_measure(common,name,cfg,total) for name in cfg['measures']},
                'limit':'Same-case comparison across measures; not clean/perturbed group pairing or random missingness.'}}


def analyze(rows,cfg):
    return {'version':cfg['version'],'scope':cfg['scope'],'rows':len(rows),
            'by_panel':{p:cohort([r for r in rows if r['panel']==p],cfg) for p in ('official_reference_compliance','tooleyes_relevance')},
            'by_benchmark':{b:cohort([r for r in rows if r['benchmark']==b],cfg) for b in sorted({r['benchmark'] for r in rows})},
            'calibration':'not_fitted_or_evaluated','routing_threshold':'not_selected','group_bootstrap':'not_performed',
            'official_labels_changed':False,'reference_exclusions_applied':False,
            'held_out_access_enabled':False,'main_experiment_ready':False,'network_requests':0,'prior_files_modified':False,
            'limits':['Retrospective development diagnostics on one hash-selected case per constructed stratum, not population estimates or a final protocol freeze.',
                      'Official noncompliance and ToolEyes irrelevance are proxy outcomes, not execution failure or semantic adjudication.',
                      'Pooled benchmark measures can be confounded by benchmark-specific score scales and outcome rates; inspect per-benchmark results.',
                      'Meaningful-token availability changes the case population. Compare common eligible cases separately; neither cohort repairs nonrandom missingness.',
                      'Score ties are exact equality with no rounding, jitter or tie splitting. Curve cutoffs are observed score blocks, not chosen deployment thresholds.',
                      'Zero-acceptance risk is undefined; unavailable evidence never becomes certain or incorrect through imputation.',
                      'AP is noninterpolated tied-score-block average precision, not trapezoidal PR AUC. Error prevalence is reported, not asserted as exact expected finite-sample random AP.',
                      'No group independence assumption, confidence interval, significance test or causal perturbation comparison is supplied.',
                      'Token likelihood is not calibrated correctness probability. No exponential mapping, calibration fit or held-out method selection is performed.']}


def publish(source,output):
    for attempt in range(6):
        if output.exists() or output.is_symlink():raise ValueError('Output exists; preserve it')
        try:source.rename(output);return
        except PermissionError:
            if attempt==5:raise
            time.sleep(0.1*(2**attempt))
