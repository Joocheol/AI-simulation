# 6단계에서 쓴 SVB 숫자와 출처

모형에 들어간 값은 전부 아래에서 가져왔습니다.
기억이나 어림짐작으로 넣은 숫자는 없습니다.

## 대차대조표 (2022년 12월 31일 기준)

| 항목 | 값 | 비고 |
|:---|---:|:---|
| 총자산 | 2,090억 달러 | |
| 총예금 | 1,750억 달러 | FDIC가 인수한 고객 계좌 기준 |
| 자기자본 | 160억 달러 | SVB Financial Group 연결 기준 |
| 현금 및 현금성자산 | 138억 달러 | |
| 증권 장부가 (HTM+AFS) | 1,174억 달러 | HTM 913억 + AFS 261억 |
| 대출 | 743억 달러 | |
| **HTM 미실현손실** | **152억 달러** | 상각원가 913.21억 → 공정가치 761.69억 |
| **AFS 미실현손실** | **25억 달러** | |
| 무보험 예금 비율 | 85~94% | 자료마다 기준 시점이 다름 |

1년 전(2021년 말)의 미실현손실은 HTM 13억, AFS 3.13억 달러였습니다.
2022년 금리 인상으로 **1년 만에 10배 이상 불어난** 것입니다.

### 모형에서 이 숫자들이 만들어 내는 것

```
자산  = 현금 138 + 증권 1,174 + 대출 743 + 기타 35 = 2,090억
부채  = 예금 1,750 + 기타 180                      = 1,930억
장부 자기자본                                       =   160억  (+9.1%)

시가평가하면
자산  = 2,090 - 미실현손실 177                      = 1,913억
시가 자기자본 = 1,913 - 1,930                       =  -17억  (-0.97%)
```

**미실현손실 177억 > 자기자본 160억.**
시가로 보면 이미 자본잠식이었지만, 만기보유 증권은 손실을 실현하지 않으므로
회계상으로는 건전한 은행이었습니다. 이 착시가 뱅크런으로 깨집니다.

`steps/step06_bankrun.py`의 `BankRunModel`은 이 비율들을 그대로 써서
장부자본 +9.1% / 시가자본 -0.97%를 재현합니다.

## 타임라인

| 날짜 | 사건 |
|:---|:---|
| 2019년 말 → 2021년 말 | 예금이 약 620억 → 1,890억 달러로 3배 증가 |
| 2022년 | 금리 인상으로 보유 증권 평가손실 급증 |
| 2023년 3월 8일 | AFS 증권 약 210억 달러 매각, 세후 손실 약 18억 달러 발표. 동시에 22.5억 달러 자본조달 계획 발표 |
| 2023년 3월 9일 | 하루에 **420억 달러** 인출 (예금의 약 24%). 주가 60% 급락 |
| 2023년 3월 10일 | 추가로 **1,000억 달러** 인출 요청이 대기. 지급 불가. 캘리포니아 금융보호혁신국이 폐쇄하고 FDIC를 관재인으로 지정 |
| 2023년 3월 12일 | 시스템 리스크 예외를 적용해 **모든 예금자를 전액 보호**한다고 발표 |

3월 8일 발표는 새로운 손실을 만든 것이 아니라 **이미 있던 손실을 보이게 만든 사건**입니다.
모형의 `shock_step`과 `signal_after`가 이 역할을 합니다.

FDIC는 전액 보호 결정으로 무보험 예금자가 졌을 손실 **167억 달러**를 대신 흡수한 것으로
추산했습니다.

## 모형이 의도적으로 뺀 것

- 중앙은행의 긴급대출(BTFP 등), 인수합병, 감독당국의 사전 개입
- 다른 은행으로의 전염 (모형에는 은행이 하나뿐입니다)
- 주가와 예금의 상호작용 (모형에는 주식시장이 없습니다)
- 전액 보장이 만들어 내는 도덕적 해이

이것들을 빼도 "왜 이틀 만에 무너지는가"는 설명됩니다.
빼도 되는 것과 빼면 안 되는 것을 가르는 것이 모형 설계입니다.

## 출처

- [Material Loss Review of Silicon Valley Bank — Federal Reserve OIG (2023년 9월)](https://oig.federalreserve.gov/reports/board-material-loss-review-silicon-valley-bank-sep2023.pdf)
- [FDIC Acts to Protect All Depositors of the former Silicon Valley Bank — FDIC 보도자료 (2023년 3월 13일)](https://www.fdic.gov/news/press-releases/2023/pr23019.html)
- [Recent Bank Failures and the Federal Regulatory Response — FDIC (2023년 3월 27일)](https://www.fdic.gov/news/speeches/2023/spmar2723.html)
- [Lessons Learned from the U.S. Regional Bank Failures of 2023 — FDIC (2024년)](https://www.fdic.gov/news/speeches/2024/lessons-learned-us-regional-bank-failures-2023)
- [SVB Financial Group Announces Proposed Offerings — 2023년 3월 8일 보도자료](https://ir.svb.com/news-and-research/news/news-details/2023/SVB-Financial-Group-Announces-Proposed-Offerings-of-Common-Stock-and-Mandatory-Convertible-Preferred-Stock/default.aspx)
- [SVB Financial Group 2022년 4분기 실적발표 (자기자본 160억 달러)](https://www.sec.gov/Archives/edgar/data/719739/000071973923000009/q422earningsrelease_991.htm)
- [Bank Failures Highlight the Shortcomings of Held-to-Maturity Accounting — The CPA Journal (2024년 4월)](https://www.cpajournal.com/2024/04/08/bank-failures-highlight-the-shortcomings-of-held-to-maturity-htm-accounting/)
- [Most of Silicon Valley Bank's Deposits Were Uninsured — TIME](https://time.com/6262009/silicon-valley-bank-deposit-insurance/)
- [Silicon Valley Bank is shut down by regulators — CNBC (2023년 3월 10일)](https://www.cnbc.com/2023/03/10/silicon-valley-bank-is-shut-down-by-regulators-fdic-to-protect-insured-deposits.html)

이론적 배경:

- Diamond, D. W., & Dybvig, P. H. (1983). *Bank Runs, Deposit Insurance, and Liquidity.*
  Journal of Political Economy, 91(3), 401–419.
  뱅크런의 다중균형 구조와 예금보험의 역할을 정식화한 논문입니다.
  6단계 [실험 D]와 [실험 E]가 이 논문의 두 결론에 대응합니다.
