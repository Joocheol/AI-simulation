#!/usr/bin/env python3
"""Reproducible Hill / constrained POT-GPD laboratory.
Requires: Python 3.10+, numpy, scipy (pip install numpy scipy).
Usage: python tail_lab.py --csv returns.csv --column return --tail loss --q .9 --k 100
Without --csv, generates seed-20261003 GPD magnitudes and negates them as losses.
CSV must contain numeric returns (not prices); zeros/nonfinite values are excluded.
No confidence intervals: dependence, threshold selection and finite-sample bias matter.
"""
import argparse, csv, json
import numpy as np
from scipy.optimize import minimize
from scipy.stats import genpareto

def select_tail(returns, tail='loss'):
    r=np.asarray(returns,dtype=float);r=r[np.isfinite(r)]
    x=-r if tail=='loss' else r if tail=='gain' else np.abs(r)
    return x[x>0]

def hill(values,k):
    x=np.asarray(values,dtype=float);x=np.sort(x[np.isfinite(x)&(x>0)])[::-1]
    if not 1<=k<len(x):return {'valid':False,'reason':'Require 1 <= k < positive sample count'}
    u=x[k];xi=float(np.mean(np.log(x[:k]/u)))
    return {'valid':xi>0,'k':k,'u':float(u),'xi':xi,'alpha':1/xi if xi>0 else None,'ties':bool(x[k-1]==u)}

def fit_gpd(values,q=.9):
    x=np.asarray(values,dtype=float);x=x[np.isfinite(x)&(x>0)]
    if not 0<=q<1 or not len(x):return {'valid':False,'reason':'Invalid quantile or empty positive tail'}
    u=float(np.quantile(x,q,method='linear'));y=x[x>u]-u;n=len(y)
    base={'nTail':len(x),'nExceed':n,'u':u,'quantile':q}
    if n<20:return {**base,'valid':False,'reason':'Fewer than 20 strict exceedances'}
    norm=y.mean();z=y/norm
    def nll(p):
        xi,ls=p;b=np.exp(ls)
        if not -.5<=xi<=2 or not -25<=ls<=25 or np.any(1+xi*z/b<=0):return np.inf
        return float(-np.sum(genpareto.logpdf(z,xi,loc=0,scale=b)))
    fits=[minimize(nll,[c,np.log(max(.2,1-c,-c*z.max()*1.05))],method='Nelder-Mead',
        options={'maxiter':3000,'xatol':1e-10,'fatol':1e-9}) for c in [-.4,-.2,0,.2,.6,1.3,1.9]]
    best=min(fits,key=lambda f:f.fun);xi=float(best.x[0]);scale=float(np.exp(best.x[1])*norm)
    ll=float(-best.fun-n*np.log(norm))
    return {**base,'valid':bool(np.isfinite(best.fun)),'converged':bool(best.success),'boundary':bool(xi<-.4999 or xi>1.9999),
        'xi':xi,'scale':scale,'loglik':ll,'AIC':4-2*ll,'endpoint':u-scale/xi if xi<0 else None,
        'warnings':['Fewer than 50 exceedances: unstable estimate'] if n<50 else []}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--csv');p.add_argument('--column',default='return')
    p.add_argument('--tail',choices=['loss','gain','absolute'],default='loss');p.add_argument('--q',type=float,default=.9)
    p.add_argument('--k',type=int,default=100);p.add_argument('--seed',type=int,default=20261003);p.add_argument('--n',type=int,default=5000)
    args=p.parse_args()
    if args.csv:
        with open(args.csv,encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        if rows and args.column not in rows[0]:raise SystemExit('Requested return column missing')
        returns=[]
        for row in rows:
            try:returns.append(float(row[args.column]))
            except (ValueError,TypeError):pass
        source=args.csv
    else:
        rng=np.random.default_rng(args.seed);returns=-genpareto.rvs(.3,scale=.01,size=args.n,random_state=rng);source='seeded GPD simulation, xi=.3 scale=.01'
    x=select_tail(returns,args.tail)
    print(json.dumps({'source':source,'seed':args.seed,'tail':args.tail,'hill':hill(x,args.k),'gpd':fit_gpd(x,args.q),
      'notes':['Hill assumes positive regularly varying tails; no proof of a power law.',
       'GPD xi<0 is a finite endpoint; xi=0 is exponential. Search range [-.5,2].',
       'Threshold selection and serial volatility clusters affect interpretation; no naive confidence intervals.',
       'AIC is conditional on one threshold; do not compare AIC across different exceedance samples.']},indent=2,allow_nan=False))
if __name__=='__main__':main()
