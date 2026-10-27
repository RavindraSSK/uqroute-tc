import math
import unittest
import calibration as c
import paired_intervals as p


class Calibration(unittest.TestCase):
    def test_increasing(self):
        m=c.fit([0,1,2,3],[False,False,True,True])
        self.assertGreater(m['slope'],0)
        probs=[c.predict(m,x) for x in [0,1,2,3,100]]
        self.assertEqual(probs,sorted(probs))
    def test_reverse_boundary(self):
        m=c.fit([0,1,2,3],[True,True,False,False])
        self.assertEqual(m['slope'],0)
        self.assertTrue(m['boundary_solution'])
        self.assertAlmostEqual(c.predict(m,100),.5)
    def test_boundary_intercept(self):
        m=c.fit([0,1,2,3],[True,False,False,False])
        self.assertEqual(m['slope'],0)
        self.assertAlmostEqual(c.predict(m,9),.25)
    def test_constant_scores(self):
        m=c.fit([2,2,2,2],[True,False,False,False])
        self.assertAlmostEqual(c.predict(m,2),.25)
    def test_bad_inputs(self):
        for xs,ys in [([],[]),([1],[True]),([-1,2],[True,False]),([math.nan,2],[True,False]),([1,2],[1,0])]:
            with self.subTest(xs=xs),self.assertRaises(ValueError):c.fit(xs,ys)
    def test_crossfit_groups(self):
        rows=[{'case_key':f'{g}/{v}','benchmark':'b','canonical_base_id':str(g),'score':g+v/10,'error':g%2==0} for g in range(30) for v in range(2)]
        result=c.crossfit(rows,c.folds(rows))
        self.assertEqual(result['oof_rows'],60)
        bykey={r['case_key']:r['canonical_base_id'] for r in rows}
        for f in result['folds']:
            self.assertFalse({bykey[k] for k in f['train_case_keys']} & {bykey[k] for k in f['validation_case_keys']})
            self.assertGreaterEqual(f['fitted_parameters']['slope'],0)
    def test_objective_optimum(self):
        # Check feasible nearby parameters against constrained optimum.
        for ys in [[True,False,True,False,False],[False,False,True,True,True]]:
            xs=[0,.1,1,2,5];m=c.fit(xs,ys)
            z=[(math.log1p(x)-m['log1p_train_mean'])/m['log1p_train_scale'] for x in xs]
            def loss(a,b):return sum(c.softplus(a+b*x)-y*(a+b*x) for x,y in zip(z,ys))+.5*b*b
            optimum=loss(m['intercept'],m['slope'])
            for da in [-.1,0,.1]:
                for db in [-.1,0,.1]:
                    b=m['slope']+db
                    if b>=0:self.assertLessEqual(optimum,loss(m['intercept']+da,b)+1e-8)


class Pairing(unittest.TestCase):
    def row(self,k,g,a,b):
        return {'perturbed_case_key':k,'clean_case_key':'clean/'+g,'benchmark':'b','canonical_base_id':g,'panel':'ref','source_file':'x','clean_correct':a,'perturbed_correct':b,'correctness_change_perturbed_minus_clean':int(b)-int(a)}
    def data(self):
        rows=[self.row('a','1',True,False),self.row('b','1',True,False),self.row('c','2',False,True)]
        return {'a':rows,'b':[{**r,'perturbed_correct':r['clean_correct'],'correctness_change_perturbed_minus_clean':0} for r in rows]}
    def test_weighting(self):
        groups=p.units(self.data());value=p.aggregate([g['models'] for g in groups],['a','b'])
        self.assertAlmostEqual(value['a/pair_weighted_change'],-1/3)
        self.assertEqual(value['a/equal_group_change'],0)
    def test_resampled_multiplicity(self):
        groups=p.units(self.data());value=p.aggregate([groups[0]['models'],groups[0]['models'],groups[1]['models']],['a','b'])
        self.assertAlmostEqual(value['a/equal_group_change'],-1/3)
        self.assertAlmostEqual(value['a/pair_weighted_change'],-3/5)
    def test_join_rejects(self):
        data=self.data();data['b']=data['b'][:-1]
        with self.assertRaises(ValueError):p.units(data)
    def test_duplicate_rejected(self):
        data=self.data();data['a'].append(data['a'][0])
        with self.assertRaises(ValueError):p.units(data)
    def test_lineage_rejected(self):
        data=self.data();data['b'][0]['clean_case_key']='wrong'
        with self.assertRaises(ValueError):p.units(data)
    def test_deterministic(self):
        def interval(point,samples,reps,groups):return [point,samples,reps,groups]
        units=p.units(self.data())
        a=p.bootstrap(units,['a','b'],interval,replicates=20)
        b=p.bootstrap(units,['a','b'],interval,replicates=20)
        self.assertEqual(a,b)
        self.assertEqual(a['metrics']['a/pair_weighted_change'][2:], [20,2])
    def test_empty(self):
        self.assertIsNone(p.aggregate([],['a'])['a/equal_group_change'])


if __name__=='__main__':unittest.main()
