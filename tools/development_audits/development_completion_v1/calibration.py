"""Fixed, exploratory group-separated cross-fitting of error probabilities."""
import hashlib
import math


def folds(rows):
    strata = {}
    for r in rows:
        strata.setdefault(r['benchmark'], set()).add(r['canonical_base_id'])
    result = {}
    for benchmark, groups in sorted(strata.items()):
        ordered = sorted(groups, key=lambda g:hashlib.sha256(('1729/'+benchmark+'/'+g).encode()).hexdigest())
        for i, group in enumerate(ordered):
            result[(benchmark, group)] = i % 5
    return result


def sigmoid(x):
    return 1/(1+math.exp(-x)) if x >= 0 else math.exp(x)/(1+math.exp(x))


def softplus(x):
    return max(x,0)+math.log1p(math.exp(-abs(x)))


def unconstrained_fit(scores, labels):
    if len(scores)!=len(labels) or not scores or any(type(y) is not bool for y in labels):
        raise ValueError('Training scores and boolean labels required')
    if any(type(x) not in (int,float) or not math.isfinite(x) or x < 0 for x in scores):
        raise ValueError('Finite nonnegative NLL required')
    if len(set(labels)) < 2:
        raise ValueError('Training requires both outcome classes')
    xs = [math.log1p(x) for x in scores]
    mean = sum(xs)/len(xs)
    scale = math.sqrt(sum((x-mean)**2 for x in xs)/len(xs)) or 1.0
    xs = [(x-mean)/scale for x in xs]
    a, b = math.log(sum(labels)/(len(labels)-sum(labels))), 0.0
    def objective(a,b):
        return sum(softplus(a+b*x)-y*(a+b*x) for x,y in zip(xs,labels))+.5*b*b
    converged = False
    for iteration in range(100):
        probs = [sigmoid(a+b*x) for x in xs]
        weights = [p*(1-p) for p in probs]
        ga = sum(p-y for p,y in zip(probs,labels))
        gb = sum((p-y)*x for p,y,x in zip(probs,labels,xs))+b
        if max(abs(ga),abs(gb)) < 1e-8:
            converged = True
            break
        haa = sum(weights); hab = sum(w*x for w,x in zip(weights,xs))
        hbb = sum(w*x*x for w,x in zip(weights,xs))+1
        determinant = haa*hbb-hab*hab
        if determinant <= 0:
            raise ValueError('Singular calibration Hessian')
        da = (hbb*ga-hab*gb)/determinant
        db = (haa*gb-hab*ga)/determinant
        old = objective(a,b)
        step = 1.0
        for _ in range(40):
            if objective(a-step*da,b-step*db) <= old-1e-4*step*(ga*da+gb*db):
                break
            step *= .5
        else:
            raise ValueError('Calibration line search failed')
        a -= step*da; b -= step*db
        if max(abs(step*da),abs(step*db)) < 1e-9:
            converged = True
            break
    if not converged:
        raise ValueError('Calibration did not converge')
    return {'intercept':a,'slope':b,'log1p_train_mean':mean,'log1p_train_scale':scale,'iterations':iteration+1}


def fit(scores, labels):
    """Convex ridge logistic optimum constrained to a nonnegative error slope."""
    model = unconstrained_fit(scores, labels)
    model['constraint'] = 'error_probability_nondecreasing_with_nll'
    if model['slope'] < 0:
        # The strictly convex objective's constrained optimum is on b=0.
        # Re-optimize the unpenalized intercept at the training error fraction.
        model['intercept'] = math.log(sum(labels)/(len(labels)-sum(labels)))
        model['slope'] = 0.0
        model['boundary_solution'] = True
    else:
        model['boundary_solution'] = False
    return model


def predict(model, score):
    if type(score) not in (int,float) or not math.isfinite(score) or score < 0:
        raise ValueError('Finite nonnegative NLL required')
    return sigmoid(model['intercept']+model['slope']*(math.log1p(score)-model['log1p_train_mean'])/model['log1p_train_scale'])


def measures(predictions):
    bins = [{'rows':0,'sum_probability':0.,'errors':0} for _ in range(10)]
    brier = loss = 0.0
    for r in predictions:
        p,y = r['probability'],r['error']
        if type(y) is not bool or type(p) not in (float,int) or not math.isfinite(p) or not 0<=p<=1:
            raise ValueError('Invalid probability or outcome')
        cell = bins[min(int(p*10),9)]
        cell['rows'] += 1; cell['sum_probability'] += p; cell['errors'] += y
        brier += (p-y)**2
        clipped = max(1e-15,min(1-1e-15,p))
        loss -= math.log(clipped if y else 1-clipped)
    n = len(predictions); ece = 0.0
    for i,cell in enumerate(bins):
        count = cell['rows']
        cell.update({'lower_inclusive':i/10,'upper':(i+1)/10,'upper_inclusive':i==9,
                     'mean_error_probability':cell['sum_probability']/count if count else None,
                     'observed_error_rate':cell['errors']/count if count else None})
        if count: ece += count/n*abs(cell['mean_error_probability']-cell['observed_error_rate'])
    return {'rows':n,'brier_score':brier/n if n else None,'log_loss_clipped_1e_minus_15':loss/n if n else None,
            'ece_10_equal_width_bins':ece if n else None,'reliability_bins':bins}


def crossfit(rows, assignment):
    if len({r['case_key'] for r in rows})!=len(rows):
        raise ValueError('Duplicate case identity')
    predictions = []; fold_records = []
    for fold in range(5):
        train = [r for r in rows if assignment[(r['benchmark'],r['canonical_base_id'])] != fold]
        test = [r for r in rows if assignment[(r['benchmark'],r['canonical_base_id'])] == fold]
        groups = {(r['benchmark'],r['canonical_base_id']) for r in train}
        if groups & {(r['benchmark'],r['canonical_base_id']) for r in test}:
            raise ValueError('Group leakage')
        reason = None
        if not test: reason = 'no_validation_rows'
        elif len(groups) < 10: reason = 'fewer_than_10_training_groups'
        elif len({r['error'] for r in train}) < 2: reason = 'one_class_training_outcomes'
        record = {'fold':fold,'train_case_keys':[r['case_key'] for r in train],
                  'validation_case_keys':[r['case_key'] for r in test],'unavailable_reason':reason}
        if reason:
            predictions.extend({'case_key':r['case_key'],'fold':fold,'error':r['error'],'probability':None,'baseline_probability':None,'unavailable_reason':reason} for r in test)
        else:
            model = fit([r['score'] for r in train],[r['error'] for r in train])
            constant = (sum(r['error'] for r in train)+1)/(len(train)+2)
            record.update({'fitted_parameters':model,'training_fold_smoothed_baseline':constant})
            predictions.extend({'case_key':r['case_key'],'fold':fold,'error':r['error'],'probability':predict(model,r['score']),
                                'baseline_probability':constant,'unavailable_reason':None} for r in test)
        fold_records.append(record)
    valid = [r for r in predictions if r['probability'] is not None]
    baseline = [{**r,'probability':r['baseline_probability']} for r in valid]
    return {'input_rows':len(rows),'oof_rows':len(valid),'unavailable_rows':len(rows)-len(valid),
            'logistic':measures(valid),'training_fold_constant_baseline':measures(baseline),
            'folds':fold_records,'predictions':predictions}
