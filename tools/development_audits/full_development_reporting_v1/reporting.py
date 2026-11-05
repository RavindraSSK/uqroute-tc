"""Retrospective development report helpers; no inference or label changes."""
import math


def taxonomy(records, models, classify):
    base={r['case_key']:r for r in models['qwen15b']}
    if len(base)!=1728:raise ValueError('Expected full construction candidate set')
    result={}
    for record in records:
        key=record['case_key']
        if key not in base:continue
        if key in result:raise ValueError('Duplicate selected metadata')
        if record.get('split')!='development' or record.get('population')!='primary':raise ValueError('Not primary development')
        if any(record[f]!=base[key][f] for f in ('benchmark','canonical_base_id','source_file')):raise ValueError('Taxonomy lineage differs')
        result[key]={'category':classify(record),'released_perturbation':record['sample']['perturbation']}
    if set(result)!=set(base):raise ValueError('Missing candidate taxonomy')
    return result


def common_rows(models, measure_names, cfg, measured, scope):
    indexes={m:{r['case_key']:r for r in rows} for m,rows in models.items()}
    base=indexes['qwen15b'];keys=sorted(k for k,r in base.items() if r['panel']==scope or r['benchmark']==scope)
    if any(set(index)!=set(base) for index in indexes.values()):raise ValueError('Model case sets differ')
    selected=[k for k in keys if all(measured(indexes[m][k],cfg['measures'][n]) is not None for m in indexes for n in measure_names)]
    rows=[{'case_key':k,'benchmark':base[k]['benchmark'],'canonical_base_id':base[k]['canonical_base_id'],
           'models':{m:{'error':not index[k]['official_score']['correct'],**{n:measured(index[k],cfg['measures'][n]) for n in measure_names}} for m,index in indexes.items()}} for k in selected]
    return rows,len(keys)


def low_uncertainty_band(rows, fraction=.2):
    if not 0<fraction<=1:raise ValueError('Invalid band fraction')
    values=[]
    for row in rows:
        whole=row['whole_output_scores']
        if whole is not None:
            value=whole['mean_token_nll']
            if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Invalid uncertainty')
            values.append(value)
    if not values:return {'eligible_rows':0,'accepted_rows':0,'threshold':None,'failure_case_keys':[]}
    threshold=sorted(values)[math.ceil(len(values)*fraction)-1]
    accepted=[r for r in rows if r['whole_output_scores'] is not None and r['whole_output_scores']['mean_token_nll']<=threshold]
    return {'eligible_rows':len(values),'accepted_rows':len(accepted),'threshold':threshold,
            'failure_case_keys':[r['case_key'] for r in accepted if r['official_score']['correct'] is False],
            'definition':'Lowest mean-NLL 20 percent target within model/benchmark; entire boundary tie retained; not calibrated confidence.'}


def calibrated_band(result):
    valid=[r for r in result['predictions'] if r['probability'] is not None]
    accepted=[r for r in valid if r['probability']<=.1]
    return {'oof_eligible_rows':len(valid),'accepted_rows':len(accepted),
            'failure_case_keys':[r['case_key'] for r in accepted if r['error']],
            'definition':'OOF estimated compliance probability >= 0.9; exploratory fixed reporting band, not a deployment threshold or coverage guarantee.'}
