# 赛程页面与导航重构设计规格

## 概述

本规格针对「World Cup 2026 Predictor」项目实现以下三项调整：

1. 底部导航移除「球队」入口，替换为「赛程」入口；开发全新赛程页面（含小组赛 + 赛程两个 Tab）。
2. 赛事模拟页内新增「球队详情」功能卡片，保持与原球队页面相同的功能入口。
3. 后端新增赛程/积分榜聚合 API，为前端赛程页提供数据支持。

核心目标：为用户提供完整的赛程查阅体验，同时保持球队浏览功能可用，导航逻辑清晰。

---

## 术语约定

- **小组赛（Group Stage）**：12 个小组 × 4 支球队的积分排名表。
- **赛程（Schedule）**：所有比赛的日期、时间、对阵双方、赛果、预测、赔率数据。
- **积分榜（Standings）**：各小组球队的赛/胜/平/负/进/失球/净胜球/积分数据。

---

## 背景与目标

### 背景

现有底部导航包含「球队」入口，但用户更需要一个能查看完整赛程和小组积分的页面。球队浏览功能仍然重要，但可作为赛事模拟页的子入口，而非独立占据导航位。

### 目标

- 底部导航新增「赛程」入口，替换原「球队」位置。
- 赛程页以 Tab 形式展示小组赛积分表 + 完整赛程数据。
- 赛事模拟页新增「球队详情」卡片，保持球队浏览功能可访问。
- 所有页面风格一致，导航流畅，数据加载性能良好。

---

## 需求分析

### 功能需求

**底部导航栏调整：**
- 移除「球队」入口
- 在「赛事模拟」与「投注推荐」之间新增「赛程」入口
- 图标：`Icons.schedule`，标签：「赛程」

**赛程页（SchedulePage）：**
- 顶部 2 个 Tab 切换：小组赛 / 赛程
- **小组赛 Tab：**
  - 按 Group 字母（A-L）分组展示积分表
  - 表格列：排名 | 球队(国旗+名称) | 赛 | 胜 | 平 | 负 | 进/失球 | 净胜球 | 积分
  - 支持按 Group 字母筛选（下拉选择器）
  - 数据来源：`DongqiudiStanding` 表
- **赛程 Tab：**
  - 按日期分组展示所有比赛
  - 每场比赛卡片：日期时间 | 对阵双方(国旗+名称) | 比分(如已完成) | 预测概率 | 赔率
  - 支持筛选：全部 / 已完成 / 未开始
  - 数据来源：`DongqiudiMatch` 表 + `MatchOddsSummary` 表 + 预测引擎
- 响应式表格设计，小屏设备可横向滚动
- 支持下拉刷新、加载态、空状态、错误态

**赛事模拟页新增球队详情卡片：**
- 在「对战预测」卡片下方插入「球队详情」功能卡片
- 风格与「对战预测」卡片完全一致：`Card` + `InkWell` + 居中图标 + 标题 + 描述 + 按钮
- 图标：`Icons.groups`
- 标题：「球队详情」
- 描述：「浏览全部 48 支参赛球队数据，支持搜索、筛选与排序」
- 点击 → `Navigator.push` 到 `TeamListPage`（带淡入过渡动画）

### 非功能需求

- 首屏加载 ≤ 3 秒：通过单次后端聚合接口完成数据获取
- 响应式布局：表格在小屏设备上支持横向滚动
- 平滑过渡：页面间使用统一的 `MaterialPageRoute` 或 `flutter_animate` 转场
- 视觉一致性：与现有页面风格保持一致（Material 3 + Riverpod + 深色主题）

---

## 架构设计

### 整体数据流

```
用户进入赛程页
  → Riverpod Provider 触发 API 请求
  → 后端 /api/v1/matches/schedule 返回所有比赛（含预测+赔率）
  → 后端 /api/v1/matches/standings 返回所有小组积分榜
  → 渲染小组赛表格 / 赛程列表
  → 用户操作（切换 Tab / 筛选 / 下拉刷新）
```

### 模块边界

**前端（新增/修改）：**
- `flutter_app/lib/pages/schedule/schedule_page.dart`：赛程页 UI
- `flutter_app/lib/providers/schedule_provider.dart`：赛程数据 Provider
- `flutter_app/lib/pages/home_page.dart`：修改底部导航
- `flutter_app/lib/pages/simulation/simulation_page.dart`：新增球队详情卡片
- `flutter_app/lib/services/api_service.dart`：新增 API 调用方法

**后端（新增）：**
- `backend/app/api/matches.py`：扩展路由，新增 `/schedule` 和 `/standings` 端点
- `backend/app/main.py`：注册 matches router

**复用现有：**
- `models/team.py`
- `models/dongqiudi_match.py`
- `models/dongqiudi_standings.py`
- `models/odds_data.py`
- `core/prediction.py`
- 前端 `models/team.dart`、`providers/teams_provider.dart`

---

## 详细设计

### 1. 底部导航调整

**影响文件：** `flutter_app/lib/pages/home_page.dart`

**变更内容：**

- `_pages` 列表第 3 项（索引 2）从 `TeamListPage()` 改为 `SchedulePage()`
- `_titles` 列表第 3 项从「球队详情」改为「赛程」
- 底部导航第 3 项 `NavigationDestination`：
  - 图标：`Icons.schedule_outlined` / `Icons.schedule`
  - 标签：「赛程」
- 移除 `import 'teams/team_list_page.dart'`，新增 `import 'schedule/schedule_page.dart'`

**导航顺序（调整后）：**

| 索引 | 页面 | 标题 | 图标 |
|------|------|------|------|
| 0 | TodayMatchesPage | 当日赛事 | event |
| 1 | SimulationPage | 赛事模拟 | bar_chart |
| 2 | **SchedulePage** | **赛程** | **schedule** |
| 3 | BettingPage | 投注推荐 | trending_up |
| 4 | ProfilePage | 我的 | person |

### 2. 赛事模拟页新增球队详情卡片

**影响文件：** `flutter_app/lib/pages/simulation/simulation_page.dart`

**变更内容：**

在 `_buildPredictionCard` 方法之后新增 `_buildTeamDetailCard` 方法：

```dart
Widget _buildTeamDetailCard(BuildContext context) {
  return Card(
    child: InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => Navigator.of(context).push(
        MaterialPageRoute(builder: (_) => const TeamListPage()),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Icon(Icons.groups, size: 48, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 12),
            Text(
              '球队详情',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              '浏览全部 48 支参赛球队数据，支持搜索、筛选与排序',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => const TeamListPage()),
              ),
              icon: const Icon(Icons.groups),
              label: const Text('进入球队详情'),
              style: FilledButton.styleFrom(
                minimumSize: const Size(double.infinity, 48),
              ),
            ),
          ],
        ),
      ),
    ),
  );
}
```

在 `build` 方法的 `ListView` 中：
```dart
children: [
  _buildControlCard(context, state, notifier),
  const SizedBox(height: 16),
  _buildPredictionCard(context),
  const SizedBox(height: 16),
  _buildTeamDetailCard(context),   // ← 新增
  const SizedBox(height: 16),
  // ... 其余内容
]
```

新增 import：`import '../teams/team_list_page.dart'`

### 3. 赛程页面

**新增文件：**
- `flutter_app/lib/pages/schedule/schedule_page.dart`
- `flutter_app/lib/providers/schedule_provider.dart`

**页面结构：**

```
SchedulePage (ConsumerStatefulWidget)
├── TabBar (小组赛 | 赛程)
├── TabBarView
│   ├── GroupStageTab
│   │   ├── Group 筛选 Dropdown
│   │   └── ListView
│   │       └── GroupCard (per group)
│   │           └── DataTable
│   │               ├── 排名 | 球队(国旗) | 赛 | 胜 | 平 | 负 | 进球 | 失球 | 净胜 | 积分
│   └── ScheduleTab
│       ├── FilterChips (全部 | 已完成 | 未开始)
│       └── ListView
│           └── MatchCard
│               ├── 日期时间
│               ├── 对阵双方 (国旗+名称)
│               ├── 比分 (如已完成)
│               ├── 预测概率 (胜/平/负)
│               └── 赔率数据
```

**状态管理：**

- `scheduleProvider`：`FutureProvider`，返回 `ScheduleData`（含 matches 和 standings）
- 加载态：`LoadingWidget` / 骨架屏
- 空态：显示「暂无赛程数据」
- 错误态：显示错误信息 + 重试按钮

**DataTable 响应式设计：**
- 使用 `SingleChildScrollView` + `horizontal` 滚动包裹 `DataTable`
- 固定前两列（排名、球队），其余列可横向滚动
- 或使用自定义 `Table` widget 实现更灵活的响应式布局

### 4. 后端 API 设计

**扩展 `matches.py` 路由：**

当前 `matches.py` 已有 `/today` 端点，但 router 未在 `main.py` 中注册。需同时注册。

**新增端点 1：** `GET /api/v1/matches/schedule`

返回所有比赛的赛程数据，含预测和赔率。

参数：
- `stage`（可选）：筛选比赛阶段，如 `group_stage`、`round_of_16`
- `status`（可选）：筛选比赛状态，`completed`、`upcoming`
- `date`（可选）：筛选特定日期

响应体示例：
```json
{
  "matches": [
    {
      "match_id": "wc2026-A1",
      "stage": "group_stage",
      "group_name": "A",
      "home": {
        "code": "MEX",
        "name": "Mexico",
        "name_cn": "墨西哥",
        "flag_url": "/static/images/flags/MEX.png"
      },
      "away": {
        "code": "KOR",
        "name": "Korea Republic",
        "name_cn": "韩国",
        "flag_url": "/static/images/flags/KOR.png"
      },
      "score_home": null,
      "score_away": null,
      "status": "upcoming",
      "commence_time": "2026-06-11T20:00:00+08:00",
      "stadium": "Estadio Azteca",
      "prediction": {
        "win": 0.45,
        "draw": 0.28,
        "lose": 0.27
      },
      "odds": {
        "avg_win": 2.10,
        "avg_draw": 3.50,
        "avg_lose": 3.20
      }
    }
  ],
  "total": 64
}
```

**新增端点 2：** `GET /api/v1/matches/standings`

返回所有小组的积分榜数据。

参数：
- `group`（可选）：筛选特定小组，如 `A`

响应体示例：
```json
{
  "standings": [
    {
      "group_name": "A",
      "position": 1,
      "team_code": "MEX",
      "team_name": "Mexico",
      "team_name_cn": "墨西哥",
      "flag_url": "/static/images/flags/MEX.png",
      "played": 3,
      "won": 2,
      "drawn": 1,
      "lost": 0,
      "goals_for": 5,
      "goals_against": 2,
      "goal_diff": 3,
      "points": 7
    }
  ]
}
```

**后端实现要点：**
- 赛程数据优先从 `DongqiudiMatch` 读取，无数据时 fallback 到 `ZafronixMatch`
- 积分榜数据从 `DongqiudiStanding` 读取
- 预测数据通过 `PredictionEngine` 实时计算
- 赔率数据从 `MatchOddsSummary` 读取
- 所有数据聚合在一个请求内完成，避免前端 N+1 请求

**`main.py` 变更：**
- 新增 `from .api import matches`
- 新增 `app.include_router(matches.router)`

### 5. 前端 API Service 扩展

**影响文件：** `flutter_app/lib/services/api_service.dart`

新增方法：
```dart
Future<dynamic> getSchedule({String? stage, String? status, DateTime? date}) async {
  final params = <String, dynamic>{};
  if (stage != null) params['stage'] = stage;
  if (status != null) params['status'] = status;
  if (date != null) params['date'] = date.toIso8601String().split('T').first;
  final resp = await _dio.get(ApiConfig.scheduleEndpoint, queryParameters: params);
  return resp.data;
}

Future<dynamic> getStandings({String? group}) async {
  final params = <String, dynamic>{};
  if (group != null) params['group'] = group;
  final resp = await _dio.get(ApiConfig.standingsEndpoint, queryParameters: params);
  return resp.data;
}
```

**`api_config.dart` 新增常量：**
```dart
static const String scheduleEndpoint = '/matches/schedule';
static const String standingsEndpoint = '/matches/standings';
```

### 6. 数据模型

**新增前端模型（`flutter_app/lib/models/schedule.dart`）：**

```dart
class MatchSchedule {
  final String matchId;
  final String stage;
  final String? groupName;
  final TeamInfo home;
  final TeamInfo away;
  final int? scoreHome;
  final int? scoreAway;
  final String status; // upcoming, completed, live
  final DateTime? commenceTime;
  final String? stadium;
  final MatchPrediction? prediction;
  final MatchOddsSummary? odds;
}

class TeamInfo {
  final String code;
  final String name;
  final String? nameCn;
  final String? flagUrl;
}

class StandingEntry {
  final String groupName;
  final int position;
  final String teamCode;
  final String teamName;
  final String? teamNameCn;
  final String? flagUrl;
  final int played;
  final int won;
  final int drawn;
  final int lost;
  final int goalsFor;
  final int goalsAgainst;
  final int goalDiff;
  final int points;
}
```

---

## 测试计划

### 后端测试

- 测试 `GET /api/v1/matches/schedule` 返回结构完整性
- 测试 `GET /api/v1/matches/standings` 返回结构完整性
- 测试 `stage` / `status` / `group` 筛选参数
- 测试空数据场景（无比赛、无积分榜）

### 前端测试

- 底部导航切换正常，第 3 项为「赛程」
- 赛程页 Tab 切换正常
- 小组赛 Tab 表格展示正确，Group 筛选可用
- 赛程 Tab 比赛列表展示正确，状态筛选可用
- 赛事模拟页「球队详情」卡片可见且可点击跳转
- 下拉刷新、错误重试、空状态展示正确
- 表格在窄屏设备上可横向滚动

---

## 实现计划（摘要）

1. **后端 API 扩展**：新增 `/schedule` 和 `/standings` 端点，注册 matches router
2. **前端模型与 API Service**：新增 `schedule.dart` 模型，扩展 API 调用方法
3. **新建赛程页面**：`schedule_page.dart` + `schedule_provider.dart`
4. **修改底部导航**：`home_page.dart` 替换球队为赛程
5. **赛事模拟页新增卡片**：`simulation_page.dart` 新增球队详情卡片
6. **测试与优化**：端到端走查、性能验证、视觉对齐

---

## 兼容性与回滚

- 不删除 `TeamListPage` 和 `TeamDetailPage`，仅变更入口位置
- 后端新增接口不影响现有路由
- 底部导航变更可通过还原 `home_page.dart` 回退
- 赛事模拟页新增卡片为纯增量，不影响现有功能