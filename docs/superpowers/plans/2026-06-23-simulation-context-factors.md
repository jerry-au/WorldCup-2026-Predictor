# 赛事模拟场景因素实现计划

2026-06-23

## 概述

本计划实现赛事模拟中的小组赛动态战意、默契球、环境和纪律因素。它还会新增数据库持久化的模拟参数预设、管理面板中的可视化调参控件，以及赛事模拟页对当前默认预设的只读展示。

实现拆分为后端预设基础设施、模拟引擎行为、API 集成、Flutter 管理面板 UI、赛事模拟页展示和最终验证。每个任务都应让项目保持在可测试状态。

## 文件映射

### 后端

- `backend/app/models/simulation_preset.py` — 新增 SQLAlchemy 模型，用于持久化模拟参数预设。
- `backend/app/models/__init__.py` — 导出 `SimulationPreset`，确保 `init_db()` 创建表。
- `backend/app/schemas/simulation_preset.py` — Pydantic 请求/响应模型与参数校验。
- `backend/app/services/simulation_preset.py` — 内置预设定义、初始化、加载、更新、复制、重置和设为默认逻辑。
- `backend/app/api/simulation.py` — 预设 CRUD/default 操作的 REST API。
- `backend/app/main.py` — 注册新的 simulation router。
- `backend/app/schemas/predict.py` — 在赛事模拟任务响应中增加可选 `preset_id` 和 `preset_name`。
- `backend/app/api/predict.py` — 模拟开始时加载默认预设，将参数传入引擎，并返回预设元数据。
- `backend/app/core/simulation.py` — 增加参数 dataclass、逐轮小组赛模拟、修正因子计算、平局提升、黄牌/停赛状态和环境因素钩子。
- `backend/tests/core/test_simulation.py` — 扩展核心模拟测试，覆盖确定性和因素影响。
- `backend/tests/api/test_simulation_presets.py` — 新增预设服务/API 测试。

### Flutter

- `flutter_app/lib/models/simulation_preset.dart` — 预设列表/详情和参数分组 Dart 模型。
- `flutter_app/lib/providers/simulation_preset_provider.dart` — Riverpod 状态，负责加载、编辑、保存、复制、重置和设置默认预设。
- `flutter_app/lib/services/api_service.dart` — 预设 API 方法和赛事模拟预设元数据解析。
- `flutter_app/lib/config/api_config.dart` — 模拟预设端点常量。
- `flutter_app/lib/providers/simulation_provider.dart` — 保存/展示赛事模拟开始时返回的预设元数据。
- `flutter_app/lib/pages/admin/admin_page.dart` — 新增紧凑型 `_SimulationPresetCard`，包含分组 Slider。
- `flutter_app/lib/pages/simulation/simulation_page.dart` — 在控制卡片中展示当前默认预设名称。

## 任务

### 任务 1 — 编写默认预设服务的失败测试

**要创建/修改的文件**

- 创建 `backend/tests/api/test_simulation_presets.py`

**实现细节**

新增测试，预期行为如下：

- 默认初始化会创建名为 `保守`、`标准`、`激进` 的内置预设。
- 初始化后恰好只有一个预设是默认预设。
- 默认预设包含设计文档中的保守参数。
- 重复调用初始化函数是幂等的。

优先沿用现有后端测试里的隔离数据库/session 模式。如果没有现成 fixture，就在测试文件中用临时 SQLite engine 直接测试 service function。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/api/test_simulation_presets.py -v
```

预期：测试失败，因为 model/service 尚不存在。

**依赖**

无。

**任务后提交**

不提交；这是失败测试步骤。

### 任务 2 — 实现 `SimulationPreset` 模型和默认预设服务

**要创建/修改的文件**

- 创建 `backend/app/models/simulation_preset.py`
- 修改 `backend/app/models/__init__.py`
- 创建 `backend/app/services/simulation_preset.py`

**实现细节**

模型字段：

```python
id = Column(String(36), primary_key=True)
name = Column(String(80), nullable=False, unique=True)
description = Column(Text, nullable=True)
is_default = Column(Boolean, nullable=False, default=False)
is_builtin = Column(Boolean, nullable=False, default=False)
parameters_json = Column(Text, nullable=False)
created_at = Column(DateTime, default=datetime.utcnow)
updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

服务函数：

- `get_builtin_presets() -> dict[str, dict]`
- `ensure_default_presets(db: Session) -> None`
- `get_default_preset(db: Session) -> SimulationPreset`
- `parse_preset_parameters(preset: SimulationPreset) -> dict`

保守默认参数必须和设计文档完全一致。初始化时将 `保守` 设为 `is_default=True`，`标准` 和 `激进` 设为 `False`。`标准`/`激进` 的值保持克制，并基于保守值调整；具体数值用命名常量表达，不额外写解释性注释。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/api/test_simulation_presets.py -v
```

预期：任务 1 的测试通过。

**依赖**

任务 1。

**任务后提交**

提交信息：

```text
feat: add simulation preset model defaults
```

### 任务 3 — 编写预设更新/default 行为的失败测试

**要创建/修改的文件**

- 修改 `backend/tests/api/test_simulation_presets.py`

**实现细节**

新增测试，预期行为如下：

- 更新预设后会持久化修改后的参数 JSON。
- 将某个预设设为默认时，会清除其他预设的 `is_default`。
- 复制内置预设时，新预设 `is_builtin=False`，参数被复制。
- 重置内置预设时，会恢复原始内置参数。
- 超出允许范围的非法参数会被 schema 或 service 校验拒绝。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/api/test_simulation_presets.py -v
```

预期：新增测试失败，因为 schema/update API 尚未实现。

**依赖**

任务 2。

**任务后提交**

不提交；这是失败测试步骤。

### 任务 4 — 实现预设 schema 和 service 变更操作

**要创建/修改的文件**

- 创建 `backend/app/schemas/simulation_preset.py`
- 修改 `backend/app/services/simulation_preset.py`

**实现细节**

定义 Pydantic 模型：

- `SimulationPresetParameters`
- `MotivationParameters`
- `CollusionParameters`
- `EnvironmentParameters`
- `DisciplineParameters`
- `SimulationPresetOut`
- `SimulationPresetUpdate`
- `SimulationPresetCreate`
- `SimulationPresetDuplicateRequest`

校验范围保持保守：

- 大多数 multiplier：`0.5 <= value <= 1.5`
- cap 的 min 必须小于 max。
- draw boost：`1.0 <= value <= 1.5`

新增 service 函数：

- `list_presets(db)`
- `create_preset(db, body)`
- `update_preset(db, preset_id, body)`
- `set_default_preset(db, preset_id)`
- `duplicate_preset(db, preset_id, name)`
- `reset_builtin_preset(db, preset_id)`

JSON 序列化/反序列化集中在 service 层，确保 API 和引擎共享同一参数形状。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/api/test_simulation_presets.py -v
```

预期：测试通过。

**依赖**

任务 3。

**任务后提交**

提交信息：

```text
feat: support simulation preset mutations
```

### 任务 5 — 编写预设 API endpoint 的失败测试

**要创建/修改的文件**

- 修改 `backend/tests/api/test_simulation_presets.py`

**实现细节**

新增 API 级测试，覆盖：

- `GET /api/v1/simulation/presets`
- `GET /api/v1/simulation/presets/default`
- `POST /api/v1/simulation/presets`
- `PUT /api/v1/simulation/presets/{id}`
- `POST /api/v1/simulation/presets/{id}/set-default`
- `POST /api/v1/simulation/presets/{id}/duplicate`
- `POST /api/v1/simulation/presets/{id}/reset`

验证响应包含 `id`、`name`、`description`、`is_default`、`is_builtin` 和 `parameters`。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/api/test_simulation_presets.py -v
```

预期：测试失败，因为 router 尚未实现。

**依赖**

任务 4。

**任务后提交**

不提交；这是失败测试步骤。

### 任务 6 — 实现模拟预设 API router

**要创建/修改的文件**

- 创建 `backend/app/api/simulation.py`
- 修改 `backend/app/main.py`

**实现细节**

创建 router：

```python
router = APIRouter(prefix="/api/v1/simulation", tags=["simulation"])
```

endpoint 调用任务 4 中的 service 函数。list/default 操作前调用 `ensure_default_presets(db)`，确保全新数据库也有内置预设。

修改 `backend/app/main.py`，导入并 include 新 router。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/api/test_simulation_presets.py -v
```

预期：API 测试通过。

**依赖**

任务 5。

**任务后提交**

提交信息：

```text
feat: add simulation preset API
```

### 任务 7 — 编写预设确定性和参数传递的模拟失败测试

**要创建/修改的文件**

- 修改 `backend/tests/core/test_simulation.py`

**实现细节**

新增测试，预期行为如下：

- `MonteCarloEngine(...).simulate(..., preset_parameters=...)` 接受显式参数。
- 相同 seed + 相同 preset 产生相同结果。
- 空参数或省略参数时，保持与旧行为足够接近，现有测试继续通过。

使用较小的 `num_iterations`，保证测试快速。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/core/test_simulation.py -v
```

预期：新增测试失败，因为 `simulate` 尚不接受 preset 参数。

**依赖**

任务 6。

**任务后提交**

不提交；这是失败测试步骤。

### 任务 8 — 增加模拟参数 dataclass 和兼容旧行为的参数管线

**要创建/修改的文件**

- 修改 `backend/app/core/simulation.py`

**实现细节**

新增 dataclass：

- `SimulationParameters`
- `MotivationConfig`
- `CollusionConfig`
- `EnvironmentConfig`
- `DisciplineConfig`

新增解析函数：

```python
def _parameters_from_dict(data: dict | None) -> SimulationParameters:
    ...
```

更新签名：

```python
def simulate(..., preset_parameters: dict | None = None) -> SimulationResults:

def _simulate_group_stage(..., parameters: SimulationParameters, ...):
```

当前任务只打通参数，不改变模拟行为；除非后续任务显式使用参数，否则保持中性值。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/core/test_simulation.py -v
```

预期：现有测试和新增参数管线测试通过。

**依赖**

任务 7。

**任务后提交**

提交信息：

```text
refactor: pass simulation preset parameters through engine
```

### 任务 9 — 编写逐轮小组赛兼容性的回归测试

**要创建/修改的文件**

- 修改 `backend/tests/core/test_simulation.py`

**实现细节**

新增测试断言：

- 已完成比赛保持固定，并继续影响概率。
- 逐轮模拟后小组排名 sanity 仍成立。
- 空 completed matches 与 `None` 在同 seed 下仍一致。

现有测试已覆盖其中大部分；新增一个聚焦用例：第 1 轮已有一场完成比赛，只模拟剩余比赛。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/core/test_simulation.py -v
```

预期：旧实现可能已经通过；保留为回归覆盖。

**依赖**

任务 8。

**任务后提交**

除非测试文件有实质变更，否则不单独提交；和任务 10 一起提交。

### 任务 10 — 将小组赛重构为三轮向量化模拟

**要创建/修改的文件**

- 修改 `backend/app/core/simulation.py`

**实现细节**

引入：

```python
GROUP_ROUNDS = [
    [(0, 1), (2, 3)],
    [(0, 2), (1, 3)],
    [(0, 3), (1, 2)],
]
```

修改 `_simulate_group_stage`：

- 像现在一样维护 points/GD/GF 数组。
- 先应用已完成比赛。
- 记录 completed pairs，并在对应轮次跳过。
- 每轮之后调用占位 `_update_group_context_state(...)`，暂时返回中性因子。
- 保持最终排名逻辑不变。

注意 `group_rankings[:, gi, pos] = idxs[0] + order[:, pos]` 依赖组内索引连续。继续保持当前 sorted team construction，不扩大重构范围。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/core/test_simulation.py -v
```

预期：全部模拟测试通过。

**依赖**

任务 9。

**任务后提交**

提交信息：

```text
refactor: simulate group stage round by round
```

### 任务 11 — 编写战意因子的失败测试

**要创建/修改的文件**

- 修改 `backend/tests/core/test_simulation.py`

**实现细节**

围绕 helper method 写窄范围测试，避免脆弱的整赛概率断言：

- 两轮后 6 分球队被 `_calculate_motivation_factors` 标记为应用 `qualified_rotation_multiplier`。
- 两轮后 0 分且净胜球很差的球队应用 `eliminated_morale_multiplier`。
- 第 3 轮前排名竞争接近时，争第一/第二球队应用 `top_spot_motivation_multiplier`。
- 多个因子的乘积被 `motivation_min_cap` 和 `motivation_max_cap` 限制。

即使 helper 是私有方法，测试也可以调用，因为这是算法核心逻辑。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/core/test_simulation.py -v
```

预期：测试失败，因为 helper 尚不存在。

**依赖**

任务 10。

**任务后提交**

不提交；这是失败测试步骤。

### 任务 12 — 实现战意因子 helper 和 λ 应用

**要创建/修改的文件**

- 修改 `backend/app/core/simulation.py`

**实现细节**

新增 helper：

```python
def _calculate_motivation_factors(points, gd_arr, gf_arr, round_idx, match_pair, parameters) -> tuple[np.ndarray, np.ndarray]:
    ...

def _apply_factor_caps(factors, min_cap, max_cap):
    return np.clip(factors, min_cap, max_cap)
```

在每场未完成比赛模拟中：

- 计算 base λ。
- 计算长度为 `self.N` 的 `factor_i`、`factor_j` 数组。
- 用 `g_i = self.rng.poisson(λ_i * factor_i)` 和对应 `j` 抽样。

第 1 轮战意因子保持中性；环境/主场因素由后续任务接入。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/core/test_simulation.py -v
```

预期：战意测试通过。

**依赖**

任务 11。

**任务后提交**

提交信息：

```text
feat: apply group stage motivation factors
```

### 任务 13 — 编写打平携手出线和荣誉战随机性的失败测试

**要创建/修改的文件**

- 修改 `backend/tests/core/test_simulation.py`

**实现细节**

新增 helper 级测试：

- `_detect_mutual_draw_scenario(...)` 在第 3 轮双方平局后都安全的场景返回 true。
- `_apply_mutual_draw_boost(...)` 在固定 seed 或受控数组下增加低比分一球胜负被转平的数量。
- 荣誉战随机性会调整 λ 方差或比分离散程度，但不直接改积分榜。

比分后处理测试优先使用确定性数组输入。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/core/test_simulation.py -v
```

预期：测试失败，因为 helper 尚不存在。

**依赖**

任务 12。

**任务后提交**

不提交；这是失败测试步骤。

### 任务 14 — 实现打平携手出线提升和荣誉战随机性

**要创建/修改的文件**

- 修改 `backend/app/core/simulation.py`

**实现细节**

新增：

```python
def _detect_mutual_draw_scenario(...):
    ...

def _apply_mutual_draw_boost(g_i, g_j, mask, boost):
    ...

def _apply_honor_match_randomness(lambda_i, lambda_j, mask, multiplier):
    ...
```

实现规则：

- 打平携手出线只在第 3 轮触发。
- 只把低比分的一球小胜转为平局。
- 不强行把大比分改为平局。
- 荣誉战随机性保守提升不确定性，例如根据 `honor_match_randomness_multiplier` 在 1.0 附近施加小范围随机 λ multiplier。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/core/test_simulation.py -v
```

预期：打平和荣誉战测试通过。

**依赖**

任务 13。

**任务后提交**

提交信息：

```text
feat: model mutual draw and honor match effects
```

### 任务 15 — 编写纪律因素的失败测试

**要创建/修改的文件**

- 修改 `backend/tests/core/test_simulation.py`

**实现细节**

新增测试，预期行为如下：

- 黄牌状态数组按 group/team/iteration 初始化。
- 球队已基本安全且存在黄牌风险时，应用 yellow caution factor。
- 模拟出核心球员停赛后，下一场应用 suspension factor。
- 现有 deterministic seed 行为保持稳定。

测试保持 helper 级别，避免脆弱的整赛概率断言。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/core/test_simulation.py -v
```

预期：测试失败，因为纪律状态尚未实现。

**依赖**

任务 14。

**任务后提交**

不提交；这是失败测试步骤。

### 任务 16 — 实现黄牌和停赛状态

**要创建/修改的文件**

- 修改 `backend/app/core/simulation.py`

**实现细节**

在每个小组模拟中维护：

```python
yellow_risk = np.zeros((self.N, 4), dtype=bool)
suspended_next = np.zeros((self.N, 4), dtype=bool)
```

每场比赛前：

- 对已安全且 `yellow_risk` 为 true 的球队应用 `yellow_card_caution_multiplier`。
- 对 `suspended_next` 为 true 的球队应用 `key_player_suspension_multiplier`，本场后清除。

每场比赛后：

- 用保守概率更新 `yellow_risk` 和 `suspended_next`。
- 基础概率可以是来自保守模型的小常量。

本次不增加球员级状态。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/core/test_simulation.py -v
```

预期：纪律测试通过。

**依赖**

任务 15。

**任务后提交**

提交信息：

```text
feat: add discipline factors to group simulation
```

### 任务 17 — 编写环境/context 因子的失败测试

**要创建/修改的文件**

- 修改 `backend/tests/core/test_simulation.py`

**实现细节**

新增 helper 测试，预期行为如下：

- 东道主球队应用 `home_advantage_multiplier`。
- context factors 被 `context_min_cap` 和 `context_max_cap` 限制。
- 缺少城市/天气/旅途数据时返回中性或保守默认行为，不报错。

使用 `USA`、`MEX`、`CAN` 作为东道主识别测试代码。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/core/test_simulation.py -v
```

预期：测试失败，因为 context helper 尚不存在。

**依赖**

任务 16。

**任务后提交**

不提交；这是失败测试步骤。

### 任务 18 — 实现环境/context 因子

**要创建/修改的文件**

- 修改 `backend/app/core/simulation.py`

**实现细节**

新增：

```python
HOST_TEAM_CODES = {"USA", "MEX", "CAN"}

def _calculate_context_factors(team_codes, match_pair, parameters):
    ...
```

第一版实现：

- 东道主球队应用 `home_advantage_multiplier`。
- 旅途、天气、时差在缺少元数据时保持中性。
- 参数仍完整接入，保证 UI 调整能持久化；等数据源补齐后再启用真实计算。
- 使用 context caps 限制最终 context factor。

在 Poisson 抽样前，将 context factor 与战意、纪律因子一起应用。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/core/test_simulation.py -v
```

预期：context 测试通过。

**依赖**

任务 17。

**任务后提交**

提交信息：

```text
feat: add host and context factors to simulation
```

### 任务 19 — 将默认预设接入赛事模拟 API

**要创建/修改的文件**

- 修改 `backend/app/api/predict.py`
- 修改 `backend/app/schemas/predict.py`

**实现细节**

在 `start_tournament_simulation` 中：

- 确保默认预设存在。
- 加载默认预设。
- 在 `_task_registry[run_id]` 中保存 `preset_id`、`preset_name` 和参数 dict。
- 返回 `TournamentResponse(task_id=..., status="running", preset_id=..., preset_name=...)`。

在 `_run_simulation` 中：

- 像现在一样打开 DB session。
- 从 `_task_registry[task_id]` 读取预设元数据/参数。
- 调用 `engine.simulate(..., preset_parameters=...)`。

在 completed task 响应中：

- 将预设元数据放入 `result`，或在扩展 schema 时放到 `TaskProgressResponse` 顶层。

**测试方式**

运行：

```bash
cd backend; python -m pytest tests/api/test_simulation_presets.py tests/core/test_simulation.py -v
```

可选运行完整后端测试：

```bash
cd backend; python -m pytest tests/ -v
```

预期：相关后端测试全部通过。

**依赖**

任务 18。

**任务后提交**

提交信息：

```text
feat: use default preset for tournament simulations
```

### 任务 20 — 创建 Flutter 预设模型和 API 方法

**要创建/修改的文件**

- 创建 `flutter_app/lib/models/simulation_preset.dart`
- 修改 `flutter_app/lib/config/api_config.dart`
- 修改 `flutter_app/lib/services/api_service.dart`

**实现细节**

Dart 模型：

- `SimulationPreset`
- `SimulationPresetParameters`
- motivation/collusion/environment/discipline 的嵌套分组类
- 用于编辑 Slider 值的 `copyWith`
- `toJson` / `fromJson`

API config 常量：

```dart
static const String simulationPresetsEndpoint = '/simulation/presets';
static const String simulationDefaultPresetEndpoint = '/simulation/presets/default';
```

API service 方法：

- `getSimulationPresets()`
- `getDefaultSimulationPreset()`
- `createSimulationPreset(...)`
- `updateSimulationPreset(...)`
- `setDefaultSimulationPreset(String id)`
- `duplicateSimulationPreset(String id, String name)`
- `resetSimulationPreset(String id)`

**测试方式**

后续 UI 任务完成后统一运行静态分析。当前任务完成后，确保 Dart 格式和类型在任务 25 的 `flutter analyze` 中通过。

**依赖**

任务 19。

**任务后提交**

提交信息：

```text
feat: add Flutter simulation preset API model
```

### 任务 21 — 实现 Flutter 预设 provider

**要创建/修改的文件**

- 创建 `flutter_app/lib/providers/simulation_preset_provider.dart`

**实现细节**

Provider state 字段：

- `List<SimulationPreset> presets`
- `SimulationPreset? selectedPreset`
- `bool isLoading`
- `bool isSaving`
- `String? error`
- `String? successMessage`

Notifier action：

- `loadPresets()`
- `selectPreset(String id)`
- `updateDraft(SimulationPreset preset)`
- `saveSelected()`
- `setDefaultSelected()`
- `duplicateSelected(String name)`
- `resetSelected()`

保持状态管理局部且简单；除了后端持久化，不额外增加全局持久化。

**测试方式**

后续任务 25 运行 Flutter analysis。

**依赖**

任务 20。

**任务后提交**

提交信息：

```text
feat: manage simulation preset state in Flutter
```

### 任务 22 — 在 AdminPage 添加紧凑型模拟预设卡片

**要创建/修改的文件**

- 修改 `flutter_app/lib/pages/admin/admin_page.dart`

**实现细节**

将 `_SimulationPresetCard` 插入 `_OddsUpdateCard()` 之后、`_SystemInfoCard()` 之前。

卡片内容：

- 标题：`模拟参数`
- 说明：`当前模拟使用默认预设，赛事模拟页不可临时切换`
- 预设 Dropdown。
- `当前默认` 状态 chip。
- 操作：`设为默认`、`复制`、`重置`、`保存配置`。
- 分组 Slider：
  - 战意
  - 默契球
  - 环境
  - 纪律
  - 通过 `ExpansionTile` 展示高级设置

在同一文件中新增小型 helper widget：

- `_PresetSlider`
- `_PresetSection`

每个 Slider 必须展示明确 label 和当前数值。Slider 范围与后端校验保持一致。

**测试方式**

后续运行：

```bash
cd flutter_app; flutter analyze
```

UI 实现后，如 Flutter web 可启动，必须进行浏览器预览验证。

**依赖**

任务 21。

**任务后提交**

提交信息：

```text
feat: add admin simulation preset controls
```

### 任务 23 — 在赛事模拟页展示默认预设名称

**要创建/修改的文件**

- 修改 `flutter_app/lib/providers/simulation_provider.dart`
- 修改 `flutter_app/lib/pages/simulation/simulation_page.dart`
- 如需要解析元数据，修改 `flutter_app/lib/services/api_service.dart`

**实现细节**

在 `SimulationState` 中新增：

```dart
final String? presetName;
```

`startTournamentSimulation()` 返回 `preset_name` 后保存该值。在 `_buildControlCard` 的模型说明下方展示：

```text
当前模拟预设：保守
```

如果页面打开后尚未运行模拟，可以选择通过 preset provider 获取默认预设，或暂时展示 `当前模拟预设：默认预设`。优先选择低耦合方案，避免过度联动。

**测试方式**

后续运行：

```bash
cd flutter_app; flutter analyze
```

UI 实现后需要浏览器预览验证。

**依赖**

任务 22。

**任务后提交**

提交信息：

```text
feat: show simulation preset in tournament page
```

### 任务 24 — 准备缺失数据清单输出

**要创建/修改的文件**

- 只有当实现发现设计变更时，才修改 `docs/superpowers/specs/2026-06-23-simulation-context-factors-design.md`。
- 除非 UI 已需要运行时展示，否则优先在最终完成总结中提供缺失数据清单。

**实现细节**

实现完成后，准备面向用户的当前缺失数据源清单：

- 比赛城市/球场。
- 球队大本营/训练地。
- 球队时区和旅行路线。
- 比赛日天气、湿度、海拔。
- 球员黄牌累计。
- 核心球员重要性权重。
- 完整官方同分规则细节。
- 官方小组第三落位规则。

除非实现需要代码可见常量，否则不新增文件。

**测试方式**

除非实现到代码中，否则无自动化测试。

**依赖**

任务 23。

**任务后提交**

只有发生文件变更时才提交。

### 任务 25 — 运行后端测试套件

**要创建/修改的文件**

- 预期不修改文件。

**实现细节**

运行：

```bash
cd backend; python -m pytest tests/ -v
```

如果出现失败，回到对应任务修复。不要为了通过而削弱测试。

**测试方式**

以上命令就是验证方式。

**依赖**

任务 1-24。

**任务后提交**

如果需要修复，使用聚焦的提交信息提交。

### 任务 26 — 运行 Flutter 静态分析

**要创建/修改的文件**

- 预期不修改文件。

**实现细节**

运行：

```bash
cd flutter_app; flutter analyze
```

修复本次工作引入的 analyzer 错误和警告。

**测试方式**

以上命令就是验证方式。

**依赖**

任务 25。

**任务后提交**

如果需要修复，使用聚焦的提交信息提交。

### 任务 27 — 浏览器验证管理面板预设 UI 和赛事模拟页展示

**要创建/修改的文件**

- 除非验证发现问题，否则预期不修改文件。

**实现细节**

如果 Flutter web 可以通过配置启动，使用 preview 工具而不是 Bash 进行 UI 验证。验证内容：

- 管理面板能加载模拟参数卡片。
- 预设 Dropdown 切换后值正确变化。
- Slider 修改后展示新值。
- 保存时显示 loading 和成功/失败反馈。
- 设为默认后默认 chip 正确更新。
- 复制会创建新的自定义预设。
- 重置会恢复内置默认值。
- 赛事模拟页展示当前默认预设名称。
- 运行模拟仍能完成并展示结果。

如果 preview 环境无法运行 Flutter web，需要明确说明限制，并以后台测试和 `flutter analyze` 作为验证依据。

**测试方式**

使用 preview snapshot/console/network 工具验证 UI 行为和错误。

**依赖**

任务 26。

**任务后提交**

如果验证过程中修复了 UI 问题，使用聚焦的提交信息提交。

### 任务 28 — 最终代码审查和简化检查

**要创建/修改的文件**

- 仅限前面任务已修改的文件。

**实现细节**

检查：

- 是否有重复参数解析代码。
- helper function 是否过宽。
- 是否有未使用字段或 import。
- 后端/前端参数命名是否不一致。
- 是否存在只在 UI 层校验、但后端校验不一致的问题。
- 是否引入安全问题，尤其是任意 JSON shape 接收。

如果变更代码已经可用且需要清理，使用 `simplify` skill。

**测试方式**

如果清理改动影响逻辑，重新运行相关测试。

**依赖**

任务 27。

**任务后提交**

只有产生清理变更时才提交。

### 任务 29 — 最终总结和交接

**要创建/修改的文件**

- 预期不修改文件。

**实现细节**

报告：

- 变更内容。
- 通过的测试、静态分析和浏览器检查。
- 跳过的验证及原因。
- 后续数据源工作的缺失数据清单。
- 仍存在的无关本地变更，尤其是 `.claude/settings.local.json`。

**测试方式**

不适用。

**依赖**

任务 28。

**任务后提交**

不提交。
