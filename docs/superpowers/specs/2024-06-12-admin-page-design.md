# 管理页面设计文档

## 概述

在个人中心页面新增管理入口，提供数据管理功能模块，包括球员信息更新、比赛结果/积分榜更新、赔率更新三个核心模块。

---

## 架构设计

### 文件结构

```
flutter_app/lib/
├── pages/
│   ├── profile/
│   │   └── profile_page.dart          ← 修改：新增管理入口按钮
│   └── admin/
│       └── admin_page.dart            ← 新建：管理页面
├── services/
│   └── api_service.dart               ← 修改：新增管理相关 API 方法
└── config/
    └── api_config.dart                ← 修改：新增管理端点配置
```

### 数据流

```
用户点击"管理入口" → 跳转 admin_page.dart
    ↓
页面加载 → 调用 GET /data/fetch/status + GET /data/refresh/status
    ↓
展示各模块上次更新时间和状态
    ↓
用户点击"更新" → 调用 POST 触发爬虫
    ↓
后台异步执行 → 更新按钮显示加载中
    ↓
完成后 → 显示更新摘要 SnackBar + 刷新状态
```

---

## 组件设计

### 1. ProfilePage 修改

在个人资料卡片后、数据刷新状态卡片前新增：

```dart
Card(
  child: ListTile(
    leading: Icon(Icons.admin_panel_settings, color: Colors.orange.shade600),
    title: Text('管理面板', style: TextStyle(fontWeight: FontWeight.w600)),
    subtitle: Text('球员、比赛、赔率数据管理'),
    trailing: Icon(Icons.chevron_right),
    onTap: () => Navigator.push(
      context,
      PageRouteBuilder(
        pageBuilder: (context, animation, secondaryAnimation) => AdminPage(),
        transitionsBuilder: (context, animation, secondaryAnimation, child) {
          return SlideTransition(
            position: Tween(
              begin: Offset(1.0, 0.0),
              end: Offset.zero,
            ).animate(CurvedAnimation(parent: animation, curve: Curves.easeInOut)),
            child: child,
          );
        },
      ),
    ),
  ),
)
```

### 2. AdminPage 主页面

采用 `ListView` + 分组 `Card` 布局，顶部为 `AppBar` 带返回按钮。

#### 2.1 球员信息更新模块

**卡片内容：**
- 标题："球员信息更新"
- 副标题：显示上次更新时间（格式：YYYY-MM-DD HH:MM）
- 右侧状态指示器（成功/失败/未更新）
- 操作按钮："更新球员数据"

**状态获取：**
- 调用 `GET /api/v1/data/fetch/status`
- 解析 `dongqiudi_national_rosters.players`、`dongqiudi_national_rosters.players_with_season_summaries`、`dongqiudi_national_rosters.player_abilities`
- 从 `GET /api/v1/data/refresh/status` 中获取 `recent_logs` 提取最近更新时间

**更新触发：**
- 调用 `POST /api/v1/data/refresh/trigger?source=dongqiudi`（触发 roster 抓取）
- 调用 `POST /api/v1/data/fetch/dongqiudi/player-season-summaries`
- 调用 `POST /api/v1/data/fetch/dongqiudi/player-abilities`

**更新摘要反馈：**
更新成功后显示 SnackBar：
```
球员数据更新完成：
• 更新 48 支球队名单
• 更新 520 名球员赛季数据
• 更新 480 名球员能力值
```

#### 2.2 比赛结果/积分榜更新模块

**卡片内容：**
- 标题："比赛结果/积分榜更新"
- 副标题：显示上次更新时间
- 右侧状态指示器
- 两个操作按钮："更新比赛结果"、"更新积分榜"（独立触发）

**更新触发：**
- 比赛结果：`POST /api/v1/data/fetch/results`
- 积分榜：`POST /api/v1/data/fetch/standings`

**更新摘要反馈：**
更新成功后显示 SnackBar：
```
比赛结果更新完成：已获取 64 场比赛数据
```
或
```
积分榜更新完成：已更新 12 个小组排名
```

#### 2.3 赔率更新模块

**卡片内容：**
- 标题："赔率更新"
- 副标题：显示上次更新时间
- 右侧状态指示器
- 操作按钮："更新赔率"

**更新触发：**
- `POST /api/v1/data/refresh/trigger?source=odds`

**更新摘要反馈：**
更新成功后显示 SnackBar：
```
赔率更新完成：已获取 25 场比赛赔率（3 家博彩公司）
```

---

## 状态指示器设计

### 视觉样式

| 状态 | 图标 | 颜色 | 显示文字 |
|------|------|------|---------|
| 成功（24小时内） | `check_circle` | `Colors.green` | "已更新" |
| 成功（超过24小时） | `schedule` | `Colors.orange` | "待更新" |
| 失败 | `error` | `Colors.red` | "更新失败" |
| 从未更新 | `schedule` | `Colors.grey` | "暂无数据" |

### 实现

```dart
class UpdateStatusIndicator extends StatelessWidget {
  final bool success;
  final bool recent; // 24小时内
  final bool hasData;

  const UpdateStatusIndicator({
    required this.success,
    required this.recent,
    required this.hasData,
  });

  @override
  Widget build(BuildContext context) {
    if (!hasData) {
      return _buildIndicator(Icons.schedule, Colors.grey, '暂无数据');
    }
    if (!success) {
      return _buildIndicator(Icons.error, Colors.red, '更新失败');
    }
    if (!recent) {
      return _buildIndicator(Icons.schedule, Colors.orange, '待更新');
    }
    return _buildIndicator(Icons.check_circle, Colors.green, '已更新');
  }
}
```

---

## 错误处理

### API 调用失败

- 显示错误 SnackBar："更新失败，请重试"
- 状态指示器变为红色 error 状态
- 不阻塞其他模块操作

### 网络异常

- Dio 异常捕获后显示："网络连接异常，请检查网络"
- 按钮恢复可点击状态

### 服务器超时

- 显示："服务器响应超时，请稍后重试"

---

## 响应式设计

### 屏幕适配

- 使用 `MediaQuery` 获取屏幕宽度
- 小屏幕（< 600dp）：单列布局
- 中等屏幕（≥ 600dp）：双列卡片布局（`GridView.count(crossAxisCount: 2)`）
- 大屏幕（≥ 900dp）：三列卡片布局

### 文字大小

- 标题：`Theme.of(context).textTheme.titleLarge`
- 副标题：`Theme.of(context).textTheme.bodyMedium`
- 按钮文字：`Theme.of(context).textTheme.labelLarge`

---

## 数据持久化

### 更新状态存储

- 后端通过 `DataRefreshLog` 模型记录每次更新操作
- 前端通过 `GET /data/refresh/status` 获取状态
- 状态包括：更新时间、是否成功、数据来源

### 前端缓存

- 页面加载时获取一次状态
- 更新完成后主动刷新状态
- 不实现本地缓存，依赖后端数据

---

## 测试要点

1. **UI 测试：**
   - 管理入口按钮点击跳转
   - 状态指示器各状态显示
   - 加载状态显示
   - 不同屏幕尺寸布局

2. **功能测试：**
   - 各模块更新触发
   - 更新后状态刷新
   - 错误处理
   - 网络异常处理

3. **集成测试：**
   - 端到端更新流程
   - 后端爬虫触发验证
