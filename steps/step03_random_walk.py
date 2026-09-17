"""3단계: 공간을 얹는다 - 격자 위의 랜덤워크.

2단계까지 에이전트는 '어디에도' 없었다. 이제 격자 위에 세운다.
공간이 생기면 '이웃'이라는 개념이 따라오고, 이웃이 생겨야
다음 단계의 상호작용이 가능해진다. 이 단계는 그 징검다리다.

아직 에이전트끼리는 서로를 보지 않는다. 각자 무작위로 한 칸씩 걸을 뿐이다.
그런데도 배울 것이 있다.

[이 단계의 핵심 주장]
    개별 궤적은 완전히 예측 불가능한데, 집단의 통계량은 정확히 예측된다.

    무어(Moore) 이웃 8칸 중 하나를 균등하게 고르면
        dx 는 -1이 3칸, 0이 2칸, +1이 3칸  ->  E[dx^2] = 6/8 = 0.75
        dy 도 마찬가지                      ->  E[dy^2] = 0.75
    한 스텝의 변위는 서로 독립이므로 t스텝 후 평균제곱변위(MSD)는

        MSD(t) = E[x^2 + y^2] = 1.5 * t      <- 코드로 확인할 이론값

    따라서 '중심에서 떨어진 거리'는 sqrt(1.5 t), 즉 sqrt(t)에 비례한다.
    1단계의 오차가 1/sqrt(N)이었던 것과 같은 뿌리(중심극한정리)다.
    시간의 제곱근이라는 이 느린 속도가 확산 현상의 본질이다.

[기억해 둘 것]
    시뮬레이션 결과는 반드시 '따로 계산할 수 있는 무언가'와 맞춰 봐야 한다.
    여기서는 MSD = 1.5t 가 그 역할을 한다. 이런 확인 없이 얻은
    숫자는 모형의 결과인지 버그의 결과인지 구분할 수 없다.

실행:
    python3 steps/step03_random_walk.py
"""

from __future__ import annotations

import math

import mesa
from mesa.discrete_space import CellAgent, OrthogonalMooreGrid

GRID_SIZE = 21  # 홀수라야 정중앙 칸이 존재한다


class Walker(CellAgent):
    """무작위로 한 칸씩 걷는 보행자."""

    def __init__(self, model: mesa.Model, cell) -> None:
        super().__init__(model)
        self.cell = cell          # 현재 위치 (격자 위, torus라 감긴다)
        self.disp_x = 0           # 출발점 기준 누적 변위 (감기지 않는 '진짜' 이동량)
        self.disp_y = 0

    def step(self) -> None:
        old_x, old_y = self.cell.coordinate

        # 무어 이웃 8칸 중 하나를 무작위로 골라 이동한다.
        self.cell = self.cell.neighborhood.select_random_cell()
        new_x, new_y = self.cell.coordinate

        # torus에서는 오른쪽 끝에서 한 칸 더 가면 왼쪽 끝으로 나온다.
        # 그러면 좌표 차이가 +1이 아니라 -(W-1)로 찍힌다. 보정해 준다.
        # (한 스텝 이동은 항상 ±1 또는 0이므로 이 판정으로 충분하다.)
        self.disp_x += _unwrap(new_x - old_x, GRID_SIZE)
        self.disp_y += _unwrap(new_y - old_y, GRID_SIZE)

    @property
    def squared_displacement(self) -> int:
        return self.disp_x**2 + self.disp_y**2


def _unwrap(delta: int, size: int) -> int:
    """torus 경계를 넘어가며 생긴 좌표 점프를 실제 이동량(-1/0/+1)로 되돌린다."""
    if delta > 1:
        return delta - size
    if delta < -1:
        return delta + size
    return delta


class RandomWalkModel(mesa.Model):
    """보행자 n명이 정중앙에서 동시에 출발하는 세계."""

    def __init__(self, n_walkers: int = 500, size: int = GRID_SIZE, seed: int | None = None) -> None:
        super().__init__(seed=seed)
        self.size = size
        self.grid = OrthogonalMooreGrid((size, size), torus=True, random=self.random)

        center = self.grid[(size // 2, size // 2)]
        for _ in range(n_walkers):
            Walker(self, center)  # 전원 같은 칸에서 출발

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "msd": lambda m: m.mean_squared_displacement,
                "msd_theory": lambda m: 1.5 * m.steps,
                "spread": lambda m: m.occupied_cell_count,
            }
        )
        self.datacollector.collect(self)

    @property
    def mean_squared_displacement(self) -> float:
        """모든 보행자의 제곱변위 평균. 이론값 1.5 * t 와 비교할 양."""
        return sum(a.squared_displacement for a in self.agents) / len(self.agents)

    @property
    def occupied_cell_count(self) -> int:
        return sum(1 for cell in self.grid.all_cells.cells if len(cell.agents) > 0)

    def step(self) -> None:
        self.agents.shuffle_do("step")
        self.datacollector.collect(self)

    # --- 터미널용 밀도 그림 ---
    def render(self) -> str:
        """칸마다 몇 명이 있는지 농도 문자로 그린다."""
        shades = " .:-=+*#%@"
        counts = {
            cell.coordinate: len(cell.agents)
            for cell in self.grid.all_cells.cells
        }
        peak = max(counts.values()) or 1
        rows = []
        for y in range(self.size - 1, -1, -1):
            row = "".join(
                shades[min(len(shades) - 1, int(counts[(x, y)] / peak * (len(shades) - 1)))]
                for x in range(self.size)
            )
            rows.append("    " + row)
        return "\n".join(rows)


def main() -> None:
    print("=" * 68)
    print("3단계 | 격자 위의 랜덤워크 - 공간과 확산")
    print("=" * 68)

    model = RandomWalkModel(n_walkers=500, seed=42)
    print(f"{model.size}x{model.size} 격자(torus), 보행자 500명, 전원 정중앙 출발\n")

    print("[t=0] 전원이 한 칸에 몰려 있다")
    print(model.render())

    snapshots = {5: None, 20: None, 100: None}
    for t in range(1, 101):
        model.step()
        if t in snapshots:
            snapshots[t] = model.render()

    for t, picture in snapshots.items():
        print(f"\n[t={t}] 점유 칸 {model.datacollector.model_vars['spread'][t]}개 / "
              f"{model.size**2}개")
        print(picture)

    print("\n" + "-" * 68)
    print("[검증] 평균제곱변위가 이론값 1.5t 와 맞는가")
    print(f"{'t':>6} {'MSD(측정)':>12} {'1.5t(이론)':>12} {'비율':>8} {'RMS 거리':>10}")
    print("-" * 68)
    msd_series = model.datacollector.model_vars["msd"]
    for t in (1, 5, 10, 25, 50, 75, 100):
        measured = msd_series[t]
        theory = 1.5 * t
        print(f"{t:>6} {measured:>12.3f} {theory:>12.3f} "
              f"{measured / theory:>8.3f} {math.sqrt(measured):>10.3f}")

    print("\n  => 비율이 1 근처에서 맴돈다. 모형이 이론과 일치한다는 뜻이다.")
    print("     RMS 거리는 t=25일 때 약 6칸, t=100일 때 약 12칸.")
    print("     시간이 4배가 되어도 거리는 2배밖에 늘지 않는다 (sqrt(t)).")

    # 개별 궤적은 제각각이라는 것을 보여 준다.
    finals = sorted(a.squared_displacement for a in model.agents)
    print(f"\n[개별과 집단] t=100에서 보행자 500명의 제곱변위")
    print(f"  최솟값 {finals[0]:>4}   중앙값 {finals[len(finals)//2]:>4}   "
          f"최댓값 {finals[-1]:>4}   평균 {msd_series[100]:.1f}")
    print("  => 어떤 사람은 출발점 근처에 있고 어떤 사람은 멀리 갔다.")
    print("     한 명의 미래는 예측할 수 없지만 500명의 평균은 1.5t로 예측된다.")
    print("     이것이 '확률적 모형을 여러 번 돌려 평균으로 말한다'는 원칙의 근거다.")

    print("\n" + "=" * 68)
    print("여기까지 에이전트는 서로를 쳐다보지 않았다.")
    print("4단계에서 '옆 사람에게 영향을 준다'는 규칙 한 줄을 추가하면,")
    print("손으로 풀기 어려운 결과가 나오기 시작한다.")
    print("=" * 68)


if __name__ == "__main__":
    main()
