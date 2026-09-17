"""4단계: 상호작용을 얹는다 - 볼츠만 부(wealth) 모형과 불평등의 창발.

3단계까지 에이전트는 서로를 쳐다보지 않았다. 규칙 한 줄을 더한다.

    "같은 칸에 있는 누군가에게 내 돈 1을 준다."

단 한 줄인데, 여기서부터 성격이 달라진다.

[이 단계의 핵심 주장]
    완벽하게 대칭적이고 공정한 규칙에서도 극심한 불평등이 나타난다.

    모두 같은 돈으로 시작한다. 누구도 더 유능하지 않고, 이자도 없고,
    착취도 상속도 없다. 주는 사람과 받는 사람은 매번 무작위다.
    그런데 지니계수는 0에서 출발해 0.6 위까지 올라가 거기 머문다.
    부자가 된 사람은 운이 좋았을 뿐인데 결과는 구조적으로 보인다.

    이것이 창발(emergence)이다. 거시적 패턴이 미시적 규칙 어디에도
    적혀 있지 않은데 나타나는 것. 에이전트 기반 모형을 쓰는 진짜 이유다.

[검증: 이 모형에는 정답지가 있다]
    돈이 1단위씩만 오가므로 부는 정수다. 따라서 정상 상태의 분포는
    연속 지수분포가 아니라 이산 기하분포가 된다.

        P(부 = k) = (1 - p) * p^k ,   평균 m 일 때 p = m / (1 + m)

    평균 부가 1이면 p = 1/2 이므로 P(k) = (1/2)^(k+1).
    즉 부가 1 늘 때마다 사람 수가 절반씩 줄어든다.
    이 분포의 지니계수도 닫힌 식으로 나온다 (아래 gini_geometric).

        평균 부 1  ->  0.6667
        평균 부 5  ->  0.5455
        평균 부 10 ->  0.5238
        평균 부 -> 무한대  ->  0.5  (교과서에 나오는 지수분포의 값)

    교과서의 0.5를 그대로 기대하면 측정값 0.66과 안 맞아서 당황하게 된다.
    0.5는 '돈을 잘게 쪼갤 수 있을 때'의 극한값이고, 우리 모형은
    1원 단위로 거래하는 이산 모형이라 더 불평등한 것이 맞다.
    아래 [실험 D]에서 초기 부를 늘려 이 극한을 직접 확인한다.

[돈은 왜 사라지지 않는가]
    한 스텝에 오가는 것은 이동뿐이므로 총액은 항상 보존된다.
    이런 '반드시 성립해야 하는 불변량'을 코드로 확인해 두면
    조용히 값을 망가뜨리는 버그를 초기에 잡을 수 있다.

실행:
    python3 steps/step04_wealth.py
"""

from __future__ import annotations

from collections import Counter

import mesa
from mesa.discrete_space import CellAgent, OrthogonalMooreGrid


def gini(values: list[int]) -> float:
    """지니계수. 0이면 완전 평등, 1에 가까울수록 한 명이 독식.

    정렬한 뒤의 표준 공식:
        G = (2 * sum(i * x_i) - (n + 1) * sum(x)) / (n * sum(x))   (i는 1부터)
    """
    xs = sorted(values)
    n = len(xs)
    total = sum(xs)
    if total == 0:
        return 0.0
    weighted = sum((i + 1) * x for i, x in enumerate(xs))
    return (2 * weighted - (n + 1) * total) / (n * total)


def gini_geometric(mean_wealth: float) -> float:
    """평균이 mean_wealth인 이산 기하분포의 지니계수 (이론값).

    지니계수는 G = E|X - Y| / (2 * 평균) 으로 쓸 수 있고,
    기하분포에서는 E|X - Y| = 2p / ((1+p)(1-p)) 이다.
    mean_wealth가 커지면 0.5(연속 지수분포 값)로 수렴한다.
    """
    p = mean_wealth / (1.0 + mean_wealth)
    return (2 * p / ((1 + p) * (1 - p))) / (2 * mean_wealth)


class MoneyAgent(CellAgent):
    """돈을 들고 돌아다니며 마주친 사람에게 1을 건네는 에이전트."""

    def __init__(self, model: mesa.Model, cell, wealth: int = 1) -> None:
        super().__init__(model)
        self.cell = cell
        self.wealth = wealth  # 전원 똑같은 값에서 출발한다

    def move(self) -> None:
        self.cell = self.cell.neighborhood.select_random_cell()

    def give_money(self) -> None:
        """같은 칸에 있는 다른 에이전트 한 명에게 1을 준다."""
        if self.wealth <= 0:
            return  # 빈털터리는 줄 것이 없다 (부는 음수가 될 수 없다)

        neighbors = [a for a in self.cell.agents if a is not self]
        if not neighbors:
            return  # 아무도 없으면 거래가 일어나지 않는다

        other = self.random.choice(neighbors)
        other.wealth += 1
        self.wealth -= 1

    def step(self) -> None:
        self.move()
        self.give_money()


class BoltzmannWealthModel(mesa.Model):
    def __init__(
        self,
        n_agents: int = 200,
        size: int = 15,
        initial_wealth: int = 1,
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self.n_agents = n_agents
        self.initial_wealth = initial_wealth
        self.grid = OrthogonalMooreGrid((size, size), torus=True, random=self.random)

        for _ in range(n_agents):
            cell = self.random.choice(self.grid.all_cells.cells)
            MoneyAgent(self, cell, wealth=initial_wealth)

        self.initial_total_wealth = self.total_wealth

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "gini": lambda m: gini(m.wealth_list),
                "total_wealth": lambda m: m.total_wealth,
                "max_wealth": lambda m: max(m.wealth_list),
                "n_broke": lambda m: sum(1 for w in m.wealth_list if w == 0),
            },
            agent_reporters={"wealth": "wealth"},
        )
        self.datacollector.collect(self)

    @property
    def wealth_list(self) -> list[int]:
        return [a.wealth for a in self.agents]

    @property
    def total_wealth(self) -> int:
        return self.agents.agg("wealth", sum)

    def step(self) -> None:
        # 실행 순서를 매번 섞는다. 여기서는 먼저 움직인 사람이 마주칠
        # 상대가 달라지므로 순서가 실제로 결과에 영향을 준다.
        self.agents.shuffle_do("step")
        self.datacollector.collect(self)


def histogram(values: list[int], width: int = 40, max_rows: int = 10) -> str:
    """부의 분포를 터미널 막대그래프로. 정수 값마다 한 줄씩."""
    counts = Counter(values)
    top = max(counts)
    peak = max(counts.values())
    lines = []
    for k in range(min(top, max_rows - 1) + 1):
        bar = "█" * round(counts.get(k, 0) / peak * width)
        lines.append(f"  부 {k:>3} | {bar} {counts.get(k, 0)}")
    if top >= max_rows:
        tail = sum(c for k, c in counts.items() if k >= max_rows)
        bar = "█" * round(tail / peak * width)
        lines.append(f"  {max_rows:>3}+  | {bar} {tail}")
    return "\n".join(lines)


def run_to_end(steps: int, **kwargs) -> BoltzmannWealthModel:
    model = BoltzmannWealthModel(**kwargs)
    for _ in range(steps):
        model.step()
    return model


def main() -> None:
    print("=" * 70)
    print("4단계 | 볼츠만 부 모형 - 공정한 규칙에서 자라나는 불평등")
    print("=" * 70)

    model = BoltzmannWealthModel(n_agents=200, size=15, seed=42)
    print("에이전트 200명, 15x15 격자, 전원 부 = 1 로 출발")
    print(f"출발 시 지니계수 = {gini(model.wealth_list):.4f}  (완전 평등)\n")

    n_steps = 1000
    print("[실험 A] 시간에 따른 불평등")
    print(f"{'스텝':>6} {'지니':>8} {'최대 부':>8} {'무일푼 수':>10} {'총액':>8}")
    print("-" * 70)
    for t in range(1, n_steps + 1):
        model.step()
        if t in (1, 2, 5, 10, 25, 50, 100, 300, 600, 1000):
            v = model.datacollector.model_vars
            print(f"{t:>6} {v['gini'][t]:>8.4f} {v['max_wealth'][t]:>8} "
                  f"{v['n_broke'][t]:>10} {v['total_wealth'][t]:>8}")

    print("\n  => 지니계수가 첫 몇 스텝 만에 0.5를 넘고, 이후 0.6대에서 진동한다.")
    print("     계속 나빠지는 것이 아니라 '정상 상태'에 도달해 머무는 것이다.")
    print("     단 그 안에서 누가 부자인지는 계속 바뀐다. 구조는 고정, 개인은 유동.")

    print("\n[불변량 확인] 돈은 오가기만 할 뿐 생기거나 사라지지 않는다")
    ok = model.initial_total_wealth == model.total_wealth
    print(f"  출발 총액 {model.initial_total_wealth} / 현재 총액 {model.total_wealth} "
          f"-> {'보존됨' if ok else '버그!'}")
    print("  이런 확인을 코드에 박아 두면, 결과가 이상할 때")
    print("  '모형이 그런 것'인지 '코드가 틀린 것'인지 빠르게 갈라낼 수 있다.")

    print("\n[실험 B] 부의 분포 모양 (1000스텝 뒤)")
    wealths = model.wealth_list
    print(histogram(wealths))
    srt = sorted(wealths)
    print(f"\n  평균 {sum(wealths)/len(wealths):.2f}  중앙값 {srt[len(srt)//2]}  "
          f"최댓값 {max(wealths)}  무일푼 {sum(1 for w in wealths if w == 0)}명")
    print("  => 왼쪽에 몰리고 오른쪽으로 길게 늘어진 모양.")
    print("     평균(1.0)에 해당하는 '평균적인 사람'은 사실상 존재하지 않는다.")

    print("\n[실험 C] 분포가 이론(기하분포)과 맞는가")
    print("  한 번의 실행은 표본이 200명뿐이라 들쭉날쭉하다. 10회분을 합쳐서 본다.")
    pool: list[int] = []
    for s in range(10):
        pool += run_to_end(1000, n_agents=200, size=15, seed=s).wealth_list
    counter = Counter(pool)
    print(f"\n{'부 k':>6} {'관측 비율':>12} {'이론 (1/2)^(k+1)':>18} {'관측/이론':>10}")
    print("-" * 70)
    for k in range(7):
        obs = counter[k] / len(pool)
        theory = 0.5 ** (k + 1)
        print(f"{k:>6} {obs:>12.4f} {theory:>18.4f} {obs/theory:>10.2f}")
    print(f"  (표본 {len(pool):,}명분 = 10회 x 200명)")
    print("  => 부가 1 늘 때마다 사람 수가 절반씩 줄어드는 기하분포와 맞는다.")
    print("     꼬리(부 6 이상)는 관측 수 자체가 적어 비율이 크게 튄다.")
    print("     '표본이 적은 구간은 못 믿는다'는 것도 같이 읽어야 할 정보다.")

    measured = [gini(run_to_end(1000, n_agents=200, size=15, seed=s).wealth_list)
                for s in range(10)]
    mean_g = sum(measured) / len(measured)
    sd_g = (sum((g - mean_g) ** 2 for g in measured) / (len(measured) - 1)) ** 0.5
    theory_g = gini_geometric(1.0)
    print(f"\n  지니계수: 측정 {mean_g:.4f} (10회, 표준편차 {sd_g:.4f}) vs 이론 {theory_g:.4f}")
    print(f"  차이 {theory_g - mean_g:+.4f} - 측정값이 1~2% 정도 체계적으로 낮다.")
    print("     이유: (1) 표본 지니계수는 n이 유한하면 약간 낮게 나오는 편향이 있고,")
    print("           (2) 우리 모형은 총액이 정확히 200으로 고정되어 있어서")
    print("               총액이 자유롭게 변동하는 이론 모형보다 극단값이 덜 나온다.")
    print("     이 정도 차이를 '버그'와 '유한 크기 효과'로 구분하는 것이")
    print("     시뮬레이션 검증의 실제 내용이다. 억지로 맞추려 들면 안 된다.")

    print("\n[실험 D] 교과서의 0.5는 어디 갔는가 - 초기 부를 늘려 본다")
    print("  돈을 잘게 쪼갤수록 이산 모형은 연속 모형에 가까워진다.")
    print(f"\n{'초기 부':>8} {'측정 지니':>12} {'기하분포 이론':>14} {'연속 극한':>10}")
    print("-" * 70)
    for w0 in (1, 2, 5, 10):
        steps = 400 + 400 * w0   # 돈이 많을수록 섞이는 데 더 오래 걸린다
        vals = [gini(run_to_end(steps, n_agents=200, size=15,
                                initial_wealth=w0, seed=s).wealth_list)
                for s in range(3)]
        print(f"{w0:>8} {sum(vals)/len(vals):>12.4f} "
              f"{gini_geometric(w0):>14.4f} {0.5:>10.4f}")
    print("\n  => 초기 부가 커질수록 측정값이 기하분포 이론을 따라 0.5로 내려간다.")
    print("     (각 줄은 3회 평균이라 0.01~0.03 정도는 그냥 출렁인다. 큰 흐름만 읽을 것.)")
    print("     교과서 값과 모형이 안 맞았던 것은 버그가 아니라")
    print("     '어떤 극한의 이론인지'를 확인하지 않았기 때문이다.")
    print("     모형과 이론을 맞출 때 가장 자주 나오는 종류의 함정이다.")

    print("\n" + "=" * 70)
    print("정리: 규칙은 대칭적인데 결과는 불평등하다. 이것이 창발이다.")
    print("5단계에서는 이런 이론적 정답지가 아예 없는 문제로 간다.")
    print("=" * 70)


if __name__ == "__main__":
    main()
