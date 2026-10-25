"""Dependency-free, explicitly tied-threshold development ranking diagnostics."""
from __future__ import annotations
from itertools import groupby
import math


def checked(labels,scores):
    if len(labels)!=len(scores):raise ValueError('Label/score lengths differ')
    if any(type(y) is not bool for y in labels):raise ValueError('Error labels must be bool')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in scores):
        raise ValueError('Scores must be finite real numbers; no bool or missing values')
    return list(zip(scores,labels))


def discrimination(labels,scores):
    """Higher scores predict official noncompliance/irrelevance (error=True).

    AUROC: error/compliant pair concordance, ties half credit.
    AP: descending score blocks, sum(delta_recall * precision_after_block).
    """
    pairs=checked(labels,scores);n=len(pairs);positive=sum(labels);negative=n-positive
    roc=None;roc_reason=None;ap=None;ap_reason=None
    if not n:
        roc_reason=ap_reason='no_eligible_observations'
    else:
        if not positive or not negative:roc_reason='one_class_outcomes'
        else:
            # Ascending rank sweep, maintaining negatives strictly below block.
            wins=0.0;neg_below=0
            for _,block in groupby(sorted(pairs,key=lambda x:x[0]),key=lambda x:x[0]):
                block=list(block);p=sum(y for _,y in block);q=len(block)-p
                wins+=p*(neg_below+0.5*q);neg_below+=q
            roc=wins/(positive*negative)
        if not positive:ap_reason='no_error_positive_observations'
        else:
            tp=seen=0;ap=0.0
            for _,block in groupby(sorted(pairs,key=lambda x:x[0],reverse=True),key=lambda x:x[0]):
                block=list(block);new_positive=sum(y for _,y in block)
                tp+=new_positive;seen+=len(block)
                ap+=(new_positive/positive)*(tp/seen)
    return {'eligible_rows':n,'error_positive_rows':positive,'compliant_rows':negative,
            'error_prevalence':positive/n if n else None,
            'auroc':roc,'auroc_undefined_reason':roc_reason,
            'average_precision':ap,'average_precision_undefined_reason':ap_reason,
            'average_precision_definition':'noninterpolated score-block AP; not trapezoidal PR area'}


def risk_coverage(labels,scores,panel_rows):
    """Accept ascending uncertainty by entire equal-score blocks; no tie splits."""
    pairs=checked(labels,scores);n=len(pairs)
    if type(panel_rows) is not int or panel_rows<0 or panel_rows<n:
        raise ValueError('Invalid original panel denominator')
    points=[{'threshold_inclusive':None,'accepted_rows':0,'accepted_errors':0,
             'eligible_coverage':0.0 if n else None,'panel_coverage':0.0 if panel_rows else None,'risk':None}]
    accepted=errors=0;area=0.0
    for score,block in groupby(sorted(pairs,key=lambda x:x[0]),key=lambda x:x[0]):
        block=list(block);accepted+=len(block);errors+=sum(y for _,y in block)
        risk=errors/accepted
        if n:area+=(len(block)/n)*risk
        points.append({'threshold_inclusive':score,'accepted_rows':accepted,'accepted_errors':errors,
                       'eligible_coverage':accepted/n,'panel_coverage':accepted/panel_rows,'risk':risk})
    return {'original_panel_rows':panel_rows,'eligible_rows':n,'original_panel_rows_outside_eligible_cohort':panel_rows-n,
            'maximum_panel_coverage':n/panel_rows if panel_rows else None,
            'tie_block_right_step_area_on_eligible_coverage':area if n else None,
            'area_definition':'sum(block_size / eligible_rows * cumulative_error_risk_after_block)',
            'points':points,'routing_threshold_selected':False}
