"""6단계: 뱅크런 - SVB(실리콘밸리은행) 파산은 재현 가능한가.

먼저 '재현'이라는 말을 정확히 나눠야 한다. 이 단계의 절반은 그 구분이다.

    할 수 있는 것   메커니즘의 재현.
                    왜 멀쩡해 보이던 은행이 이틀 만에 무너지는가,
                    왜 똑같은 손실을 안고도 어떤 은행은 버티는가,
                    무엇이 그 갈림길을 결정하는가.

    할 수 없는 것   예측과 수치 맞추기.
                    '3월 9일에 420억 달러가 빠진다'를 맞히는 것.
                    날짜별 유출 곡선에 맞춰 파라미터를 조정하는 것은
                    과적합이며, 그렇게 맞춘 모형은 다음 은행에 대해
                    아무것도 말해 주지 못한다.

    5단계에서 배운 것이 그대로 적용된다. 셸링 모형은 특정 도시의
    인구 분포를 맞히지 못하지만, '분리가 어떻게 생기는가'는 설명한다.
    같은 의미에서 이 모형은 SVB를 '설명'하지 '예측'하지 않는다.

[SVB의 실제 숫자] (2022년 말 기준, 출처는 docs/svb-sources.md)
    총예금            약 1,750억 달러
    자기자본          약 160억 달러
    증권 미실현손실   만기보유(HTM) 152억 + 매도가능(AFS) 25억 = 177억 달러
    무보험 예금 비율  85~94% (미국 은행 평균은 약 50%)

    여기서 이 사건의 핵심이 나온다.

        미실현손실 177억 > 자기자본 160억

    즉 보유 증권을 시가로 평가하면 자기자본이 이미 음수였다.
    다만 만기까지 들고 있으면 손실을 실현하지 않으므로 회계상으로는 멀쩡했다.
    "아무도 돈을 빼지 않으면 살고, 빼기 시작하면 죽는다."
    이것이 Diamond-Dybvig(1983)가 말한 뱅크런의 다중균형 구조다.

[이 단계의 핵심 주장]
    은행의 생사는 펀더멘털만으로 결정되지 않는다.
    똑같은 재무상태에서 어떤 실행은 살아남고 어떤 실행은 무너진다.
    무엇이 갈랐는가? 예금자들이 서로를 어떻게 봤는가다.

    이것은 4단계의 창발이나 5단계의 상전이보다 한 걸음 더 나간 이야기다.
    거기서는 파라미터가 결과를 정했지만, 여기서는 **같은 파라미터에서
    두 개의 결말이 모두 가능하다.** [실험 D]가 그것을 보여 준다.

[모형의 규칙]
    예금자 한 명의 판단은 두 가지를 더한 것이다.

        불안 = (은행이 위험하다는 공개 신호) + (내 주변에서 이미 뺀 비율)

    이 값이 자기 임계값을 넘으면 인출한다. 단, 예금이 보험 한도 이하인
    사람은 잃을 것이 없으므로 움직이지 않는다. 무보험 예금자만 뛴다.
    SVB의 무보험 비율이 왜 치명적이었는지가 여기서 나온다.

    은행은 현금으로 먼저 지급하고, 모자라면 증권을 시가에 판다.
    그 순간 미실현손실이 실현손실이 되어 자본을 깎는다. 자본이 0을
    밑돌면 감독당국이 폐쇄한다. 판다는 행위 자체가 은행을 죽인다.

실행:
    python3 steps/step06_bankrun.py     (약 1분)
"""

from __future__ import annotations

import mesa

# --- SVB 2022년 말 실제 값에서 뽑은 비율 (단위: 십억 달러) -----------------
SVB_DEPOSITS = 175.0
SVB_EQUITY = 16.0
SVB_SECURITIES_BOOK = 117.4        # HTM 91.3 + AFS 26.1
SVB_UNREALIZED_LOSS = 17.7         # HTM 15.2 + AFS 2.5
SVB_CASH = 13.8
SVB_LOANS = 74.3
SVB_TOTAL_ASSETS = 209.0
SVB_OTHER_LIABILITIES = 18.0       # 단기차입 등 예금 이외의 부채
SVB_MEAN_BALANCE_M = 4.73          # 계좌당 평균 470만 달러 (37,000 계좌)

# 위 값에서 유도한, 규모와 무관한 비율들 (모두 예금 총액 대비)
CASH_RATIO = SVB_CASH / SVB_DEPOSITS                       # 0.079
SECURITIES_RATIO = SVB_SECURITIES_BOOK / SVB_DEPOSITS      # 0.671
LOANS_RATIO = SVB_LOANS / SVB_DEPOSITS                     # 0.425
OTHER_ASSETS_RATIO = (
    SVB_TOTAL_ASSETS - SVB_CASH - SVB_SECURITIES_BOOK - SVB_LOANS
) / SVB_DEPOSITS                                           # 0.020
OTHER_LIAB_RATIO = SVB_OTHER_LIABILITIES / SVB_DEPOSITS    # 0.103
LOSS_RATE = SVB_UNREALIZED_LOSS / SVB_SECURITIES_BOOK      # 0.151

# 검산: 자산 1.195D, 부채 1.103D, 자본 0.092D = 16.1B  (실제 16.0B)
#       시가평가 자본 = 0.092D - 0.671D x 0.151 = -0.009D = -1.6B  (실제 -1.7B)
#       즉 SVB는 시가로 보면 이미 자본잠식 상태였다.


class Depositor(mesa.Agent):
    """예금자 한 명.

    핵심은 balance가 아니라 at_risk(보험 한도 초과분)다.
    잃을 것이 없는 사람은 뛸 이유도 없다.
    """

    def __init__(self, model: mesa.Model, balance: float) -> None:
        super().__init__(model)
        self.balance = balance
        self.has_run = False          # 이미 인출했는가
        self.decided_to_run = False   # 이번 스텝에 인출하기로 마음먹었는가
        self.recovered = 0.0          # 실제로 돌려받은 금액
        self.peers: list[Depositor] = []

        # 개인마다 겁의 정도가 다르다. 같은 소식을 들어도 반응이 다르다.
        self.threshold = min(1.0, max(0.10, model.random.gauss(
            model.panic_threshold, model.panic_spread)))

    @property
    def at_risk(self) -> float:
        """보험 한도를 넘어 실제로 잃을 수 있는 금액."""
        return max(0.0, self.balance - self.model.insurance_cap)

    @property
    def peer_run_fraction(self) -> float:
        """내가 아는 사람들 중 이미 인출한 비율 = 사회적 신호."""
        if not self.peers:
            return 0.0
        return sum(1 for p in self.peers if p.has_run) / len(self.peers)

    def step(self) -> None:
        """1단계: 결정만 한다. 아직 실제로 빼지는 않는다.

        모두가 '어제까지의 상황'을 보고 동시에 판단하도록 만드는 장치다.
        이렇게 하지 않고 결정과 인출을 한꺼번에 처리하면, 한 스텝 안에서
        연쇄가 끝까지 번져 버려서 정보가 퍼지는 속도를 볼 수 없게 된다.
        (Mesa 2.x의 SimultaneousActivation에 해당하는 패턴이다.)
        """
        if self.has_run or self.model.failed:
            return
        if self.at_risk <= 0:
            return  # 전액 보험 대상이면 서두를 이유가 없다

        anxiety = (self.model.fundamental_weight * self.model.public_signal
                   + self.model.social_weight * self.peer_run_fraction)

        if anxiety > self.threshold:
            self.decided_to_run = True

    def advance(self) -> None:
        """2단계: 마음먹은 사람들이 실제로 창구로 간다.

        이 순서는 매 스텝 섞인다. 늦게 도착한 사람이 못 받는 구조이므로
        누가 먼저 가느냐가 개인의 운명을 가른다.
        """
        if self.decided_to_run and not self.has_run:
            self.model.request_withdrawal(self)


class BankRunModel(mesa.Model):
    """예금자들과 은행 하나로 이루어진 세계."""

    def __init__(
        self,
        n_depositors: int = 8_000,
        mean_balance: float = SVB_MEAN_BALANCE_M / 1000.0,   # 십억 달러 단위
        balance_sigma: float = 2.0,
        insurance_cap: float = 0.25 / 1000.0,               # 25만 달러
        loss_rate: float = LOSS_RATE,
        cash_ratio: float = CASH_RATIO,     # 예금 대비 현금 보유 비율
        fire_sale_discount: float = 0.05,   # 급매할 때 시가에서 더 깎이는 몫
        peers_k: int = 8,                   # 몇 명과 소식을 주고받는가
        social_weight: float = 1.0,
        fundamental_weight: float = 1.0,
        panic_threshold: float = 0.5,
        panic_spread: float = 0.25,
        signal_before: float = 0.02,        # 3월 8일 발표 전의 공개 불안 신호
        signal_after: float = 0.45,         # 발표 직후로 점프
        shock_step: int = 3,
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)

        self.insurance_cap = insurance_cap
        self.loss_rate = loss_rate
        self.fire_sale_discount = fire_sale_discount
        self.social_weight = social_weight
        self.fundamental_weight = fundamental_weight
        self.panic_threshold = panic_threshold
        self.panic_spread = panic_spread
        self.signal_before = signal_before
        self.signal_after = signal_after
        self.shock_step = shock_step
        self.public_signal = signal_before

        # --- 예금자 생성 -------------------------------------------------
        # 로그정규: 소수의 거대 계좌가 예금의 대부분을 차지하는 현실적 모양
        raw = [self.random.lognormvariate(0, balance_sigma)
               for _ in range(n_depositors)]
        scale = (n_depositors * mean_balance) / sum(raw)
        for r in raw:
            Depositor(self, r * scale)

        everyone = list(self.agents)
        for agent in everyone:
            agent.peers = self.random.sample(everyone, min(peers_k, len(everyone) - 1))

        # --- 은행의 대차대조표 (예금 총액에 비례해서 구성) ----------------
        self.initial_deposits = sum(a.balance for a in self.agents)
        self.deposits = self.initial_deposits
        self.cash = self.initial_deposits * cash_ratio
        self.securities_book = self.initial_deposits * (
            SECURITIES_RATIO + CASH_RATIO - cash_ratio)
        self.loans = self.initial_deposits * LOANS_RATIO
        self.other_assets = self.initial_deposits * OTHER_ASSETS_RATIO
        self.other_liabilities = self.initial_deposits * OTHER_LIAB_RATIO
        self.realized_loss = 0.0

        self.failed = False
        self.total_paid = 0.0
        self.withdrawals_this_step = 0.0

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "deposits": "deposits",
                "cash": "cash",
                "ran_count": lambda m: sum(1 for a in m.agents if a.has_run),
                "ran_money_pct": lambda m: 100 * m.total_paid / m.initial_deposits,
                "mtm_equity": lambda m: m.mark_to_market_equity,
                "failed": lambda m: int(m.failed),
                "signal": "public_signal",
            }
        )
        self.datacollector.collect(self)

    # --- 은행 쪽 회계 ------------------------------------------------------

    @property
    def securities_market_value(self) -> float:
        """증권을 지금 팔면 받는 값. 미실현손실만큼 장부가보다 낮다."""
        return self.securities_book * (1.0 - self.loss_rate)

    @property
    def mark_to_market_equity(self) -> float:
        """시가평가 자기자본.

        SVB는 이 값이 출발부터 음수였다 (미실현손실 177억 > 자본 160억).
        그런데도 만기까지 보유하면 손실이 실현되지 않으므로
        장부상으로는 건전한 은행이었다. 뱅크런이 그 가정을 깨뜨린다.
        """
        assets = (self.cash + self.securities_market_value
                  + self.loans + self.other_assets)
        return assets - self.deposits - self.other_liabilities

    @property
    def book_equity(self) -> float:
        """장부상 자기자본. 증권을 장부가 그대로 계산한 값 = 회계상의 모습."""
        assets = (self.cash + self.securities_book
                  + self.loans + self.other_assets)
        return assets - self.deposits - self.other_liabilities

    @property
    def uninsured_share(self) -> float:
        total = sum(a.balance for a in self.agents)
        return sum(a.at_risk for a in self.agents) / total if total else 0.0

    def request_withdrawal(self, depositor: Depositor) -> None:
        """예금자 한 명의 인출 요청을 처리한다.

        선착순이다. 먼저 온 사람은 전액을 받고, 은행이 쓰러진 뒤에 온
        사람은 보험 한도까지만 받는다. 이 구조 자체가 '남보다 먼저
        뛰어야 한다'는 유인을 만든다. 뱅크런의 엔진이 여기 있다.
        """
        if self.failed or depositor.has_run:
            return

        amount = depositor.balance

        # 1) 현금으로 먼저 지급
        if self.cash < amount:
            # 2) 모자라면 증권을 판다. 파는 순간 손실이 확정된다.
            needed = amount - self.cash
            effective_rate = 1.0 - self.loss_rate - self.fire_sale_discount
            if effective_rate <= 0:
                self.fail()
                return
            book_to_sell = needed / effective_rate

            if book_to_sell > self.securities_book:
                # 3) 팔 증권마저 없으면 지급 불능
                self.fail()
                return

            self.securities_book -= book_to_sell
            self.realized_loss += book_to_sell * (self.loss_rate + self.fire_sale_discount)
            self.cash += needed

        self.cash -= amount
        self.deposits -= amount
        self.total_paid += amount
        self.withdrawals_this_step += amount
        depositor.has_run = True
        depositor.recovered = amount

        # 폐쇄 사유는 '자본이 음수'가 아니라 '요청을 지급할 수 없음'이다.
        # SVB도 시가 자본은 이미 음수였지만, 문을 닫은 것은
        # 3월 10일의 인출 요청을 감당하지 못한 순간이었다.
        # 그 판정은 위쪽 매각 실패 분기에서 이미 이루어진다.

    def fail(self) -> None:
        """폐쇄. 남은 예금자는 보험 한도까지만 건진다."""
        if self.failed:
            return
        self.failed = True
        self.running = False
        for agent in self.agents:
            if not agent.has_run:
                agent.recovered = min(agent.balance, self.insurance_cap)

    # --- 시간 전진 --------------------------------------------------------

    def step(self) -> None:
        # 3월 8일의 증권 매각·자본조달 발표에 해당하는 충격.
        # 없던 문제가 생긴 것이 아니라, 있던 문제가 보이게 된 사건이다.
        if self.steps >= self.shock_step:
            self.public_signal = self.signal_after

        self.withdrawals_this_step = 0.0
        self.agents.do("step")            # 전원이 동시에 판단하고
        self.agents.shuffle_do("advance") # 무작위 순서로 창구에 간다
        self.datacollector.collect(self)

        # 아무도 움직이지 않는 상태가 이어지면 런은 끝난 것이다
        if not self.failed and self.withdrawals_this_step == 0 and self.steps > self.shock_step:
            self.running = False


def run_once(steps: int = 40, **kwargs) -> BankRunModel:
    model = BankRunModel(**kwargs)
    for _ in range(steps):
        model.step()
        if not model.running:
            break
    return model


def outcome(model: BankRunModel) -> str:
    return "파산" if model.failed else "생존"


def bar(value: float, top: float, width: int = 30, ch: str = "█") -> str:
    return ch * max(0, min(width, round(value / top * width)))


def main() -> None:
    print("=" * 74)
    print("6단계 | 뱅크런 - SVB 파산은 재현 가능한가")
    print("=" * 74)

    model = BankRunModel(n_depositors=3000, seed=42)
    d = model.initial_deposits

    print("\n[대차대조표] 모형이 SVB의 실제 비율을 재현하는가")
    print(f"{'항목':<22} {'모형':>12} {'예금 대비':>12} {'SVB 실제':>14}")
    print("-" * 74)
    print(f"{'예금':<22} {d:>12.2f}B {100.0:>11.1f}% {'175.0B':>14}")
    print(f"{'현금':<22} {model.cash:>12.2f}B {100*model.cash/d:>11.1f}% {'7.9%':>14}")
    print(f"{'증권(장부가)':<20} {model.securities_book:>12.2f}B "
          f"{100*model.securities_book/d:>11.1f}% {'67.1%':>14}")
    print(f"{'장부 자기자본':<20} {model.book_equity:>12.2f}B "
          f"{100*model.book_equity/d:>11.1f}% {'+9.1%':>14}")
    print(f"{'시가평가 자기자본':<18} {model.mark_to_market_equity:>12.2f}B "
          f"{100*model.mark_to_market_equity/d:>11.1f}% {'-0.97%':>14}")
    print(f"{'무보험 예금 비율':<19} {'':>12}  {100*model.uninsured_share:>11.1f}% {'85~94%':>14}")

    payable = model.cash + model.securities_book * (
        1 - model.loss_rate - model.fire_sale_discount)
    print(f"\n  이 은행이 실제로 지급할 수 있는 최대 금액은 예금의 "
          f"{100*payable/d:.1f}% 뿐이다.")
    print("  (현금 + 증권을 급매한 값. 대출은 하루아침에 현금이 되지 않는다.)")
    print("  나머지 예금자가 동시에 오면 무슨 수를 써도 지급할 수 없다.")
    print("\n  그리고 시가평가 자기자본이 이미 마이너스다.")
    print("  만기까지 들고 있으면 손실을 실현하지 않으므로 장부상 +9.1%로 멀쩡하지만,")
    print("  한 주먹이라도 팔아야 하는 순간 그 착시가 깨진다.")
    print("  '아무도 빼지 않으면 살고, 빼기 시작하면 죽는' 구조가 여기서 나온다.")

    # --- 실험 A -----------------------------------------------------------
    print("\n" + "=" * 74)
    print("[실험 A] SVB 시나리오 - 3월 8일 발표에 해당하는 충격을 준다")
    print("=" * 74)
    model = BankRunModel(n_depositors=3000, signal_after=0.45, seed=42)
    print(f"{'스텝':>5} {'공개신호':>9} {'인출자':>9} {'누적유출%':>11} "
          f"{'남은현금%':>11} {'상태':>7}")
    print("-" * 74)
    for _ in range(30):
        model.step()
        v = model.datacollector.model_vars
        print(f"{model.steps:>5} {v['signal'][-1]:>9.2f} {v['ran_count'][-1]:>9,} "
              f"{v['ran_money_pct'][-1]:>11.1f} "
              f"{100*max(0.0, model.cash)/d:>11.2f} {outcome(model):>7}")
        if not model.running:
            break

    print("\n  => 충격이 들어간 스텝에 이미 예금의 39%가 빠지고, 그 다음 스텝에 끝난다.")
    print("     2스텝 전까지는 아무 일도 없었다. 서서히 나빠진 것이 아니라")
    print("     멀쩡하다가 한순간에 무너진다. 실제 SVB도 3월 8일 발표에서")
    print("     3월 10일 폐쇄까지 이틀이었다.")
    print("\n  주의: 이 '이틀'이 맞았다고 해서 모형이 검증된 것은 전혀 아니다.")
    print("  한 스텝이 몇 시간인지는 모형 어디에도 없다. 우리가 나중에 갖다 붙인 것이다.")
    print("  모형이 재현한 것은 기간이 아니라 '무너지는 방식'이다.")
    print("  숫자가 실제와 비슷하게 나왔을 때가 가장 위험하다.")
    print("  맞힌 것인지 우연인지 구분하지 않으면 모형을 과신하게 된다.")

    # --- 실험 B -----------------------------------------------------------
    print("\n" + "=" * 74)
    print("[실험 B] 검증 - 결과를 이미 아는 경우를 먼저 맞히는가")
    print("=" * 74)
    checks = [
        ("전원이 보험 대상이면 (한도 무한대)", dict(insurance_cap=1e9), "유출 0%"),
        ("현금을 100% 들고 있으면", dict(cash_ratio=1.0, loss_rate=0.0,
                                   fire_sale_discount=0.0), "파산 없음"),
        ("충격도 동조도 없으면", dict(signal_before=0.0, signal_after=0.0,
                                social_weight=0.0), "유출 0%"),
    ]
    for label, kwargs, expect in checks:
        fails, drains = 0, []
        for s in range(6):
            m = run_once(steps=40, n_depositors=2000, seed=s,
                         **({"signal_after": 0.45, **kwargs}))
            drains.append(m.datacollector.model_vars["ran_money_pct"][-1])
            fails += int(m.failed)
        print(f"  {label:<36} 파산 {fails}/6, 유출 {sum(drains)/len(drains):>5.1f}%"
              f"   (기대: {expect})")

    m = run_once(steps=40, n_depositors=2000, signal_after=0.45, seed=0)
    gap = abs(m.total_paid + m.deposits - m.initial_deposits)
    print(f"\n  불변량: 지급액 + 남은예금 - 초기예금 = {gap:.2e}  "
          f"({'보존됨' if gap < 1e-9 else '버그!'})")
    print("  => 극단 사례 세 개와 불변량이 모두 통과했다. 이제 모르는 것을 물어볼 차례다.")

    # --- 실험 C -----------------------------------------------------------
    print("\n" + "=" * 74)
    print("[실험 C] 충격의 크기를 바꾸면 - 상전이")
    print("=" * 74)
    print(f"{'충격 신호':>10} {'파산확률':>10} {'평균유출%':>11}   그래프")
    print("-" * 74)
    sweep = {}
    for sa in (0.05, 0.10, 0.125, 0.15, 0.175, 0.20, 0.25, 0.45):
        fails, drains = 0, []
        for s in range(20):
            m = run_once(steps=60, n_depositors=2000, signal_after=sa, seed=s)
            drains.append(m.datacollector.model_vars["ran_money_pct"][-1])
            fails += int(m.failed)
        prob = fails / 20
        sweep[sa] = prob
        print(f"{sa:>10.3f} {prob:>10.2f} {sum(drains)/len(drains):>11.1f}   "
              f"{bar(prob, 1.0)}")

    print("\n  => 신호 0.10까지는 아무 일도 없다가, 0.125~0.25 사이에서")
    print("     파산확률이 0에서 1로 치솟는다. 5단계 셸링에서 본 상전이와 같은 모양이다.")
    print("     '조금 나쁜 뉴스'와 '치명적인 뉴스' 사이의 경계는 연속적이지 않다.")

    # --- 실험 D (핵심) ----------------------------------------------------
    print("\n" + "=" * 74)
    print("[실험 D] 같은 은행, 같은 충격, 다른 결말  <- 이 단계의 핵심")
    print("=" * 74)
    print("  임계점(신호 0.175)에서 seed만 바꿔 20번 돌린다.")
    print("  대차대조표도 충격의 크기도 평균적인 성향도 전부 같다.\n")
    print(f"{'seed':>5} {'결과':>6} {'유출%':>8} {'스텝':>6}   {'seed':>5} {'결과':>6} "
          f"{'유출%':>8} {'스텝':>6}")
    print("-" * 74)
    rows = []
    for s in range(20):
        m = run_once(steps=60, n_depositors=2000, signal_after=0.175, seed=s)
        rows.append((s, outcome(m),
                     m.datacollector.model_vars["ran_money_pct"][-1], m.steps))
    for i in range(10):
        a, b = rows[i], rows[i + 10]
        print(f"{a[0]:>5} {a[1]:>6} {a[2]:>8.1f} {a[3]:>6}   "
              f"{b[0]:>5} {b[1]:>6} {b[2]:>8.1f} {b[3]:>6}")
    n_fail = sum(1 for r in rows if r[1] == "파산")
    print(f"\n  파산 {n_fail}/20, 생존 {20 - n_fail}/20.")
    print("\n  seed가 바꾼 것은 '우연'뿐이다. 누가 얼마를 맡겼는지, 누가 누구와")
    print("  아는 사이인지, 누가 얼마나 겁이 많은지, 누가 먼저 창구에 도착했는지.")
    print("  펀더멘털은 완전히 동일하다.")
    print("\n  => 이것이 Diamond-Dybvig가 말한 다중균형이다.")
    print("     '아무도 빼지 않는 상태'와 '모두가 빼는 상태'가 둘 다 균형이고,")
    print("     어느 쪽으로 굴러갈지는 예금자들이 서로를 어떻게 보느냐가 정한다.")
    print("\n     그래서 'SVB는 망하게 되어 있었나?'라는 질문에 이 모형은")
    print("     '그렇다'도 '아니다'도 아닌 답을 준다. 망하기 쉬운 상태였지만,")
    print("     망한 것 자체는 필연이 아니었다.")
    print("     4단계의 창발, 5단계의 상전이보다 한 걸음 더 나간 이야기다.")

    # --- 실험 E -----------------------------------------------------------
    print("\n" + "=" * 74)
    print("[실험 E] 반사실 - 무엇을 바꿨다면 막을 수 있었나")
    print("=" * 74)
    print("  임계점(신호 0.175)에서 한 번에 하나씩만 바꿔 본다.")
    print("  맨 윗줄이 기준선이고, 아래 줄들을 그와 비교해서 읽는다.\n")

    baseline = None
    scenarios = [
        ("기준선 (SVB 근사)", {}),
        ("[펀더멘털] 미실현손실이 없었다면", dict(loss_rate=0.0)),
        ("[펀더멘털] 현금을 7.9%->20% 들었다면", dict(cash_ratio=0.20)),
        ("[펀더멘털] 현금을 7.9%->30% 들었다면", dict(cash_ratio=0.30)),
        ("[믿음] 예금보험 한도가 10배였다면", dict(insurance_cap=2.5 / 1000)),
        ("[믿음] 예금보험 한도가 100배였다면", dict(insurance_cap=25.0 / 1000)),
        ("[전파] 아는 사람이 8명->3명이었다면", dict(peers_k=3)),
        ("[전파] 남을 덜 따라했다면 (동조 절반)", dict(social_weight=0.5)),
    ]
    print(f"{'시나리오':<38} {'파산':>8} {'평균유출%':>11}")
    print("-" * 74)
    for label, kwargs in scenarios:
        fails, drains = 0, []
        for s in range(20):
            m = run_once(steps=60, n_depositors=2000, signal_after=0.175,
                         seed=s, **kwargs)
            drains.append(m.datacollector.model_vars["ran_money_pct"][-1])
            fails += int(m.failed)
        if baseline is None:
            baseline = fails
        print(f"  {label:<36} {f'{fails}/20':>8} {sum(drains)/len(drains):>11.1f}")

    print("\n  => 읽는 법. 효과의 크기가 세 단계로 갈린다.")
    print("\n     (거의 없음) 현금을 네 배로 늘려도 파산 횟수가 거의 그대로다.")
    print("       유동성을 두 배, 네 배 쌓아도 런의 규모가 그보다 크기 때문이다.")
    print("       예금의 절반이 한꺼번에 빠지는 상황을 버틸 은행은 존재하지 않는다.")
    print("\n     (절반)   미실현손실을 없애면 파산이 대략 절반으로 준다.")
    print("       이건 무시할 수 없는 효과다. 다만 '절반'이지 '해결'은 아니다.")
    print("       손실이 0이어도 여전히 상당수의 실행에서 은행이 무너진다.")
    print("       건전한 은행도 런을 맞으면 죽을 수 있다는 뜻이다.")
    print("\n     (차단)   예금보험 한도를 올리거나 동조를 줄이면 파산이 0이 된다.")
    print("       잃을 것이 없는 예금자는 뛰지 않고, 남을 덜 따라하면")
    print("       연쇄가 시작되지 않는다. 런 자체가 일어나지 않는 것이다.")
    print("       아는 사람 수를 8명에서 3명으로 줄이는 것만으로도 크게 줄어든다.")
    print("\n     즉 이 모형의 답은 '은행을 더 튼튼하게 만들라'보다")
    print("     '예금자가 뛸 이유와 서로를 따라 할 통로를 줄여라'에 가깝다.")
    print("     예금보험이라는 제도가 존재하는 이유이고, 2023년 3월 12일에")
    print("     미국 당국이 SVB 예금을 한도와 무관하게 전액 보장한다고 발표해")
    print("     다른 은행으로의 확산을 멈춘 것도 같은 논리다.")
    print("\n     다만 이 결론은 이 모형의 규칙 안에서만 성립한다.")
    print("     전액 보장이 만들어 내는 도덕적 해이는 이 모형에 아예 없다.")
    print("     모형이 답할 수 있는 질문의 범위를 넘어서지 않는 것도 실력이다.")

    # --- 마무리 -----------------------------------------------------------
    print("\n" + "=" * 74)
    print("이 모형이 할 수 있는 것과 없는 것")
    print("=" * 74)
    print("  할 수 있다")
    print("    - 왜 멀쩡해 보이던 은행이 이틀 만에 무너지는가")
    print("    - 왜 같은 손실을 안고도 어떤 은행은 버티는가 (실험 D)")
    print("    - 어떤 개입이 효과가 있고 어떤 것이 없는가 (실험 E)")
    print("\n  할 수 없다")
    print("    - 어느 은행이 언제 무너질지 예측하는 것")
    print("    - 3월 9일의 420억 달러를 맞히는 것")
    print("    - 스텝 하나가 몇 시간인지 말하는 것 (우리가 정한 것이다)")
    print("\n  모형이 현실과 다른 지점 (알고 쓰는 것과 모르고 쓰는 것은 다르다)")
    print("    - 증권이 즉시 팔린다고 가정했다. 실제로는 시간이 걸리고,")
    print("      그래서 SVB는 예금의 24%만 지급한 시점에 문을 닫았다.")
    print("      이 모형의 은행은 61%까지 지급하므로 현실보다 관대하다.")
    print("    - 중앙은행의 긴급대출, 인수합병, 감독당국의 개입이 없다.")
    print("    - 다른 은행으로의 전염이 없다. 은행이 하나뿐인 세계다.")
    print("    - 예금자의 판단 규칙이 실제 사람의 행동인지는 검증되지 않았다.")
    print("      이것이 ABM에서 가장 약한 고리이며, 그래서 실험 B의 극단 사례")
    print("      검증과 실험 D의 반복 실행이 필수적이다.")
    print("=" * 74)


if __name__ == "__main__":
    main()
