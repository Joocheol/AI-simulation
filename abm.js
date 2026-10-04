/** Original educational implementation of Bornholdt (2001), Eq. (4).
 * Four nearest neighbors, periodic square lattice, random sequential heat bath.
 * h_i = J sum_nn(s_j) - alpha s_i |M|; P(s_i'=+1)=logistic(2 beta h_i).
 * A sweep is N selections WITH replacement, not N guaranteed spin flips.
 * Illustrative constant-fundamental price: P = fundamental * exp(kappa*M).
 * Thus log return r = kappa*(M_t-M_{t-1}); no log(M), no cumulative M drift.
 * No market calibration, financial forecast, or guaranteed stylized facts.
 */
export const MODEL_SOURCES = Object.freeze([
 'https://arxiv.org/abs/cond-mat/0105224',
 'https://arxiv.org/abs/cond-mat/0207253',
 'https://rf.mokslasplius.lt/bornholdt-model/'
]);
export const PRESETS = Object.freeze({
 teaching: {L:32, J:1, alpha:4, beta:1/1.5, kappa:1, fundamental:100, seed:42},
 control: {L:32, J:1, alpha:0, beta:1/1.5, kappa:1, fundamental:100, seed:42},
 paperInspired: {L:64, J:1, alpha:20, beta:2, kappa:1, fundamental:100, seed:42}
});
export function seededRandom(seed=42) {
 let a=Number(seed) >>> 0;
 return function() { a=(a+0x6D2B79F5) >>> 0; let t=a; t=Math.imul(t^(t>>>15),t|1); t^=t+Math.imul(t^(t>>>7),t|61); return ((t^(t>>>14))>>>0)/4294967296; };
}
export function heatBathProbability(field,beta) {
 const z=2*beta*field;
 return z>=0 ? 1/(1+Math.exp(-z)) : Math.exp(z)/(1+Math.exp(z));
}
function bounded(x,name,min,max,integer=false) {
 if (!Number.isFinite(x)||x<min||x>max||(integer&&!Number.isInteger(x))) throw new RangeError(`${name} must be ${integer?'an integer ':''}in [${min}, ${max}]`);
 return x;
}
export class BornholdtModel {
 constructor(options={}) { this.reset(options); }
 reset(options={}) {
  const p={...PRESETS.teaching,...(this.parameters||{}),...options};
  this.L=bounded(p.L,'L',4,256,true); this.N=this.L*this.L;
  this.J=bounded(p.J,'J',0,10); this.alpha=bounded(p.alpha,'alpha',0,100);
  this.beta=bounded(p.beta,'beta',0,20); this.kappa=bounded(p.kappa,'kappa',0,5);
  this.fundamental=bounded(p.fundamental,'fundamental',0.000001,1e9);
  this.seed=bounded(p.seed,'seed',0,4294967295,true);
  this.historyLimit=bounded(p.historyLimit??2000,'historyLimit',0,1000000,true);
  this.parameters={L:this.L,J:this.J,alpha:this.alpha,beta:this.beta,kappa:this.kappa,fundamental:this.fundamental,seed:this.seed,historyLimit:this.historyLimit};
  this.random=seededRandom(this.seed); this.spins=new Int8Array(this.N); this.sum=0;
  this.neighbors=new Int32Array(this.N*4);
  for(let i=0;i<this.N;i++) {
   const x=i%this.L,y=Math.floor(i/this.L);
   this.spins[i]=this.random()<0.5?-1:1; this.sum+=this.spins[i];
   this.neighbors.set([y*this.L+(x+this.L-1)%this.L,y*this.L+(x+1)%this.L,((y+this.L-1)%this.L)*this.L+x,((y+1)%this.L)*this.L+x],i*4);
  }
  this.time=0; this.history=[]; this.last=this.snapshot(0,0); this.record(this.last); return this.last;
 }
 get magnetization() { return this.sum/this.N; }
 get price() { return this.fundamental*Math.exp(this.kappa*this.magnetization); }
 localField(i) {
  bounded(i,'site',0,this.N-1,true); const k=i*4, s=this.spins,n=this.neighbors;
  return this.J*(s[n[k]]+s[n[k+1]]+s[n[k+2]]+s[n[k+3]])-this.alpha*s[i]*Math.abs(this.magnetization);
 }
 snapshot(logReturn=0,flips=0) {
  const m=this.magnetization;
  return {time:this.time,magnetization:m,m,price:this.price,logReturn,return:logReturn,absReturn:Math.abs(logReturn),buyFraction:(1+m)/2,flips,flipRate:flips/this.N};
 }
 record(row) { if(this.historyLimit) {this.history.push(row); if(this.history.length>this.historyLimit)this.history.shift();} }
 sweep() {
  const before=this.magnetization,s=this.spins,n=this.neighbors; let flips=0;
  for(let q=0;q<this.N;q++) {
   const i=Math.floor(this.random()*this.N),old=s[i],k=i*4;
   const h=this.J*(s[n[k]]+s[n[k+1]]+s[n[k+2]]+s[n[k+3]])-this.alpha*old*Math.abs(this.sum/this.N);
   const next=this.random()<heatBathProbability(h,this.beta)?1:-1;
   if(next!==old) {s[i]=next; this.sum+=next-old; flips++;}
  }
  this.time++; this.last=this.snapshot(this.kappa*(this.magnetization-before),flips); this.record(this.last); return this.last;
 }
 step(sweeps=1) { bounded(sweeps,'sweeps',1,1000000,true); let row; for(let k=0;k<sweeps;k++)row=this.sweep(); return row; }
 run(sweeps=100) { bounded(sweeps,'sweeps',1,1000000,true); return Array.from({length:sweeps},()=>this.sweep()); }
 /** Preserve stochastic state when changing couplings; use reset for clean experiments. */
 setParameters(changes={}) {
  for(const key of Object.keys(changes)) if(!['J','alpha','beta','kappa'].includes(key))throw new Error('Use reset to change '+key);
  const ranges={J:10,alpha:100,beta:20,kappa:5};
  for(const [k,v] of Object.entries(changes))bounded(v,k,0,ranges[k]);
  for(const [k,v] of Object.entries(changes)){this[k]=v;this.parameters[k]=v;} return {...this.parameters};
 }
}
/** Descriptive population-moment kurtosis (Gaussian reference 3), not bias corrected. */
export function summarizeReturns(values,lags=[1,5,10,50]) {
 const r=Array.from(values),n=r.length;
 if(!n)return {n:0,mean:null,std:null,kurtosis:null,excessKurtosis:null,absReturnACF:{}};
 const mean=r.reduce((a,b)=>a+b,0)/n;
 let s2=0,s4=0; for(const x of r){const d=x-mean;s2+=d*d;s4+=d*d*d*d;}
 const variance=s2/n,kurtosis=variance>0?s4/n/(variance*variance):null;
 const a=r.map(Math.abs),am=a.reduce((x,y)=>x+y,0)/n,den=a.reduce((v,x)=>v+(x-am)**2,0),acf={};
 for(const lag of lags){if(!Number.isInteger(lag)||lag<1||lag>=n||den===0){acf[lag]=null;continue;}let num=0;for(let i=lag;i<n;i++)num+=(a[i]-am)*(a[i-lag]-am);acf[lag]=num/den;}
 return {n,mean,std:Math.sqrt(variance),kurtosis,excessKurtosis:kurtosis===null?null:kurtosis-3,absReturnACF:acf};
}
export default BornholdtModel;
