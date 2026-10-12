# AI와 함께하는 시뮬레이션 · 신한은행 실습실

5시간 워크숍 "AI와 함께하는 시뮬레이션"의 정적 웹 교재 소스입니다.
Excel에 익숙한 금융 실무자가 Claude와 함께 몬테카를로 시뮬레이션을 만들고 검증하는
과정을 다룹니다. 라이브 사이트: https://shinhan-ai-simulation-lab.joocheol.chatgpt.site/

## 과정 구성 (300분 = 학습 260 + 휴식 40)

| 단원 | 내용 | 시간 |
|---|---|---|
| 01A/01B | 난수 → 원주율(몬테카를로), 정규 난수 → GBM 주가 경로 | 60분 |
| 02 | 정형적 사실 검정: 분포·의존성·꼬리 (실제 S&P 500 vs GBM) | 100분 |
| 03 | Game of Life: 규칙과 창발 | 25분 |
| 04 | 신용등급 전이 시뮬레이션 (CreditMetrics 교육용 행렬, 1요인 상관) | 40분 |
| 05 | 반복 실험과 AI 검증 | 35분 |

Bornholdt 시장 ABM(구 3단원)은 심화 확장 자료로 `downloads/`에 남아 있습니다.

## 구조

- `index.html`, `style.css`, `app.js` — SPA 셸과 단원별 인터랙티브 실습
- `credit.js` — 신용 전이 몬테카를로 모형 (04 단원, `downloads/`에도 동일 사본)
- `abm.js` — 시드 PRNG 공급 + 심화 확장용 Bornholdt 모형
- `statistics.js`, `tails.js`, `stats-ui.js` — 02 단원 통계 실험실
- `lessons.json` — 단원별 교재 본문(목표·시연·수식·프롬프트·체크포인트)
- `statistics-reference.json`, `tail-reference.json`, `source-and-statistics.json` —
  FRED S&P 500(2020–2025)에서 계산해 둔 검증 통계 (원자료는 재배포하지 않음)
- `downloads/` — Excel 실습 파일, 수식표, 프롬프트 모음, 모형 소스·검증 스크립트·
  재현성 점검 결과(`validate-abm.mjs`, `validate-credit.mjs`)

## 로컬 실행

정적 파일이지만 ES 모듈과 fetch를 쓰므로 간단한 서버가 필요합니다.

```bash
python3 -m http.server 8000   # 후 http://localhost:8000
```

모형 검증 재실행:

```bash
cd downloads && node validate-abm.mjs && node validate-credit.mjs
```

## 범위와 주의

교육용 모형입니다. 실제 가격 예측, 투자 권유, 규제자본·충당금 산출 도구가 아닙니다.
신용 전이행렬은 CreditMetrics 기술문서(1997) Table 1.8의 교육용 예시이며 현재 시장
자료가 아닙니다.
