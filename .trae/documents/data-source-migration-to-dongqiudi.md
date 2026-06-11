# 数据源迁移计划：全面切换至懂球帝为主数据源

## 概要

将项目数据源从多源混合架构（Zafronix API + Football-Data.org + 懂球帝 + 种子数据）迁移为以**懂球帝为主、其他源为辅**的架构。仅保留 The Odds API 作为赔率数据源。

---

## 当前状态分析

### 当前数据源依赖关系

```
                        ┌──────────────────┐
                        │  懂球帝 (已爬取)  │
                        │  - 国家队阵容      │
                        │  - 球员赛季摘要    │
                        │  - 球员能力评分    │
                        │  - 联赛球员数据    │
                        └────────┬─────────┘
                                 │
┌──────────────────┐    ┌───────┴──────────┐    ┌──────────────────┐
│  Zafronix API    │    │    核心算法       │    │ Football-Data.org│
│  - 比赛结果       │◄──►│  - Elo 评分      │◄──►│  - 联赛射手榜     │
│  - 小组积分榜     │    │  - 泊松模型      │    └──────────────────┘
│  - 赛事概览       │    │  - 蒙特卡洛模拟  │
│  - 球队/球员种子  │    └─────────────────┘
└──────────────────┘             │
                                 ▼
┌──────────────────┐    ┌──────────────────┐
│  种子数据 (本地)  │    │  The Odds API    │
│  - Elo 初始值     │    │  - 博彩赔率      │
│  - FIFA 排名      │    └──────────────────┘
│  - 球队身价       │
│  - 球队分组       │
└──────────────────┘
```

### 迁移后依赖关系

```
                        ┌──────────────────────┐
                        │  懂球帝 (主数据源)     │
                        │  - 国家队阵容 (已有)   │
                        │  - 球员赛季摘要 (已有) │
                        │  - 球员能力评分 (已有) │
                        │  - 联赛球员数据 (已有) │
                        │  - 比赛赛程 & 结果 (新增)│
                        │  - 小组积分榜 (新增)    │
                        └───────────┬──────────┘
                                    │
                        ┌───────────┴──────────┐
                        │    核心算法            │
                        │  - Elo 评分           │
                        │  - 泊松模型           │
                        │  - 蒙特卡洛模拟       │
                        └───────────┬──────────┘
                                    │
        ┌────────────────┬──────────┴──────────┬────────────────┐
        │                │                     │                │
        ▼                ▼                     ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ ┌──────────────┐
│ 种子数据(保留)│ │ FIFA 官网    │ │  The Odds API    │ │ 懂球帝球员   │
│ - Elo 初始值  │ │ (新增爬虫)   │ │  - 博彩赔率(保留) │ │ 身价聚合     │
│ - 球队分组    │ │ - FIFA排名  │ └──────────────────┘ │  → 球队总身价 │
└──────────────┘ └──────────────┘                      └──────────────┘
```

---

## 详细变更计划

### 阶段 1：懂球帝新增爬虫（2个新爬虫）

#### 1.1 比赛赛程 & 结果爬虫

**文件**：`backend/app/services/dongqiudi_match_results.py`（新增）

**数据源**：懂球帝世界杯赛程页面

**爬取内容**：
| 字段 | 说明 |
|------|------|
| match_id | 比赛唯一标识 |
| stage | 阶段（group_stage / round_of_16 / quarter / semi / final） |
| group_name | 小组名（小组赛阶段） |
| team_home_name / team_away_name | 主客队名（中文） |
| score_home / score_away | 常规时间比分 |
| score_home_et / score_away_et | 加时赛比分 |
| home_penalties / away_penalties | 点球比分 |
| status | 状态（completed / upcoming / live） |
| commence_time | 比赛时间 |
| stadium | 体育场 |

**DB 模型**：复用或新建 `dongqiudi_matches` 表

**逻辑**：
- 从懂球帝世界杯赛程页面获取所有比赛
- 通过队名中文匹配到 Team 表的 code
- 每日刷新，比赛日每 12 小时

#### 1.2 小组积分榜爬虫

**文件**：`backend/app/services/dongqiudi_standings.py`（新增）

**数据源**：懂球帝世界杯积分榜页面

**爬取内容**：
| 字段 | 说明 |
|------|------|
| group_name | 小组名 |
| position | 排名 |
| team_name | 球队名（中文） |
| played / won / drawn / lost | 场次统计 |
| goals_for / goals_against / goal_diff | 进球/失球/净胜球 |
| points | 积分 |

**DB 模型**：新建 `dongqiudi_standings` 表

**逻辑**：
- 从懂球帝积分榜页面获取所有小组排名
- 通过队名中文匹配到 Team 表的 code

---

### 阶段 2：FIFA 排名爬虫（新增）

#### 2.1 FIFA 世界排名爬虫

**文件**：`backend/app/services/fifa_ranking_fetcher.py`（新增）

**数据源**：FIFA 官网世界排名页面

**爬取内容**：
| 字段 | 说明 |
|------|------|
| team_name | 球队名称 |
| fifa_rank | FIFA 世界排名 |
| points | 积分 |
| confederation | 所属大洲 |

**DB 模型**：新建 `fifa_rankings` 表，或直接更新 `teams.fifa_rank` 字段

**逻辑**：
- 从 FIFA 官网爬取最新排名
- 匹配到 Team 表并更新 fifa_rank
- 每月刷新一次（FIFA 排名每月更新一次）

---

### 阶段 3：现有数据源切换

#### 3.1 替换 Zafronix API → 懂球帝比赛数据

**涉及文件**：
| 文件 | 变更内容 |
|------|----------|
| `backend/app/services/zafronix_service.py` | 标记为废弃，保留作为回退读取 |
| `backend/app/tasks/batch_fetch.py` | 移除 Zafronix 相关 fetch 逻辑 |
| `backend/app/tasks/scheduler.py` | 移除 refresh_zafronix_results() 任务；新增懂球帝比赛数据刷新任务 |
| `backend/app/api/matches.py` | GET `/matches/today` 改为从懂球帝比赛数据查询 |
| `backend/app/services/match_aggregator.py` | 数据源从 ZafronixMatch 改为懂球帝比赛数据 |
| `backend/app/core/elo.py` | `update_team_elos_from_completed_matches()` 从懂球帝比赛表读取已完成比赛 |
| `backend/app/api/data.py` | Zafronix 相关端点标记为废弃；懂球帝爬虫状态纳入刷新状态统计 |

**Zafronix 相关模型保留策略**：`zafronix_data.py` 中的模型保留不动，作为懂球帝数据缺失时的回退方案。

#### 3.2 替换 Football-Data.org → 懂球帝赛季数据

**涉及文件**：
| 文件 | 变更内容 |
|------|----------|
| `backend/app/services/football_data_fetcher.py` | 标记为废弃，保留作为回退读取 |
| `backend/app/tasks/scheduler.py` | 移除 refresh_player_data() 中的 football-data.org 调用 |
| `backend/app/api/teams.py` | 球队详情 API 优先从懂球帝赛季摘要获取数据 |

**具体逻辑变更（teams.py 球队详情 API）**：
- 当前顺序：football-data.org → 懂球帝
- 变更为：懂球帝（`player_season_stats` 或 `dongqiudi_player_season_summaries`）→ football-data.org（回退）

#### 3.3 球队身价：懂球帝球员身价聚合

**涉及文件**：
| 文件 | 变更内容 |
|------|----------|
| `backend/app/api/teams.py` | 球队详情中 `market_value_eur` 改为从懂球帝球员身价聚合计算 |
| `backend/seed_data/seed_rankings.py` | 移除身价数据，仅保留 FIFA 排名种子（作为 FIFA 官网爬虫上线前的过渡） |

**聚合逻辑**：
- 从 `dongqiudi_players` 表的 `market_value_text` 字段解析数值
- 同一球队的所有球员身价汇总为球队总身价
- 格式解析兼容：`6000万€` → 60,000,000，`1.2亿€` → 120,000,000

#### 3.4 俱乐部所在国家字段

- 根据用户确认，**忽略该字段**
- `teams.py` 中赛季数据的 `club_country` 返回空字符串或 null
- Flutter 前端不展示该字段

---

### 阶段 4：前端适配

#### 4.1 Flutter API Service 调整

**文件**：`flutter_app/lib/services/api_service.dart`

- Zafronix 相关 API 调用（`/api/v1/data/zafronix/*`）移除或标记
- 匹配数据端点从 `/api/v1/matches/` 获取

#### 4.2 Flutter 页面调整

**涉及文件**：
| 文件 | 变更内容 |
|------|----------|
| `flutter_app/lib/pages/simulation/simulation_page.dart` | 模拟引擎数据不变（来自核心算法） |
| `flutter_app/lib/pages/profile/profile_page.dart` | 移除 Zafronix 数据刷新状态，显示懂球帝数据刷新状态 |
| `flutter_app/lib/pages/home/` | 首页比赛数据源调整 |

---

### 阶段 5：代码清理

#### 5.1 定时任务调度器重构

**文件**：`backend/app/tasks/scheduler.py`

| 任务 | 操作 |
|------|------|
| `refresh_zafronix_results()` | 移除 |
| `refresh_player_data()` | 移除 football-data.org 部分 |
| `refresh_dongqiudi_rosters()` | 保留 |
| `refresh_dongqiudi_player_season_summaries()` | 保留 |
| `refresh_dongqiudi_player_abilities()` | 保留 |
| `refresh_odds_data()` | 保留 |
| `precompute_recommendations()` | 保留 |
| `refresh_dongqiudi_match_results()` | **新增** |
| `refresh_dongqiudi_standings()` | **新增** |
| `refresh_fifa_rankings()` | **新增**（每月1次） |

#### 5.2 数据源状态追踪更新

**文件**：`backend/app/api/data.py`

- 将 Zafronix 数据源从状态监控中移除
- 新增懂球帝比赛数据、积分榜、FIFA 排名的状态追踪
- 数据刷新状态 API 返回新的主数据源覆盖情况

#### 5.3 配置文件清理

**文件**：`backend/app/config.py`

- 移除 `ZAFRONIX_API_KEY`（如果存在）
- 保留 `ODDS_API_KEY`
- 新增 `FIFA_RANKING_REFRESH_INTERVAL`

---

### 迁移策略

| 步骤 | 内容 | 风险 |
|------|------|------|
| 1 | 新增懂球帝比赛结果爬虫 + 积分榜爬虫 + FIFA 排名爬虫 | 低（新增不影响现有） |
| 2 | 新增 DB 模型 + 数据表 | 低（仅建表） |
| 3 | 新增定时任务 | 低（新增 cron 任务） |
| 4 | 核心算法切换数据源：Elo 更新从 ZafronixMatch → 懂球帝比赛表 | 中（需充分测试） |
| 5 | API 端点切换数据源 | 中（需验证返回值一致） |
| 6 | 移除废弃代码 | 低（代码仍可回滚） |

**回退方案**：
- 每个阶段保留旧数据源代码（标记为 `@deprecated`），通过配置开关控制
- `app/config.py` 中新增 `USE_DONGQIUDI_PRIMARY: bool = True`，设为 `False` 可切回旧源

---

## 实施步骤（按优先级排序）

### Step 1：懂球帝比赛结果爬虫
- 创建 `backend/app/services/dongqiudi_match_results.py`
- 创建对应的 DB 模型（`dongqiudi_match` 表）
- 实现爬虫逻辑：从懂球帝世界杯赛程页面抓取所有比赛
- 实现队名中文 → Team code 的匹配逻辑

### Step 2：懂球帝积分榜爬虫
- 创建 `backend/app/services/dongqiudi_standings.py`
- 创建对应的 DB 模型（`dongqiudi_standings` 表）
- 实现爬虫逻辑：从懂球帝积分榜页面抓取小组排名

### Step 3：FIFA 排名爬虫
- 创建 `backend/app/services/fifa_ranking_fetcher.py`
- 实现爬虫逻辑：从 FIFA 官网抓取最新世界排名
- 更新 Team 表的 fifa_rank 字段

### Step 4：调度器更新
- 移除 `refresh_zafronix_results()` 定时任务
- 移除 `refresh_player_data()` 中的 football-data.org 部分
- 新增 `refresh_dongqiudi_match_results()` 定时任务
- 新增 `refresh_dongqiudi_standings()` 定时任务
- 新增 `refresh_fifa_rankings()` 定时任务

### Step 5：核心算法数据源切换
- Elo 评分从懂球帝比赛结果表读取已完成比赛
- 比赛聚合器从懂球帝比赛表查询数据

### Step 6：API 端点切换
- `matches.py`：从懂球帝比赛表查询
- `teams.py`：赛季数据优先从懂球帝获取，football-data.org 为回退
- `teams.py`：球队身价从懂球帝球员身价聚合
- `data.py`：移除 Zafronix 状态，新增懂球帝状态

### Step 7：前端适配
- `profile_page.dart`：更新数据刷新状态展示
- `api_service.dart`：更新 API 调用

### Step 8：代码清理
- 清理废弃的定时任务代码
- 清理 Football-Data.org 和 Zafronix 的定时调用
- 清理 seed_rankings.py 中的身价数据

---

## 验证方案

1. **懂球帝爬虫测试**：运行新增爬虫，验证数据正确写入 DB
2. **Elo 更新测试**：运行 `update_team_elos_from_completed_matches()`，验证评分更新正常
3. **API 回归测试**：所有 GET/POST API 端点返回格式与之前一致
4. **预测一致性测试**：同一场比赛，新旧数据源下的预测结果差异应 ≤5%
5. **模拟引擎测试**：`python -m pytest tests/core/test_simulation.py -v` 全部通过
6. **全量测试**：`python -m pytest tests/ -v` 保持 29/29 通过

---

## 关键决策记录

| 决策 | 结论 |
|------|------|
| FIFA 排名数据源 | FIFA 官网爬取 |
| 球队身价计算 | 从懂球帝球员 market_value_text 聚合 |
| 俱乐部所在国家 | 忽略（返回空） |
| 博彩赔率数据源 | 保留 The Odds API（不变） |
| Elo 初始值 | 保留种子数据 |
| 旧数据源代码 | 标记 `@deprecated` 保留，`USE_DONGQIUDI_PRIMARY` 配置控制 |
