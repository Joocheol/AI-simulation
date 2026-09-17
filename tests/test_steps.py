"""각 단계 모형이 '반드시 성립해야 하는 성질'을 지키는지 확인한다.

시뮬레이션 코드의 테스트는 일반 소프트웨어 테스트와 성격이 조금 다르다.
난수가 끼어 있어서 출력값을 하나로 못 박을 수 없기 때문이다.
대신 다음 세 종류를 확인한다.

    1) 불변량   - 어떤 seed에서도 반드시 참인 성질 (예: 총액 보존)
    2) 이론값   - 따로 계산할 수 있는 값과의 일치 (예: MSD = 1.5t)
    3) 재현성   - 같은 seed는 같은 결과

실행:
    python3 tests/test_steps.py      (pytest 없이도 동작)
    python3 -m pytest tests/ -v      (pytest가 있으면)
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from steps.step01_pi_plain import estimate_pi, theoretical_stderr
from steps.step02_pi_mesa import MonteCarloPiModel
from steps.step03_random_walk import RandomWalkModel
from steps.step04_wealth import BoltzmannWealthModel, gini, gini_geometric
from steps.step05_schelling import SchellingModel


# --- 1단계 ---------------------------------------------------------------

def test_pi_plain_is_close():
    """추정값이 참값에서 이론 표준오차의 4배를 벗어나면 뭔가 잘못된 것이다."""
    n = 200_000
    estimate = estimate_pi(n, seed=0)
    assert abs(estimate - math.pi) < 4 * theoretical_stderr(n)


def test_pi_plain_reproducible():
    assert estimate_pi(10_000, seed=5) == estimate_pi(10_000, seed=5)
    assert estimate_pi(10_000, seed=5) != estimate_pi(10_000, seed=6)


def test_stderr_shrinks_as_sqrt_n():
    """표본이 100배면 표준오차는 10분의 1이어야 한다."""
    ratio = theoretical_stderr(1_000) / theoretical_stderr(100_000)
    assert math.isclose(ratio, 10.0, rel_tol=1e-9)


# --- 2단계 ---------------------------------------------------------------

def test_mesa_pi_matches_plain_quality():
    model = MonteCarloPiModel(n_agents=100, seed=0)
    for _ in range(300):
        model.step()
    assert model.total_throws == 100 * 300           # 다트 수가 정확한가
    assert abs(model.pi_estimate - math.pi) < 4 * theoretical_stderr(model.total_throws)


def test_mesa_pi_reproducible():
    def run(seed: int) -> float:
        m = MonteCarloPiModel(n_agents=50, seed=seed)
        for _ in range(50):
            m.step()
        return m.pi_estimate

    assert run(3) == run(3)
    assert run(3) != run(4)


def test_datacollector_length():
    """0스텝(초기 상태)을 포함해 기록이 남아야 한다."""
    model = MonteCarloPiModel(n_agents=10, seed=1)
    for _ in range(7):
        model.step()
    assert len(model.datacollector.get_model_vars_dataframe()) == 8


# --- 3단계 ---------------------------------------------------------------

def test_msd_matches_theory():
    """무어 이웃 랜덤워크의 평균제곱변위는 1.5 * t 여야 한다."""
    model = RandomWalkModel(n_walkers=800, seed=7)
    for _ in range(80):
        model.step()
    measured = model.mean_squared_displacement
    assert math.isclose(measured, 1.5 * 80, rel_tol=0.15), measured


def test_walkers_start_together():
    model = RandomWalkModel(n_walkers=30, seed=1)
    positions = {a.cell.coordinate for a in model.agents}
    assert len(positions) == 1                 # 전원 같은 칸에서 출발
    assert model.mean_squared_displacement == 0.0


# --- 4단계 ---------------------------------------------------------------

def test_wealth_is_conserved():
    """어떤 seed에서도 총액은 절대 변하지 않는다 (가장 중요한 불변량)."""
    for seed in range(5):
        model = BoltzmannWealthModel(n_agents=120, size=12, seed=seed)
        start = model.total_wealth
        for _ in range(200):
            model.step()
            assert model.total_wealth == start


def test_wealth_never_negative():
    model = BoltzmannWealthModel(n_agents=100, size=10, seed=2)
    for _ in range(200):
        model.step()
    assert all(w >= 0 for w in model.wealth_list)


def test_inequality_emerges():
    """평등하게 출발했는데 불평등해져야 한다. 이 모형의 핵심 주장."""
    model = BoltzmannWealthModel(n_agents=200, size=15, seed=1)
    assert gini(model.wealth_list) == 0.0       # 출발은 완전 평등
    for _ in range(300):
        model.step()
    assert gini(model.wealth_list) > 0.5


def test_gini_matches_geometric_theory():
    """여러 번 돌린 평균이 이산 기하분포의 이론값 근처에 있어야 한다.

    유한 크기 효과로 이론값보다 조금 낮게 나오는 것이 정상이므로
    범위를 넉넉히 잡는다. 크게 벗어나면 모형이나 코드에 문제가 있는 것이다.
    """
    ginis = []
    for seed in range(6):
        model = BoltzmannWealthModel(n_agents=200, size=15, seed=seed)
        for _ in range(600):
            model.step()
        ginis.append(gini(model.wealth_list))
    mean_gini = sum(ginis) / len(ginis)
    theory = gini_geometric(1.0)               # 0.6667
    assert theory - 0.08 < mean_gini < theory + 0.05, mean_gini


def test_gini_formula_edge_cases():
    assert gini([5, 5, 5, 5]) == 0.0                       # 완전 평등
    assert gini([0, 0, 0, 0]) == 0.0                       # 전원 무일푼
    assert gini([0, 0, 0, 100]) > 0.7                      # 한 명이 독식
    assert math.isclose(gini_geometric(1.0), 2 / 3, rel_tol=1e-9)


# --- 5단계 ---------------------------------------------------------------

def test_segregation_emerges_from_tolerance():
    """관용도 0.3 인데 결과는 훨씬 심한 분리여야 한다. 이 모형의 핵심 주장."""
    model = SchellingModel(size=20, density=0.8, homophily=0.3, seed=42)
    start = model.mean_similar_fraction
    assert 0.4 < start < 0.6                    # 처음엔 무작위 = 0.5 근처
    for _ in range(100):
        model.step()
        if not model.running:
            break
    assert model.mean_similar_fraction > 0.7    # 요구한 0.3을 크게 넘어선다
    assert model.mean_similar_fraction > start


def test_model_stops_when_everyone_is_happy():
    model = SchellingModel(size=20, density=0.8, homophily=0.3, seed=0)
    for _ in range(200):
        model.step()
        if not model.running:
            break
    assert not model.running
    assert model.unhappy_count == 0


def test_zero_tolerance_means_nobody_moves():
    """관용도 0이면 전원이 처음부터 만족하므로 배치가 그대로여야 한다."""
    model = SchellingModel(size=15, density=0.8, homophily=0.0, seed=3)
    before = {a.unique_id: a.cell.coordinate for a in model.agents}
    model.step()
    after = {a.unique_id: a.cell.coordinate for a in model.agents}
    assert before == after
    assert not model.running


def test_extreme_tolerance_fails_to_converge():
    """관용도가 너무 높으면 아무도 만족할 수 없어 수렴하지 못한다.

    5단계 [실험 C]의 함정. 이때 분리 지표가 0.5로 내려가는데,
    이는 통합이 아니라 모형이 정상 상태에 도달하지 못한 것이다.
    """
    model = SchellingModel(size=20, density=0.8, homophily=0.875, seed=1)
    for _ in range(150):
        model.step()
        if not model.running:
            break
    assert model.running                        # 끝까지 멈추지 못한다
    assert model.unhappy_count > 0
    assert model.mean_similar_fraction < 0.65   # 지표는 오히려 낮다


def _main() -> int:
    """pytest 없이 실행할 때 쓰는 간이 러너."""
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    failed = []
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as exc:
            print(f"  FAIL  {name}  {exc}")
            failed.append(name)
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR {name}  {type(exc).__name__}: {exc}")
            failed.append(name)
    print(f"\n{len(tests) - len(failed)}/{len(tests)} 통과")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_main())
