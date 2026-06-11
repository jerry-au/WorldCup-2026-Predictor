# 赛事蒙特卡洛模拟引擎 & 淘汰赛对阵图 — 实现计划

2026-06-10

## Overview

实现 2026 世界杯赛事蒙特卡洛模拟引擎（后端）+ 晋级概率排行榜 + 淘汰赛对阵图（Flutter），采用轻量异步方案（BackgroundTasks），不引入 Celery/Redis。

## Tasks

### Task 1: 后端模拟引擎核心 — `core/simulation.py`

**Files to create:**
- `backend/app/core/simulation.py` — 蒙特卡洛模拟引擎

**Implementation details:**
The engine uses numpy vectorization to batch-sample match outcomes for all 10,000 iterations at once, rather than looping.

```python
"""
Monte Carlo tournament simulation engine.

2026 WC format: 12 groups × 4 teams → top 2 + 8 best 3rd-place → Round of 32 → knockout.
Uses numpy vectorization for performance (~1-2s for 10,000 iterations).
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

from .elo import composite_rating
from .poisson import expected_goals, match_probabilities


@dataclass
class TeamInGroup:
    """Team within its group context for simulation."""
    code: str
    group: str
    composite: float     # composite rating


@dataclass
class SimulationResults:
    team_codes: List[str]
    team_names: List[str]
    round_32: np.ndarray      # [n_teams]  float 0.0-1.0
    round_16: np.ndarray
    quarter: np.ndarray
    semi: np.ndarray
    final_: np.ndarray
    champion: np.ndarray


@dataclass
class Matchup:
    round_name: str   # round_32, round_16, quarter, semi, final
    position: int     # 1-31
    team_a_group_winner: str | None = None   # e.g. "A"
    team_a_group_runner: str | None = None   # e.g. "B"
    team_a_third_slot: int | None = None     # e.g. 1 (best 3rd)
    team_b_group_winner: str | None = None
    team_b_group_runner: str | None = None
    team_b_third_slot: int | None = None


class MonteCarloEngine:
    """Main simulation engine."""

    # Group stage: 6 matches per group (indices 0-3 are the 4 teams)
    GROUP_MATCHES = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]
    GROUP_NAMES = [chr(ord('A') + i) for i in range(12)]

    # Knockout bracket: 31 matches across 5 rounds
    # Round 32: matches 1-16, Round 16: matches 17-24, QF: 25-28, SF: 29-30, Final: 31
    KNOCKOUT_BRACKET: List[Matchup] = [...]  # See full definition in code

    def __init__(self, num_iterations: int = 10_000, seed: int = 42):
        self.N = num_iterations
        self.rng = np.random.default_rng(seed)

    def simulate(self, teams_by_group: Dict[str, List[TeamInGroup]],
                 team_names: Dict[str, str]) -> SimulationResults:
        """Run full tournament simulation."""
        ...

    def _simulate_group_stage(self, teams: List[TeamInGroup]) -> np.ndarray:
        """Simulate all group matches for all iterations.
        
        Returns: [N, 4] array where each row is (points, gd, gf) per team
        """
        ...

    def _simulate_knockout(self, ranked_teams: np.ndarray) -> np.ndarray:
        """Simulate the knockout bracket.
        
        ranked_teams: [N, 12, 4] — top-4-per-group ranking across all groups
        Returns: [N, 48] — furthest round reached per team per iteration
        """
        ...

    def _sample_match(self, comp_a: float, comp_b: float,
                      size: int) -> np.ndarray:
        """Sample match outcomes (0=loss, 1=draw, 2=win) for team A.
        
        Uses pre-computed Poisson probabilities.
        """
        ...
```

Key design for group stage:
- For each group, precompute expected goals for all 6 matchups
- Use numpy to sample scores for all N iterations at once: `np.random.poisson(lambda, size=N)`
- Compute points (3/1/0), goal difference, goals scored per team per iteration
- Sort to determine 1st-4th in each group

Key design for knockout:
- Precompute the per-matchup win probability (no draws allowed in knockout)
- For each matchup, sample winner via `np.random.choice([0,1], size=N, p=[p_win, 1-p_win])`
- Use precomputed bracket structure to advance winners
- For extra time: reduce λ by 30%, sample again if tied

**Testing approach:**
- Run engine with small N (100) and verify output shapes
- Check probabilities sum correctly
- Verify deterministic with fixed seed

**Dependencies:** None (first task)

---

### Task 2: 数据模型 — `models/simulation.py`

**Files to create:**
- `backend/app/models/simulation.py`

**Files to modify:**
- `backend/app/models/__init__.py` — add imports

**Implementation:**

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from ..database import Base


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, nullable=False, default="pending")  # pending|running|completed|failed
    total_iterations = Column(Integer, default=10000)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)


class SimulationResult(Base):
    __tablename__ = "simulation_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("simulation_runs.id"), nullable=False, index=True)
    team_code = Column(String(3), nullable=False)
    team_name = Column(String(100), nullable=False)
    round_32 = Column(Float, default=0.0)
    round_16 = Column(Float, default=0.0)
    quarter = Column(Float, default=0.0)
    semi = Column(Float, default=0.0)
    final_ = Column(Float, default=0.0)
    champion = Column(Float, default=0.0)


class KnockoutBracket(Base):
    __tablename__ = "knockout_brackets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("simulation_runs.id"), nullable=False, index=True)
    round_name = Column(String, nullable=False)
    position = Column(Integer, nullable=False)
    team_a_code = Column(String(3), nullable=True)
    team_b_code = Column(String(3), nullable=True)
    prob_a = Column(Float, nullable=True)   # team_a wins this match
    prob_b = Column(Float, nullable=True)
```

**Testing approach:**
- Verify tables are created by running `init_db()`
- Check model relationships

**Dependencies:** Task 1

---

### Task 3: API Schema — 新增请求/响应模型

**Files to modify:**
- `backend/app/schemas/predict.py` — 追加 TournamentRequest/Response

**Implementation:**

```python
class TournamentResponse(BaseModel):
    task_id: str
    status: str  # running


class TaskProgressResponse(BaseModel):
    status: str   # running / completed / failed
    progress: float = 0.0
    result: list | None = None  # populated when completed
    error: str | None = None


class TeamProbabilityOut(BaseModel):
    team_code: str
    team_name: str
    round_32: float
    round_16: float
    quarter: float
    semi: float
    final_: float
    champion: float


class KnockoutMatchOut(BaseModel):
    round_name: str
    position: int
    team_a: str | None
    team_b: str | None
    prob_a: float | None
    prob_b: float | None
```

**Dependencies:** Task 2

---

### Task 4: API 端点 — tournament + task

**Files to modify:**
- `backend/app/api/predict.py` — 新增 2 个端点
- `backend/app/main.py` — verify router is included (already is)

**Implementation:**

```python
import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi import BackgroundTasks

from ..core.simulation import MonteCarloEngine, TeamInGroup
from ..models.simulation import SimulationRun, SimulationResult, KnockoutBracket
from ..schemas.predict import TournamentResponse, TaskProgressResponse

# In-memory task registry for progress tracking
_task_registry: dict[str, dict] = {}

_executor = ThreadPoolExecutor(max_workers=1)


@router.post("/tournament", response_model=TournamentResponse)
async def start_tournament_simulation(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Start Monte Carlo tournament simulation."""
    # Create run record
    run = SimulationRun(status="running")
    db.add(run)
    db.commit()

    task_id = run.id
    _task_registry[task_id] = {"status": "running", "progress": 0.0}

    # Start simulation in background thread
    background_tasks.add_task(_run_simulation, task_id)

    return TournamentResponse(task_id=task_id, status="running")


def _run_simulation(task_id: str):
    """Run simulation in background thread."""
    db = next(get_db())
    try:
        run = db.query(SimulationRun).filter(SimulationRun.id == task_id).first()
        teams = db.query(Team).all()
        
        # Build input data
        groups = {}
        team_names = {}
        for t in teams:
            groups.setdefault(t.group_name, []).append(
                TeamInGroup(code=t.code, group=t.group_name,
                           composite=composite_rating(t.elo_rating, t.fifa_rank))
            )
            team_names[t.code] = t.name
        
        # Run simulation
        engine = MonteCarloEngine()
        results = engine.simulate(groups, team_names)
        
        # Save results
        for i, code in enumerate(results.team_codes):
            sr = SimulationResult(
                run_id=task_id,
                team_code=code,
                team_name=results.team_names[i],
                round_32=round(float(results.round_32[i]), 4),
                round_16=round(float(results.round_16[i]), 4),
                quarter=round(float(results.quarter[i]), 4),
                semi=round(float(results.semi[i]), 4),
                final_=round(float(results.final_[i]), 4),
                champion=round(float(results.champion[i]), 4),
            )
            db.add(sr)
        
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        db.commit()
        _task_registry[task_id] = {"status": "completed", "progress": 1.0}
    except Exception as e:
        run = db.query(SimulationRun).filter(SimulationRun.id == task_id).first()
        if run:
            run.status = "failed"
            run.error = str(e)
            db.commit()
        _task_registry[task_id] = {"status": "failed", "progress": 0.0, "error": str(e)}
    finally:
        db.close()


@router.get("/task/{task_id}", response_model=TaskProgressResponse)
def get_task_progress(task_id: str, db: Session = Depends(get_db)):
    """Poll simulation progress / fetch results."""
    task = _task_registry.get(task_id)
    if not task:
        raise HTTPException(404, detail={"code": 2001, "message": "Task not found"})
    
    if task["status"] == "running":
        return TaskProgressResponse(status="running", progress=task.get("progress", 0.0))
    
    if task["status"] == "failed":
        return TaskProgressResponse(status="failed", progress=0.0, error=task.get("error"))
    
    # Completed: fetch results from DB
    results = db.query(SimulationResult).filter(
        SimulationResult.run_id == task_id
    ).order_by(SimulationResult.champion.desc()).all()
    
    brackets = db.query(KnockoutBracket).filter(
        KnockoutBracket.run_id == task_id
    ).order_by(KnockoutBracket.position).all()
    
    return TaskProgressResponse(
        status="completed",
        progress=1.0,
        result={
            "standings": [
                {
                    "team_code": r.team_code,
                    "team_name": r.team_name,
                    "round_32": r.round_32,
                    "round_16": r.round_16,
                    "quarter": r.quarter,
                    "semi": r.semi,
                    "final_": r.final_,
                    "champion": r.champion,
                }
                for r in results
            ],
            "bracket": [
                {
                    "round_name": b.round_name,
                    "position": b.position,
                    "team_a": b.team_a_code,
                    "team_b": b.team_b_code,
                    "prob_a": b.prob_a,
                    "prob_b": b.prob_b,
                }
                for b in brackets
            ],
        }
    )
```

**Testing approach:**
- Start backend server
- `curl POST /api/v1/predict/tournament` → get task_id
- `curl GET /api/v1/predict/task/{task_id}` → wait for completed
- Verify results contain 48 teams with valid probabilities

**Dependencies:** Task 3

---

### Task 5: Flutter 模型 — `models/simulation.dart`

**Files to create:**
- `flutter_app/lib/models/simulation.dart`

**Implementation:**

```dart
class TeamProbability {
  final String teamCode;
  final String teamName;
  final double round32;
  final double round16;
  final double quarter;
  final double semi;
  final double final_;
  final double champion;

  TeamProbability({...});

  factory TeamProbability.fromJson(Map<String, dynamic> json) => TeamProbability(
    teamCode: json['team_code'] as String,
    teamName: json['team_name'] as String,
    round32: (json['round_32'] as num).toDouble(),
    round16: (json['round_16'] as num).toDouble(),
    quarter: (json['quarter'] as num).toDouble(),
    semi: (json['semi'] as num).toDouble(),
    final_: (json['final_'] as num).toDouble(),
    champion: (json['champion'] as num).toDouble(),
  );
}

class KnockoutMatch {
  final String roundName;
  final int position;
  final String? teamA;
  final String? teamB;
  final double? probA;
  final double? probB;
  ...
}

class SimulationResult {
  final List<TeamProbability> standings;
  final List<KnockoutMatch> bracket;
  ...
}
```

**Dependencies:** None (independent of other Flutter tasks)

---

### Task 6: Flutter Provider — `simulation_provider.dart`

**Files to create:**
- `flutter_app/lib/providers/simulation_provider.dart`

**Implementation:**

```dart
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/simulation.dart';
import '../services/providers.dart';

class SimulationState {
  bool isRunning;
  double progress;
  SimulationResult? result;
  String? error;
  
  SimulationState({...});
}

class SimulationNotifier extends StateNotifier<SimulationState> {
  SimulationNotifier(this._api) : super(SimulationState.initial());

  final ApiService _api;
  Timer? _pollTimer;

  Future<void> startSimulation() async {
    state = SimulationState(isRunning: true);
    try {
      final taskData = await _api.startTournamentSimulation();
      final taskId = taskData['task_id'] as String;
      _pollTask(taskId);
    } catch (e) {
      state = SimulationState(error: e.toString());
    }
  }

  void _pollTask(String taskId) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(milliseconds: 500), (_) async {
      try {
        final data = await _api.getTaskProgress(taskId);
        final status = data['status'] as String;
        final progress = (data['progress'] as num?)?.toDouble() ?? 0;
        
        if (status == 'completed') {
          _pollTimer?.cancel();
          final result = SimulationResult.fromJson(data['result'] as Map<String, dynamic>);
          state = SimulationState(isRunning: false, progress: 1.0, result: result);
        } else if (status == 'failed') {
          _pollTimer?.cancel();
          state = SimulationState(isRunning: false, error: data['error'] as String?);
        } else {
          state = SimulationState(isRunning: true, progress: progress);
        }
      } catch (e) {
        // Network error — keep polling
      }
    });
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}
```

**Dependencies:** Task 5

---

### Task 7: Flutter API Service — 新增模拟方法

**Files to modify:**
- `flutter_app/lib/services/api_service.dart`

Add methods to `ApiService`:

```dart
Future<dynamic> startTournamentSimulation() async {
  final resp = await _dio.post(
    ApiConfig.predictTournamentEndpoint,
    options: Options(
      sendTimeout: ApiConfig.normalTimeout,
      receiveTimeout: ApiConfig.normalTimeout,
    ),
  );
  return resp.data;
}

Future<dynamic> getTaskProgress(String taskId) async {
  final resp = await _dio.get(
    '${ApiConfig.predictTaskEndpoint}/$taskId',
  );
  return resp.data;
}
```

Note: `ApiConfig` already has `predictTournamentEndpoint` and `predictTaskEndpoint` defined.

**Dependencies:** None (independent)

---

### Task 8: Flutter 对阵图 CustomPainter — `bracket_painter.dart`

**Files to create:**
- `flutter_app/lib/pages/simulation/bracket_painter.dart`

**Implementation:**
CustomPainter that draws the knockout bracket:
- Horizontal layout: round_32 → round_16 → quarter → semi → final
- Each match node: small rounded rectangle with team code + probability
- Connector lines: vertical then horizontal to next round
- Use `InteractiveViewer` for zoom/pan
- Node colors: team name + green/red gradient probability indicator

```dart
class BracketPainter extends CustomPainter {
  final List<KnockoutMatch> matches;
  final Map<String, String> teamNames;
  
  // Layout constants
  static const double nodeWidth = 100;
  static const double nodeHeight = 40;
  static const double roundSpacing = 160;
  static const double matchSpacing = 50;
  ...
  
  @override
  void paint(Canvas canvas, Size size) {
    for (var match in matches) {
      // Draw team nodes + connector lines
    }
  }
}
```

**Dependencies:** Task 5 (KnockoutMatch model)

---

### Task 9: Flutter SimulationPage 重写

**Files to modify:**
- `flutter_app/lib/pages/simulation/simulation_page.dart` — 完整重写

**Page layout:**
```
Column
├── Card: Control (Run button / Progress bar)
├── if completed:
│   ├── Card: 晋级概率排行榜 (ListView of TeamProbability rows)
│   └── Card: InteractiveViewer + BracketPainter
```

Key widgets:
- **Ranking row**: team name, champion%, horizontal bar showing all rounds (colored segments)
- **Bracket**: InteractiveViewer wrapping CustomPaint

**Dependencies:** Task 6, Task 8

---

### Task 10: 集成测试与提交

**Actions:**
1. Start backend server and verify simulation API
2. Test with curl or Flutter web
3. Fix any issues
4. Commit all changes

**Dependencies:** All above tasks
