/** Validation for credit.js (run: node validate-credit.mjs, with credit.js in the same folder).
 * Checks model invariants, then writes finite-sample Monte Carlo diagnostics to
 * credit-validation.json. Educational reproducibility checks only - no market claim. */
import {RATINGS, TRANSITION_PCT, transitionProbabilities, cumulativeRow, transitionByUniform,
 assetThresholds, ratingByAsset, normInv, normCdf, seededRandom,
 CreditPortfolioSim, summarizeLosses, DEFAULT_PORTFOLIO} from './credit.js';
import {writeFileSync} from 'node:fs';

const tests = [];
function check(name, ok, detail = '') {
 tests.push(name);
 if (!ok) { console.error('FAIL:', name, detail); process.exit(1); }
 console.log('ok:', name, detail);
}

// 1. Matrix sanity: non-negative, rows normalize to exactly 1.
for (const r of Object.keys(TRANSITION_PCT)) {
 const p = transitionProbabilities(r);
 check(`row ${r} sums to 1`, Math.abs(p.reduce((a, b) => a + b, 0) - 1) < 1e-12 && p.every(v => v >= 0));
 const c = cumulativeRow(r);
 check(`row ${r} cumulative ascending`, c.every((v, i) => i === 0 || v >= c[i - 1]) && c.at(-1) === 1);
}
// 2. normInv / normCdf round trip on a grid.
let worst = 0;
for (let p = 0.0005; p < 1; p += 0.0007) worst = Math.max(worst, Math.abs(normCdf(normInv(p)) - p));
check('normCdf(normInv(p)) round trip', worst < 5e-7, `max |err| ${worst.toExponential(2)}`);
check('normInv spot values', Math.abs(normInv(0.5)) < 1e-9 && Math.abs(normInv(0.975) - 1.959964) < 1e-5);
// 3. Uniform-interval method reproduces the matrix (BBB, 200k seeded draws).
{
 const r = seededRandom(20261004), n = 200000, freq = new Array(8).fill(0);
 for (let i = 0; i < n; i++) freq[transitionByUniform('BBB', r())]++;
 const p = transitionProbabilities('BBB');
 const okAll = p.every((pi, i) => Math.abs(freq[i] / n - pi) < 4 * Math.sqrt(Math.max(pi * (1 - pi), 1e-8) / n) + 1e-4);
 check('uniform-interval frequencies match matrix (BBB)', okAll, `default freq ${(freq[7] / n * 100).toFixed(3)}% vs ${(p[7] * 100).toFixed(3)}%`);
}
// 4. Threshold construction: Phi(z_k) equals cumulative-from-worst probabilities.
{
 const p = transitionProbabilities('BB'), z = assetThresholds('BB');
 let acc = 0, ok = true;
 for (let i = p.length - 1, k = 0; i >= 1; i--, k++) { acc += p[i]; if (Number.isFinite(z[k]) && Math.abs(normCdf(z[k]) - acc) > 1e-6) ok = false; }
 check('asset thresholds invert cumulative tail (BB)', ok);
}
// 5. rho=0 asset mapping agrees with the matrix marginals (B, 200k draws).
{
 const r = seededRandom(7), n = 200000, freq = new Array(8).fill(0), z = assetThresholds('B');
 for (let i = 0; i < n; i++) {
  const x = Math.sqrt(-2 * Math.log(Math.max(r(), 1e-12))) * Math.cos(2 * Math.PI * r());
  freq[ratingByAsset('B', x, z)]++;
 }
 const p = transitionProbabilities('B');
 const okAll = p.every((pi, i) => Math.abs(freq[i] / n - pi) < 4 * Math.sqrt(Math.max(pi * (1 - pi), 1e-8) / n) + 1e-4);
 check('rho=0 asset mapping matches matrix (B)', okAll, `default freq ${(freq[7] / n * 100).toFixed(2)}% vs ${(p[7] * 100).toFixed(2)}%`);
}
// 6. Determinism: identical seeds give identical loss paths.
{
 const a = new CreditPortfolioSim({seed: 42, rho: 0.2}); a.runTrials(500);
 const b = new CreditPortfolioSim({seed: 42, rho: 0.2}); b.runTrials(500);
 check('fixed seed deterministic', a.losses.every((v, i) => v === b.losses[i]));
 check('lgd=0 gives zero loss', (() => { const s = new CreditPortfolioSim({seed: 7, rho: 0.4, lgd: 0}); s.runTrials(200); return s.losses.every(v => v === 0); })());
}
// 7. Analytic expected loss of the default portfolio (default-mode, LGD 0.45).
const expectedDefaults = DEFAULT_PORTFOLIO.reduce((a, {rating, count}) => a + count * transitionProbabilities(rating)[7], 0);
const analyticELPct = 100 * expectedDefaults * 0.45 / 100;
console.log(`analytic: E[defaults]=${expectedDefaults.toFixed(4)}, EL=${analyticELPct.toFixed(4)}% of exposure`);

// 8. Monte Carlo regimes: EL flat in rho (within noise), far tail grows with rho.
const TRIALS = 20000, results = [];
for (const rho of [0, 0.1, 0.2, 0.4]) for (const seed of [7, 42, 2026]) {
 const sim = new CreditPortfolioSim({rho, seed, lgd: 0.45});
 sim.runTrials(TRIALS);
 const s = summarizeLosses(sim.losses, {totalExposure: sim.totalExposure});
 const meanDefaults = sim.defaults.reduce((a, b) => a + b, 0) / sim.defaults.length;
 results.push({
  regime: `rho_${rho}`, parameters: {portfolio: DEFAULT_PORTFOLIO, rho, lgd: 0.45, seed, trials: TRIALS},
  meanDefaults, expectedLossPct: s.expectedLossPct, sdPct: s.sdPct,
  q95Pct: s.quantilesPct[0.95], q99Pct: s.quantilesPct[0.99], q999Pct: s.quantilesPct[0.999], maxPct: s.maxPct
 });
 check(`EL near analytic (rho=${rho}, seed=${seed})`,
  Math.abs(s.expectedLossPct - analyticELPct) < 5 * (s.sdPct / Math.sqrt(TRIALS)) + 0.02,
  `EL ${s.expectedLossPct.toFixed(3)}% vs ${analyticELPct.toFixed(3)}%, q99.9 ${s.quantilesPct[0.999].toFixed(2)}%`);
}
for (const seed of [7, 42, 2026]) {
 const lo = results.find(r => r.parameters.rho === 0 && r.parameters.seed === seed);
 const hi = results.find(r => r.parameters.rho === 0.4 && r.parameters.seed === seed);
 check(`tail grows with rho (seed=${seed})`, hi.q999Pct > lo.q999Pct, `${lo.q999Pct.toFixed(2)}% -> ${hi.q999Pct.toFixed(2)}%`);
}

writeFileSync('credit-validation.json', JSON.stringify({
 generated: new Date().toISOString().slice(0, 10),
 model: 'CreditMetrics TD (1997) Table 1.8 transitions + one-factor Gaussian copula, default-mode losses, EAD 1, LGD 0.45',
 method: `Seeded Mulberry32, Box-Muller normals, ${TRIALS} trials per run, order-statistic quantiles sorted[ceil(p*n)-1]. Finite-run diagnostics, not market calibration or capital figures.`,
 analytic: {expectedDefaults, expectedLossPct: analyticELPct},
 tests, results
}, null, 1));
console.log('wrote credit-validation.json');
