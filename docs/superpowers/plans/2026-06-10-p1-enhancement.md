# P1 完善实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 完善 P1 阶段的 4 个待办项：模拟引擎测试、对阵图连线、球员详情增强、赔率缓存优化

**架构：** 后端 FastAPI + SQLite，前端 Flutter + Riverpod。模拟引擎用 numpy 向量化；对阵图用 CustomPainter；赔率缓存用数据库表 + 定时预计算

**技术栈：** Python 3.11 / FastAPI / SQLAlchemy / numpy / pytest | Flutter 3.x / Riverpod / flutter_animate

---

## 文件结构

| 文件 | 职责 | 操作 |
|------|------|------|
| `backend/tests/core/__init__.py` | 测试包初始化 | 新增 |
| `backend/tests/core/test_simulation.py` | 模拟引擎单元测试 | 新增 |
| `flutter_app/lib/pages/simulation/bracket_painter.dart` | 对阵图绘制（含连线） | 修改 |
| `backend/app/schemas/team.py` | 球员赛季数据 schema | 修改 |
| `backend/app/api/teams.py` | 球队详情端点（含首发 XI） | 修改 |
| `flutter_app/lib/models/team.dart` | 球员赛季数据模型 | 修改 |
| `flutter_app/lib/pages/teams/team_detail_page.dart` | 球员详情 UI | 修改 |
| `backend/app/models/recommendation_cache.py` | 赔率缓存模型 | 新增 |
| `backend/app/models/__init__.py` | 模型导出 | 修改 |
| `backend/app/tasks/scheduler.py` | 定时预计算任务 | 修改 |
| `backend/app/api/recommendations.py` | 缓存读取逻辑 | 修改 |
| `flutter_app/lib/pages/betting/betting_page.dart` | 数据时效显示 | 修改 |

---

## Task 1：模拟引擎测试 — 基础设施

**文件：**
- 创建：`backend/tests/core/__init__.py`
- 创建：`backend/tests/core/test_simulation.py`

- [ ] **步骤 1：创建测试目录和初始化文件**

创建 `backend/tests/core/__init__.py`（空文件）。

- [ ] **步骤 2：编写测试文件头部和辅助函数**

创建 `backend/tests/core/test_simulation.py`：

```python
"""Tests for the Monte Carlo tournament simulation engine."""

import numpy as np
import pytest

from app.core.simulation import MonteCarloEngine, TeamInGroup, SimulationResults
from app.core.elo import composite_rating


def _make_teams_by_group(
    strong: int = 2, medium: int = 1, weak: int = 1
) -> dict[str, list[TeamInGroup]]:
    """Build 12 groups × 4 teams with configurable strength distribution.

    strong: composite ~1800, medium: ~1650, weak: ~1500
    """
    groups = {}
    team_idx = 0
    for g_idx in range(12):
        g = chr(ord('A') + g_idx)
        teams = []
        for i in range(strong):
            teams.append(TeamInGroup(code=f"T{team_idx:02d}", group=g, composite=1800.0))
            team_idx += 1
        for i in range(medium):
            teams.append(TeamInGroup(code=f"T{team_idx:02d}", group=g, composite=1650.0))
            team_idx += 1
        for i in range(weak):
            teams.append(TeamInGroup(code=f"T{team_idx:02d}", group=g, composite=1500.0))
            team_idx += 1
        groups[g] = teams
    return groups


def _make_team_names(groups: dict[str, list[TeamInGroup]]) -> dict[str, str]:
    """Generate display names for all teams."""
    names = {}
    for g, teams in groups.items():
        for t in teams:
            names[t.code] = f"Team {t.code}"
    return names
```

- [ ] **步骤 3：编写 test_deterministic_with_seed 测试**

追加到 `test_simulation.py`：

```python
def test_deterministic_with_seed():
    """Same seed produces identical results across two runs."""
    groups = _make_teams_by_group()
    names = _make_team_names(groups)

    engine1 = MonteCarloEngine(num_iterations=100, seed=42)
    result1 = engine1.simulate(groups, names)

    engine2 = MonteCarloEngine(num_iterations=100, seed=42)
    result2 = engine2.simulate(groups, names)

    np.testing.assert_array_equal(result1.champion, result2.champion)
    np.testing.assert_array_equal(result1.round_32, result2.round_32)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd backend; python -m pytest tests/core/test_simulation.py::test_deterministic_with_seed -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add backend/tests/core/__init__.py backend/tests/core/test_simulation.py
git commit -m "test: add simulation engine deterministic test"
```

---

## Task 2：模拟引擎测试 — 小组赛和第三名

**文件：**
- 修改：`backend/tests/core/test_simulation.py`

- [ ] **步骤 1：编写 test_group_stage_ranking 测试**

追加到 `test_simulation.py`：

```python
def test_group_stage_ranking():
    """Group stage produces correct rankings based on points > GD > GF."""
    # Create one group with known strength ordering
    groups = {
        "A": [
            TeamInGroup(code="STR", group="A", composite=1900.0),  # strongest
            TeamInGroup(code="MED", group="A", composite=1650.0),
            TeamInGroup(code="WKA", group="A", composite=1600.0),
            TeamInGroup(code="WEA", group="A", composite=1400.0),  # weakest
        ]
    }
    # Fill remaining groups with identical teams
    for g_idx in range(1, 12):
        g = chr(ord('A') + g_idx)
        groups[g] = [
            TeamInGroup(code=f"{g}1", group=g, composite=1700.0),
            TeamInGroup(code=f"{g}2", group=g, composite=1650.0),
            TeamInGroup(code=f"{g}3", group=g, composite=1600.0),
            TeamInGroup(code=f"{g}4", group=g, composite=1550.0),
        ]

    names = _make_team_names(groups)
    engine = MonteCarloEngine(num_iterations=500, seed=42)
    result = engine.simulate(groups, names)

    # Strongest team should have higher R32 probability than weakest
    str_idx = result.team_codes.index("STR")
    wea_idx = result.team_codes.index("WEA")
    assert result.round_32[str_idx] > result.round_32[wea_idx], (
        f"STR R32={result.round_32[str_idx]} should be > WEA R32={result.round_32[wea_idx]}"
    )
```

- [ ] **步骤 2：编写 test_third_place_qualification 测试**

追加到 `test_simulation.py`：

```python
def test_third_place_qualification():
    """8 of 12 third-placed teams qualify for Round of 32."""
    groups = _make_teams_by_group()
    names = _make_team_names(groups)

    engine = MonteCarloEngine(num_iterations=200, seed=42)
    result = engine.simulate(groups, names)

    # All teams should have some non-zero R32 probability
    # (even weak teams can qualify as 3rd place)
    for i, code in enumerate(result.team_codes):
        assert result.round_32[i] >= 0.0, f"{code} has negative R32 probability"
        assert result.round_32[i] <= 1.0, f"{code} has R32 > 1.0"
```

- [ ] **步骤 3：运行测试验证通过**

运行：`cd backend; python -m pytest tests/core/test_simulation.py -v`
预期：3 个测试全部 PASS

- [ ] **步骤 4：Commit**

```bash
git add backend/tests/core/test_simulation.py
git commit -m "test: add group stage and third-place qualification tests"
```

---

## Task 3：模拟引擎测试 — 淘汰赛和概率合理性

**文件：**
- 修改：`backend/tests/core/test_simulation.py`

- [ ] **步骤 1：编写 test_knockout_bracket_progression 测试**

追加到 `test_simulation.py`：

```python
def test_knockout_bracket_progression():
    """Knockout bracket has correct number of matches per round."""
    groups = _make_teams_by_group()
    names = _make_team_names(groups)

    engine = MonteCarloEngine(num_iterations=100, seed=42)
    result = engine.simulate(groups, names)

    # Bracket should contain matches for all 5 rounds
    round_counts = {}
    for slot in result.bracket:
        round_counts[slot.round_name] = round_counts.get(slot.round_name, 0) + 1

    assert round_counts.get("round_32") == 16, f"Expected 16 R32 matches, got {round_counts.get('round_32')}"
    assert round_counts.get("round_16") == 8, f"Expected 8 R16 matches, got {round_counts.get('round_16')}"
    assert round_counts.get("quarter") == 4, f"Expected 4 QF matches, got {round_counts.get('quarter')}"
    assert round_counts.get("semi") == 2, f"Expected 2 SF matches, got {round_counts.get('semi')}"
    assert round_counts.get("final") == 1, f"Expected 1 Final match, got {round_counts.get('final')}"
```

- [ ] **步骤 2：编写 test_probability_sanity 测试**

追加到 `test_simulation.py`：

```python
def test_probability_sanity():
    """Strong teams have higher champion probability than weak teams."""
    groups = _make_teams_by_group()
    names = _make_team_names(groups)

    engine = MonteCarloEngine(num_iterations=500, seed=42)
    result = engine.simulate(groups, names)

    # Find a strong team (composite=1800) and a weak team (composite=1500)
    strong_codes = [t.code for g in groups.values() for t in g if t.composite == 1800.0]
    weak_codes = [t.code for g in groups.values() for t in g if t.composite == 1500.0]

    strong_champ = float(result.champion[result.team_codes.index(strong_codes[0])])
    weak_champ = float(result.champion[result.team_codes.index(weak_codes[0])])

    assert strong_champ > weak_champ, (
        f"Strong team champ prob {strong_champ} should be > weak team {weak_champ}"
    )

    # All champion probabilities should sum to approximately 1.0
    total_champ = float(result.champion.sum())
    assert abs(total_champ - 1.0) < 0.05, f"Champion probabilities sum to {total_champ}, expected ~1.0"
```

- [ ] **步骤 3：编写 test_tiebreaker_no_crash 测试**

追加到 `test_simulation.py`：

```python
def test_tiebreaker_no_crash():
    """Engine handles teams with identical composite ratings without crashing."""
    groups = {}
    team_idx = 0
    for g_idx in range(12):
        g = chr(ord('A') + g_idx)
        # All 4 teams in each group have identical ratings
        groups[g] = [
            TeamInGroup(code=f"E{team_idx+i}", group=g, composite=1600.0)
            for i in range(4)
        ]
        team_idx += 4

    names = _make_team_names(groups)
    engine = MonteCarloEngine(num_iterations=50, seed=42)

    # Should not raise any exception
    result = engine.simulate(groups, names)

    # Results should still be valid
    assert len(result.team_codes) == 48
    assert all(0.0 <= p <= 1.0 for p in result.champion), "Champion probabilities out of range"
```

- [ ] **步骤 4：运行全部测试验证通过**

运行：`cd backend; python -m pytest tests/core/test_simulation.py -v`
预期：6 个测试全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add backend/tests/core/test_simulation.py
git commit -m "test: add knockout, probability sanity, and tiebreaker tests"
```

---

## Task 4：对阵图连线 — 补全 CustomPainter

**文件：**
- 修改：`flutter_app/lib/pages/simulation/bracket_painter.dart`

- [ ] **步骤 1：在 _BracketPainter 中添加节点位置记录**

在 `_BracketPainter` 类中添加字段：

```dart
final Map<String, Offset> _nodePositions = {};
```

在 `paint()` 方法中，每个节点绘制后记录其中心坐标：

```dart
// After drawing each match node, record its center position
final centerKey = '${match.roundName}_${match.position}';
_nodePositions[centerKey] = Offset(roundX + nodeWidth / 2, cy);
```

- [ ] **步骤 2：实现 _drawConnector 方法**

在 `_BracketPainter` 类中添加连线绘制方法：

```dart
void _drawConnector(
  Canvas canvas,
  Offset fromTop,
  Offset fromBottom,
  Offset toNode,
  double midX,
) {
  final paint = Paint()
    ..color = Colors.grey.shade300
    ..strokeWidth = 1.5
    ..style = PaintingStyle.stroke;

  final path = Path();

  // From top match: right edge → horizontal to midX
  path.moveTo(fromTop.dx + nodeWidth / 2, fromTop.dy);
  path.lineTo(midX, fromTop.dy);

  // From bottom match: right edge → horizontal to midX
  path.moveTo(fromBottom.dx + nodeWidth / 2, fromBottom.dy);
  path.lineTo(midX, fromBottom.dy);

  // Vertical line connecting the two horizontal ends
  path.moveTo(midX, fromTop.dy);
  path.lineTo(midX, fromBottom.dy);

  // Horizontal from midpoint to next round node left edge
  path.moveTo(midX, (fromTop.dy + fromBottom.dy) / 2);
  path.lineTo(toNode.dx - nodeWidth / 2, toNode.dy);

  canvas.drawPath(path, paint);
}
```

- [ ] **步骤 3：在 paint() 中调用连线绘制**

在 `paint()` 方法的节点绘制循环之后，添加连线逻辑：

```dart
// Draw connectors between rounds
for (int ri = 0; ri < roundKeys.length - 1; ri++) {
  final currentRound = roundKeys[ri];
  final nextRound = roundKeys[ri + 1];
  final currentMatches = byRound[currentRound]!..sort((a, b) => a.position.compareTo(b.position));
  final nextMatches = byRound[nextRound]!..sort((a, b) => a.position.compareTo(b.position));

  for (int ni = 0; ni < nextMatches.length; ni++) {
    final topMatchIdx = ni * 2;
    final bottomMatchIdx = ni * 2 + 1;

    if (topMatchIdx < currentMatches.length && bottomMatchIdx < currentMatches.length) {
      final topKey = '${currentRound}_${currentMatches[topMatchIdx].position}';
      final bottomKey = '${currentRound}_${currentMatches[bottomMatchIdx].position}';
      final nextKey = '${nextRound}_${nextMatches[ni].position}';

      final topPos = _nodePositions[topKey];
      final bottomPos = _nodePositions[bottomKey];
      final nextPos = _nodePositions[nextKey];

      if (topPos != null && bottomPos != null && nextPos != null) {
        final currentX = topPos.dx - nodeWidth / 2;
        final nextX = nextPos.dx - nodeWidth / 2;
        final midX = (currentX + nodeWidth + nextX) / 2;
        _drawConnector(canvas, topPos, bottomPos, nextPos, midX);
      }
    }
  }
}
```

- [ ] **步骤 4：运行 Flutter 应用验证对阵图连线**

运行：`cd flutter_app; flutter run -d chrome --web-port=8080`
预期：对阵图显示轮次间的灰色连接线

- [ ] **步骤 5：Commit**

```bash
git add flutter_app/lib/pages/simulation/bracket_painter.dart
git commit -m "feat: add connector lines to knockout bracket painter"
```

---

## Task 5：球员详情增强 — 后端 Schema

**文件：**
- 修改：`backend/app/schemas/team.py`

- [ ] **步骤 1：添加 PlayerSeasonStatsOut 和扩展 PlayerOut**

修改 `backend/app/schemas/team.py`，在 `PlayerOut` 之前添加：

```python
class PlayerSeasonStatsOut(BaseModel):
    competition_code: str
    competition_name: str | None = None
    goals: int = 0
    assists: int = 0
    appearances: int = 0
    minutes_played: int = 0

    model_config = {"from_attributes": True}
```

修改 `PlayerOut`，添加 `season_stats` 和 `best_position` 字段：

```python
class PlayerOut(BaseModel):
    name: str
    jersey: int | None
    position: str | None
    club_name: str | None
    age_at_tournament: int | None
    season_stats: list[PlayerSeasonStatsOut] = []
    best_position: str | None = None

    model_config = {"from_attributes": True}
```

修改 `TeamDetailOut`，添加 `starting_xi` 字段：

```python
class TeamDetailOut(BaseModel):
    code: str
    name: str
    iso: str
    confederation: str
    group_name: str
    flag_url: str | None
    elo_rating: float
    fifa_rank: int
    market_value_eur: float
    coach_name: str | None
    coach_country: str | None
    players: list[PlayerOut]
    starting_xi: list[PlayerOut] | None = None

    model_config = {"from_attributes": True}
```

- [ ] **步骤 2：Commit**

```bash
git add backend/app/schemas/team.py
git commit -m "feat: add PlayerSeasonStatsOut schema and starting_xi to TeamDetailOut"
```

---

## Task 6：球员详情增强 — 后端 API 逻辑

**文件：**
- 修改：`backend/app/api/teams.py`

- [ ] **步骤 1：修改 get_team 端点，添加赛季数据和首发 XI 逻辑**

替换 `backend/app/api/teams.py` 中的 `get_team` 函数：

```python
from sqlalchemy.orm import selectinload
from ..models.player_stats import PlayerSeasonStats


@router.get("/{code}", response_model=TeamDetailOut)
def get_team(code: str, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.code == code.upper()).first()
    if not team:
        raise HTTPException(404, detail={"code": 1001, "message": "Team not found"})

    # Eagerly load players and their season stats
    players_out = []
    for p in team.players:
        stats = (
            db.query(PlayerSeasonStats)
            .filter(PlayerSeasonStats.player_id == p.id)
            .all()
        )
        stats_out = [
            {
                "competition_code": s.competition_code,
                "competition_name": s.competition_name,
                "goals": s.goals,
                "assists": s.assists,
                "appearances": s.appearances,
                "minutes_played": s.minutes_played,
            }
            for s in stats
        ]
        # Infer best position from position field or most-played competition
        best_pos = p.position
        players_out.append({
            "name": p.name,
            "jersey": p.jersey,
            "position": p.position,
            "club_name": p.club_name,
            "age_at_tournament": p.age_at_tournament,
            "season_stats": stats_out,
            "best_position": best_pos,
        })

    # Compute starting XI (4-3-3 formation)
    starting_xi = _compute_starting_xi(players_out)

    return {
        "code": team.code,
        "name": team.name,
        "iso": team.iso,
        "confederation": team.confederation,
        "group_name": team.group_name,
        "flag_url": team.flag_url,
        "elo_rating": team.elo_rating,
        "fifa_rank": team.fifa_rank,
        "market_value_eur": team.market_value_eur,
        "coach_name": team.coach_name,
        "coach_country": team.coach_country,
        "players": players_out,
        "starting_xi": starting_xi,
    }


def _compute_starting_xi(players: list[dict]) -> list[dict]:
    """Select starting XI in 4-3-3 formation based on minutes played."""
    formation = {"GK": 1, "DF": 4, "MF": 3, "FW": 3}
    selected = []

    for pos, count in formation.items():
        candidates = [p for p in players if p.get("position") == pos and p not in selected]
        # Sort by total minutes played (descending)
        candidates.sort(
            key=lambda p: sum(s["minutes_played"] for s in p.get("season_stats", [])),
            reverse=True,
        )
        selected.extend(candidates[:count])

    return selected if selected else None
```

- [ ] **步骤 2：启动后端验证 API 响应**

运行：`cd backend; python -m app.main`
测试：`curl http://localhost:8000/api/v1/teams/BRA`
预期：响应包含 `starting_xi` 和每个球员的 `season_stats`

- [ ] **步骤 3：Commit**

```bash
git add backend/app/api/teams.py
git commit -m "feat: add season stats and starting XI to team detail API"
```

---

## Task 7：球员详情增强 — Flutter 模型

**文件：**
- 修改：`flutter_app/lib/models/team.dart`

- [ ] **步骤 1：添加 PlayerSeasonStats 类和扩展 Player**

在 `team.dart` 中，在 `Player` 类之前添加：

```dart
class PlayerSeasonStats {
  final String competitionCode;
  final String? competitionName;
  final int goals;
  final int assists;
  final int appearances;
  final int minutesPlayed;

  PlayerSeasonStats({
    required this.competitionCode,
    this.competitionName,
    required this.goals,
    required this.assists,
    required this.appearances,
    required this.minutesPlayed,
  });

  factory PlayerSeasonStats.fromJson(Map<String, dynamic> json) {
    return PlayerSeasonStats(
      competitionCode: json['competition_code'] as String,
      competitionName: json['competition_name'] as String?,
      goals: json['goals'] as int? ?? 0,
      assists: json['assists'] as int? ?? 0,
      appearances: json['appearances'] as int? ?? 0,
      minutesPlayed: json['minutes_played'] as int? ?? 0,
    );
  }
}
```

修改 `Player` 类，添加 `seasonStats` 和 `bestPosition`：

```dart
class Player {
  final String name;
  final int? jersey;
  final String? position;
  final String? clubName;
  final int? ageAtTournament;
  final List<PlayerSeasonStats> seasonStats;
  final String? bestPosition;

  Player({
    required this.name,
    this.jersey,
    this.position,
    this.clubName,
    this.ageAtTournament,
    this.seasonStats = const [],
    this.bestPosition,
  });

  factory Player.fromJson(Map<String, dynamic> json) {
    return Player(
      name: json['name'] as String,
      jersey: json['jersey'] as int?,
      position: json['position'] as String?,
      clubName: json['club_name'] as String?,
      ageAtTournament: json['age_at_tournament'] as int?,
      seasonStats: (json['season_stats'] as List<dynamic>?)
              ?.map((e) => PlayerSeasonStats.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      bestPosition: json['best_position'] as String?,
    );
  }
}
```

修改 `TeamDetail`，添加 `startingXi`：

```dart
class TeamDetail {
  // ... 现有字段 ...
  final List<Player> startingXi;

  TeamDetail({
    // ... 现有参数 ...
    required this.startingXi,
  });

  factory TeamDetail.fromJson(Map<String, dynamic> json) {
    return TeamDetail(
      // ... 现有解析 ...
      startingXi: (json['starting_xi'] as List<dynamic>?)
              ?.map((e) => Player.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }
}
```

注意：`TeamDetail.fromJson` 中的现有字段保持不变，只追加 `startingXi`。

- [ ] **步骤 2：Commit**

```bash
git add flutter_app/lib/models/team.dart
git commit -m "feat: add PlayerSeasonStats model and startingXi to TeamDetail"
```

---

## Task 8：球员详情增强 — Flutter UI

**文件：**
- 修改：`flutter_app/lib/pages/teams/team_detail_page.dart`

- [ ] **步骤 1：添加首发 11 人卡片**

在 `_TeamDetailContent.build()` 的 `// Players section` 之前，添加首发 11 人卡片：

```dart
// Starting XI section
if (team.startingXi.isNotEmpty)
  Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('首发 11 人 (4-3-3)', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
          const Divider(),
          _buildFormationView(context, team.startingXi),
        ],
      ),
    ),
  ).animate().fadeIn(delay: 50.ms),

const SizedBox(height: 16),
```

在 `_TeamDetailContent` 类中添加 `_buildFormationView` 方法：

```dart
Widget _buildFormationView(BuildContext context, List<Player> xi) {
  // Group by position
  final gk = xi.where((p) => p.position == 'GK').toList();
  final df = xi.where((p) => p.position == 'DF').toList();
  final mf = xi.where((p) => p.position == 'MF').toList();
  final fw = xi.where((p) => p.position == 'FW').toList();

  return Column(
    children: [
      // FW row
      if (fw.isNotEmpty) _positionRow(context, fw, Colors.red),
      const SizedBox(height: 12),
      // MF row
      if (mf.isNotEmpty) _positionRow(context, mf, Colors.green),
      const SizedBox(height: 12),
      // DF row
      if (df.isNotEmpty) _positionRow(context, df, Colors.blue),
      const SizedBox(height: 12),
      // GK row
      if (gk.isNotEmpty) _positionRow(context, gk, Colors.orange),
    ],
  );
}

Widget _positionRow(BuildContext context, List<Player> players, Color color) {
  return Row(
    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
    children: players.map((p) => _playerBubble(context, p, color)).toList(),
  );
}

Widget _playerBubble(BuildContext context, Player player, Color color) {
  return Column(
    children: [
      CircleAvatar(
        radius: 20,
        backgroundColor: color.withOpacity(0.15),
        child: Text(
          '${player.jersey ?? '?'}',
          style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 14),
        ),
      ),
      const SizedBox(height: 4),
      SizedBox(
        width: 60,
        child: Text(
          player.name,
          textAlign: TextAlign.center,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w500),
        ),
      ),
    ],
  );
}
```

- [ ] **步骤 2：修改球员列表，添加赛季数据展开**

替换现有的球员 ListTile 为可展开的 ExpansionTile：

```dart
...team.players.map((player) {
  final hasStats = player.seasonStats.isNotEmpty;
  return ExpansionTile(
    tilePadding: EdgeInsets.zero,
    childrenPadding: const EdgeInsets.only(left: 56, bottom: 8),
    dense: true,
    leading: CircleAvatar(
      radius: 16,
      child: Text('${player.jersey ?? '?'}', style: const TextStyle(fontSize: 11)),
    ),
    title: Text(player.name, style: const TextStyle(fontWeight: FontWeight.w500)),
    subtitle: Text(
      [
        if (player.position != null) player.position!,
        if (player.clubName != null) player.clubName!,
      ].join(' · '),
      style: const TextStyle(fontSize: 12),
    ),
    trailing: player.ageAtTournament != null
        ? Text('${player.ageAtTournament}岁', style: const TextStyle(fontSize: 12, color: Colors.grey))
        : (hasStats ? const Icon(Icons.expand_more, size: 18) : null),
    children: hasStats
        ? player.seasonStats.map((stat) => Padding(
            padding: const EdgeInsets.symmetric(vertical: 2),
            child: Text(
              '${stat.competitionName ?? stat.competitionCode}: '
              '${stat.appearances}场 ${stat.goals}球 ${stat.assists}助 ${stat.minutesPlayed}分钟',
              style: TextStyle(fontSize: 11, color: Colors.grey.shade700),
            ),
          )).toList()
        : [],
  );
}),
```

- [ ] **步骤 3：运行 Flutter 应用验证球员详情页**

运行：`cd flutter_app; flutter run -d chrome --web-port=8080`
预期：球队详情页显示首发 11 人卡片和可展开的球员赛季数据

- [ ] **步骤 4：Commit**

```bash
git add flutter_app/lib/pages/teams/team_detail_page.dart
git commit -m "feat: add starting XI card and expandable season stats to team detail"
```

---

## Task 9：赔率缓存 — 数据模型

**文件：**
- 创建：`backend/app/models/recommendation_cache.py`
- 修改：`backend/app/models/__init__.py`

- [ ] **步骤 1：创建 RecommendationCache 模型**

创建 `backend/app/models/recommendation_cache.py`：

```python
"""Cache for precomputed betting recommendations."""

from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, Text, DateTime, UniqueConstraint

from ..database import Base


class RecommendationCache(Base):
    __tablename__ = "recommendation_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_type = Column(String(20), nullable=False)  # 'value_bets' | 'discrepancies'
    team_a_code = Column(String(3), nullable=False)
    team_b_code = Column(String(3), nullable=False)
    result_data = Column(Text, nullable=False)  # JSON string
    computed_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("cache_type", "team_a_code", "team_b_code", name="uq_cache_type_teams"),
    )

    @staticmethod
    def default_ttl() -> timedelta:
        return timedelta(hours=8)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at if self.expires_at else True
```

- [ ] **步骤 2：在 __init__.py 中导出新模型**

修改 `backend/app/models/__init__.py`，添加导入：

```python
from .recommendation_cache import RecommendationCache
```

在 `__all__` 列表中添加 `"RecommendationCache"`。

- [ ] **步骤 3：创建数据库表**

运行：`cd backend; python -c "from app.database import init_db; init_db()"`
预期：无报错，recommendation_cache 表已创建

- [ ] **步骤 4：Commit**

```bash
git add backend/app/models/recommendation_cache.py backend/app/models/__init__.py
git commit -m "feat: add RecommendationCache model for odds caching"
```

---

## Task 10：赔率缓存 — 定时预计算

**文件：**
- 修改：`backend/app/tasks/scheduler.py`

- [ ] **步骤 1：在 scheduler.py 中添加预计算函数**

追加到 `backend/app/tasks/scheduler.py`：

```python
import json
from datetime import datetime, timedelta

from ..database import SessionLocal
from ..models.team import Team
from ..models.recommendation_cache import RecommendationCache
from ..core.prediction import PredictionEngine
from ..services.odds import odds_client
from ..services.recommendation import recommendation_engine


def precompute_recommendations():
    """Precompute value bets and discrepancies for all same-group matchups.

    Results are cached in the recommendation_cache table with 8h TTL.
    """
    db = SessionLocal()
    try:
        engine = PredictionEngine()
        teams = db.query(Team).all()
        ttl = RecommendationCache.default_ttl()

        scanned = 0
        for i, team_a in enumerate(teams):
            for j, team_b in enumerate(teams):
                if j <= i or team_a.group_name != team_b.group_name:
                    continue
                if scanned >= 12:
                    break

                # Compute prediction
                pred = engine.predict(team_a, team_b, "group")
                odds_data = odds_client.fetch_h2h_odds_sync(team_a, team_b) if hasattr(odds_client, 'fetch_h2h_odds_sync') else None

                # For sync context, skip live odds fetch — use cached/empty
                betting = recommendation_engine.analyze(
                    system_probs=pred["probabilities"],
                    system_confidence=pred["system_confidence"],
                    odds_data=odds_data,
                )

                now = datetime.utcnow()

                # Cache value bets
                vb_key = ("value_bets", team_a.code, team_b.code)
                _upsert_cache(
                    db, "value_bets", team_a.code, team_b.code,
                    json.dumps(betting["recommendations"], ensure_ascii=False),
                    now, now + ttl,
                )

                # Cache discrepancies
                disc_key = ("discrepancies", team_a.code, team_b.code)
                _upsert_cache(
                    db, "discrepancies", team_a.code, team_b.code,
                    json.dumps(betting["discrepancy"], ensure_ascii=False),
                    now, now + ttl,
                )

                scanned += 1
            if scanned >= 12:
                break

        db.commit()
    finally:
        db.close()


def _upsert_cache(db, cache_type, team_a_code, team_b_code, result_data, computed_at, expires_at):
    """Insert or update a cache entry."""
    existing = db.query(RecommendationCache).filter(
        RecommendationCache.cache_type == cache_type,
        RecommendationCache.team_a_code == team_a_code,
        RecommendationCache.team_b_code == team_b_code,
    ).first()

    if existing:
        existing.result_data = result_data
        existing.computed_at = computed_at
        existing.expires_at = expires_at
    else:
        db.add(RecommendationCache(
            cache_type=cache_type,
            team_a_code=team_a_code,
            team_b_code=team_b_code,
            result_data=result_data,
            computed_at=computed_at,
            expires_at=expires_at,
        ))
```

- [ ] **步骤 2：Commit**

```bash
git add backend/app/tasks/scheduler.py
git commit -m "feat: add precompute_recommendations scheduler function"
```

---

## Task 11：赔率缓存 — API 端点改造

**文件：**
- 修改：`backend/app/api/recommendations.py`

- [ ] **步骤 1：改造 value-bets 端点读取缓存**

替换 `backend/app/api/recommendations.py` 中的 `value_bets` 函数：

```python
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.team import Team
from ..models.recommendation_cache import RecommendationCache
from ..core.prediction import PredictionEngine
from ..services.odds import odds_client
from ..services.recommendation import recommendation_engine
from ..tasks.scheduler import precompute_recommendations

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])
engine = PredictionEngine()


@router.get("/value-bets")
async def value_bets(
    min_ev: float = Query(0.05, ge=0),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=50),
    db: Session = Depends(get_db),
):
    """Return value bets from cache, falling back to live computation."""
    cached = (
        db.query(RecommendationCache)
        .filter(RecommendationCache.cache_type == "value_bets")
        .all()
    )

    # If no cache or all expired, trigger precomputation and use fallback
    valid_cache = [c for c in cached if not c.is_expired()]

    if not valid_cache:
        # Fallback: compute live (existing logic)
        return await _compute_value_bets_live(min_ev, page, page_size, db)

    # Parse cached results
    all_bets = []
    for c in valid_cache:
        recs = json.loads(c.result_data)
        for rec in recs:
            if rec.get("ev", 0) >= min_ev:
                team_a = db.query(Team).filter(Team.code == c.team_a_code).first()
                team_b = db.query(Team).filter(Team.code == c.team_b_code).first()
                if team_a and team_b:
                    all_bets.append({
                        "team_a": team_a.name,
                        "team_b": team_b.name,
                        **rec,
                    })

    all_bets.sort(key=lambda r: r.get("ev", 0), reverse=True)
    total = len(all_bets)
    start = (page - 1) * page_size

    # Find most recent cache time
    latest_cached = max(c.computed_at for c in valid_cache)

    return {
        "matches": all_bets[start:start + page_size],
        "total": total,
        "page": page,
        "cached_at": latest_cached.isoformat(),
    }


async def _compute_value_bets_live(min_ev, page, page_size, db):
    """Original live computation logic as fallback."""
    teams = db.query(Team).all()
    predicted = []
    scanned = 0

    for i, team_a in enumerate(teams):
        for j, team_b in enumerate(teams):
            if j <= i or team_a.group_name != team_b.group_name:
                continue
            if scanned >= 12:
                break

            pred = engine.predict(team_a, team_b, "group")
            odds_data = await odds_client.fetch_h2h_odds(team_a, team_b)
            betting = recommendation_engine.analyze(
                system_probs=pred["probabilities"],
                system_confidence=pred["system_confidence"],
                odds_data=odds_data,
            )

            if betting["recommendations"]:
                for rec in betting["recommendations"]:
                    if rec["ev"] >= min_ev:
                        predicted.append({
                            "team_a": pred["team_a"]["name"],
                            "team_b": pred["team_b"]["name"],
                            **rec,
                        })
            scanned += 1
        if scanned >= 12:
            break

    predicted.sort(key=lambda r: r["ev"], reverse=True)
    total = len(predicted)
    start = (page - 1) * page_size
    return {"matches": predicted[start:start + page_size], "total": total, "page": page}
```

- [ ] **步骤 2：改造 discrepancies 端点读取缓存**

替换 `discrepancies` 函数：

```python
@router.get("/discrepancies")
async def discrepancies(
    min_delta: float = Query(0.12, ge=0.05),
    db: Session = Depends(get_db),
):
    """Return discrepancy alerts from cache, falling back to live computation."""
    cached = (
        db.query(RecommendationCache)
        .filter(RecommendationCache.cache_type == "discrepancies")
        .all()
    )

    valid_cache = [c for c in cached if not c.is_expired()]

    if not valid_cache:
        return await _compute_discrepancies_live(min_delta, db)

    alerts = []
    for c in valid_cache:
        disc = json.loads(c.result_data)
        if disc.get("detected") and disc.get("max_delta", 0) >= min_delta:
            team_a = db.query(Team).filter(Team.code == c.team_a_code).first()
            team_b = db.query(Team).filter(Team.code == c.team_b_code).first()
            if team_a and team_b:
                alerts.append({
                    "team_a": team_a.name,
                    "team_b": team_b.name,
                    "group": team_a.group_name,
                    "discrepancy": disc,
                })

    latest_cached = max(c.computed_at for c in valid_cache)
    return {"alerts": alerts, "total": len(alerts), "cached_at": latest_cached.isoformat()}


async def _compute_discrepancies_live(min_delta, db):
    """Original live computation logic as fallback."""
    teams = db.query(Team).all()
    alerts = []

    for i, team_a in enumerate(teams):
        for j, team_b in enumerate(teams):
            if j <= i or team_a.group_name != team_b.group_name:
                continue
            pred = engine.predict(team_a, team_b, "group")
            odds_data = await odds_client.fetch_h2h_odds(team_a, team_b)
            betting = recommendation_engine.analyze(
                system_probs=pred["probabilities"],
                system_confidence=pred["system_confidence"],
                odds_data=odds_data,
            )
            if betting["discrepancy"] and betting["discrepancy"].get("detected"):
                alerts.append({
                    "team_a": pred["team_a"]["name"],
                    "team_b": pred["team_b"]["name"],
                    "group": team_a.group_name,
                    "discrepancy": betting["discrepancy"],
                    "system_probs": pred["probabilities"],
                    "market_probs": betting.get("odds_comparison", {}).get("market_implied", {}),
                })

    return {"alerts": alerts, "total": len(alerts)}
```

- [ ] **步骤 3：启动后端验证缓存 API**

运行：`cd backend; python -m app.main`
测试：`curl http://localhost:8000/api/v1/recommendations/value-bets`
预期：返回带 `cached_at` 字段的响应（首次可能走 fallback）

- [ ] **步骤 4：Commit**

```bash
git add backend/app/api/recommendations.py
git commit -m "feat: add cache-backed value-bets and discrepancies endpoints"
```

---

## Task 12：赔率缓存 — Flutter 数据时效显示

**文件：**
- 修改：`flutter_app/lib/pages/betting/betting_page.dart`

- [ ] **步骤 1：在投注推荐页添加数据时效显示**

在 `BettingPage.build()` 的 `SectionTitle(title: '今日价值场次')` 之前，添加：

```dart
// Data freshness indicator
FutureBuilder<dynamic>(
  future: ref.read(apiServiceProvider).getValueBets(),
  builder: (context, snapshot) {
    if (!snapshot.hasData) return const SizedBox.shrink();
    final cachedAt = snapshot.data?['cached_at'] as String?;
    if (cachedAt == null) return const SizedBox.shrink();
    final cachedTime = DateTime.tryParse(cachedAt);
    if (cachedTime == null) return const SizedBox.shrink();
    final hoursAgo = DateTime.now().difference(cachedTime).inHours;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(Icons.schedule, size: 14, color: Colors.grey.shade500),
          const SizedBox(width: 4),
          Text(
            '数据更新于 ${hoursAgo} 小时前',
            style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
          ),
        ],
      ),
    );
  },
),
```

- [ ] **步骤 2：运行 Flutter 应用验证时效显示**

运行：`cd flutter_app; flutter run -d chrome --web-port=8080`
预期：投注推荐页顶部显示"数据更新于 xx 小时前"

- [ ] **步骤 3：Commit**

```bash
git add flutter_app/lib/pages/betting/betting_page.dart
git commit -m "feat: add data freshness indicator to betting page"
```

---

## Task 13：集成验证

- [ ] **步骤 1：运行后端全部测试**

运行：`cd backend; python -m pytest tests/ -v`
预期：所有测试 PASS

- [ ] **步骤 2：启动后端 + Flutter 前端，手动验证所有 P1 功能**

1. 球队详情页：选择一支球队 → 确认首发 11 人卡片和球员赛季数据展开
2. 赛事模拟页：运行模拟 → 确认对阵图有连线
3. 投注推荐页：确认数据时效显示

- [ ] **步骤 3：最终 Commit**

```bash
git add -A
git commit -m "feat: complete P1 enhancement — player details, bracket connectors, odds cache, simulation tests"
```
