# P1 完善设计 — 球员详情增强、对阵图连线、赔率缓存、模拟测试

> 版本：v1.0 | 日期：2026-06-10 | 状态：设计已审

***

## 一、概述

P1 阶段（赛事蒙特卡洛模拟引擎 + 淘汰赛对阵图 + 球员详情页 + 赔率偏差检测）的主体功能已实现，但存在 4 个待完善项。本文档定义这 4 项的具体实现方案。

***

## 二、模块 1：球员详情页增强

### 2.1 现状

* 后端 `PlayerSeasonStats` 模型已存在（goals/assists/appearances/minutes\_played/competition\_code）

* `football_data_fetcher.py` 已有抓取逻辑

* 但 `PlayerOut` schema 不包含赛季数据

* Flutter 球员展示只有姓名/号码/位置/俱乐部/年龄

### 2.2 后端改动

**Schema 扩展** — `schemas/team.py`：

```python
class PlayerSeasonStatsOut(BaseModel):
    competition_code: str
    competition_name: str | None
    goals: int = 0
    assists: int = 0
    appearances: int = 0
    minutes_played: int = 0

    model_config = {"from_attributes": True}

class PlayerOut(BaseModel):
    name: str
    jersey: int | None
    position: str | None
    club_name: str | None
    age_at_tournament: int | None
    season_stats: list[PlayerSeasonStatsOut] = []
    best_position: str | None = None   # 推断的首发位置

    model_config = {"from_attributes": True}
```

**首发 11 人预估逻辑** — 在 `api/teams.py` 的 `get_team` 中：

* 按位置分组：GK×1, DF×4, MF×3, FW×3

* 每组取赛季出场时间（minutes\_played 总和）最多的球员

* `best_position` 字段：取该球员出场最多的位置（如无 position 则按赛季数据推断）

* 不足 11 人时按实际人数返回

**API 响应扩展** — `TeamDetailOut` 新增字段：

```python
class TeamDetailOut(BaseModel):
    # ... 现有字段 ...
    starting_xi: list[PlayerOut] | None = None   # 首发 11 人预估
```

### 2.3 Flutter 改动

**模型扩展** — `models/team.dart`：

```dart
class PlayerSeasonStats {
  final String competitionCode;
  final String? competitionName;
  final int goals;
  final int assists;
  final int appearances;
  final int minutesPlayed;
}

class Player {
  // ... 现有字段 ...
  final List<PlayerSeasonStats> seasonStats;
  final String? bestPosition;
}
```

**UI 改动** — `team_detail_page.dart`：

1. 新增"首发 11 人"卡片：按 4-3-3 阵型排列，每人显示姓名+位置+俱乐部
2. 球员列表每行增加可展开区域，展示赛季数据（联赛/进球/助攻/出场/分钟）
3. 球员按位置分组显示（门将/后卫/中场/前锋）

***

## 三、模块 2：对阵图连线完善

### 3.1 现状

`bracket_painter.dart` 只画了节点（球队名+概率矩形），没有轮次间的连接线。

### 3.2 连线逻辑

**连接规则**：相邻轮次的两场比赛胜者汇聚到下一轮的一场比赛。

* R32 match 0 + match 1 → R16 match 0

* R32 match 2 + match 3 → R16 match 1

* R16 match 0 + match 1 → QF match 0

* 以此类推

**连线样式**：三段式

1. 从当前节点右侧中点水平延伸到中间位置
2. 垂直线连接两场比赛到下一轮节点的高度
3. 水平线延伸到下一轮节点左侧中点

**视觉参数**：

* 颜色：`Colors.grey.shade300`

* 宽度：1.5

* 节点间距：保持现有 `roundSpacing`

### 3.3 实现要点

在 `_BracketPainter.paint()` 中：

1. 先绘制所有节点（保持现有逻辑）
2. 记录每个节点的中心坐标到 `_nodePositions` map（key: `roundName_position`）
3. 遍历轮次，对每对相邻比赛画连线到下一轮

需要新增 `_drawConnector()` 方法处理三段式连线绘制。

***

## 四、模块 3：赔率偏差检测优化

### 4.1 现状

* `/recommendations/value-bets` 和 `/discrepancies` 每次请求实时计算

* 扫描 12 组同组对阵，每次调用 PredictionEngine + OddsClient

* 慢（数秒）且浪费 Odds API 配额（500 次/月）

### 4.2 缓存方案

**新增数据表** — `recommendation_cache`：

```sql
CREATE TABLE recommendation_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_type TEXT NOT NULL,          -- 'value_bets' | 'discrepancies'
    team_a_code TEXT NOT NULL,
    team_b_code TEXT NOT NULL,
    result_data TEXT NOT NULL,         -- JSON
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    UNIQUE(cache_type, team_a_code, team_b_code)
);
```

**定时预计算** — 在 `tasks/scheduler.py` 中新增：

* 每 8 小时执行一次 `_precompute_recommendations()`

* 遍历所有同组对阵，计算 value bets 和 discrepancies

* 结果写入 `recommendation_cache` 表

* TTL = 8 小时

**API 端点改造**：

* `/recommendations/value-bets`：从缓存读取，按 EV 排序返回

* `/recommendations/discrepancies`：从缓存读取

* 如果缓存为空或全部过期，触发一次同步计算（降级为现有逻辑）

* 响应新增 `cached_at` 字段

**Flutter 改动**：

* 投注推荐页显示数据时效："数据更新于 xx 小时前"

* 手动刷新按钮触发 `POST /api/v1/data/refresh`（已有端点）

***

## 五、模块 4：模拟引擎测试覆盖

### 5.1 测试文件

新增 `backend/tests/core/test_simulation.py`

### 5.2 测试用例

| # | 名称                                   | 验证内容                            |
| - | ------------------------------------ | ------------------------------- |
| 1 | test\_group\_stage\_ranking          | 4 队已知比分 → 积分/净胜球/排名正确           |
| 2 | test\_third\_place\_qualification    | 12 组第三名 → 前 8 名按规则选出            |
| 3 | test\_knockout\_bracket\_progression | 固定种子 → R32/R16/QF/SF/Final 对阵正确 |
| 4 | test\_deterministic\_with\_seed      | 相同 seed 两次运行结果完全一致              |
| 5 | test\_probability\_sanity            | 强队夺冠概率 > 弱队；所有队概率之和合理           |
| 6 | test\_tiebreaker\_no\_crash          | 2 队同分同净胜球时不崩溃                   |

### 5.3 测试数据

* 使用小规模模拟（N=100）加速测试

* 构造 12 组 × 4 队的 `TeamInGroup` 测试数据

* 强队 composite=1800，弱队 composite=1500，中等队 composite=1650

***

## 六、文件变更清单

| 文件                                                      | 操作 | 模块      |
| ------------------------------------------------------- | -- | ------- |
| `backend/app/schemas/team.py`                           | 修改 | 1-球员详情  |
| `backend/app/api/teams.py`                              | 修改 | 1-球员详情  |
| `flutter_app/lib/models/team.dart`                      | 修改 | 1-球员详情  |
| `flutter_app/lib/pages/teams/team_detail_page.dart`     | 修改 | 1-球员详情  |
| `flutter_app/lib/pages/simulation/bracket_painter.dart` | 修改 | 2-对阵图连线 |
| `backend/app/models/recommendation_cache.py`            | 新增 | 3-赔率缓存  |
| `backend/app/models/__init__.py`                        | 修改 | 3-赔率缓存  |
| `backend/app/tasks/scheduler.py`                        | 修改 | 3-赔率缓存  |
| `backend/app/api/recommendations.py`                    | 修改 | 3-赔率缓存  |
| `flutter_app/lib/pages/betting/betting_page.dart`       | 修改 | 3-赔率缓存  |
| `backend/tests/core/__init__.py`                        | 新增 | 4-模拟测试  |
| `backend/tests/core/test_simulation.py`                 | 新增 | 4-模拟测试  |

***

## 七、实现顺序

1. 模块 4：模拟引擎测试（无依赖，先验证核心逻辑正确性）
2. 模块 2：对阵图连线（纯前端，独立）
3. 模块 1：球员详情增强（后端 + 前端）
4. 模块 3：赔率缓存（依赖推荐引擎稳定运行）

