# 赛事模拟动态战意、默契球与多预设管理设计

> 日期：2026-06-23  
> 状态：设计已确认  
> 范围：后端模拟引擎、模拟参数多预设、管理面板可视化调参、缺失数据清单

## 1. 背景与目标

当前赛事模拟引擎主要基于 Elo/composite rating 与 Poisson 进球模型，对小组赛 6 场比赛一次性抽样。这个实现性能好，但无法表达小组赛后半段常见的动态因素，例如已出线轮换、已出局战意下降、打平携手出线、争排名、挑对手、黄牌保守、主场和环境适应等。

本次设计目标是在不引入宿敌/政治因素的前提下，实现所有当前规划的默契球与战意因素，并让这些因素通过管理面板可视化调整。模拟运行时只使用当前默认预设，普通赛事模拟页不提供临时预设选择。

## 2. 总体方案

采用“后端数据库预设 + 模拟引擎读取默认预设”的方案：

1. 小组赛从一次性模拟 6 场改为 3 轮逐轮模拟。
2. 每轮前基于当前积分、净胜球、进球数与剩余赛程计算出线形势。
3. 根据默认 `SimulationPreset` 计算战意、默契球、环境、纪律修正。
4. 修正后的 λ 继续用 Poisson 抽样比分。
5. 每轮后更新积分榜、黄牌与停赛状态。
6. 管理面板维护多个参数预设，且只能有一个默认预设。
7. `POST /api/v1/predict/tournament` 不接受前端临时参数，始终读取默认预设。

## 3. 模拟参数预设

新增 `SimulationPreset` 数据表，建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string/uuid | 主键 |
| `name` | string | 预设名称，如“保守” |
| `description` | string | 预设说明 |
| `is_default` | bool | 是否当前默认预设 |
| `is_builtin` | bool | 是否内置预设 |
| `parameters_json` | JSON/text | 参数 JSON |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

默认初始化三套内置预设：

| 预设 | 用途 |
|---|---|
| 保守 | 默认启用，场外因素只做小幅修正，不盖过 Elo/Poisson |
| 标准 | 稍微增强战意、默契球和环境影响 |
| 激进 | 用于压力测试和探索场外因素上限，不建议作为默认 |

第一版默认使用“保守”预设。

### 3.1 保守默认参数

```json
{
  "motivation": {
    "qualified_rotation_multiplier": 0.88,
    "eliminated_morale_multiplier": 0.82,
    "top_spot_motivation_multiplier": 1.06,
    "honor_match_randomness_multiplier": 1.10,
    "motivation_min_cap": 0.80,
    "motivation_max_cap": 1.15
  },
  "collusion": {
    "mutual_draw_boost": 1.12,
    "opponent_selection_loss_multiplier": 0.94
  },
  "environment": {
    "home_advantage_multiplier": 1.05,
    "travel_fatigue_multiplier": 0.97,
    "weather_adaptation_multiplier": 0.96,
    "jet_lag_multiplier": 0.97,
    "context_min_cap": 0.85,
    "context_max_cap": 1.10
  },
  "discipline": {
    "yellow_card_caution_multiplier": 0.96,
    "key_player_suspension_multiplier": 0.90
  }
}
```

所有参数后端均可调；管理面板第一屏只展示业务含义明确的参数，cap 等参数放入高级设置。

## 4. 小组赛逐轮模拟

当前 `GROUP_MATCHES` 顺序已经天然对应三轮：

```python
GROUP_ROUNDS = [
    [(0, 1), (2, 3)],
    [(0, 2), (1, 3)],
    [(0, 3), (1, 2)],
]
```

每个小组仍按 numpy 批量处理 `N` 次模拟，但不再一次性循环 6 场，而是：

1. 应用已完成比赛结果。
2. 对第 1 轮未完成比赛抽样。
3. 更新积分、净胜球、进球数。
4. 对第 2 轮开始前计算当前形势与修正因子。
5. 抽样第 2 轮。
6. 再次更新积分榜。
7. 对第 3 轮计算更强的出线形势修正。
8. 抽样第 3 轮。
9. 计算最终小组排名与第三名跨组排名。

已完成比赛必须保持固定结果，不受新参数影响。

## 5. 出线形势与触发逻辑

第一版采用保守启发式，不做复杂全路径精确枚举。

| 因素 | 主要触发 | 影响 |
|---|---|---|
| 打平携手出线 | 第 3 轮，两队平局后都处于安全晋级区 | 提升平局概率 |
| 已出线球队轮换 | 积分与净胜球优势足以基本锁定晋级 | 进攻 λ 下降 |
| 已出局战意不足 | 即使赢球也很难进入前二，第三名希望低 | 进攻 λ 下降 |
| 挑对手 | 强队已基本晋级且第二路径明显更优 | 自身进攻 λ 小幅下降 |
| 争第一/第二名 | 本场结果显著影响前二或第三名排名 | 进攻 λ 小幅提升 |
| 双双出局荣誉战 | 双方都基本无关出线 | 比分随机性上升 |
| 黄牌在身避免停赛 | 核心球员带牌且球队已基本安全 | 进攻 λ 小幅下降 |
| 主场优势 | 东道主球队比赛 | 进攻 λ 小幅提升 |
| 旅途疲劳 | 后续接入城市与驻地数据 | 进攻 λ 小幅下降 |
| 天气适应 | 后续接入城市天气数据 | 进攻 λ 小幅下降 |
| 时差 | 后续接入时区与旅行路线数据 | 进攻 λ 小幅下降 |

### 5.1 已出线判断

满足任一条件时进入“基本已出线”状态：

- 第 2 轮后积分达到 6 分。
- 第 3 轮前排名前二，且领先第 3 名较多。
- 当前积分、净胜球与进球数使其即使输球也大概率前二或前三区间安全。

### 5.2 已出局判断

满足任一条件时进入“基本已出局”状态：

- 第 2 轮后积分为 0 且净胜球较差。
- 第 3 轮前即使获胜也很难进入前二，且第三名晋级希望低。

### 5.3 打平携手出线

主要在第 3 轮触发：

- 两队当前积分接近。
- 平局后双方都能维持前二，或一方前二、一方第三名安全。
- 不考虑宿敌、政治因素和历史恩怨。

### 5.4 挑对手

第一版只做保守处理：

- 只在第 3 轮触发。
- 只对 composite 明显更高的强队触发。
- 球队已经基本晋级。
- 小组第一潜在淘汰赛路径比小组第二明显更强。
- 路径强弱先用当前 bracket slot 潜在对手 composite 粗估，后续在官方落位规则完整后优化。

## 6. 修正因子合成

基础进球期望仍来自 `expected_goals(comp_a, comp_b)`。

每队 λ 合成规则：

```text
λ = base_λ × motivation_factor × context_factor × discipline_factor
```

其中：

```text
motivation_factor = clamp(product(战意与默契相关修正), motivation_min_cap, motivation_max_cap)
context_factor = clamp(product(环境与纪律相关修正), context_min_cap, context_max_cap)
```

这样既允许所有参数可调，也避免多个负面因素叠加后让 λ 过度失真。

## 7. 平局默契处理

`mutual_draw_boost` 不直接改写所有结果，而采用温和后处理：

1. 先用修正后的 λ 抽样比分。
2. 对符合“打平携手出线”的迭代额外抽样一次。
3. 命中时只把小比分胜负拉向平局。
4. 大比分不强制改平。

示例：

| 原比分 | 可调整为 |
|---|---|
| 1-0 / 0-1 | 1-1 |
| 2-1 / 1-2 | 1-1 或 2-2 |
| 3-0 / 0-3 | 不调整 |

## 8. 黄牌与停赛

第一版不依赖真实黄牌数据，采用内置轻量模型：

- 每场按球队随机生成黄牌数量。
- 核心球员风险用 composite 和随机事件代理。
- 若球队已基本出线且核心球员有黄牌风险，应用 `yellow_card_caution_multiplier`。
- 若模拟中触发停赛，则下一场应用 `key_player_suspension_multiplier`。

后续接入真实黄牌和核心球员数据后替换估计逻辑。

## 9. 环境因素

第一版保守启用，数据不足时降级为轻量启发式：

- 主场优势：识别 USA/MEX/CAN 等东道主球队。
- 旅途疲劳：预留参数和合成逻辑，真实距离缺失时不强行夸大。
- 天气适应：可按球队所属地区粗略估计，后续接入城市天气。
- 时差：可按球队所属地区与赛区大致差异估计，后续接入时区和旅行路线。

## 10. API 设计

新增模拟预设 API：

```text
GET    /api/v1/simulation/presets
POST   /api/v1/simulation/presets
GET    /api/v1/simulation/presets/default
PUT    /api/v1/simulation/presets/{id}
POST   /api/v1/simulation/presets/{id}/set-default
POST   /api/v1/simulation/presets/{id}/duplicate
POST   /api/v1/simulation/presets/{id}/reset
```

`POST /api/v1/predict/tournament` 保持不需要前端传 preset，后端自动读取默认预设。

返回任务信息时可附带：

```json
{
  "task_id": "...",
  "status": "running",
  "preset_id": "...",
  "preset_name": "保守"
}
```

## 11. 管理面板 UI

在 `flutter_app/lib/pages/admin/admin_page.dart` 的赔率卡片后、系统信息卡片前新增 `_SimulationPresetCard`。

紧凑卡片式布局：

```text
[模拟参数]
说明：当前模拟使用默认预设，赛事模拟页不可临时切换

预设： 保守 ▼       [设为默认] [复制] [重置]
状态：当前默认

战意
  已出线轮换强度             0.88
  已出局战意下降             0.82
  争第一/第二战意增强         1.06
  荣誉战随机性               1.10

默契球
  打平携手出线平局提升        1.12
  挑对手倾向强度             0.94

环境
  主场优势                   1.05
  旅途疲劳                   0.97
  天气不适应                 0.96
  时差影响                   0.97

纪律
  黄牌保守影响               0.96
  核心停赛影响               0.90

高级设置 v
  战意下限/上限
  环境下限/上限

[保存配置]
```

UX 要求：

- Slider 必须有明确标签和当前数值。
- 保存时显示 loading 状态。
- 保存成功/失败有明确反馈。
- 内置预设不能删除。
- 编辑内置预设时允许保存，但提供“重置内置默认值”。
- 用户可复制内置预设为自定义预设。

## 12. 赛事模拟页展示

赛事模拟页不提供预设选择，只显示当前默认预设名称，例如：

```text
当前模拟预设：保守
```

模拟运行始终使用服务端默认预设，保证多端一致。

## 13. 缺失数据清单

算法完成后应向用户列出还缺少的数据，供后续补充数据源：

| 数据 | 用途 |
|---|---|
| 每场比赛举办城市/球场 | 主场、旅途、天气、时差 |
| 球队驻地/训练基地 | 旅途疲劳 |
| 球队所属时区/旅行路线 | 时差 |
| 比赛当天温度/湿度/海拔 | 天气适应 |
| 球员黄牌累计 | 黄牌保守与停赛 |
| 核心球员名单/重要性权重 | 核心停赛影响 |
| 官方出线规则完整细节 | 精确锁定出线/出局 |
| 淘汰赛官方第三名落位规则 | 挑对手路径判断更准确 |

## 14. 测试策略

### 14.1 后端测试

- 默认预设初始化。
- 多预设 CRUD。
- 只能存在一个默认预设。
- 旧 `run_simulation(...)` 调用不破坏。
- 相同 seed + 相同 preset 结果确定。
- `mutual_draw_boost` 提高时，特定第 3 轮场景平局率上升。
- `qualified_rotation_multiplier` 降低时，已出线队进球期望下降。
- `eliminated_morale_multiplier` 降低时，已出局队表现下降。
- 修正因子被 cap 限制，不出现极端 λ。
- 已完成比赛固定结果不受 preset 影响。

### 14.2 前端测试/验证

- 管理面板能加载预设列表。
- 切换预设后 Slider 展示对应值。
- Slider 修改后能保存。
- 切换默认预设成功。
- 复制预设成功。
- 重置内置预设成功。
- 保存失败展示错误反馈。
- 赛事模拟页展示当前默认预设名称。

## 15. 文件影响范围

预计新增/修改：

```text
backend/app/core/simulation.py
backend/app/models/simulation_preset.py
backend/app/schemas/simulation_preset.py
backend/app/api/simulation.py
backend/app/main.py
backend/tests/core/test_simulation.py
backend/tests/api/test_simulation_presets.py

flutter_app/lib/models/simulation_preset.dart
flutter_app/lib/providers/simulation_preset_provider.dart
flutter_app/lib/pages/admin/admin_page.dart
flutter_app/lib/services/api_service.dart
flutter_app/lib/config/api_config.dart
```

## 16. 非目标

本次不实现：

- 宿敌/政治因素。
- 赛事模拟页临时选择预设。
- 精确真实天气、真实旅行路线、真实黄牌累计接入。
- 大规模重构 Elo/Poisson 基础模型。

这些可以在后续数据源补齐后独立迭代。
