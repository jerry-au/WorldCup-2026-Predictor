# 当日赛事与对战预测入口迁移实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 新增「当日赛事」页面与后端聚合接口，并将「对战预测」入口从底部导航迁移到「赛事模拟」页面内。

**架构：** 后端新增 `/api/v1/matches/today`，一次聚合赛程、预测概率与赔率摘要，避免前端 N+1 请求。前端新增 `TodayMatch` 模型、Riverpod Provider 和页面，底部导航首项改为「当日赛事」，现有 `PredictionPage` 支持预填主客队并自动展示预测。

**技术栈：** Python FastAPI、SQLAlchemy、pytest、Flutter、Riverpod、Dio、Material 3、flutter_animate。

---

## 文件结构

### 后端

- 创建：`backend/app/services/match_aggregator.py`
  - 职责：查询当日比赛，聚合球队、预测和赔率数据，返回 API 可序列化结构。
- 创建：`backend/app/api/matches.py`
  - 职责：暴露 `/api/v1/matches/today` 路由。
- 修改：`backend/app/main.py`
  - 职责：注册 `matches.router`。
- 创建：`backend/tests/services/test_match_aggregator.py`
  - 职责：覆盖当日无比赛、有比赛、缺失赔率场景。

### 前端

- 创建：`flutter_app/lib/models/today_match.dart`
  - 职责：解析后端当日赛事响应。
- 创建：`flutter_app/lib/providers/today_matches_provider.dart`
  - 职责：拉取当日赛事数据并在 Riverpod 层提供短 TTL 缓存。
- 创建：`flutter_app/lib/pages/today_matches/today_matches_page.dart`
  - 职责：卡片式展示当日比赛，处理跳转、刷新、加载、错误、空状态。
- 修改：`flutter_app/lib/config/api_config.dart`
  - 职责：新增当日赛事接口路径常量。
- 修改：`flutter_app/lib/services/api_service.dart`
  - 职责：新增 `getTodayMatches()` 方法。
- 修改：`flutter_app/lib/pages/prediction/prediction_page.dart`
  - 职责：支持 `initialTeamA`、`initialTeamB`、`initialMatchType` 参数。
- 修改：`flutter_app/lib/pages/simulation/simulation_page.dart`
  - 职责：新增「对战预测」功能卡片入口。
- 修改：`flutter_app/lib/pages/home_page.dart`
  - 职责：底部导航首项替换为「当日赛事」。

---

## 任务 1：后端聚合服务

**文件：**
- 创建：`backend/app/services/match_aggregator.py`
- 测试：`backend/tests/services/test_match_aggregator.py`

- [ ] **步骤 1：编写失败的服务测试**

在 `backend/tests/services/test_match_aggregator.py` 写入以下测试。测试通过 monkeypatch 隔离数据库，验证聚合函数的输出结构。

```python
from datetime import date, datetime
from types import SimpleNamespace

from app.services.match_aggregator import build_today_matches_response


def test_build_today_matches_response_empty(monkeypatch):
    monkeypatch.setattr("app.services.match_aggregator._query_matches_for_date", lambda db, target_date: [])

    response = build_today_matches_response(db=object(), target_date=date(2026, 6, 11))

    assert response["matches"] == []
    assert response["total"] == 0
    assert response["cache"]["ttl_seconds"] == 300


def test_build_today_matches_response_with_prediction_and_odds(monkeypatch):
    match = SimpleNamespace(
        match_id="BRA-FRA-2026-06-11",
        stage="group_stage",
        group_name="E",
        team_home_code="BRA",
        team_away_code="FRA",
        team_home_name="Brazil",
        team_away_name="France",
        commence_time=datetime(2026, 6, 11, 20, 0),
        fetched_at=datetime(2026, 6, 11, 10, 0),
    )
    team_a = SimpleNamespace(code="BRA", name="Brazil")
    team_b = SimpleNamespace(code="FRA", name="France")
    odds = SimpleNamespace(
        avg_odds_win=2.1,
        avg_odds_draw=3.4,
        avg_odds_lose=2.9,
        best_odds_win=2.2,
        best_odds_draw=3.5,
        best_odds_lose=3.0,
        best_win_provider="Book A",
        best_draw_provider="Book B",
        best_lose_provider="Book C",
        provider_count=3,
        updated_at=datetime(2026, 6, 11, 9, 0),
    )

    class FakeQuery:
        def __init__(self, value):
            self.value = value
        def filter(self, *args):
            return self
        def first(self):
            return self.value

    class FakeDb:
        def query(self, model):
            name = model.__name__
            if name == "Team":
                return FakeQuery(team_a if getattr(self, "team_calls", 0) == 0 else team_b)
            if name == "MatchOddsSummary":
                return FakeQuery(odds)
            return FakeQuery(None)

    fake_db = FakeDb()
    original_query = fake_db.query
    calls = {"team": 0}
    def query(model):
        if model.__name__ == "Team":
            value = team_a if calls["team"] == 0 else team_b
            calls["team"] += 1
            return FakeQuery(value)
        return original_query(model)
    fake_db.query = query

    monkeypatch.setattr("app.services.match_aggregator._query_matches_for_date", lambda db, target_date: [match])
    monkeypatch.setattr(
        "app.services.match_aggregator.engine.predict",
        lambda a, b, match_type: {
            "probabilities": {"win": 0.42, "draw": 0.28, "lose": 0.30},
            "system_confidence": 0.75,
        },
    )

    response = build_today_matches_response(db=fake_db, target_date=date(2026, 6, 11))

    assert response["total"] == 1
    item = response["matches"][0]
    assert item["match_id"] == "BRA-FRA-2026-06-11"
    assert item["home"]["code"] == "BRA"
    assert item["away"]["code"] == "FRA"
    assert item["prediction"]["win"] == 0.42
    assert item["odds"]["avg_win"] == 2.1
    assert item["odds"]["provider_count"] == 3
```

- [ ] **步骤 2：运行测试验证失败**

运行：

```powershell
cd backend; python -m pytest tests/services/test_match_aggregator.py -v
```

预期：FAIL，报错包含 `ModuleNotFoundError: No module named 'app.services.match_aggregator'`。

- [ ] **步骤 3：实现聚合服务**

创建 `backend/app/services/match_aggregator.py`：

```python
from datetime import date, datetime, time

from sqlalchemy.orm import Session

from ..core.prediction import PredictionEngine
from ..models.odds_data import MatchOddsSummary
from ..models.team import Team
from ..models.zafronix_data import ZafronixMatch

engine = PredictionEngine()
CACHE_TTL_SECONDS = 300


def build_today_matches_response(db: Session, target_date: date | None = None) -> dict:
    if target_date is None:
        target_date = date.today()

    matches = _query_matches_for_date(db, target_date)
    items = [_build_match_item(db, match) for match in matches]
    updated_candidates = [match.fetched_at for match in matches if getattr(match, "fetched_at", None)]

    return {
        "matches": items,
        "total": len(items),
        "cache": {
            "updated_at": max(updated_candidates).isoformat() if updated_candidates else datetime.utcnow().isoformat(),
            "ttl_seconds": CACHE_TTL_SECONDS,
        },
    }


def _query_matches_for_date(db: Session, target_date: date) -> list[ZafronixMatch]:
    start = datetime.combine(target_date, time.min)
    end = datetime.combine(target_date, time.max)
    return (
        db.query(ZafronixMatch)
        .filter(ZafronixMatch.commence_time >= start)
        .filter(ZafronixMatch.commence_time <= end)
        .order_by(ZafronixMatch.commence_time.asc())
        .all()
    )


def _build_match_item(db: Session, match: ZafronixMatch) -> dict:
    team_a = db.query(Team).filter(Team.code == match.team_home_code).first()
    team_b = db.query(Team).filter(Team.code == match.team_away_code).first()

    prediction = None
    if team_a and team_b:
        pred = engine.predict(team_a, team_b, _normalize_match_type(match.stage))
        probs = pred["probabilities"]
        prediction = {
            "win": probs["win"],
            "draw": probs["draw"],
            "lose": probs["lose"],
            "system_confidence": pred["system_confidence"],
        }

    odds = _get_odds_summary(db, match.team_home_code, match.team_away_code)

    return {
        "match_id": match.match_id,
        "home": {
            "code": match.team_home_code,
            "name": match.team_home_name,
        },
        "away": {
            "code": match.team_away_code,
            "name": match.team_away_name,
        },
        "stage": match.stage,
        "group_name": match.group_name,
        "commence_time": match.commence_time.isoformat() if match.commence_time else None,
        "prediction": prediction,
        "odds": odds,
    }


def _normalize_match_type(stage: str | None) -> str:
    return "group" if not stage or "group" in stage else "knockout"


def _get_odds_summary(db: Session, team_a_code: str | None, team_b_code: str | None) -> dict | None:
    if not team_a_code or not team_b_code:
        return None

    summary = (
        db.query(MatchOddsSummary)
        .filter(MatchOddsSummary.team_a_code == team_a_code)
        .filter(MatchOddsSummary.team_b_code == team_b_code)
        .first()
    )
    if not summary:
        summary = (
            db.query(MatchOddsSummary)
            .filter(MatchOddsSummary.team_a_code == team_b_code)
            .filter(MatchOddsSummary.team_b_code == team_a_code)
            .first()
        )
        if not summary:
            return None
        return _reverse_odds(summary)

    return _forward_odds(summary)


def _forward_odds(summary: MatchOddsSummary) -> dict:
    return {
        "avg_win": summary.avg_odds_win,
        "avg_draw": summary.avg_odds_draw,
        "avg_lose": summary.avg_odds_lose,
        "best_win": summary.best_odds_win,
        "best_draw": summary.best_odds_draw,
        "best_lose": summary.best_odds_lose,
        "best_win_provider": summary.best_win_provider,
        "best_draw_provider": summary.best_draw_provider,
        "best_lose_provider": summary.best_lose_provider,
        "provider_count": summary.provider_count,
        "updated_at": summary.updated_at.isoformat() if summary.updated_at else None,
    }


def _reverse_odds(summary: MatchOddsSummary) -> dict:
    return {
        "avg_win": summary.avg_odds_lose,
        "avg_draw": summary.avg_odds_draw,
        "avg_lose": summary.avg_odds_win,
        "best_win": summary.best_odds_lose,
        "best_draw": summary.best_odds_draw,
        "best_lose": summary.best_odds_win,
        "best_win_provider": summary.best_lose_provider,
        "best_draw_provider": summary.best_draw_provider,
        "best_lose_provider": summary.best_win_provider,
        "provider_count": summary.provider_count,
        "updated_at": summary.updated_at.isoformat() if summary.updated_at else None,
    }
```

- [ ] **步骤 4：运行服务测试验证通过**

运行：

```powershell
cd backend; python -m pytest tests/services/test_match_aggregator.py -v
```

预期：PASS。

- [ ] **步骤 5：检查点**

仅在用户明确授权提交时运行：

```powershell
git add backend/app/services/match_aggregator.py backend/tests/services/test_match_aggregator.py; git commit -m "feat: add today matches aggregator"
```

---

## 任务 2：后端当日赛事 API

**文件：**
- 创建：`backend/app/api/matches.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：编写路由文件**

创建 `backend/app/api/matches.py`：

```python
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.match_aggregator import build_today_matches_response

router = APIRouter(prefix="/api/v1/matches", tags=["matches"])


@router.get("/today")
def today_matches(
    target_date: date | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
):
    return build_today_matches_response(db=db, target_date=target_date)
```

- [ ] **步骤 2：注册路由**

修改 `backend/app/main.py`：

```python
from .api import auth, teams, predict, recommendations, data, matches
```

并在现有 `app.include_router(data.router)` 后添加：

```python
app.include_router(matches.router)
```

- [ ] **步骤 3：运行后端测试**

运行：

```powershell
cd backend; python -m pytest tests/ -v
```

预期：全部 PASS。

- [ ] **步骤 4：启动后端并手工验证接口**

运行：

```powershell
cd backend; python -m app.main
```

在浏览器或 API 客户端请求：

```text
http://127.0.0.1:8000/api/v1/matches/today?date=2026-06-11
```

预期：返回 JSON，包含 `matches`、`total`、`cache` 字段。

- [ ] **步骤 5：检查点**

仅在用户明确授权提交时运行：

```powershell
git add backend/app/api/matches.py backend/app/main.py; git commit -m "feat: expose today matches endpoint"
```

---

## 任务 3：前端模型、API 与 Provider

**文件：**
- 创建：`flutter_app/lib/models/today_match.dart`
- 创建：`flutter_app/lib/providers/today_matches_provider.dart`
- 修改：`flutter_app/lib/config/api_config.dart`
- 修改：`flutter_app/lib/services/api_service.dart`

- [ ] **步骤 1：新增 TodayMatch 模型**

创建 `flutter_app/lib/models/today_match.dart`：

```dart
class TodayMatchesResponse {
  final List<TodayMatch> matches;
  final int total;
  final TodayMatchesCache cache;

  TodayMatchesResponse({
    required this.matches,
    required this.total,
    required this.cache,
  });

  factory TodayMatchesResponse.fromJson(Map<String, dynamic> json) {
    final rawMatches = json['matches'];
    return TodayMatchesResponse(
      matches: rawMatches is List
          ? rawMatches.map((e) => TodayMatch.fromJson(e as Map<String, dynamic>)).toList()
          : const [],
      total: (json['total'] as num?)?.toInt() ?? 0,
      cache: TodayMatchesCache.fromJson((json['cache'] as Map<String, dynamic>?) ?? const {}),
    );
  }
}

class TodayMatch {
  final String matchId;
  final MatchTeam home;
  final MatchTeam away;
  final String? stage;
  final String? groupName;
  final DateTime? commenceTime;
  final MatchPredictionSummary? prediction;
  final MatchOddsSummary? odds;

  TodayMatch({
    required this.matchId,
    required this.home,
    required this.away,
    this.stage,
    this.groupName,
    this.commenceTime,
    this.prediction,
    this.odds,
  });

  factory TodayMatch.fromJson(Map<String, dynamic> json) {
    return TodayMatch(
      matchId: json['match_id'] as String? ?? '',
      home: MatchTeam.fromJson((json['home'] as Map<String, dynamic>?) ?? const {}),
      away: MatchTeam.fromJson((json['away'] as Map<String, dynamic>?) ?? const {}),
      stage: json['stage'] as String?,
      groupName: json['group_name'] as String?,
      commenceTime: DateTime.tryParse(json['commence_time'] as String? ?? ''),
      prediction: json['prediction'] is Map<String, dynamic>
          ? MatchPredictionSummary.fromJson(json['prediction'] as Map<String, dynamic>)
          : null,
      odds: json['odds'] is Map<String, dynamic>
          ? MatchOddsSummary.fromJson(json['odds'] as Map<String, dynamic>)
          : null,
    );
  }

  String get matchType => stage != null && stage!.contains('group') ? 'group' : 'knockout';
}

class MatchTeam {
  final String code;
  final String name;

  MatchTeam({required this.code, required this.name});

  factory MatchTeam.fromJson(Map<String, dynamic> json) {
    return MatchTeam(
      code: json['code'] as String? ?? '',
      name: json['name'] as String? ?? '',
    );
  }
}

class MatchPredictionSummary {
  final double win;
  final double draw;
  final double lose;
  final double systemConfidence;

  MatchPredictionSummary({
    required this.win,
    required this.draw,
    required this.lose,
    required this.systemConfidence,
  });

  factory MatchPredictionSummary.fromJson(Map<String, dynamic> json) {
    return MatchPredictionSummary(
      win: (json['win'] as num?)?.toDouble() ?? 0,
      draw: (json['draw'] as num?)?.toDouble() ?? 0,
      lose: (json['lose'] as num?)?.toDouble() ?? 0,
      systemConfidence: (json['system_confidence'] as num?)?.toDouble() ?? 0,
    );
  }
}

class MatchOddsSummary {
  final double? avgWin;
  final double? avgDraw;
  final double? avgLose;
  final double? bestWin;
  final double? bestDraw;
  final double? bestLose;
  final String? bestWinProvider;
  final String? bestDrawProvider;
  final String? bestLoseProvider;
  final int providerCount;
  final DateTime? updatedAt;

  MatchOddsSummary({
    this.avgWin,
    this.avgDraw,
    this.avgLose,
    this.bestWin,
    this.bestDraw,
    this.bestLose,
    this.bestWinProvider,
    this.bestDrawProvider,
    this.bestLoseProvider,
    required this.providerCount,
    this.updatedAt,
  });

  factory MatchOddsSummary.fromJson(Map<String, dynamic> json) {
    return MatchOddsSummary(
      avgWin: (json['avg_win'] as num?)?.toDouble(),
      avgDraw: (json['avg_draw'] as num?)?.toDouble(),
      avgLose: (json['avg_lose'] as num?)?.toDouble(),
      bestWin: (json['best_win'] as num?)?.toDouble(),
      bestDraw: (json['best_draw'] as num?)?.toDouble(),
      bestLose: (json['best_lose'] as num?)?.toDouble(),
      bestWinProvider: json['best_win_provider'] as String?,
      bestDrawProvider: json['best_draw_provider'] as String?,
      bestLoseProvider: json['best_lose_provider'] as String?,
      providerCount: (json['provider_count'] as num?)?.toInt() ?? 0,
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? ''),
    );
  }
}

class TodayMatchesCache {
  final DateTime? updatedAt;
  final int ttlSeconds;

  TodayMatchesCache({this.updatedAt, required this.ttlSeconds});

  factory TodayMatchesCache.fromJson(Map<String, dynamic> json) {
    return TodayMatchesCache(
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? ''),
      ttlSeconds: (json['ttl_seconds'] as num?)?.toInt() ?? 300,
    );
  }
}
```

- [ ] **步骤 2：新增接口常量与 API 方法**

在 `flutter_app/lib/config/api_config.dart` 的 endpoints 区域添加：

```dart
static const String todayMatchesEndpoint = '/matches/today';
```

在 `flutter_app/lib/services/api_service.dart` 中添加：

```dart
Future<dynamic> getTodayMatches({DateTime? date}) async {
  final params = <String, dynamic>{};
  if (date != null) {
    params['date'] = date.toIso8601String().split('T').first;
  }
  final resp = await _dio.get(ApiConfig.todayMatchesEndpoint, queryParameters: params);
  return resp.data;
}
```

- [ ] **步骤 3：新增 Provider**

创建 `flutter_app/lib/providers/today_matches_provider.dart`：

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/today_match.dart';
import '../services/providers.dart';

final todayMatchesProvider = FutureProvider.autoDispose<TodayMatchesResponse>((ref) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.getTodayMatches();
  if (data == null || data is! Map<String, dynamic>) {
    throw Exception('服务器返回了无效的当日赛事数据');
  }
  return TodayMatchesResponse.fromJson(data);
});
```

- [ ] **步骤 4：运行 Flutter 静态分析**

运行：

```powershell
cd flutter_app; flutter analyze
```

预期：新增文件无语法错误；此阶段可能因页面尚未引用而不产生功能验证。

- [ ] **步骤 5：检查点**

仅在用户明确授权提交时运行：

```powershell
git add flutter_app/lib/models/today_match.dart flutter_app/lib/providers/today_matches_provider.dart flutter_app/lib/config/api_config.dart flutter_app/lib/services/api_service.dart; git commit -m "feat: add today matches client data layer"
```

---

## 任务 4：对战预测页支持预填

**文件：**
- 修改：`flutter_app/lib/pages/prediction/prediction_page.dart`

- [ ] **步骤 1：改造 Widget 构造函数**

将 `PredictionPage` 改为：

```dart
class PredictionPage extends ConsumerStatefulWidget {
  final String? initialTeamA;
  final String? initialTeamB;
  final String initialMatchType;

  const PredictionPage({
    super.key,
    this.initialTeamA,
    this.initialTeamB,
    this.initialMatchType = 'group',
  });

  @override
  ConsumerState<PredictionPage> createState() => _PredictionPageState();
}
```

- [ ] **步骤 2：初始化预填状态**

在 `_PredictionPageState` 中添加 `initState`：

```dart
@override
void initState() {
  super.initState();
  _teamA = widget.initialTeamA;
  _teamB = widget.initialTeamB;
  _matchType = widget.initialMatchType;
}
```

当前 `build` 已基于 `_teamA != null && _teamB != null` 自动 watch `predictionProvider`，因此预填后会自动展示预测结果，不需要额外调用 `_predict()`。

- [ ] **步骤 3：运行 Flutter 静态分析**

运行：

```powershell
cd flutter_app; flutter analyze
```

预期：PASS 或仅剩项目既有 warning，无新增错误。

- [ ] **步骤 4：检查点**

仅在用户明确授权提交时运行：

```powershell
git add flutter_app/lib/pages/prediction/prediction_page.dart; git commit -m "feat: support prefilled prediction page"
```

---

## 任务 5：新增当日赛事页面

**文件：**
- 创建：`flutter_app/lib/pages/today_matches/today_matches_page.dart`

- [ ] **步骤 1：创建页面骨架**

创建 `flutter_app/lib/pages/today_matches/today_matches_page.dart`，先实现加载、错误、空状态和列表结构：

```dart
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/today_match.dart';
import '../../providers/today_matches_provider.dart';
import '../../widgets/common_widgets.dart';
import '../prediction/prediction_page.dart';
import '../teams/team_detail_page.dart';

class TodayMatchesPage extends ConsumerWidget {
  const TodayMatchesPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final matchesAsync = ref.watch(todayMatchesProvider);

    return RefreshIndicator(
      onRefresh: () async => ref.invalidate(todayMatchesProvider),
      child: matchesAsync.when(
        loading: () => const LoadingWidget(message: '正在加载当日赛事...'),
        error: (err, _) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            ErrorWidgetView(
              message: '加载失败: ${err.toString()}',
              onRetry: () => ref.invalidate(todayMatchesProvider),
            ),
          ],
        ),
        data: (data) {
          if (data.matches.isEmpty) {
            return ListView(
              padding: const EdgeInsets.all(16),
              children: const [
                _EmptyTodayMatchesCard(),
              ],
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: data.matches.length + 1,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              if (index == 0) return _CacheInfo(cache: data.cache);
              return _TodayMatchCard(match: data.matches[index - 1]).animate().fadeIn();
            },
          );
        },
      ),
    );
  }
}
```

- [ ] **步骤 2：实现空状态和缓存提示**

在同文件追加：

```dart
class _EmptyTodayMatchesCard extends StatelessWidget {
  const _EmptyTodayMatchesCard();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          children: [
            Icon(Icons.event_busy, size: 48, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text('今日暂无比赛', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text('下拉可刷新最新赛程', style: TextStyle(color: Colors.grey.shade500)),
          ],
        ),
      ),
    );
  }
}

class _CacheInfo extends StatelessWidget {
  final TodayMatchesCache cache;

  const _CacheInfo({required this.cache});

  @override
  Widget build(BuildContext context) {
    final updatedAt = cache.updatedAt;
    final text = updatedAt == null
        ? '赛事数据实时更新'
        : '更新于 ${_formatDateTime(updatedAt)} · 下拉刷新';
    return Row(
      children: [
        Icon(Icons.schedule, size: 14, color: Colors.grey.shade500),
        const SizedBox(width: 4),
        Text(text, style: TextStyle(fontSize: 12, color: Colors.grey.shade500)),
      ],
    );
  }
}
```

- [ ] **步骤 3：实现比赛卡片与跳转**

在同文件追加：

```dart
class _TodayMatchCard extends StatelessWidget {
  final TodayMatch match;

  const _TodayMatchCard({required this.match});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.calendar_month, size: 16, color: Colors.grey.shade600),
                const SizedBox(width: 6),
                Text(
                  match.commenceTime == null ? '开赛时间待定' : _formatDateTime(match.commenceTime!),
                  style: TextStyle(fontSize: 13, color: Colors.grey.shade700),
                ),
                const Spacer(),
                if (match.groupName != null)
                  Chip(label: Text('${match.groupName}组'), visualDensity: VisualDensity.compact),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(child: _TeamTapTarget(team: match.home)),
                const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 12),
                  child: Text('VS', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.grey)),
                ),
                Expanded(child: _TeamTapTarget(team: match.away, alignEnd: true)),
              ],
            ),
            const SizedBox(height: 16),
            _PredictionPanel(match: match),
            const SizedBox(height: 12),
            _OddsPanel(odds: match.odds),
          ],
        ),
      ),
    );
  }
}

class _TeamTapTarget extends StatelessWidget {
  final MatchTeam team;
  final bool alignEnd;

  const _TeamTapTarget({required this.team, this.alignEnd = false});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: team.code.isEmpty
          ? null
          : () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => TeamDetailPage(teamCode: team.code, teamName: team.name),
                ),
              ),
      child: Row(
        mainAxisAlignment: alignEnd ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: [
          if (!alignEnd) _TeamLogo(code: team.code),
          if (!alignEnd) const SizedBox(width: 8),
          Flexible(
            child: Text(
              team.name.isEmpty ? team.code : team.name,
              textAlign: alignEnd ? TextAlign.end : TextAlign.start,
              style: const TextStyle(fontWeight: FontWeight.w600),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (alignEnd) const SizedBox(width: 8),
          if (alignEnd) _TeamLogo(code: team.code),
        ],
      ),
    );
  }
}

class _TeamLogo extends StatelessWidget {
  final String code;

  const _TeamLogo({required this.code});

  @override
  Widget build(BuildContext context) {
    return CircleAvatar(
      radius: 18,
      backgroundColor: Theme.of(context).colorScheme.primaryContainer,
      child: Text(code, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
    );
  }
}
```

- [ ] **步骤 4：实现预测与赔率区域**

在同文件追加：

```dart
class _PredictionPanel extends StatelessWidget {
  final TodayMatch match;

  const _PredictionPanel({required this.match});

  @override
  Widget build(BuildContext context) {
    final prediction = match.prediction;
    if (prediction == null) {
      return _InfoPanel(
        icon: Icons.analytics_outlined,
        title: '预测数据暂不可用',
        child: Text('稍后刷新查看最新预测', style: TextStyle(color: Colors.grey.shade600)),
      );
    }

    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => PredictionPage(
            initialTeamA: match.home.code,
            initialTeamB: match.away.code,
            initialMatchType: match.matchType,
          ),
        ),
      ),
      child: _InfoPanel(
        icon: Icons.travel_explore,
        title: '赛果预测',
        child: Row(
          children: [
            _ProbabilityChip(label: '主胜', value: prediction.win, color: Colors.green),
            const SizedBox(width: 8),
            _ProbabilityChip(label: '平局', value: prediction.draw, color: Colors.orange),
            const SizedBox(width: 8),
            _ProbabilityChip(label: '客胜', value: prediction.lose, color: Colors.red),
          ],
        ),
      ),
    );
  }
}

class _OddsPanel extends StatelessWidget {
  final MatchOddsSummary? odds;

  const _OddsPanel({required this.odds});

  @override
  Widget build(BuildContext context) {
    if (odds == null || odds!.providerCount == 0) {
      return _InfoPanel(
        icon: Icons.trending_up,
        title: '赔率指数',
        child: Text('暂无赔率数据', style: TextStyle(color: Colors.grey.shade600)),
      );
    }

    return _InfoPanel(
      icon: Icons.trending_up,
      title: '赔率指数 · ${odds!.providerCount} 家',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _OddsChip(label: '主胜', value: odds!.avgWin),
              const SizedBox(width: 8),
              _OddsChip(label: '平局', value: odds!.avgDraw),
              const SizedBox(width: 8),
              _OddsChip(label: '客胜', value: odds!.avgLose),
            ],
          ),
          if (odds!.bestWin != null || odds!.bestDraw != null || odds!.bestLose != null) ...[
            const SizedBox(height: 6),
            Text(
              '最佳赔率：主胜 ${_formatOdds(odds!.bestWin)} / 平 ${_formatOdds(odds!.bestDraw)} / 客胜 ${_formatOdds(odds!.bestLose)}',
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
          ],
        ],
      ),
    );
  }
}

class _InfoPanel extends StatelessWidget {
  final IconData icon;
  final String title;
  final Widget child;

  const _InfoPanel({required this.icon, required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.45),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 6),
              Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
            ],
          ),
          const SizedBox(height: 8),
          child,
        ],
      ),
    );
  }
}

class _ProbabilityChip extends StatelessWidget {
  final String label;
  final double value;
  final Color color;

  const _ProbabilityChip({required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(10)),
        child: Column(
          children: [
            Text(label, style: TextStyle(fontSize: 12, color: color)),
            Text('${(value * 100).toStringAsFixed(0)}%', style: TextStyle(fontWeight: FontWeight.bold, color: color)),
          ],
        ),
      ),
    );
  }
}

class _OddsChip extends StatelessWidget {
  final String label;
  final double? value;

  const _OddsChip({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(color: Colors.blue.shade50, borderRadius: BorderRadius.circular(10)),
        child: Column(
          children: [
            Text(label, style: TextStyle(fontSize: 12, color: Colors.blue.shade700)),
            Text(_formatOdds(value), style: TextStyle(fontWeight: FontWeight.bold, color: Colors.blue.shade700)),
          ],
        ),
      ),
    );
  }
}

String _formatDateTime(DateTime value) {
  String two(int n) => n.toString().padLeft(2, '0');
  return '${value.year}-${two(value.month)}-${two(value.day)} ${two(value.hour)}:${two(value.minute)}';
}

String _formatOdds(double? value) => value == null ? '-' : value.toStringAsFixed(2);
```

- [ ] **步骤 5：运行 Flutter 静态分析**

运行：

```powershell
cd flutter_app; flutter analyze
```

预期：PASS 或仅剩项目既有 warning，无新增错误。

- [ ] **步骤 6：检查点**

仅在用户明确授权提交时运行：

```powershell
git add flutter_app/lib/pages/today_matches/today_matches_page.dart; git commit -m "feat: add today matches page"
```

---

## 任务 6：导航入口迁移与赛事模拟页功能卡片

**文件：**
- 修改：`flutter_app/lib/pages/home_page.dart`
- 修改：`flutter_app/lib/pages/simulation/simulation_page.dart`

- [ ] **步骤 1：修改首页底部导航**

在 `home_page.dart` 中：

```dart
import 'today_matches/today_matches_page.dart';
```

将 `_pages` 第一项从：

```dart
PredictionPage(),
```

改为：

```dart
TodayMatchesPage(),
```

将第一个 `NavigationDestination` 改为：

```dart
NavigationDestination(
  icon: Icon(Icons.event_outlined),
  selectedIcon: Icon(Icons.event),
  label: '当日赛事',
),
```

将 `_titles` 第一项改为：

```dart
'当日赛事',
```

- [ ] **步骤 2：赛事模拟页引入预测页**

在 `simulation_page.dart` 增加 import：

```dart
import '../prediction/prediction_page.dart';
```

在 `_buildControlCard(context, state, notifier)` 后插入：

```dart
const SizedBox(height: 16),
_buildPredictionEntryCard(context),
const SizedBox(height: 16),
```

注意替换原来控制卡后紧跟的单个 `const SizedBox(height: 16)`，避免重复间距。

- [ ] **步骤 3：新增入口卡片方法**

在 `SimulationPage` 内添加：

```dart
Widget _buildPredictionEntryCard(BuildContext context) {
  return Card(
    child: InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => const PredictionPage()),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Icon(Icons.sports_soccer, size: 44, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 12),
            Text(
              '对战预测',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              '选择任意两支球队，查看胜平负概率与赔率分析',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey),
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const PredictionPage()),
              ),
              icon: const Icon(Icons.travel_explore),
              label: const Text('立即预测'),
              style: FilledButton.styleFrom(minimumSize: const Size(double.infinity, 48)),
            ),
          ],
        ),
      ),
    ),
  ).animate().fadeIn(delay: 100.ms);
}
```

- [ ] **步骤 4：运行 Flutter 静态分析**

运行：

```powershell
cd flutter_app; flutter analyze
```

预期：PASS 或仅剩项目既有 warning，无新增错误。

- [ ] **步骤 5：检查点**

仅在用户明确授权提交时运行：

```powershell
git add flutter_app/lib/pages/home_page.dart flutter_app/lib/pages/simulation/simulation_page.dart; git commit -m "feat: move prediction entry to simulation page"
```

---

## 任务 7：端到端验证

**文件：**
- 不新增文件。

- [ ] **步骤 1：运行后端测试**

运行：

```powershell
cd backend; python -m pytest tests/ -v
```

预期：全部 PASS。

- [ ] **步骤 2：运行 Flutter 静态分析**

运行：

```powershell
cd flutter_app; flutter analyze
```

预期：PASS 或仅剩项目既有 warning，无新增错误。

- [ ] **步骤 3：启动后端服务**

运行：

```powershell
cd backend; python -m app.main
```

预期：服务监听 `http://127.0.0.1:8000`。

- [ ] **步骤 4：启动 Flutter Web**

运行：

```powershell
cd flutter_app; flutter run -d chrome --web-port=8080
```

预期：浏览器打开前端页面。

- [ ] **步骤 5：手工验证关键路径**

验证清单：

- 底部导航第 1 项显示「当日赛事」。
- 「当日赛事」页面能显示加载态、空状态或比赛卡片。
- 点击比赛卡片中的球队名称/标识，进入对应球队详情页。
- 点击预测区域，进入对战预测页并预填主客队，页面自动展示预测结果。
- 切换到底部「赛事模拟」Tab 后，主卡片下方显示「对战预测」功能卡片。
- 点击「对战预测」功能卡片，进入原有对战预测页。
- 下拉刷新「当日赛事」页面时不会报错。

- [ ] **步骤 6：最终检查点**

仅在用户明确授权提交时运行：

```powershell
git status; git add backend/app/services/match_aggregator.py backend/app/api/matches.py backend/app/main.py backend/tests/services/test_match_aggregator.py flutter_app/lib/models/today_match.dart flutter_app/lib/providers/today_matches_provider.dart flutter_app/lib/pages/today_matches/today_matches_page.dart flutter_app/lib/config/api_config.dart flutter_app/lib/services/api_service.dart flutter_app/lib/pages/prediction/prediction_page.dart flutter_app/lib/pages/home_page.dart flutter_app/lib/pages/simulation/simulation_page.dart; git commit -m "feat: add today matches experience"
```

---

## 自检

### 规格覆盖度

- 「当日赛事」聚合接口：任务 1、任务 2 覆盖。
- 前端单请求与缓存 Provider：任务 3 覆盖。
- 当日赛事卡片、球队详情跳转、预测跳转、赔率展示：任务 5 覆盖。
- 对战预测页预填：任务 4 覆盖。
- 底部导航替换与模拟页新增入口卡片：任务 6 覆盖。
- 验证与性能目标：任务 7 覆盖，通过后端聚合与单请求达成。

### 占位符扫描

计划中无「待定」「TODO」「后续实现」等占位符。每个代码变更步骤均给出具体文件、代码片段、运行命令与预期结果。

### 类型一致性

- 后端响应字段与前端模型保持一致：`match_id`、`commence_time`、`prediction.win/draw/lose`、`odds.avg_win/avg_draw/avg_lose`。
- 前端 `TodayMatch.matchType` 与 `PredictionPage.initialMatchType` 一致，取值为 `group` 或 `knockout`。
- 跳转所需球队字段统一使用 `MatchTeam.code` 与 `MatchTeam.name`。
