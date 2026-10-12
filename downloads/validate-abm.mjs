import fs from 'node:fs';
import assert from 'node:assert/strict';
import {BornholdtModel,heatBathProbability,summarizeReturns} from './abm.js';
const a=new BornholdtModel({seed:13}),b=new BornholdtModel({seed:13});
for(let i=0;i<30;i++){assert.deepEqual(a.sweep(),b.sweep());assert.deepEqual(a.spins,b.spins);assert.equal(a.sum,a.spins.reduce((x,y)=>x+y,0));assert.ok(a.spins.every(s=>s===1||s===-1));}
const p=new BornholdtModel({L:4});p.spins.fill(1);p.sum=16;assert.equal(p.localField(0),4-p.alpha);p.spins.fill(-1);p.sum=-16;assert.equal(p.localField(0),-4+p.alpha);
assert.equal(heatBathProbability(100,0),.5);assert.ok(Number.isFinite(heatBathProbability(-1e5,20)));assert.equal(p.neighbors[0],3);assert.equal(p.neighbors[2],12);
let last=a.price;const row=a.sweep();assert.ok(Math.abs(Math.log(row.price/last)-row.logReturn)<1e-12);
const tests=['fixed-seed deterministic','spin values ±1','incremental magnetization equals full sum','periodic neighbors','spin-inversion field symmetry','beta=0 heatbath is 1/2','stable logistic','price-return identity'];
const results=[];
const regimes=[{name:'alpha_zero_control',L:32,beta:1/1.5,alpha:0},{name:'teaching_competition',L:32,beta:1/1.5,alpha:4},{name:'paper_inspired_matched_control',L:64,beta:2,alpha:0},{name:'paper_inspired_finite_lattice',L:64,beta:2,alpha:20}];
for(const regime of regimes)for(const seed of [7,42,2026]){
 const burnin=5000,sweeps=25000,model=new BornholdtModel({...regime,seed,historyLimit:0});model.step(burnin);
 const returns=[],mag=[];for(let t=0;t<sweeps;t++){const x=model.sweep();returns.push(x.logReturn);mag.push(x.m);}
 const item={regime:regime.name,parameters:model.parameters,burnin,sweeps,magnetizationMin:Math.min(...mag),magnetizationMax:Math.max(...mag),...summarizeReturns(returns)};results.push(item);console.log(JSON.stringify(item));
}
const report={generated:'2026-10-02',model:'Bornholdt 2001 Eq.4 + constant-fundamental 2002 price map',tests,method:'Seeded Mulberry32, random sequential heat bath with replacement; 1 sweep=N attempted site updates; instantaneous magnetization updated each attempt. 5000 burn-in, then 25000 single-sweep returns per seed. Population-moment kurtosis, ACF denominator full centered sum of squares. Finite-run diagnostics, not tail exponent fitting or market validation.',results};
fs.writeFileSync(new URL('./abm-validation.json',import.meta.url),JSON.stringify(report,null,2));
