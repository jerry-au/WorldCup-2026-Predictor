# 当日赛事与对战预测入口迁移设计规格

## 概述

本规格针对「World Cup 2026 Predictor」项目实现以下两项调整：

1. 将底部导航中原来的「对战预测」Tab 替换为「当日赛事」入口，并开发全新的当日赛事聚合页面。
2. 将「对战预测」入口迁移至「赛事模拟」页面内，保持现有预测页功能不变。

核心目标：为用户提供更贴近观赛场景的当日比赛入口，同时保留完整的对战预测能力，并确保导航流畅、首屏加载在 3 秒内完成。

---

## 术语约定

- **当日赛事（Today Matches）**：指当日进行的所有世界杯比赛，包含赛程、预测概率、市场赔率。
- **主客队（Home/Away）**：一场比赛的主队与客队，对应到预测引擎的 `team_a` 与 `team_b`。
- **预填跳转（Prefill Navigation）**：从当日赛事卡片点击后，将主客队信息带入预测页并自动展示预测结果。

---

## 背景与目标

### 背景

现有底部导航第一项为「对战预测」，需要用户手动选择两支球队才能查看结果；而「赛事模拟」页聚合性强但缺少快速进入单场预测的入口。与此同时，用户需要一个能快速查看当日比赛的页面，并在查看后自然进入预测或球队详情。

### 目标

- 提供「当日赛事」聚合页，卡片式展示当日比赛，支持球队详情跳转、预测跳转、赔率展示。
- 将「对战预测」入口迁移到「赛事模拟」页内卡片，保持视觉一致。
- 首屏加载时间 ≤ 3 秒，通过后端聚合接口避免 N+1 请求。
- 页面交互与视觉风格与现有设计保持一致，使用 Material 3、Riverpod、`flutter_animate`。
- 数据具有新鲜度标识与合理缓存策略。

---

## 需求分析

### 功能需求

- 「当日赛事」页面：
  - 以卡片列表展示当日所有比赛。
  - 每场卡片显示：
    - 主客队名称与球队标识/Logo 占位。
    - 开赛时间（日期 + 24 小时制具体时间）。
    - 赛果预测摘要（主胜/平/客胜概率）。
    - 胜平负赔率（平均赔率，如后端提供则追加最佳赔率及博彩公司来源）。
  - 点击球队名称/Logo → 跳转到对应球队详情页。
  - 点击预测区域 → 跳转到对战预测页并预填当前比赛的主客队，自动触发预测展示。
  - 支持下拉刷新、加载态、空状态、错误态。
- 「赛事模拟」页面：
  - 在「2026 世界杯赛事模拟」主卡片正下方新增一个同样 Card 风格的功能卡片。
  - 卡片标题：「对战预测」，点击后导航到现有对战预测页。
- 「对战预测」页面：
  - 构造函数支持可选初始主客队参数。
  - 若接收到预填参数，页面加载后自动执行预测并展示结果。

### 非功能需求

- 首屏加载 ≤ 3 秒：通过单次后端聚合接口完成数据获取。
- 数据缓存：前端数据使用短 TTL 缓存；后端已有的赔率缓存可继续复用。
- 响应式布局：在移动端和桌面端均有良好表现。
- 平滑过渡：页面间使用统一的 `MaterialPageRoute` 或 `flutter_animate` 转场。

---

## 架构设计

### 整体数据流

```
用户进入首页（TodayMatchesPage）
  → Riverpod Provider 触发 API 请求
  → 后端 /api/v1/matches/today 聚合返回当日比赛列表
  → 渲染卡片列表
  → 用户操作（点球队/点预测/下拉刷新）
    → 跳转球队详情
    → 跳转对战预测（带参数）
```

### 模块边界

- **前端：**
  - `TodayMatchesPage`：UI 页面与交互。
  - `today_matches_provider.dart`：Riverpod Provider，管理数据、缓存和刷新。
  - `today_match_model.dart`：数据模型。
  - `api_service.dart`：新增后端当日赛事接口调用方法。
- **后端：**
  - `backend/app/api/matches.py`：新增当日赛事路由。
  - `backend/app/services/match_aggregator.py`（可选）：聚合比赛、预测、赔率的服务。
  - 复用现有：
    - `models/odds_data.py`
    - `models/zafronix_data.py`
    - `core/prediction.py`

---

## 详细设计

### 1. 导航与入口调整

**影响文件：** `flutter_app/lib/pages/home_page.dart`、`flutter_app/lib/pages/simulation/simulation_page.dart`

**HomePage 变更：**

- `_pages` 列表第 1 项从 `PredictionPage()` 改为 `TodayMatchesPage()`。
- `_titles` 列表第 1 项从「对战预测」改为「当日赛事」。
- 底部导航第 1 项 `NavigationDestination`：
  - 建议图标：体育日程或日历类图标（如 `sports_soccer`/`calendar_month`），保持与足球主题一致。
  - 标签：「当日赛事」。

**SimulationPage 变更：**

- 在主功能卡片之后插入一个相同尺寸、相同圆角、相同阴影的 `Card`：
  - 图标：与原 Tab 图标一致（如 `sports_soccer`）。
  - 标题：「对战预测」。
  - 描述：选择任意两支球队，查看胜平负概率与投注分析。
  - 按钮：使用 `FilledButton.icon`，文案为「立即预测」，点击 `Navigator.push` 到 `PredictionPage()`，如后续支持不带参数的通用预测即可直接使用；如需要可再扩展参数，但迁移阶段先不依赖参数。

### 2. 当日赛事页面

**新增文件：**
- `flutter_app/lib/pages/today_matches/today_matches_page.dart`
- `flutter_app/lib/models/today_match.dart`
- `flutter_app/lib/providers/today_matches_provider.dart`

**页面结构：**

- `Scaffold` + `RefreshIndicator` 包裹 `ListView`。
- 加载中状态：复用现有骨架或 `LoadingWidget`。
- 空状态：「今日暂无比赛」并附一个提示性图标。
- 错误状态：错误文案 + 重试按钮，触发 refresh。

**单场卡片：**

- 顶部：开赛时间（24 小时制，显示日期与时间）。
- 中部：主队徽标/占位 → 主队名 → VS → 客队名 → 客队徽标/占位。
  - 队名/徽标：点击跳转到 `TeamDetailPage`，使用 `team.code` 作为参数。
- 预测区：
  - 显示主胜/平/客胜概率百分比。
  - 整区可点击，跳转 `PredictionPage` 并预填主客队。
- 赔率区：
  - 显示平均胜/平/负赔率，如有最佳赔率信息可补充显示。
  - 样式参考现有投注推荐页的赔率展示。

**交互：**

- 页面间跳转使用 `MaterialPageRoute` 或统一的自定义过渡，保持平滑。
- Riverpod 使用 `FutureProvider.family`/`FutureProvider`，支持 `invalidate` 触发强制刷新。

### 3. 对战预测页支持预填

**影响文件：** `flutter_app/lib/pages/prediction/prediction_page.dart`

- 构造函数新增可选参数：
  - `String? initialTeamA`
  - `String? initialTeamB`
  - `String initialMatchType = 'group'`
- `initState` / `ConsumerState` 初始化时，将参数写入 `_teamA` / `_teamB`。
- 若两个参数均不为空，可在页面构建完成后自动调用 `_predict()` 并展示结果，减少用户二次点击。

### 4. 后端 API 设计

**新增接口：** `GET /api/v1/matches/today`

**参数（可选）：**
- `tz` / `date`（可选，默认使用服务器当天日期）

**响应体示例：**

```json
{
  "matches": [
    {
      "match_id": "BRA-vs-FRA-2026-06-11",
      "home": {
        "code": "BRA",
        "name": "Brazil"
      },
      "away": {
        "code": "FRA",
        "name": "France"
      },
      "stage": "group",
      "group_name": "E",
      "commence_time": "2026-06-11T20:00:00+03:00",
      "prediction": {
        "win": 0.42,
        "draw": 0.28,
        "lose": 0.30,
        "system_confidence": 0.75
      },
      "odds": {
        "avg_win": 2.15,
        "avg_draw": 3.40,
        "avg_lose": 2.80,
        "best_win": 2.25,
        "best_win_provider": "Bet365",
        "provider_count": 8
      }
    }
  ],
  "total": 1,
  "cache": {
    "updated_at": "2026-06-11T12:00:00+00:00",
    "ttl_seconds": 300
  }
}
```

**后端实现要点：**

- 优先从数据库缓存读取：
  - 比赛信息来自 `ZafronixMatch`（或 `MatchOddsSummary` / 自定义赛程表）。
  - 赔率信息来自 `MatchOddsSummary` 和 `MatchOdds`。
  - 预测信息由 `PredictionEngine` 实时计算或从缓存读取。
- 若赛程表中没有「比赛日期」字段，需要先补充该字段（建议在 `ZafronixMatch` 或新模型中增加 `commence_time`）。
- 若当日无比赛，返回 `"matches": []` 和正常 `cache` 信息，不抛出错误。
- 所有计算与查询合并在一个请求内完成，避免前端多轮请求。
- 该 API 应注册到 FastAPI 路由中，并在 `main.py` 中引入。

**数据模型补充建议（如需要）：**

- 如现有模型不支持按日期查询比赛，可在 `ZafronixMatch` 或新增 `MatchSchedule` 表中加入 `commence_time` 字段，并编写迁移。
- 如果赛程尚未入库，先以临时静态/配置数据兜底，后续再替换为爬虫实时数据。

### 5. 性能与缓存设计

- 前端：
  - Riverpod Provider 在短时间（如 5 分钟）内可复用上次结果，下拉刷新时强制刷新。
  - 首屏先显示骨架/加载卡片，数据返回后渐入替换（使用 `flutter_animate`）。
- 后端：
  - 赔率与预测已有缓存能力，尽量复用 `RecommendationCache` / `MatchOddsSummary`。
  - 如当日比赛很少且访问频繁，可考虑增加服务端短 TTL 缓存。

---

## 测试计划

### 单元与服务测试

- 测试 `GET /api/v1/matches/today` 返回结构与字段完整性。
- 测试当日无比赛、有比赛、部分比赛缺少赔率三种场景。
- 前端模型可覆盖空值/缺省值逻辑。

### 集成与手工测试

- 底部导航切换正常，第一个 Tab 为当日赛事，标题正确。
- 当日赛事页卡片可点击球队跳转到详情页。
- 当日赛事页卡片可点击预测区跳转到对战预测页，并自动预填与展示预测。
- 赛事模拟页内新增功能卡片视觉一致且可正常跳转。
- 下拉刷新、错误重试、空状态展示正确。

---

## 实现计划（摘要）

1. **后端新增当日赛事接口**：补充数据字段（如 `commence_time`），完成 API 与聚合逻辑。
2. **前端模型与 API Service**：新增 `TodayMatch` 模型和 API 调用方法。
3. **新增当日赛事页面与 Provider**：完成列表、卡片、刷新与异常态。
4. **对战预测页支持预填**：改造构造参数与自动预测逻辑。
5. **导航入口迁移**：修改首页底部导航与赛事模拟页卡片。
6. **测试与优化**：端到端走查、性能验证、视觉对齐。

---

## 兼容性与回滚

- 前端不删除 `PredictionPage`，仅变更入口位置，可随时回退到原导航布局。
- 后端新增接口不影响现有路由，若 API 不可用，前端可显示空状态/错误态，不影响其他功能。

---

## 开放性问题

无。本规格已明确所有关键实现路径，无需额外决策点。
