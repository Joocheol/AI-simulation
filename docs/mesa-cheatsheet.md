# Mesa 3.x 치트시트

이 튜토리얼은 **mesa 3.3.1**에서 검증되었습니다.
아래 내용은 모두 실제로 실행해 확인한 것입니다.

> **가장 먼저 알아야 할 것**
> 인터넷의 Mesa 예제 상당수는 2.x 기준이고, 그 코드는 **3.x에서 실행되지 않습니다.**
> 아래 [2.x 자료를 볼 때](#2x-자료를-볼-때) 절을 먼저 읽으면 시간을 아낄 수 있습니다.

## 최소 뼈대

```python
import mesa

class MyAgent(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)        # model 하나만 넘긴다. unique_id는 자동
        self.state = 0

    def step(self):                    # 이 에이전트의 '한 번의 차례'
        self.state += self.random.randint(0, 1)

class MyModel(mesa.Model):
    def __init__(self, n=10, seed=None):
        super().__init__(seed=seed)    # seed는 여기 한 번만
        MyAgent.create_agents(self, n) # 만들기만 하면 self.agents 에 자동 등록
        self.datacollector = mesa.DataCollector(
            model_reporters={"total": lambda m: m.agents.agg("state", sum)},
            agent_reporters={"state": "state"},
        )

    def step(self):                    # 세계의 '1 스텝'
        self.agents.shuffle_do("step")
        self.datacollector.collect(self)

model = MyModel(n=100, seed=42)
for _ in range(50):
    model.step()

df = model.datacollector.get_model_vars_dataframe()   # pandas DataFrame
```

## Model

| 항목 | 설명 |
|:---|:---|
| `super().__init__(seed=...)` | seed 고정 = 실험 전체가 재현 가능해짐 |
| `self.agents` | 모든 에이전트를 담은 `AgentSet` |
| `self.agents_by_type[Cls]` | 특정 클래스만 |
| `self.steps` | 지금까지 진행된 스텝 수 (자동 증가) |
| `self.running` | `False`로 두면 `run_model()`과 `batch_run`이 멈춘다 |
| `self.random` | `random.Random` 인스턴스. 에이전트도 이것을 공유 |
| `self.rng` | numpy `Generator`. 벡터 연산이 필요할 때 |
| `self.run_model()` | `self.running`이 `False`가 될 때까지 `step()` 반복 |

## Agent

| 항목 | 설명 |
|:---|:---|
| `super().__init__(model)` | **model만** 넘긴다 (2.x와 다른 지점) |
| `self.unique_id` | 자동 부여 (1부터) |
| `self.model` | 소속 모형 |
| `self.random` | 모형의 난수 생성기 |
| `Cls.create_agents(model, n, **kw)` | n개를 한 번에 생성 |
| `self.remove()` | 모형에서 제거 |

## AgentSet — 스케줄러를 대체한 것

2.x의 `RandomActivation` 같은 스케줄러는 3.x에 **없습니다.**
대신 `AgentSet`에 직접 실행 순서를 지시합니다.

```python
self.agents.do("step")              # 생성 순서대로
self.agents.shuffle_do("step")      # 매번 순서를 섞어서  ← 보통 이것
self.agents.select(lambda a: a.wealth > 0).do("step")   # 조건부
self.agents.sort("wealth", ascending=False).do("step")  # 정렬 후

self.agents.get("wealth")           # 속성을 리스트로
self.agents.set("wealth", 0)        # 일괄 설정
self.agents.agg("wealth", sum)      # 집계 (sum, max, min, ...)
self.agents.groupby("kind")         # 그룹별로
len(self.agents)                    # 개수
```

**실행 순서는 결과를 바꿉니다.** 에이전트가 서로 영향을 주는 모형(4·5단계)에서
먼저 움직인 쪽이 유리하거나 불리해질 수 있으므로, 특별한 이유가 없으면
`shuffle_do`를 쓰는 것이 안전합니다.

## 공간 — `mesa.discrete_space` (권장)

```python
from mesa.discrete_space import OrthogonalMooreGrid, CellAgent

self.grid = OrthogonalMooreGrid(
    (width, height),
    torus=True,        # 경계가 반대편과 이어진다
    capacity=1,        # 한 칸에 몇 명까지 (None이면 무제한)
    random=self.random,
)
```

| 하는 일 | 코드 |
|:---|:---|
| 좌표로 칸 얻기 | `grid[(x, y)]` |
| 모든 칸 | `grid.all_cells.cells` |
| 빈 칸 하나 | `grid.select_random_empty_cell()` |
| 빈 칸 모음 | `grid.empties` |
| 칸의 좌표 | `cell.coordinate` |
| 칸 안의 에이전트 | `cell.agents` |
| 이웃 칸들 | `cell.neighborhood` |
| 이웃 칸의 에이전트 전부 | `cell.neighborhood.agents` |
| 이웃 중 하나 무작위 | `cell.neighborhood.select_random_cell()` |
| 에이전트 이동 | `agent.cell = 새로운_cell` (대입만 하면 됨) |

`CellAgent`를 상속하면 `self.cell`로 위치를 다룰 수 있습니다.
생성자에서 `cell`을 키워드로 넘길 수는 없으므로, `super().__init__(model)`
다음에 `self.cell = cell`로 직접 대입합니다.

격자 종류: `OrthogonalMooreGrid`(8방향), `OrthogonalVonNeumannGrid`(4방향),
`HexGrid`, `Network`, `VoronoiGrid`.

> 구식 API인 `mesa.space.MultiGrid` / `SingleGrid`도 3.3에서 아직 동작하며
> 경고도 뜨지 않습니다. 하지만 새 코드는 `discrete_space`를 쓰는 편이 좋습니다.

## DataCollector

```python
self.datacollector = mesa.DataCollector(
    model_reporters={
        "gini": lambda m: gini(m.wealth_list),   # 함수
        "n": "n_agents",                          # 속성 이름(문자열)도 가능
    },
    agent_reporters={"wealth": "wealth"},
    agenttype_reporters={MyAgent: {"x": "x"}},   # 특정 타입만
)

self.datacollector.collect(self)   # 기록할 시점에 직접 호출한다 (자동 아님)

model_df = self.datacollector.get_model_vars_dataframe()   # index = 스텝
agent_df = self.datacollector.get_agent_vars_dataframe()   # index = (Step, AgentID)
raw      = self.datacollector.model_vars["gini"]           # 그냥 리스트로
```

`collect()`를 `__init__` 끝에서 한 번 부르면 **0스텝(초기 상태)**도 남습니다.
전/후 비교를 하려면 이렇게 해 두는 편이 편합니다.

## batch_run — 파라미터 스윕

```python
results = mesa.batch_run(
    MyModel,
    parameters={
        "size": 20,                    # 고정값
        "homophily": [0.25, 0.5, 0.75] # 리스트면 모든 조합을 만든다
    },
    iterations=5,               # 조합마다 5회 (seed는 Mesa가 알아서 바꾼다)
    max_steps=200,
    data_collection_period=-1,  # -1이면 마지막 스텝만
    number_processes=1,         # None이면 가용 코어 전부
    display_progress=False,
)

import pandas as pd
df = pd.DataFrame(results)
df.groupby("homophily")["segregation"].agg(["mean", "std"])
```

`model.running = False`로 두면 `max_steps` 전에도 조기 종료합니다.

## 2.x 자료를 볼 때

옛 코드에서 아래를 보면 3.x용으로 바꿔야 합니다.

| 2.x 코드 | 3.x에서는 |
|:---|:---|
| `from mesa.time import RandomActivation` | **모듈 자체가 없음.** `self.agents.shuffle_do("step")` |
| `self.schedule = RandomActivation(self)` | 불필요. 에이전트는 자동 등록됨 |
| `self.schedule.add(agent)` | 불필요 |
| `self.schedule.step()` | `self.agents.shuffle_do("step")` |
| `self.schedule.steps` | `self.steps` |
| `self.schedule.agents` | `self.agents` |
| `def __init__(self, unique_id, model)` | `def __init__(self, model)` — unique_id 자동 |
| `super().__init__(unique_id, model)` | `super().__init__(model)` |
| `from mesa.time import SimultaneousActivation` | `self.agents.do("step")` 후 `self.agents.do("advance")` |

`mesa.time`, `mesa.visualization`, `mesa.flat`은 기본 설치에 존재하지 않습니다
(`ModuleNotFoundError`). 특히 **스케줄러를 쓰는 예제는 그대로 실행하면 반드시 실패합니다.**

웹 기반 대화형 시각화(SolaraViz)를 쓰려면 `pip install "mesa[viz]"`로 추가 설치가
필요합니다. 이 튜토리얼은 의존성을 늘리지 않으려고 터미널 출력만 사용합니다.

## 흔한 실수

- **`collect()`를 안 부른다** — DataCollector는 자동으로 기록하지 않습니다.
  `Model.step()` 안에서 직접 불러야 합니다.
- **`random` 모듈을 직접 쓴다** — `random.random()` 대신 `self.random.random()`.
  전자를 쓰면 seed를 고정해도 재현되지 않습니다.
- **에이전트를 순회하면서 제거한다** — `self.agents`를 직접 순회하며
  `remove()`하면 문제가 생길 수 있습니다. 먼저 리스트로 뽑아 두고 지우세요.
- **한 번 돌린 결과를 보고한다** — 확률적 모형입니다. 반복 실행하고
  평균과 표준편차로 말해야 합니다.
