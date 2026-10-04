/* Tail laboratory. All magnitudes and excesses use input-return units. */
const positive = values => Array.from(values).filter(x => Number.isFinite(x) && x > 0);
export function selectTail(returns, tail='loss') {
  if (!['loss','gain','absolute'].includes(tail)) throw new Error('Unknown tail');
  return Array.from(returns).filter(Number.isFinite).map(r=>tail==='loss'?-r:tail==='gain'?r:Math.abs(r)).filter(x=>x>0);
}
export function quantile(values, p) {
  const a=positive(values).sort((a,b)=>a-b); if(!a.length||!Number.isFinite(p)||p<0||p>1)return NaN;
  const h=(a.length-1)*p,i=Math.floor(h);return a[i]+(a[Math.min(i+1,a.length-1)]-a[i])*(h-i);
}
function hillSorted(a,k){
  const nTail=a.length,warnings=[];
  if(!Number.isInteger(k)||k<1||k>=nTail)return {valid:false,reason:'k는 1 이상, 양의 꼬리 표본 수 미만이어야 합니다.',k,nTail,warnings};
  const u=a[k],xi=a.slice(0,k).reduce((s,x)=>s+Math.log(x/u),0)/k;
  const ties=a[k-1]===u;
  if(ties)warnings.push('경계 동률: 상위 k개와 문턱값이 같아 엄격한 초과 표본 수가 k보다 작습니다.');
  if(k<30)warnings.push('상위 표본이 30개 미만이라 추정 변동이 큽니다.');
  if(!(xi>0))return {valid:false,reason:'동률로 Hill ξ가 0입니다. α를 추정할 수 없습니다.',k,nTail,u,xi,alpha:null,ties,warnings};
  return {valid:true,k,nTail,u,xi,alpha:1/xi,ties,warnings};
}
export function hill(values,k){return hillSorted(positive(values).sort((a,b)=>b-a),k);}
export function hillCurve(values,{minK=5,maxK,points=70}={}){
 const a=positive(values).sort((a,b)=>b-a);maxK=Math.min(a.length-1,maxK??Math.floor(a.length*.3));minK=Math.max(1,minK);
 if(maxK<minK)return [];
 const count=Math.max(2,Math.min(200,points));
 return [...new Set(Array.from({length:count},(_,i)=>Math.round(minK+(maxK-minK)*i/(count-1))))].map(k=>hillSorted(a,k));
}
export function gpdQuantile(p,xi,scale){return Math.abs(xi)<1e-10?-scale*Math.log1p(-p):scale*Math.expm1(-xi*Math.log1p(-p))/xi;}
export function gpdSurvival(y,xi,scale){if(y<0)return 1;const z=1+xi*y/scale;if(z<=0)return 0;return Math.abs(xi)<1e-10?Math.exp(-y/scale):Math.exp(-Math.log1p(xi*y/scale)/xi);}
function simplex(fn,start,maxIter=450){
 let v=[start,[start[0]+.045,start[1]],[start[0],start[1]+.12]].map(x=>({x,f:fn(x)}));
 let converged=false,iterations=0;
 for(;iterations<maxIter;iterations++){
  v.sort((a,b)=>a.f-b.f);
  if(Number.isFinite(v[0].f)&&Math.max(...v.map(z=>Math.abs(z.f-v[0].f)))<1e-8&&Math.max(...v.map(z=>Math.hypot(z.x[0]-v[0].x[0],z.x[1]-v[0].x[1])))<1e-6){converged=true;break;}
  const c=[(v[0].x[0]+v[1].x[0])/2,(v[0].x[1]+v[1].x[1])/2];
  const trial=t=>{const x=c.map((z,i)=>z+t*(c[i]-v[2].x[i]));return {x,f:fn(x)};};
  const r=trial(1);
  if(r.f<v[0].f){const e=trial(2);v[2]=e.f<r.f?e:r;}
  else if(r.f<v[1].f)v[2]=r;
  else {const outside=r.f<v[2].f;const z=trial(outside?.5:-.5);if(z.f<(outside?r.f:v[2].f))v[2]=z;else for(let j=1;j<3;j++){v[j].x=v[j].x.map((x,i)=>(x+v[0].x[i])/2);v[j].f=fn(v[j].x);}}
 }
 v.sort((a,b)=>a.f-b.f);return {...v[0],converged,iterations};
}
export function fitGPD(values,{quantile:q=.9}={}){
 const a=positive(values).sort((a,b)=>a-b),nTail=a.length,warnings=[];
 if(!Number.isFinite(q)||q<0||q>=1)return {valid:false,reason:'문턱 분위수는 0 이상 1 미만이어야 합니다.',nTail,nExceed:0,warnings};
 const u=quantile(a,q),ys=a.filter(x=>x>u).map(x=>x-u),nExceed=ys.length;
 const base={nTail,nExceed,u,quantile:q,warnings};
 if(nExceed<20)return {...base,valid:false,converged:false,boundary:false,reason:'엄격한 초과 표본이 20개 미만입니다. 문턱을 낮추거나 표본을 늘리세요.'};
 if(nExceed<50)warnings.push('초과 표본이 50개 미만입니다. GPD 추정이 불안정할 수 있습니다.');
 if(a.filter(x=>x===u).length>1)warnings.push('문턱 동률은 제외했습니다. 초과 표본 수를 확인하세요.');
 const norm=ys.reduce((s,y)=>s+y,0)/nExceed,y=ys.map(z=>z/norm),ymax=y[y.length-1];
 // Normalization protects tiny return units. Near xi=0 use a series for log1p(xi*z)/xi.
 const nll=([xi,ls])=>{
  if(xi<-.5||xi>2||ls< -25||ls>25)return Infinity;
  const b=Math.exp(ls);let sum=0;
  for(const t of y){const z=t/b,v=xi*z;if(1+v<=0)return Infinity;const h=Math.abs(v)<1e-5?z*(1-v/2+v*v/3-v*v*v/4):Math.log1p(v)/xi;sum+=(1+xi)*h;}
  return nExceed*ls+sum;
 };
 const fits=[-.4,-.2,0,.2,.6,1.3,1.9].map(xi=>{const b=Math.max(.2,1-xi,-xi*ymax*1.05);return simplex(nll,[xi,Math.log(b)]);}).filter(f=>Number.isFinite(f.f)).sort((a,b)=>a.f-b.f);
 if(!fits.length)return {...base,valid:false,converged:false,boundary:false,reason:'유효한 GPD 해를 찾지 못했습니다.'};
 const best=fits[0],xi=best.x[0],scale=Math.exp(best.x[1])*norm,converged=best.converged,boundary=xi<-.4999||xi>1.9999;
 if(!converged)warnings.push('최적화가 수렴하지 않았습니다. 추정치를 확정적으로 해석하지 마세요.');
 if(boundary)warnings.push('ξ가 검색 경계 [−0.5, 2]에 도달했습니다. 경계 밖 모형 가능성과 수치 안정성을 확인하세요.');
 const loglik=-best.f-nExceed*Math.log(norm);
 const plotN=Math.min(nExceed,250),indices=[...new Set(Array.from({length:plotN},(_,i)=>Math.round(i*(nExceed-1)/Math.max(1,plotN-1))))];
 const qq=indices.map(i=>({theoretical:gpdQuantile((i+.5)/nExceed,xi,scale),observed:ys[i]}));
 const survival=indices.map(i=>({x:ys[i],empirical:(nExceed-i)/nExceed,fitted:gpdSurvival(ys[i],xi,scale)}));
 return {...base,valid:true,converged,boundary,xi,scale,loglik,AIC:4-2*loglik,endpoint:xi<0?u-scale/xi:null,qq,survival,iterations:best.iterations};
}
export const NOTES={hill:'Hill은 정규변동하는 양의 두꺼운 꼬리(ξ>0)를 가정합니다. α=1/ξ이며 작은 α가 더 두꺼운 꼬리입니다. 평탄 구간만으로 멱법칙을 입증할 수 없습니다.',pot:'GPD는 Y=X−u | X>u에 적합합니다. ξ>0은 두꺼운 꼬리, ξ=0은 지수형, ξ<0은 유한 상한을 뜻합니다. 추정 부호만으로 모형을 확정하지 마세요.',threshold:'문턱이 낮으면 근사 편향, 높으면 표본 부족에 따른 변동이 커집니다. 결과를 보고 문턱을 고르는 선택 편향도 고려하세요.',dependence:'수익률의 변동성 군집과 시계열 의존성은 독립 표본 가정을 약화합니다. 여기서는 신뢰구간·유의성 검정이나 독립성 보정을 제공하지 않습니다.',plots:'QQ와 생존확률은 문턱 초과량의 조건부 분포입니다. 전체 수익률 분포나 무조건부 손실확률이 아닙니다.'};
export const SOURCES=[{title:'Hill (1975), A Simple General Approach to Inference About the Tail of a Distribution',url:'https://doi.org/10.1214/aos/1176343247'},{title:'SciPy: generalized Pareto distribution',url:'https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.genpareto.html'},{title:'NIST: Maximum Likelihood for Univariate Distributional Models',url:'https://itl.nist.gov/div898/software/dataplot/refman1/auxillar/mle.htm'}];
