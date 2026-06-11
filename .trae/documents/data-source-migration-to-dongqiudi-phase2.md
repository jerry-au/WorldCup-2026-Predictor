# 数据源迁移 Phase 2 — 全面切换至懂球帝

## 概述

将 WorldCup 2026 预测项目全面切换至以懂球帝为主数据源，其他源仅作为缺少数据时的补充回退。

### 当前状态

| 组件 | 状态 |
|------|------|
| ZafronixTournament 模型移除 | ✅ 已完成 |
| `__init__.py` import 更新 | ✅ 已完成 |
| `zafronix_service.py` 清理（移除 get_tournament/get_cache_status） | ✅ 已完成 |
| `batch_fetch.py` Zafronix 代码移除 | ✅ 已完成 |
| `data.py` `/tournament-overview` 端点新增 | ✅ 已完成 |
| `dongqiudi_match_results.py` 新增 `compute_tournament_overview` | ✅ 已完成 |
| `seed_from_dongqiudi.py` 种子脚本创建 | ✅ 已完成（581行） |
| `scheduler.py` Zafronix 引用清理 | ✅ 已完成 |
| `match_aggregator.py` ZafronixMatch 回退代码 | ✅ 保留作为回退（符合策略） |
| `data.py` Zafronix 废弃端点 | ✅ 保留作为回退（标记 deprecated） |

### 剩余问题

**Bug**: `seed_from_dongqiudi.py` 第 60 行和第 64 行存在重复的 `"KSA"` key：
- `"1640": "KSA"`（第 60 行）
- `"1970": "KSA"`（第 64 行）

第二个 `"1970": "KSA"` 会覆盖第一个，导致 team_id "1640" 对应的 Saudi Arabia 丢失。需要确认正确的 team_id 或分别命名。

---

## Step 1: 修复 seed_from_dongqiudi.py KSA 重复键 Bug

**文件**: `backend\seed_data\seed_from_dongqiudi.py`

**问题**: `DONGQIUDI_TEAM_ID_TO_CODE` 字典中 "KSA" 作为 value 重复出现在两个 key 中：
- `"1640": "KSA"`（第 60 行）
- `"1970": "KSA"`（第 64 行）

Python 字典中后面的 key 会覆盖前面的，导致 team 1640 的数据丢失。

**操作**:
1. 搜索懂球帝数据确认哪个 team_id 是真正的沙特阿拉伯国家队
2. 如果两个都是沙特（不同时期/不同球队），需要区分命名，如 `"KSA"` 和 `"KSA_2"`
3. 或者删除错误的那个，只保留正确的

## Step 2: 验证导入

运行以下命令验证所有修改后文件的导入是否正常：

```powershell
cd d:\code_space\WorldCup\backend
python -c "from app.models.zafronix_data import ZafronixMatch, ZafronixStanding; print('✓ zafronix_data')"
python -c "from app.models import ZafronixMatch, ZafronixStanding; print('✓ models __init__')"
python -c "from app.services.zafronix_service import get_matches; print('✓ zafronix_service')"
python -c "from app.services.dongqiudi_match_results import compute_tournament_overview; print('✓ dongqiudi_match_results')"
python -c "from app.tasks.batch_fetch import run_football_data_batch; print('✓ batch_fetch')"
python -c "from seed_data.seed_from_dongqiudi import seed_from_dongqiudi; print('✓ seed_from_dongqiudi')"
```

## Step 3: 运行测试

```powershell
cd d:\code_space\WorldCup\backend
python -m pytest tests/ -v
```

预期 29/29 测试通过（6 个模拟引擎测试 + 23 个爬虫测试）。

## Step 4: 全局搜索确认无残留引用

搜索 `ZafronixTournament` 确认所有代码中已无引用：

```powershell
cd d:\code_space\WorldCup\backend
python -c "
import ast, os
count = 0
for root, dirs, files in os.walk('.'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, encoding='utf-8') as fh:
                try:
                    tree = ast.parse(fh.read())
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Name) and node.id == 'ZafronixTournament':
                            print(f'Found in {path}')
                            count += 1
                except SyntaxError:
                    pass
print(f'Total references: {count}')
"
```

## 决策记录

| 决策 | 说明 |
|------|------|
| 保留 `match_aggregator.py` 的 ZafronixMatch 回退 | Dongqiudi 无数据时使用 Zafronix 历史数据 |
| 保留 `data.py` 的 Zafronix 废弃端点 | 标记 `deprecated=True`，兼容旧客户端 |
| 不主动创建文档文件 | 除非用户明确要求 |
