# 신용등급 전이 시뮬레이션 · 수식과 구현 설명

04 단원(신용등급 전이와 포트폴리오 손실)의 브라우저 구현 `credit.js`에 대한 노트입니다.
교육용 모형이며, 규제자본·IFRS 9 충당금·가격산정·투자 판단 도구가 아닙니다.

## 1. 전이행렬

- 출처: Gupton, Finger & Bhatia, *CreditMetrics — Technical Document* (J.P. Morgan, 1997),
  Table 1.8 "One-year transition matrix (%)". 원자료는 S&P CreditWeek (1996-04-15).
- 1990년대 자료에 기초한 **교육용 예시**입니다. 현재 시장의 부도율·전이율이 아니며,
  실무에서는 자체 추정 또는 최신 공표 행렬의 출처·기간·등급체계를 확인해야 합니다.
- 문서에 인쇄된 행 합계는 반올림 때문에 99.99~100.01%입니다. 구현은 각 행을 합 1로
  재정규화합니다 (`transitionProbabilities`).
- D(부도)는 흡수 상태로 취급합니다. 1년 시계만 다루므로 행렬 거듭제곱(다년 전이)은
  구현하지 않았습니다.

## 2. 대출 한 건: 누적구간 판정

행렬의 한 행은 "현재 등급 조건부, 1년 후 등급의 분포"입니다. 균등난수 U 하나를 뽑아
누적확률 구간에서 위치를 찾으면 1년 후 등급이 됩니다 (`transitionByUniform`).

Excel 등가물: 누적 하한(0부터 오름차순)을 한 행에 두고
`=INDEX(등급이름, MATCH(RAND(), 누적하한, 1))`.
`credit-transition-matrix.csv`의 `cum_lower_*` 열이 이 누적 하한입니다.

## 3. 포트폴리오: 1요인 가우스 코퓰라

대출 i의 표준화 자산가치를

    x_i = sqrt(rho) * Z + sqrt(1 - rho) * eps_i,   Z, eps_i ~ iid N(0,1)

로 두고, 누적확률의 표준정규 분위수 문턱(`assetThresholds`, 나쁜 등급부터 누적)과
비교해 1년 후 등급을 정합니다. rho=0이면 누적구간 판정과 같은 분포입니다.

- rho는 **자산가치의 상관**입니다. 부도사건의 상관은 이보다 훨씬 작습니다.
- 모든 대출이 같은 한 개의 공통요인 Z를 공유합니다. 산업·지역별 다요인 구조는
  범위 밖입니다.

## 4. 손실의 정의 (default-mode)

- 1년 후 상태가 D일 때만 손실 EAD × LGD를 인식합니다. EAD=1(건별), LGD는 상수
  (기본 0.45)입니다.
- 등급 하락의 스프레드 재평가(원문 CreditMetrics의 핵심 확장), 회수율의 불확실성,
  익스포저 변동, 할인은 생략합니다. 따라서 여기의 분포는 원문 모형의 손실 분포보다
  좁습니다.
- 기대손실 EL = Σ 건수 × PD × LGD 는 rho와 무관합니다. 기본 포트폴리오
  (A 20 · BBB 40 · BB 25 · B 10 · CCC 5, 총 EAD 100)에서 기대 부도 1.8585건,
  EL = 0.8363% 입니다. rho가 바꾸는 것은 손실 분포의 꼬리(극단 분위수)입니다.

## 5. 수치 구현

- 난수: Mulberry32 시드 PRNG(`seededRandom`) + Box-Muller 정규변환. 시드가 같으면
  결과가 완전히 재현됩니다. 암호학적 난수가 아닙니다.
- 표준정규 분위수: Acklam 근사(`normInv`, 상대오차 ~1e-9). CDF 검산용으로
  Abramowitz & Stegun 7.1.26 기반 `normCdf`(절대오차 <1.5e-7)를 포함합니다.
- 분위수: 정렬 표본의 순서통계량 `sorted[ceil(p*n)-1]`. Excel PERCENTILE.INC의
  보간 방식과 다를 수 있으므로 비교 시 정의를 명시하세요.
- 99.9% 분위수는 20,000회 시행에서 20개 관측의 영역입니다. 시드 간 범위를 함께
  보고해야 합니다 (`credit-validation.json` 참조).

## 6. 검증

`node validate-credit.mjs` (credit.js와 같은 폴더)로 다음을 점검하고
`credit-validation.json`을 다시 만듭니다.

- 행 합 = 1, 누적 하한의 단조성
- normInv/normCdf 왕복 오차
- 누적구간 방식과 rho=0 문턱 방식이 행렬 주변분포를 재현하는지 (몬테카를로 허용오차)
- 고정 시드 재현성, LGD=0 → 손실 0
- EL이 해석적 값과 가깝고 rho에 무관한지, 먼 꼬리 분위수가 rho와 함께 커지는지

## 7. API 요약

```js
import {CreditPortfolioSim, summarizeLosses} from './credit.js';
const sim = new CreditPortfolioSim({rho: 0.2, lgd: 0.45, seed: 42});
sim.runTrials(20000);                       // 나눠서 여러 번 호출 가능
const s = summarizeLosses(sim.losses, {totalExposure: sim.totalExposure});
// s.expectedLossPct, s.quantilesPct[0.99], s.quantilesPct[0.999], ...
```
