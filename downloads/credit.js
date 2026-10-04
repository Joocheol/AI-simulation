/** Educational CreditMetrics-style one-year rating-transition Monte Carlo.
 * Transition matrix: CreditMetrics Technical Document (Gupton, Finger & Bhatia,
 * J.P. Morgan 1997), Table 1.8, source S&P CreditWeek (15 April 96).
 * It is a 1990s illustration for teaching, NOT current market data.
 * Default-mode portfolio loss only: loss = EAD x LGD on default at the one-year
 * horizon. Spread-based revaluation of migrations, stochastic recovery, exposure
 * uncertainty and multi-year horizons are intentionally out of scope.
 * Dependence: one-factor Gaussian copula on asset values,
 *   x_i = sqrt(rho) Z + sqrt(1-rho) e_i,  Z, e_i ~ iid N(0,1),
 * mapped to end ratings through NORM.S.INV thresholds of the cumulative row.
 * rho is ASSET correlation, not default correlation. Educational model only:
 * no capital, pricing, IFRS 9 or regulatory claim. */
export const RATINGS = Object.freeze(['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC', 'D']);
export const MODEL_SOURCES = Object.freeze([
 'https://www.msci.com/documents/10199/93396227-d449-4229-9143-24a94dab122f'
]);
/** Printed rows sum to 99.99-100.01 (%); probabilities are renormalized to 1. */
export const TRANSITION_PCT = Object.freeze({
 AAA: [90.81, 8.33, 0.68, 0.06, 0.12, 0, 0, 0],
 AA: [0.70, 90.65, 7.79, 0.64, 0.06, 0.14, 0.02, 0],
 A: [0.09, 2.27, 91.05, 5.52, 0.74, 0.26, 0.01, 0.06],
 BBB: [0.02, 0.33, 5.95, 86.93, 5.30, 1.17, 0.12, 0.18],
 BB: [0.03, 0.14, 0.67, 7.73, 80.53, 8.84, 1.00, 1.06],
 B: [0, 0.11, 0.24, 0.43, 6.48, 83.46, 4.07, 5.20],
 CCC: [0.22, 0, 0.22, 1.30, 2.38, 11.24, 64.86, 19.79]
});
export const DEFAULT_PORTFOLIO = Object.freeze([
 {rating: 'A', count: 20}, {rating: 'BBB', count: 40}, {rating: 'BB', count: 25},
 {rating: 'B', count: 10}, {rating: 'CCC', count: 5}
]);
export function seededRandom(seed = 42) {
 let a = Number(seed) >>> 0;
 return function() { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
export function normalFrom(r) {
 return Math.sqrt(-2 * Math.log(Math.max(r(), 1e-12))) * Math.cos(2 * Math.PI * r());
}
/** Acklam's rational approximation of the standard normal quantile (|rel err| ~ 1e-9). */
export function normInv(p) {
 if (!(p > 0 && p < 1)) throw new RangeError('p must be in (0, 1)');
 const a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
 const b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01];
 const c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
 const d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
 const pl = 0.02425;
 if (p < pl) { const q = Math.sqrt(-2 * Math.log(p)); return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
 if (p > 1 - pl) { const q = Math.sqrt(-2 * Math.log(1 - p)); return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
 const q = p - 0.5, s = q * q;
 return (((((a[0] * s + a[1]) * s + a[2]) * s + a[3]) * s + a[4]) * s + a[5]) * q / (((((b[0] * s + b[1]) * s + b[2]) * s + b[3]) * s + b[4]) * s + 1);
}
/** Standard normal CDF via Abramowitz & Stegun 7.1.26 (|abs err| < 1.5e-7); for checks. */
export function normCdf(x) {
 const z = Math.abs(x) / Math.SQRT2;
 const t = 1 / (1 + 0.3275911 * z);
 const erf = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-z * z);
 const phi = 0.5 * (1 + erf);
 return x >= 0 ? phi : 1 - phi;
}
export function transitionProbabilities(rating) {
 const row = TRANSITION_PCT[rating];
 if (!row) throw new RangeError('Unknown rating: ' + rating);
 const s = row.reduce((x, y) => x + y, 0);
 return row.map(v => v / s);
}
/** Ascending cumulative upper bounds in RATINGS order (AAA..D); last entry exactly 1. */
export function cumulativeRow(rating) {
 const p = transitionProbabilities(rating), c = [];
 let acc = 0;
 for (const v of p) { acc += v; c.push(acc); }
 c[c.length - 1] = 1;
 return c;
}
/** One uniform draw u in [0,1) -> end-rating index. Same structure as the pi lesson:
 * uniform number -> cumulative-interval lookup (Excel: INDEX + MATCH). */
export function transitionByUniform(rating, u) {
 if (!(u >= 0 && u < 1)) throw new RangeError('u must be in [0, 1)');
 const c = cumulativeRow(rating);
 for (let i = 0; i < c.length; i++) if (u < c[i]) return i;
 return c.length - 1;
}
/** Asset-value thresholds, worst state first: x < z[0] -> D, z[0] <= x < z[1] -> CCC, ...
 * Built so that normCdf(z[k]) equals the cumulative probability from the worst state. */
export function assetThresholds(rating) {
 const p = transitionProbabilities(rating);
 const z = [];
 let acc = 0;
 for (let i = p.length - 1; i >= 1; i--) { // cumulate D -> AA; above last cut is AAA
  acc += p[i];
  z.push(acc >= 1 ? Infinity : acc <= 0 ? -Infinity : normInv(acc));
 }
 return z; // length 7; state index for x: see ratingByAsset
}
export function ratingByAsset(rating, x, z = assetThresholds(rating)) {
 for (let k = 0; k < z.length; k++) if (x < z[k]) return RATINGS.length - 1 - k;
 return 0; // AAA
}
function bounded(x, name, min, max, integer = false) {
 if (!Number.isFinite(x) || x < min || x > max || (integer && !Number.isInteger(x))) throw new RangeError(`${name} must be ${integer ? 'an integer ' : ''}in [${min}, ${max}]`);
 return x;
}
/** Default-mode portfolio simulation with chunked execution for responsive UIs.
 * Every loan has EAD 1; losses are in EAD units (divide by totalExposure for %). */
export class CreditPortfolioSim {
 constructor(options = {}) {
  const p = {portfolio: DEFAULT_PORTFOLIO, rho: 0, lgd: 0.45, seed: 42, ...options};
  this.rho = bounded(p.rho, 'rho', 0, 0.99);
  this.lgd = bounded(p.lgd, 'lgd', 0, 1);
  this.seed = bounded(p.seed, 'seed', 0, 4294967295, true);
  this.portfolio = p.portfolio.map(({rating, count}) => {
   if (!TRANSITION_PCT[rating]) throw new RangeError('Unknown rating: ' + rating);
   bounded(count, 'count', 1, 100000, true);
   return {rating, count, thresholds: assetThresholds(rating)};
  });
  this.totalExposure = this.portfolio.reduce((a, b) => a + b.count, 0);
  this.random = seededRandom(this.seed);
  this.losses = []; this.defaults = []; this.endRatingTotals = new Array(RATINGS.length).fill(0);
 }
 runTrials(n = 1000) {
  bounded(n, 'n', 1, 1000000, true);
  const a = Math.sqrt(this.rho), b = Math.sqrt(1 - this.rho);
  for (let t = 0; t < n; t++) {
   const Z = normalFrom(this.random);
   let defaults = 0;
   for (const {count, thresholds} of this.portfolio) {
    for (let i = 0; i < count; i++) {
     const x = a * Z + b * normalFrom(this.random);
     let state = 0;
     for (let k = 0; k < thresholds.length; k++) { if (x < thresholds[k]) { state = RATINGS.length - 1 - k; break; } }
     this.endRatingTotals[state]++;
     if (state === RATINGS.length - 1) defaults++;
    }
   }
   this.defaults.push(defaults);
   this.losses.push(defaults * this.lgd);
  }
  return this.losses.length;
 }
}
/** Order-statistic quantiles: sorted[ceil(p*n)-1]. Descriptive Monte Carlo summaries,
 * not fitted risk measures; far-tail quantiles are noisy at small trial counts. */
export function summarizeLosses(losses, {totalExposure = 100, levels = [0.95, 0.99, 0.999]} = {}) {
 const n = losses.length;
 if (!n) return {n: 0};
 const sorted = Array.from(losses).sort((x, y) => x - y);
 const mean = losses.reduce((x, y) => x + y, 0) / n;
 const sd = n > 1 ? Math.sqrt(losses.reduce((x, y) => x + (y - mean) ** 2, 0) / (n - 1)) : 0;
 const q = {};
 for (const p of levels) q[p] = sorted[Math.min(n - 1, Math.max(0, Math.ceil(p * n) - 1))];
 return {
  n, totalExposure,
  expectedLoss: mean, expectedLossPct: 100 * mean / totalExposure,
  sd, sdPct: 100 * sd / totalExposure,
  quantiles: q,
  quantilesPct: Object.fromEntries(levels.map(p => [p, 100 * q[p] / totalExposure])),
  max: sorted[n - 1], maxPct: 100 * sorted[n - 1] / totalExposure
 };
}
export default CreditPortfolioSim;
