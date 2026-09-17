"""2단계: 똑같은 pi 계산을 Mesa로 다시 쓰기.

1단계의 for 루프를 Mesa의 부품으로 갈아 끼운다. 답은 같다.
목적은 더 좋은 pi를 얻는 것이 아니라, Mesa의 뼈대를 '이미 아는 문제' 위에서
익히는 것이다. 새 도구는 새 문제와 함께 배우면 둘 다 어려워진다.

[1단계 -> Mesa 대응표]
    1단계의 코드                     Mesa의 부품
    ---------------------------------------------------------------
    점을 던지는 주체 (암묵적)   ->   Agent          다트를 던지는 사람
    inside, total 변수          ->   Agent/Model 속성
    x, y 뽑기 + 판정            ->   Agent.step()   한 에이전트의 1회 행동
    for _ in range(N)           ->   Model.step()   전체의 1회 시간 전진
    4 * inside / total          ->   DataCollector  매 스텝 자동 기록
    random.Random(seed)         ->   Model(seed=..) 모형 전체가 공유하는 난수

[솔직하게 짚고 갈 점]
    pi 추정에 에이전트 기반 모형은 명백한 과잉이다. 에이전트들이 서로를
    쳐다보지 않고 완전히 독립적이기 때문에, 1000명이 1번씩 던지든
    1명이 1000번 던지든 결과는 통계적으로 같다.
    그러면 Mesa는 언제 필요한가?
        -> 에이전트가 '서로에게 반응하기 시작할 때'.
           그 순간 손으로 푸는 수식이 막히고, 돌려 보는 것 말고
           답을 얻을 방법이 없어진다. 4단계와 5단계가 그 예다.
    이 단계는 그 전에 부품 이름을 외워 두는 자리다.

실행:
    python3 steps/step02_pi_mesa.py
"""

from __future__ import annotations

import math

import mesa


class Thrower(mesa.Agent):
    """다트를 던지는 에이전트.

    Mesa 3.x에서 Agent는 model 하나만 받으면 된다.
    unique_id는 Mesa가 자동으로 붙여 주고, 생성과 동시에
    model.agents 안에 자동 등록된다 (별도의 scheduler가 없다).
    """

    def __init__(self, model: mesa.Model) -> None:
        super().__init__(model)
        self.throws = 0  # 내가 던진 횟수
        self.hits = 0    # 그 중 원 안에 들어간 횟수

    def step(self) -> None:
        """이 에이전트의 '한 번의 차례'. 다트를 한 개 던진다.

        self.random 은 모형이 가진 난수 생성기다.
        모든 에이전트가 이 하나를 공유하기 때문에,
        Model(seed=42) 한 번으로 실험 전체가 재현된다.
        """
        x = self.random.uniform(-1.0, 1.0)
        y = self.random.uniform(-1.0, 1.0)
        self.throws += 1
        if x * x + y * y <= 1.0:
            self.hits += 1


class MonteCarloPiModel(mesa.Model):
    """다트 던지는 사람 n명이 모여 있는 세계."""

    def __init__(self, n_agents: int = 100, seed: int | None = None) -> None:
        super().__init__(seed=seed)  # seed는 여기 한 번만 주면 된다
        self.n_agents = n_agents

        # 에이전트 생성. 만들기만 하면 self.agents 에 들어간다.
        Thrower.create_agents(self, n_agents)

        # 매 스텝 자동으로 기록할 값들을 선언해 둔다.
        #   model_reporters: 세계 전체에 대한 값
        #   agent_reporters: 에이전트 한 명 한 명에 대한 값
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "pi_estimate": lambda m: m.pi_estimate,
                "total_throws": lambda m: m.total_throws,
                "abs_error": lambda m: abs(m.pi_estimate - math.pi),
            },
            agent_reporters={"hits": "hits", "throws": "throws"},
        )
        self.datacollector.collect(self)  # 0스텝(초기 상태)도 기록

    # --- 집계: 흩어져 있는 에이전트의 상태를 전체 통계로 모은다 ---
    @property
    def total_hits(self) -> int:
        # AgentSet.agg 는 모든 에이전트의 속성을 한 번에 집계한다.
        return self.agents.agg("hits", sum)

    @property
    def total_throws(self) -> int:
        return self.agents.agg("throws", sum)

    @property
    def pi_estimate(self) -> float:
        if self.total_throws == 0:
            return float("nan")
        return 4.0 * self.total_hits / self.total_throws

    def step(self) -> None:
        """세계의 1 스텝 = 모든 에이전트가 한 번씩 던진다.

        shuffle_do("step") 은 '순서를 매번 섞어서' 모두의 step()을 부른다.
        여기서는 서로 영향을 주지 않으니 순서가 무의미하지만,
        4, 5단계에서는 실행 순서가 결과를 바꾼다.
        그래서 처음부터 섞는 습관을 들이는 편이 안전하다.
        """
        self.agents.shuffle_do("step")
        self.datacollector.collect(self)


def sparkline(values: list[float], target: float, width: int = 60) -> str:
    """수렴 과정을 터미널에 간단히 그린다 (matplotlib 없이)."""
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if math.isclose(lo, hi):
        lo, hi = lo - 0.01, hi + 0.01
    blocks = "▁▂▃▄▅▆▇█"
    stride = max(1, len(values) // width)
    sampled = values[::stride][:width]
    line = "".join(blocks[min(7, int((v - lo) / (hi - lo) * 8))] for v in sampled)
    return f"  {lo:.4f} |{line}| {hi:.4f}   (참값 {target:.4f})"


def main() -> None:
    print("=" * 68)
    print("2단계 | 같은 pi 계산을 Mesa로")
    print("=" * 68)

    model = MonteCarloPiModel(n_agents=200, seed=42)
    n_steps = 500

    print(f"에이전트 {model.n_agents}명 x {n_steps}스텝 = "
          f"다트 {model.n_agents * n_steps:,}개\n")

    print(f"{'스텝':>6} {'누적 다트':>12} {'추정 pi':>12} {'오차':>10}")
    print("-" * 68)
    for step in range(1, n_steps + 1):
        model.step()
        if step in (1, 5, 10, 50, 100, 250, 500):
            print(f"{step:>6} {model.total_throws:>12,} "
                  f"{model.pi_estimate:>12.6f} {abs(model.pi_estimate - math.pi):>10.6f}")

    # DataCollector에 쌓인 것을 pandas DataFrame으로 꺼낸다.
    model_df = model.datacollector.get_model_vars_dataframe()
    agent_df = model.datacollector.get_agent_vars_dataframe()

    print("\n[DataCollector가 모아 둔 모형 수준 기록] 마지막 5스텝")
    print(model_df.tail(5).to_string())

    print("\n[수렴 곡선] 누적 추정값의 궤적 (세로 폭이 0.05도 안 되게 확대된 그림)")
    print(sparkline(model_df["pi_estimate"].tolist()[1:], math.pi))

    # 수렴은 '값이 참값에 닿는 것'이 아니라 '출렁임의 폭이 좁아지는 것'이다.
    # 구간별로 추정값의 진폭을 재 보면 그 점이 눈에 보인다.
    print("\n[수렴의 정확한 의미] 구간별 추정값의 출렁임 폭")
    print(f"{'스텝 구간':>14} {'최솟값':>10} {'최댓값':>10} {'폭':>10} {'이론 SE':>10}")
    print("-" * 68)
    series = model_df["pi_estimate"]
    p_true = math.pi / 4.0
    for lo in range(1, n_steps + 1, 100):
        hi = min(lo + 99, n_steps)
        window = series.loc[lo:hi]
        # 구간 중간 지점에서의 누적 표본 수로 이론 SE를 계산
        n_cum = int(model_df["total_throws"].loc[(lo + hi) // 2])
        se = 4.0 * math.sqrt(p_true * (1 - p_true) / n_cum)
        print(f"{f'{lo}-{hi}':>14} {window.min():>10.4f} {window.max():>10.4f} "
              f"{window.max() - window.min():>10.4f} {se:>10.4f}")
    print("  => 폭이 단조롭게 줄어든다. 이것이 수렴이다.")
    print("     값이 참값에 '도달'하는 것이 아니라, 참값 주변의 구름이 조여드는 것.")

    final_error = abs(model.pi_estimate - math.pi)
    final_se = 4.0 * math.sqrt(p_true * (1 - p_true) / model.total_throws)
    print(f"\n  최종 오차 {final_error:.5f} = 이론 SE({final_se:.5f})의 "
          f"{final_error / final_se:.2f}배")
    print("     1~2배 사이면 지극히 정상이다. 오히려 항상 0에 가깝게 나온다면")
    print("     난수 생성이나 집계 코드를 의심해야 한다.")

    print("\n[에이전트 수준 기록] 마지막 스텝, 개인별 적중률 상/하위 3명")
    last = agent_df.xs(n_steps, level="Step").copy()
    last["rate"] = last["hits"] / last["throws"]
    ranked = last.sort_values("rate", ascending=False)
    print(ranked.head(3).to_string())
    print("  ...")
    print(ranked.tail(3).to_string())
    print(f"\n  개인별 적중률 범위: {last['rate'].min():.3f} ~ {last['rate'].max():.3f}")
    print(f"  전체 적중률       : {model.total_hits / model.total_throws:.3f}  (이론값 pi/4 = {math.pi/4:.3f})")
    print("  => 개인은 제각각인데 전체는 안정적이다. 미시와 거시의 차이가")
    print("     가장 평화롭게 나타난 예. 5단계에서는 이 둘이 충돌한다.")

    # 재현성: 1단계와 똑같은 원리가 Mesa에서도 성립한다.
    print("\n[재현성] 같은 seed로 다시 돌리면 완전히 동일한가")
    def run(seed: int) -> float:
        m = MonteCarloPiModel(n_agents=200, seed=seed)
        for _ in range(100):
            m.step()
        return m.pi_estimate

    print(f"  seed=1 -> {run(1):.8f}")
    print(f"  seed=1 -> {run(1):.8f}   (동일: {run(1) == run(1)})")
    print(f"  seed=2 -> {run(2):.8f}")

    print("\n" + "=" * 68)
    print("여기까지가 Mesa의 전부다: Agent.step / Model.step / DataCollector / seed.")
    print("3단계부터는 이 뼈대에 '공간'과 '상호작용'을 하나씩 얹는다.")
    print("=" * 68)


if __name__ == "__main__":
    main()
