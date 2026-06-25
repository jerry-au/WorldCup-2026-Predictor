# WorldCup 2026 Predictor - AI Agent Configuration

## Role
您是 WorldCup 2026 预测项目的 AI 助手，负责帮助开发者进行项目开发、数据分析和功能实现。

---

## 项目概述

**2026 美加墨世界杯球队对战获胜几率预测 App**，Flutter 移动端 + Python FastAPI 后端 + SQLite 数据库。

---

## 项目结构

```
WorldCup/
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── api/               # REST API 端点
│   │   │   ├── teams.py        # 球队详情 API
│   │   │   ├── predict.py      # 预测 + 赛事模拟 API
│   │   │   ├── recommendations.py # 投注推荐 API（含缓存）
│   │   │   └── match.py        # 比赛数据 API
│   │   ├── core/               # 核心算法
│   │   │   ├── elo.py          # Elo 评分计算
│   │   │   ├── poisson.py      # 泊松分布进球预测
│   │   │   ├── prediction.py    # 预测引擎
│   │   │   └── simulation.py   # 蒙特卡洛赛事模拟引擎
│   │   ├── models/             # 数据库模型（SQLAlchemy）
│   │   │   ├── team.py         # 球队模型
│   │   │   ├── player.py       # 球员模型
│   │   │   ├── player_stats.py # 球员赛季数据模型
│   │   │   └── recommendation_cache.py # 投注推荐缓存模型
│   │   ├── schemas/            # Pydantic 数据结构
│   │   ├── services/           # 业务服务
│   │   │   ├── odds.py         # 博彩公司赔率服务（The Odds API）
│   │   │   ├── recommendation.py # 推荐引擎
│   │   │   └── dongqiudi/      # 懂球帝数据抓取
│   │   └── tasks/              # 定时任务调度器
│   ├── seed_data/              # 初始数据（48 队 + 球员）
│   └── tests/                  # 测试用例
│       └── core/
│           └── test_simulation.py  # 模拟引擎测试（6 个用例）
├── flutter_app/               # Flutter 移动端应用
│   └── lib/
│       ├── models/             # 数据模型
│       ├── providers/          # Riverpod 状态管理
│       ├── services/           # API 服务层
│       ├── pages/              # 页面
│       │   ├── home/          # 首页
│       │   ├── prediction/     # 对战预测页
│       │   ├── simulation/     # 赛事模拟页
│       │   ├── teams/         # 球队列表 + 详情页
│       │   ├── betting/       # 投注推荐页
│       │   └── profile/       # 个人页
│       └── widgets/           # 通用组件
├── data/                      # 数据文件
└── docs/                     # 文档
    └── superpowers/
        ├── specs/             # 设计文档
        └── plans/            # 实现计划
```

---

## 功能清单与开发阶段

### P0 — 核心功能 ✅ 已完成

| 功能 | 后端 | 前端 | 状态 |
|------|------|------|------|
| 48 支球队基础数据（Elo/排名/身价） | `models/team.py` | `team.dart` | ✅ |
| 单场比赛预测 API | `core/prediction.py` | — | ✅ |
| 对战预测页 | — | `prediction_page.dart` | ✅ |
| 投注推荐引擎 v1 | `services/recommendation.py` | — | ✅ |

### P1 — 增强功能 ✅ 已完成

| 功能 | 后端 | 前端 | 状态 |
|------|------|------|------|
| 赛事蒙特卡洛模拟引擎 | `core/simulation.py` | — | ✅ |
| 淘汰赛对阵图 | — | `bracket_painter.dart` | ✅ |
| 球队列表 + 详情页 | `api/teams.py` | `team_list_page.dart`, `team_detail_page.dart` | ✅ |
| 球员详情页（含赛季数据 + 首发 XI） | `api/teams.py`, `schemas/team.py` | `team_detail_page.dart` | ✅ |
| 赔率偏差检测 | `services/odds.py` | — | ✅ |
| 模拟引擎测试覆盖（6 个用例） | `tests/core/test_simulation.py` | — | ✅ |
| 赔率缓存优化（数据库 + 预计算） | `models/recommendation_cache.py`, `tasks/scheduler.py` | — | ✅ |

### P2 — 完善功能 ✅ 已完成

| 功能 | 后端 | 前端 | 状态 |
|------|------|------|------|
| 外部数据实时接入（懂球帝爬虫） | `services/dongqiudi/` | — | ✅ |
| 多家博彩公司赔率聚合（The Odds API） | `services/odds.py` | — | ✅ |
| 自动数据刷新调度器 | `tasks/scheduler.py` | — | ✅ |
| 动态刷新策略（比赛日/非比赛日） | `tasks/scheduler.py` | — | ✅ |
| 数据刷新状态追踪 | `models/data_refresh_log.py` | — | ✅ |
| 数据刷新状态 API | `api/data.py` | — | ✅ |
| Flutter 投注推荐 Tab | — | `betting_page.dart` | ✅ |
| Flutter 数据刷新状态展示 | — | `profile_page.dart` | ✅ |

### P3 — 优化功能 ✅ 已完成

| 功能 | 后端 | 前端 | 状态 |
|------|------|------|------|
| UI 动画和过渡效果 | — | `animated_widgets.dart` | ✅ |
| 结果分享功能 | — | `share_service.dart` | ✅ |
| 性能优化（缓存+骨架屏） | — | `cache_service.dart`, `skeleton_widgets.dart` | ✅ |
| 页面切换动画 | — | `app.dart` | ✅ |
| 列表项入场动画 | — | `team_list_page.dart` | ✅ |

---

## 关键技术细节

### 后端核心算法

- **Elo 评分**：`core/elo.py` — 球队实力量化，初始值 1500，K=32
- **进球预测**：`core/poisson.py` — 泊松分布模拟比赛进球数
- **预测引擎**：`core/prediction.py` — 结合 Elo + Poisson 输出胜平负概率
- **推荐引擎**：`services/recommendation.py` — 分析系统概率与市场赔率偏差，筛选价值投注
- **蒙特卡洛模拟**：`core/simulation.py` — 模拟世界杯全部赛程（小组赛 48 场 + 淘汰赛 16 场），统计各队夺冠/晋级概率

### 前端状态管理

- **Riverpod**：`providers/` 下各模块对应独立 Provider
- **API Service**：`services/api_service.dart` — 封装所有后端 API 调用

### 数据库

- SQLite，`backend/app/database.py` 管理连接
- 模型定义在 `backend/app/models/`
- 种子数据在 `backend/seed_data/`

---

## 开发进度速查

```
P0 核心    ✅ 已完成
P1 增强    ✅ 已完成
P2 完善    ✅ 已完成
P3 优化    ✅ 已完成
```

**后端测试**：29/29 通过（6 个模拟引擎测试 + 23 个爬虫测试）

**最新 Commit**：
- `073cbf0` feat: add data freshness indicator to betting page
- `991bf8b` feat: add cache-backed value-bets and discrepancies endpoints
- `b32d4ca` feat: add precompute_recommendations scheduler function
- `6de756f` feat: add RecommendationCache model for odds caching
- `3a3a3c9` feat: add starting XI card and expandable season stats to team detail
- `4135649` feat: add PlayerSeasonStats model and startingXi to TeamDetail
- `2341cbc` feat: add season stats and starting XI to team detail API
- `7eee617` feat: add PlayerSeasonStatsOut schema and starting_xi to TeamDetailOut
- `a33e2bf` feat: add connector lines to knockout bracket painter
- `f8acbb6` test: add group stage, knockout, probability, and tiebreaker tests
- `a9fecf0` test: add simulation engine deterministic test

---

## 端口配置

| 服务 | 端口 | 说明 |
|------|------|------|
| 后端 FastAPI | **9000** | API 服务地址 `http://localhost:9000` |
| 前端 Flutter Web | **9001** | 开发服务器地址 `http://localhost:9001` |

> 重启服务时必须使用上述固定端口，避免端口不一致导致前后端连接失败。

---

## 常用命令

```powershell
# 后端测试
cd backend; python -m pytest tests/ -v

# 后端开发服务器（固定端口 9000）
cd backend; python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload

# Flutter 开发服务器（固定端口 9001）
cd flutter_app; flutter run -d chrome --web-port=9001

# 查看 git 状态
git status
git log --oneline -20
```

---

## Goals
1. 协助开发世界杯预测模型和算法
2. 支持后端 API 开发和调试
3. 帮助实现前端界面和交互
4. 提供数据抓取和处理支持
5. 辅助进行比赛模拟和预测分析

---

## Workflow

### 开发流程
1. **需求分析**: 理解需求并制定实现计划
2. **设计阶段**: 编写技术文档和架构设计
3. **实现阶段**: 编写代码并进行单元测试
4. **审查阶段**: 代码审查和质量保证
5. **验证阶段**: 运行测试并验证功能

### 数据流程
1. **数据抓取**: 从懂球帝等源获取数据
2. **数据处理**: 清洗和转换数据
3. **模型训练**: 更新 Elo 评分和预测模型
4. **预测生成**: 生成比赛预测结果
5. **结果展示**: 通过 API 和前端展示

---

## Available Skills

### Development Skills
- `code-review`: 代码审查和质量检查
- `systematic-debugging`: 系统性调试
- `test-driven-development`: 测试驱动开发
- `finishing-a-development-branch`: 完成开发分支
- `brainstorming`: 头脑风暴（任何创造性工作之前必用）
- `subagent-driven-development`: 子智能体驱动开发（执行多任务计划）
- `writing-plans`: 编写实现计划

### Browser Skills
- `browser_navigate`: 导航网页
- `browser_click`: 点击元素
- `browser_fill`: 填写表单
- `browser_evaluate`: 执行 JavaScript

### Database Skills
- `create_entities`: 创建实体
- `read_graph`: 读取图数据
- `search_nodes`: 搜索节点

---

## Tool Usage Guidelines

### 代码操作
- 使用 `Edit` 工具修改现有文件
- 使用 `Write` 工具创建新文件
- 使用 `Read` 工具读取文件内容
- 使用 `Grep` 工具搜索代码

### 命令执行
- 使用 `RunCommand` 运行 Python 脚本和测试
- 使用 `cd` 切换目录（PowerShell 不支持 `&&`，用分号或换行）
- 使用 `pip` 安装依赖
- 使用 `python -m pytest` 运行测试

### 浏览器操作
- 使用浏览器工具进行网页抓取
- 优先使用 Obscura 作为浏览器后端
- 抓取完成后及时关闭页面

---

## Best Practices

1. **代码规范**: 遵循 PEP8 规范，使用类型注解
2. **测试覆盖**: 关键功能应有单元测试
3. **文档更新**: 代码变更时同步更新文档
4. **错误处理**: 完善的异常处理和日志记录
5. **代码复用**: 抽取公共逻辑到工具函数
6. **YAGNI**: 避免过度工程，专注于当前需求

---

## UI/UX 设计规范

> **强制规则**：所有涉及 UI 结构、视觉设计、交互模式或用户体验的任务，**必须优先调用 `ui-ux-pro-max` 技能**，使用其设计系统搜索和 UX 准则数据库进行决策。

### 触发场景（必须调用）

- 新建/重构页面（Landing Page、Dashboard、列表页、详情页等）
- 创建或修改 UI 组件（按钮、卡片、表单、图表、导航等）
- 选择配色方案、字体搭配、间距标准、布局系统
- 审查 UI 代码的可访问性、视觉一致性或用户体验
- 实现导航结构、动画效果、响应式布局
- 产品级设计决策（风格选择、信息层级、品牌表达）
- 改善界面的感知质量、清晰度或易用性

### 使用方式

```bash
# 生成完整设计系统（首选）
python .trae/skills/ui-ux-pro-max/scripts/search.py "<产品类型> <关键词>" --design-system -p "WorldCup"

# 按领域搜索细节
python .trae/skills/ui-ux-pro-max/scripts/search.py "<关键词>" --domain <domain>

# 搜索 Flutter 栈最佳实践
python .trae/skills/ui-ux-pro-max/scripts/search.py "<关键词>" --stack flutter
```

### 可用领域

| 域 | 用途 |
|---|------|
| `style` | UI 风格（glassmorphism、minimalism 等 67+ 种） |
| `color` | 配色方案（161 套，按产品类型分类） |
| `typography` | 字体搭配（57 组 Google Fonts） |
| `ux` | UX 准则（99 条：无障碍、动画、导航等） |
| `chart` | 图表类型（25 种） |
| `product` | 产品类型推荐（161 种） |

---

## Safety Guidelines
- 不要泄露敏感信息（API keys、密码等）
- 不要执行危险命令（rm -rf、格式化等）
- 定期备份重要数据
- 测试环境和生产环境分离
