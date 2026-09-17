"""1단계: 순수 파이썬 몬테카를로 - 시뮬레이션의 최소 형태로 pi 구하기.

Mesa는 아직 쓰지 않는다. 시뮬레이션이라는 것이 결국 무엇인지를
표준 라이브러리만으로 드러내는 것이 이 단계의 목적이다.

[아이디어]
    한 변이 2인 정사각형 [-1, 1] x [-1, 1] 안에 반지름 1인 원이 들어 있다.
        정사각형 넓이 = 4
        원의 넓이     = pi * 1^2 = pi
    정사각형 안에 점을 고르게 뿌리면, 그 중 원 안에 떨어지는 점의 비율은
    넓이의 비율인 pi/4 에 수렴한다. 따라서

        pi ~= 4 * (원 안의 점 수) / (전체 점 수)

    적분을 풀지 않고, '해 보고 세어서' 답을 얻는다. 이것이 시뮬레이션이다.

[시뮬레이션의 4가지 부품]
    1) 상태(state)      : inside(원 안에 들어간 점의 개수), total(던진 점의 개수)
    2) 규칙(rule)       : 점 하나를 무작위로 뽑고, x^2 + y^2 <= 1 이면 inside += 1
    3) 반복(iteration)  : 규칙을 N번 되풀이한다
    4) 집계(aggregation): 4 * inside / total 로 관심 있는 값을 계산한다
    이 4가지는 앞으로 나올 모든 모형에서 그대로 반복된다.
    2단계에서 Mesa가 하는 일은 이 4가지에 '이름표를 붙여 주는 것'뿐이다.

실행:
    python3 steps/step01_pi_plain.py
"""

from __future__ import annotations

import math
import random


def estimate_pi(n_samples: int, seed: int | None = None) -> float:
    """점을 n_samples개 던져서 pi를 추정한다.

    seed를 고정하면 몇 번을 돌려도 완전히 같은 결과가 나온다.
    난수를 쓰는 실험이 '재현 가능한 실험'이 되는 지점이라 중요하다.
    """
    rng = random.Random(seed)  # 전역 random 대신 독립된 난수 생성기를 쓴다
    inside = 0

    for _ in range(n_samples):          # 3) 반복
        x = rng.uniform(-1.0, 1.0)      # 2) 규칙: 무작위로 점 하나
        y = rng.uniform(-1.0, 1.0)
        if x * x + y * y <= 1.0:        #    원 안인가?
            inside += 1                 # 1) 상태 갱신

    return 4.0 * inside / n_samples     # 4) 집계


def theoretical_stderr(n_samples: int) -> float:
    """추정값의 이론적 표준오차.

    '원 안인가?'는 성공확률 p = pi/4 인 베르누이 시행이다.
    비율의 표준오차는 sqrt(p(1-p)/N) 이고, 여기에 4를 곱한 것이
    pi 추정값의 표준오차가 된다.

        SE = 4 * sqrt(p(1-p)/N),  p = pi/4

    핵심은 N이 분모에서 제곱근으로 들어간다는 점이다.
    즉 오차를 1/10로 줄이려면 표본을 100배 늘려야 한다.
    몬테카를로가 느린 이유이자, 그 느림이 '수렴하지 않음'과는
    다르다는 것을 보여 주는 식이다.
    """
    p = math.pi / 4.0
    return 4.0 * math.sqrt(p * (1.0 - p) / n_samples)


def main() -> None:
    print("=" * 68)
    print("1단계 | 순수 파이썬 몬테카를로로 pi 추정하기")
    print("=" * 68)
    print(f"참값 pi = {math.pi:.6f}\n")

    # (1) 표본 수를 10배씩 늘려 가며 수렴을 관찰한다.
    print("[실험 A] 표본 수 N을 늘리면 오차는 어떻게 줄어드는가")
    print(f"{'N':>10} {'추정 pi':>12} {'실제 오차':>12} {'이론 SE':>12}")
    print("-" * 68)
    for exponent in range(2, 8):                 # N = 100 ... 10,000,000
        n = 10**exponent
        estimate = estimate_pi(n, seed=42)
        error = abs(estimate - math.pi)
        print(f"{n:>10,} {estimate:>12.6f} {error:>12.6f} {theoretical_stderr(n):>12.6f}")

    print("\n  => N이 100배 커질 때 오차는 대략 10분의 1이 된다 (1/sqrt(N) 법칙).")
    print("     '실제 오차'는 한 번의 실행에서 나온 값이라 이론 SE 주변에서 출렁인다.")

    # (2) 같은 N이라도 seed가 다르면 답이 다르다 = 확률적 모형의 본질.
    print("\n[실험 B] 같은 N(=10,000), seed만 바꿔 30번 반복")
    runs = [estimate_pi(10_000, seed=s) for s in range(30)]
    mean = sum(runs) / len(runs)
    variance = sum((r - mean) ** 2 for r in runs) / (len(runs) - 1)
    print(f"  최솟값 {min(runs):.4f} / 최댓값 {max(runs):.4f}")
    print(f"  30회 평균 {mean:.6f}  (참값 {math.pi:.6f})")
    print(f"  30회 표준편차 {math.sqrt(variance):.6f}  (이론 SE {theoretical_stderr(10_000):.6f})")
    print("\n  => 확률적 시뮬레이션의 결과는 '한 개의 숫자'가 아니라 '분포'다.")
    print("     따라서 단 한 번 돌린 결과로 결론을 내리면 안 된다.")
    print("     반복 실행 -> 평균과 산포로 보고. 5단계에서 다시 만난다.")

    # (3) 재현성.
    print("\n[실험 C] 재현성 확인")
    a = estimate_pi(50_000, seed=7)
    b = estimate_pi(50_000, seed=7)
    c = estimate_pi(50_000, seed=8)
    print(f"  seed=7 첫 번째: {a:.6f}")
    print(f"  seed=7 두 번째: {b:.6f}   <- 같은 seed면 항상 같다 ({a == b})")
    print(f"  seed=8        : {c:.6f}   <- seed가 다르면 다른 세계선")
    print("\n  => seed는 '이 실험을 남이 그대로 재연할 수 있는가'를 결정한다.")
    print("     논문/보고서에 반드시 기록해야 하는 값이다.")

    print("\n" + "=" * 68)
    print("정리: 시뮬레이션 = 상태 + 규칙 + 반복 + 집계")
    print("다음 단계에서 똑같은 계산을 Mesa로 다시 쓴다.")
    print("=" * 68)


if __name__ == "__main__":
    main()
