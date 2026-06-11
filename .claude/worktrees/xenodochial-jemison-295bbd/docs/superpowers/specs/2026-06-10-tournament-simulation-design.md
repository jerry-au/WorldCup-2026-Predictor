# 赛事蒙特卡洛模拟引擎 & 淘汰赛对阵图 — 实现设计

> 版本：v1.0 | 日期：2026-06-10 | 状态：设计待审

---

## 一、概述

实现 2026 世界杯完整赛事模拟，从小组赛到决赛的蒙特卡洛 10,000 次模拟，并在 Flutter 端展示晋级概率排行榜和淘汰赛对阵图。

## 二、后端模拟引擎

### 2.1 模块结构

```
backend/app/
├── core/
│   ├── elo.py                    # 已有
│   ├── poisson.py                # 已有
│   ├── prediction.py             # 已有
│   └── simulation.py             # 新增 — 蒙特卡洛模拟引擎
├── models/
│   ├── team.py                   # 已有
│   ├── simulation.py             # 新增 — SimulationRun, SimulationResult, KnockoutBracket
│   └── ...
├── api/
│   ├── predict.py                # 修改 — 新增 tournament 端点
│   └── ...
└── tasks/
    └── scheduler.py              # 已有
```

### 2.2 模拟引擎核心逻辑 (`core/simulation.py`)

```python
class MonteCarloEngine:
    """蒙特卡洛赛事模拟引擎"""

    GROUP_STAGE_MATCHES = [
        # 每组 6 场比赛索引 (0-3 为四支球队)
        (0, 1), (2, 3),  # 第 1 轮
        (0, 2), (1, 3),  # 第 2 轮
        (0, 3), (1, 2),  # 第 3 轮
    ]

    def __init__(self, num_iterations: int = 10000):
        ...

    def simulate(self, teams: list[Team]) -> SimulationResult:
        """主入口：执行完整赛事模拟"""

    def _simulate_group_stage(self, teams) -> np.ndarray:
        """小组赛阶段：每场用泊松抽样 → 积分排定名次"""

    def _simulate_knockout(self, bracket, prob_matrix) -> list[int]:
        """淘汰赛阶段：按对阵表推进，无平局（加时+点球）"""

    def _build_prob_matrix(self, teams: list[Team]) -> np.ndarray:
        """预计算所有球队对阵概率矩阵 (N×N×3)"""
```

### 2.3 关键实现细节

**小组赛模拟：**
- 每组 4 队，6 场比赛
- 每场比赛按混合泊松-Elo 模型抽样比分
- 积分规则：胜 3 平 1 负 0，同分先比净胜球再比进球数（进球数次之，直接交锋再次之）
- 每组前 2 名（共 24 队）直接晋级

**小组第三排名（8/12 晋级）：**
- 12 个小组第三按积分、净胜球、进球数排序
- 前 8 名晋级 32 强，后 4 名淘汰
- 这 8 队按预定槽位分配到对阵图中

**淘汰赛模拟：**
- 32 强对阵按官方预定规则：特定小组第一 vs 特定小组第二/第三
- 淘汰赛无平局：常规时间平局 → 加时赛（额外 Poisson λ × 0.3，30 分钟）→ 点球（50/50 概率）
- 逐轮推进至决赛

**对阵表槽位规则（简化 v1）：**
- 小组第一固定对阵另一组第二/第三
- 第三名晋级队的槽位按排名分配（如 3A→Slot X, 3B→Slot Y）
- v1 实现简化为最可能的 8 个第三名来源组合，不枚举所有 C(12,8) 种可能

**向量化性能策略：**
- 预计算 N×N 的 Poisson 比分概率矩阵（每组独立）
- 用 `numpy.random.choice` 批量抽样比分，而非逐场循环
- 10,000 次迭代总耗时预估 **1-2 秒**

### 2.4 数据表

```sql
CREATE TABLE simulation_runs (
    id TEXT PRIMARY KEY,            -- UUID
    status TEXT NOT NULL DEFAULT 'pending',  -- pending|running|completed|failed
    total_iterations INTEGER DEFAULT 10000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE simulation_results (
    run_id TEXT REFERENCES simulation_runs(id),
    team_code TEXT NOT NULL,
    round_32 REAL DEFAULT 0,    -- 晋级32强概率
    round_16 REAL DEFAULT 0,    -- 晋级16强概率
    quarter REAL DEFAULT 0,     -- 晋级8强概率
    semi REAL DEFAULT 0,        -- 晋级4强概率
    final REAL DEFAULT 0,       -- 晋级决赛概率
    champion REAL DEFAULT 0,    -- 夺冠概率
    PRIMARY KEY (run_id, team_code)
);

CREATE TABLE knockout_brackets (
    round_name TEXT NOT NULL,    -- round_32|round_16|quarter|semi|final
    position INTEGER NOT NULL,   -- 对阵位置 1-31
    group_winner TEXT,           -- 小组第一来源 (如 "A")
    group_runner TEXT,           -- 小组第二来源 (如 "B")
    PRIMARY KEY (round_name, position)
);
```

### 2.5 API

**POST /api/v1/predict/tournament**
- 触发后台模拟
- 返回 `{ "task_id": "uuid", "status": "running" }`

**GET /api/v1/predict/task/{task_id}**
- 轮询进度和结果
- running 时返回 `{ "status": "running", "progress": 0.45 }`
- completed 时返回 `{ "status": "completed", "progress": 1.0, "result": [...] }`
- result 包含 48 队的晋级概率和淘汰赛对阵详情

## 三、Flutter 前端

### 3.1 页面改造

**SimulationPage** — 从占位页改造为功能页：

| 区域 | 内容 |
|------|------|
| 顶部控制 | 运行按钮 / 进度条（LinearProgressIndicator） |
| 晋级概率排行榜 | 按夺冠概率降序，每行显示球队+各轮次概率条形图 |
| 淘汰赛对阵图 | InteractiveViewer + CustomPainter 绘制对阵连线 |

### 3.2 新增模型

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
}

class KnockoutMatch {
  final String roundName;
  final int position;
  final String? teamA;
  final String? teamB;
  final double? probA;  // teamA 晋级概率
  final double? probB;  // teamB 晋级概率
}
```

### 3.3 新 Provider

```dart
final simulationProvider = StateNotifierProvider<SimulationNotifier, SimulationState>(...);
```

轮询逻辑：启动后每 500ms 轮询 GET /task/{id}，completed 后停止并更新 UI。

### 3.4 对阵图绘制

- 使用 `InteractiveViewer` 包裹 `CustomPainter`，支持缩放平移
- 左到右排列 5 轮：32强 → 16强 → 8强 → 4强 → 决赛
- 每场比赛卡片标注队名和胜率
- 连线表示晋级路径

## 四、文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/core/simulation.py` | 新增 | 蒙特卡洛模拟引擎 |
| `backend/app/models/simulation.py` | 新增 | 模拟相关数据模型 |
| `backend/app/schemas/predict.py` | 修改 | 新增 TournamentRequest/Response |
| `backend/app/api/predict.py` | 修改 | 新增 tournament/task 端点 |
| `backend/app/main.py` | 修改 | 无变动（已有 predict router） |
| `flutter_app/lib/models/simulation.dart` | 新增 | TeamProbability, KnockoutMatch 模型 |
| `flutter_app/lib/providers/simulation_provider.dart` | 新增 | 模拟状态管理 + 轮询 |
| `flutter_app/lib/pages/simulation/simulation_page.dart` | 重写 | 从占位改功能页 |
| `flutter_app/lib/pages/simulation/bracket_painter.dart` | 新增 | CustomPainter 对阵图画布 |
| `flutter_app/lib/services/api_service.dart` | 修改 | 新增模拟 API 方法 |
| `flutter_app/lib/config/api_config.dart` | 确认 | 已有 endpoint 配置 |

## 五、实现顺序

1. `core/simulation.py` — 模拟引擎核心
2. `models/simulation.py` — 数据表
3. `api/predict.py` — tournament + task 端点
4. 测试验证后端 API
5. Flutter 模型 + Provider + API 对接
6. Flutter SimulationPage 重写 + BracketPainter
