"""5단계: 셸링(Schelling) 분리 모형 - 미시적 의도와 거시적 결과의 괴리.

이제 정답지가 없는 곳으로 간다. 4단계에는 기하분포라는 이론값이 있었지만,
셸링 모형에는 손으로 풀 수 있는 해가 없다. 돌려 보는 것 외에 방법이 없다.
에이전트 기반 모형이 실제로 쓰이는 곳이 바로 여기다.

[모형]
    격자 위에 두 종류의 주민이 산다. 각자 규칙은 하나뿐이다.

        "내 이웃 중 나와 같은 종류가 일정 비율에 못 미치면 이사 간다."

    그 비율이 관용도 파라미터(homophily)다. 0.3이면
    "이웃의 30%만 나와 같으면 만족한다"는 뜻이다.
    바꿔 말하면 이웃의 70%가 나와 달라도 괜찮다는 것이니,
    현실의 어떤 기준으로 보아도 상당히 관용적인 사람이다.

[이 단계의 핵심 주장]
    아무도 분리를 원하지 않아도 분리가 일어난다.

    관용도 0.3짜리 주민들만 모아 놓아도, 몇십 스텝 뒤 격자는
    같은 종류끼리 뭉친 큰 덩어리로 갈라진다. 최종적으로 각자의
    이웃 중 같은 종류 비율은 0.3이 아니라 0.7~0.9가 된다.
    아무도 원한 적 없는 수준의 분리가 결과로 나온 것이다.

    이유는 연쇄 반응이다. 한 사람이 이사하면 그가 떠난 자리의
    이웃 구성이 바뀌고, 그 때문에 불만족해진 사람이 또 이사한다.
    각자는 작은 기준을 만족시키려 했을 뿐인데, 그 움직임이 서로를
    밀어내며 거시적 패턴을 만든다.

    정책적으로 중요한 함의가 있다. 관찰된 분리로부터
    '사람들이 분리를 원한다'를 추론할 수 없다는 것이다.
    개인의 선호를 조금 바꾸는 것만으로 거시 결과가 바뀌지도 않는다.
    [실험 C]의 상전이가 그 이야기다.

[방법론적으로 새로 배우는 것]
    이론값이 없으니 다른 것으로 답해야 한다. 파라미터 스윕이다.
    관용도를 0.0부터 0.8까지 훑으면서 결과가 어떻게 달라지는지 본다.
    Mesa의 batch_run이 이 반복 실행을 대신해 준다.

실행:
    python3 steps/step05_schelling.py
"""

from __future__ import annotations

import mesa
from mesa.discrete_space import CellAgent, OrthogonalMooreGrid


class Resident(CellAgent):
    """두 종류(0, 1) 중 하나에 속하는 주민."""

    def __init__(self, model: mesa.Model, cell, kind: int) -> None:
        super().__init__(model)
        self.cell = cell
        self.kind = kind

    @property
    def similar_fraction(self) -> float:
        """이웃 중 나와 같은 종류의 비율. 이웃이 없으면 1.0(만족)으로 본다."""
        neighbors = [a for a in self.cell.neighborhood.agents]
        if not neighbors:
            return 1.0
        same = sum(1 for a in neighbors if a.kind == self.kind)
        return same / len(neighbors)

    @property
    def is_happy(self) -> bool:
        return self.similar_fraction >= self.model.homophily

    def step(self) -> None:
        if self.is_happy:
            self.model.happy_count += 1
            return
        # 불만족이면 빈 칸 중 아무 데로나 이사한다.
        # 주의: 이사 갈 곳이 더 나은지 따지지 않는다. 규칙은 이토록 단순하다.
        empty = self.model.grid.select_random_empty_cell()
        if empty is not None:
            self.cell = empty


class SchellingModel(mesa.Model):
    def __init__(
        self,
        size: int = 20,
        density: float = 0.8,
        homophily: float = 0.3,
        seed: int | None = None,
    ) -> None:
        super().__init__(seed=seed)
        self.size = size
        self.homophily = homophily
        self.happy_count = 0

        # capacity=1 : 한 칸에 한 명만 산다
        self.grid = OrthogonalMooreGrid(
            (size, size), torus=True, capacity=1, random=self.random
        )

        for cell in self.grid.all_cells.cells:
            if self.random.random() < density:
                Resident(self, cell, kind=self.random.randrange(2))

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "segregation": lambda m: m.mean_similar_fraction,
                "unhappy": lambda m: m.unhappy_count,
                "unhappy_pct": lambda m: 100 * m.unhappy_count / len(m.agents),
                "steps_taken": lambda m: m.steps,
            }
        )
        self.datacollector.collect(self)

    @property
    def mean_similar_fraction(self) -> float:
        """분리 지표: 모든 주민의 '같은 이웃 비율' 평균.

        무작위로 섞여 있으면 0.5 근처, 완전히 갈라져 있으면 1에 가깝다.
        """
        return sum(a.similar_fraction for a in self.agents) / len(self.agents)

    @property
    def unhappy_count(self) -> int:
        return sum(1 for a in self.agents if not a.is_happy)

    def step(self) -> None:
        self.happy_count = 0
        self.agents.shuffle_do("step")
        self.datacollector.collect(self)

        # 전원이 만족하면 더 이상 아무 일도 일어나지 않는다. 멈춘다.
        # batch_run은 이 running 플래그를 보고 조기 종료한다.
        if self.happy_count == len(self.agents):
            self.running = False

    def render(self) -> str:
        """격자 그림. A/B는 두 종류, 점은 빈 칸."""
        symbols = {0: "A", 1: "B"}
        rows = []
        for y in range(self.size - 1, -1, -1):
            row = []
            for x in range(self.size):
                agents = self.grid[(x, y)].agents
                row.append(symbols[agents[0].kind] if agents else "·")
            rows.append("    " + " ".join(row))
        return "\n".join(rows)


def run_once(steps: int = 100, **kwargs) -> SchellingModel:
    model = SchellingModel(**kwargs)
    for _ in range(steps):
        model.step()
        if not model.running:
            break
    return model


def main() -> None:
    print("=" * 74)
    print("5단계 | 셸링 분리 모형 - 아무도 원하지 않은 분리")
    print("=" * 74)

    model = SchellingModel(size=20, density=0.8, homophily=0.3, seed=42)
    print(f"20x20 격자, 주민 {len(model.agents)}명(A/B 두 종류), 관용도 = 0.3")
    print("   '이웃의 30%만 나와 같으면 만족' = 70%가 달라도 괜찮다는 뜻\n")

    print(f"[t=0] 무작위 배치.  분리 지표 {model.mean_similar_fraction:.3f}  "
          f"불만족 {model.unhappy_count}명")
    print(model.render())

    for t in range(1, 101):
        model.step()
        if not model.running:
            break

    v = model.datacollector.model_vars
    print(f"\n[t={model.steps}] 전원 만족해서 멈춤.  "
          f"분리 지표 {model.mean_similar_fraction:.3f}  불만족 {model.unhappy_count}명")
    print(model.render())

    print(f"\n  분리 지표가 {v['segregation'][0]:.3f} -> {v['segregation'][-1]:.3f} 로 올라갔다.")
    print(f"  주민들이 요구한 것은 0.3 이었는데, 실제로 도달한 곳은 "
          f"{v['segregation'][-1]:.2f} 다.")
    print("  아무도 이런 수준의 분리를 원하지 않았고, 요구하지도 않았다.")

    print("\n[실험 A] 시간에 따른 진행")
    print(f"{'스텝':>6} {'분리 지표':>12} {'불만족 수':>10} {'불만족 %':>10}")
    print("-" * 74)
    for t in range(len(v["segregation"])):
        if t in (0, 1, 2, 3, 5, 10, 20) or t == len(v["segregation"]) - 1:
            print(f"{t:>6} {v['segregation'][t]:>12.3f} {v['unhappy'][t]:>10} "
                  f"{v['unhappy_pct'][t]:>10.1f}")
    print("\n  => 대부분의 변화가 처음 몇 스텝에서 끝난다.")
    print("     그리고 한번 전원 만족에 도달하면 되돌아갈 힘이 없다.")
    print("     만족한 사람은 움직이지 않는다는 규칙 자체가 그 상태를 고정시킨다.")

    print("\n[실험 B] 관용도를 바꾸면 어떻게 되는가 (각 5회 반복)")
    print(f"{'관용도':>8} {'분리 지표':>12} {'표준편차':>10} {'멈춘 스텝':>10} {'해결됨':>8}")
    print("-" * 74)
    sweep = {}
    for h in (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875):
        segs, stops, solved = [], [], 0
        for s in range(5):
            m = run_once(steps=200, size=20, density=0.8, homophily=h, seed=s)
            segs.append(m.mean_similar_fraction)
            stops.append(m.steps)
            if not m.running:
                solved += 1
        mean_s = sum(segs) / len(segs)
        sd = (sum((x - mean_s) ** 2 for x in segs) / (len(segs) - 1)) ** 0.5
        sweep[h] = (mean_s, solved)
        print(f"{h:>8.3f} {mean_s:>12.3f} {sd:>10.3f} "
              f"{sum(stops)/len(stops):>10.1f} {f'{solved}/5':>8}")
    print("\n  '해결됨'은 전원이 만족해서 모형이 스스로 멈춘 실행의 수다.")
    print("  마지막 줄에서 이 값이 0/5로 떨어지는 것을 눈여겨볼 것.")

    print("\n[실험 C] 위 결과를 그림으로 - 관용도 대 분리 지표")
    print("       분리 지표 0.5 ─────────────────────────────── 1.0")
    for h, (seg, solved) in sweep.items():
        pos = max(0, min(44, round((seg - 0.5) / 0.5 * 44)))
        bar = " " * pos + ("●" if solved == 5 else "✗")
        flag = "" if solved == 5 else "   <- 수렴 실패"
        print(f"  관용도 {h:>5.3f} |{bar:<45}| {seg:.3f}{flag}")
    print("\n       ● = 전원 만족에 도달(안정 상태)   ✗ = 끝까지 못 멈춤")

    print("\n  => 읽는 법이 중요하다. 세 구간으로 나뉜다.")
    print("     (1) 관용도 0.0~0.125 : 요구가 거의 없으니 아무도 안 움직이고")
    print("         처음의 무작위 배치(0.5)가 그대로 남는다.")
    print("     (2) 관용도 0.25~0.375 : 지표가 0.60에서 0.78로 급격히 튀어오른다.")
    print("         개인 기준의 작은 변화가 거시 결과의 큰 변화를 만드는 구간,")
    print("         즉 상전이(phase transition)다. 관용도를 0.125만 올렸는데")
    print("         분리는 그 몇 배로 뛴다. 선형적 직관이 통하지 않는 지점이다.")
    print("     (3) 관용도 0.875 : 지표가 0.5로 '떨어진다'.")

    print("\n  [함정] (3)을 '관용도가 아주 높으면 오히려 통합된다'로 읽으면 완전히 틀린다.")
    print("     '해결됨' 열을 보라. 0/5 다. 이 실행들은 끝까지 멈추지 못했다.")
    print("     이웃 8명 중 7명 이상이 나와 같기를 요구하면 그런 자리는")
    print("     거의 존재하지 않는다. 그래서 주민 대부분이 영원히 이사를 반복하고,")
    print("     계속 무작위로 재배치되니 지표가 무작위 값인 0.5로 돌아간 것이다.")
    print("     통합이 아니라 '모형이 정상 상태에 도달하지 못한 상태'다.")
    print("\n     이것이 시뮬레이션 결과를 읽을 때 가장 자주 하는 실수다.")
    print("     지표 하나만 떼어 보지 말고, 그 숫자가 나온 상태가 무엇인지")
    print("     (수렴했는가? 몇 스텝 만에 멈췄는가? 여전히 움직이는가?)")
    print("     함께 확인해야 한다. 그래서 unhappy와 steps_taken도 같이 기록한 것이다.")

    print("\n[실험 D] Mesa의 batch_run으로 같은 스윕을 자동화하기")
    print("  실무에서는 위의 이중 for문 대신 batch_run을 쓴다.")
    print("  파라미터 조합을 알아서 만들고, 반복 실행하고, 결과를 표로 돌려준다.\n")

    results = mesa.batch_run(
        SchellingModel,
        parameters={
            "size": 20,
            "density": 0.8,
            "homophily": [0.25, 0.375, 0.5, 0.875],  # 리스트로 주면 자동으로 조합
        },
        iterations=5,        # 조합마다 5회씩 (seed는 Mesa가 알아서 바꿔 준다)
        max_steps=200,
        data_collection_period=-1,  # 마지막 스텝만 기록
        display_progress=False,
    )

    import pandas as pd

    df = pd.DataFrame(results)
    summary = df.groupby("homophily").agg(
        분리지표_평균=("segregation", "mean"),
        분리지표_표준편차=("segregation", "std"),
        불만족_평균=("unhappy", "mean"),
        실행횟수=("segregation", "count"),
    )
    print(summary.round(3).to_string())
    print("\n  => 위의 손으로 짠 스윕과 같은 결론이 나온다. 코드는 훨씬 짧다.")
    print("     0.875 줄의 '불만족_평균'이 0이 아니라는 점에 주목할 것.")
    print("     이 한 열이 없었다면 분리지표 0.5를 '통합'으로 오독했을 것이다.")
    print("     파라미터가 3개, 4개로 늘어나면 batch_run 없이는 관리가 안 된다.")
    print("     (number_processes 인자를 주면 여러 코어로 병렬 실행도 된다.)")

    print("\n" + "=" * 74)
    print("정리")
    print("  - 미시적 의도와 거시적 결과는 다르다. 후자에서 전자를 역추론할 수 없다.")
    print("  - 이론적 해가 없는 문제에서는 파라미터 스윕이 분석 도구가 된다.")
    print("  - 확률적 모형이므로 조합마다 여러 번 돌려 평균과 산포로 말해야 한다.")
    print("=" * 74)


if __name__ == "__main__":
    main()
