# 管理页面实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在个人中心页面添加管理入口，新建独立的管理页面，实现球员信息、比赛结果/积分榜、赔率三个数据更新模块。

**架构：** ProfilePage 新增入口卡片，点击跳转 AdminPage。AdminPage 通过调用后端 API 获取各数据源更新状态，展示状态指示器，提供手动触发爬虫更新的按钮。更新后显示摘要反馈并刷新状态。

**技术栈：** Flutter (Material Design 3), Riverpod, Dio, FastAPI

---

## 文件结构

```
flutter_app/lib/
├── pages/
│   ├── profile/
│   │   └── profile_page.dart              ← 修改：添加管理入口卡片
│   └── admin/
│       └── admin_page.dart                ← 新建：管理页面主文件
├── services/
│   └── api_service.dart                   ← 修改：新增管理相关 API 方法
├── config/
│   └── api_config.dart                    ← 修改：新增管理端点配置
└── providers/
    └── admin_data_provider.dart           ← 新建：管理页面数据状态 Provider
```

---

### 任务 1：新增 API 端点配置和 API 服务方法

**文件：**
- 修改：`flutter_app/lib/config/api_config.dart`
- 修改：`flutter_app/lib/services/api_service.dart`

- [ ] **步骤 1：添加 API 端点配置**

在 `api_config.dart` 末尾添加新端点：

```dart
  // ─── Admin Data Management ──────────────────────────
  static const String fetchStatusEndpoint = '/data/fetch/status';
  static const String fetchPlayersEndpoint = '/data/refresh/trigger';
  static const String fetchResultsEndpoint = '/data/fetch/results';
  static const String fetchStandingsEndpoint = '/data/fetch/standings';
  static const String fetchOddsEndpoint = '/data/refresh/trigger';
  static const String fetchSeasonSummariesEndpoint = '/data/fetch/dongqiudi/player-season-summaries';
  static const String fetchPlayerAbilitiesEndpoint = '/data/fetch/dongqiudi/player-abilities';
```

- [ ] **步骤 2：添加 ApiService 管理相关方法**

在 `api_service.dart` 末尾（`getDataRefreshLogs` 方法之后）添加新方法：

```dart
  // ─── Admin Data Management ──────────────────────────

  Future<dynamic> getFetchStatus() async {
    final resp = await _dio.get(ApiConfig.fetchStatusEndpoint);
    return resp.data;
  }

  Future<dynamic> triggerPlayerDataRefresh() async {
    final resp = await _dio.post(
      ApiConfig.fetchPlayersEndpoint,
      queryParameters: {'source': 'dongqiudi'},
    );
    return resp.data;
  }

  Future<dynamic> triggerSeasonSummariesRefresh() async {
    final resp = await _dio.post(ApiConfig.fetchSeasonSummariesEndpoint);
    return resp.data;
  }

  Future<dynamic> triggerPlayerAbilitiesRefresh() async {
    final resp = await _dio.post(ApiConfig.fetchPlayerAbilitiesEndpoint);
    return resp.data;
  }

  Future<dynamic> triggerMatchResultsRefresh() async {
    final resp = await _dio.post(ApiConfig.fetchResultsEndpoint);
    return resp.data;
  }

  Future<dynamic> triggerStandingsRefresh() async {
    final resp = await _dio.post(ApiConfig.fetchStandingsEndpoint);
    return resp.data;
  }

  Future<dynamic> triggerOddsRefresh() async {
    final resp = await _dio.post(
      ApiConfig.fetchOddsEndpoint,
      queryParameters: {'source': 'odds'},
    );
    return resp.data;
  }
```

- [ ] **步骤 3：Commit**

```bash
git add flutter_app/lib/config/api_config.dart flutter_app/lib/services/api_service.dart
git commit -m "feat: add admin data management API endpoints and service methods"
```

---

### 任务 2：创建管理页面数据 Provider

**文件：**
- 创建：`flutter_app/lib/providers/admin_data_provider.dart`

- [ ] **步骤 1：创建数据模型和 Provider**

创建 `admin_data_provider.dart`：

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/providers.dart';

class AdminDataSourceStatus {
  final String name;
  final String displayName;
  final DateTime? lastUpdateTime;
  final bool hasData;
  final bool lastUpdateSuccess;
  final int? recordCount;

  AdminDataSourceStatus({
    required this.name,
    required this.displayName,
    this.lastUpdateTime,
    this.hasData = false,
    this.lastUpdateSuccess = true,
    this.recordCount,
  });

  String get lastUpdateLabel {
    if (lastUpdateTime == null) return '从未更新';
    final now = DateTime.now();
    final diff = now.difference(lastUpdateTime!);
    final timeStr = '${lastUpdateTime!.year}-${lastUpdateTime!.month.toString().padLeft(2, '0')}-${lastUpdateTime!.day.toString().padLeft(2, '0')} '
        '${lastUpdateTime!.hour.toString().padLeft(2, '0')}:${lastUpdateTime!.minute.toString().padLeft(2, '0')}';
    if (diff.inMinutes < 1) return '刚刚 ($timeStr)';
    if (diff.inMinutes < 60) return '${diff.inMinutes} 分钟前 ($timeStr)';
    if (diff.inHours < 24) return '${diff.inHours} 小时前 ($timeStr)';
    return '${diff.inDays} 天前 ($timeStr)';
  }
}

final adminFetchStatusProvider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final api = ref.read(apiServiceProvider);
  return await api.getFetchStatus() as Map<String, dynamic>;
});

final adminDataSourceStatusProvider = Provider<AsyncValue<AdminDataSourceStatus>>((ref) {
  final statusAsync = ref.watch(adminFetchStatusProvider);
  return statusAsync.when(
    data: (data) {
      final dqd = data['dongqiudi_national_rosters'] as Map<String, dynamic>? ?? {};
      final players = dqd['players'] as int? ?? 0;
      final summaries = dqd['player_season_summaries'] as int? ?? 0;
      final abilities = dqd['player_abilities'] as int? ?? 0;
      return AsyncValue.data(AdminDataSourceStatus(
        name: 'players',
        displayName: '球员信息',
        hasData: players > 0,
        recordCount: players,
      ));
    },
    loading: () => const AsyncValue.loading(),
    error: (e, _) => AsyncValue.error(e, StackTrace.current),
  );
});

// Provider for match results status
final adminMatchResultsStatusProvider = Provider<AsyncValue<AdminDataSourceStatus>>((ref) {
  final statusAsync = ref.watch(adminFetchStatusProvider);
  return statusAsync.when(
    data: (data) {
      final matches = data['dongqiudi_matches'] as int? ?? 0;
      return AsyncValue.data(AdminDataSourceStatus(
        name: 'matches',
        displayName: '比赛结果',
        hasData: matches > 0,
        recordCount: matches,
      ));
    },
    loading: () => const AsyncValue.loading(),
    error: (e, _) => AsyncValue.error(e, StackTrace.current),
  );
});

// Provider for standings status
final adminStandingsStatusProvider = Provider<AsyncValue<AdminDataSourceStatus>>((ref) {
  final statusAsync = ref.watch(adminFetchStatusProvider);
  return statusAsync.when(
    data: (data) {
      final standings = data['dongqiudi_standings'] as int? ?? 0;
      return AsyncValue.data(AdminDataSourceStatus(
        name: 'standings',
        displayName: '积分榜',
        hasData: standings > 0,
        recordCount: standings,
      ));
    },
    loading: () => const AsyncValue.loading(),
    error: (e, _) => AsyncValue.error(e, StackTrace.current),
  );
});

// Provider for odds status
final adminOddsStatusProvider = Provider<AsyncValue<AdminDataSourceStatus>>((ref) {
  final statusAsync = ref.watch(adminFetchStatusProvider);
  return statusAsync.when(
    data: (data) {
      final queue = data['queue'] as Map<String, dynamic>? ?? {};
      final oddsCount = queue['odds'] as int? ?? 0;
      return AsyncValue.data(AdminDataSourceStatus(
        name: 'odds',
        displayName: '赔率数据',
        hasData: oddsCount > 0,
        recordCount: oddsCount,
      ));
    },
    loading: () => const AsyncValue.loading(),
    error: (e, _) => AsyncValue.error(e, StackTrace.current),
  );
});
```

- [ ] **步骤 2：Commit**

```bash
git add flutter_app/lib/providers/admin_data_provider.dart
git commit -m "feat: add admin data providers for fetch status tracking"
```

---

### 任务 3：修改 ProfilePage 添加管理入口

**文件：**
- 修改：`flutter_app/lib/pages/profile/profile_page.dart:17-33`

- [ ] **步骤 1：添加 AdminPage import**

在文件顶部添加 import：

```dart
import '../../pages/admin/admin_page.dart';
```

- [ ] **步骤 2：在个人资料卡片后添加管理入口卡片**

在第一个 Card（个人资料）之后、第二个 Card（数据刷新状态）之前，插入管理入口卡片：

```dart
        const SizedBox(height: 12),

        // 管理入口卡片
        Card(
          child: ListTile(
            leading: Icon(
              Icons.admin_panel_settings,
              color: Colors.orange.shade600,
              size: 28,
            ),
            title: Text(
              '管理面板',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
            ),
            subtitle: Text(
              '球员、比赛、赔率数据管理',
              style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
            ),
            trailing: Icon(Icons.chevron_right, color: Colors.grey.shade400),
            contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            onTap: () {
              Navigator.push(
                context,
                PageRouteBuilder(
                  pageBuilder: (context, animation, secondaryAnimation) => const AdminPage(),
                  transitionsBuilder: (context, animation, secondaryAnimation, child) {
                    const begin = Offset(1.0, 0.0);
                    const end = Offset.zero;
                    const curve = Curves.easeInOut;
                    var tween = Tween(begin: begin, end: end).chain(CurveTween(curve: curve));
                    return SlideTransition(
                      position: animation.drive(tween),
                      child: child,
                    );
                  },
                ),
              );
            },
          ),
        ),
```

- [ ] **步骤 3：Commit**

```bash
git add flutter_app/lib/pages/profile/profile_page.dart
git commit -m "feat: add admin panel entry card to profile page"
```

---

### 任务 4：创建 AdminPage 管理页面主体

**文件：**
- 创建：`flutter_app/lib/pages/admin/admin_page.dart`

- [ ] **步骤 1：创建 AdminPage 主体框架**

创建 `admin_page.dart` 文件，包含 AppBar、三个功能模块卡片骨架：

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/admin_data_provider.dart';
import '../../services/providers.dart';

class AdminPage extends ConsumerWidget {
  const AdminPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('数据管理'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _PlayerUpdateCard(ref: ref),
          const SizedBox(height: 12),
          _MatchResultsCard(ref: ref),
          const SizedBox(height: 12),
          _OddsUpdateCard(ref: ref),
        ],
      ),
    );
  }
}
```

- [ ] **步骤 2：创建状态指示器组件**

在文件末尾添加状态指示器组件：

```dart
class _UpdateStatusIndicator extends StatelessWidget {
  final bool hasData;
  final bool isSuccess;
  final DateTime? lastUpdateTime;

  const _UpdateStatusIndicator({
    required this.hasData,
    required this.isSuccess,
    this.lastUpdateTime,
  });

  @override
  Widget build(BuildContext context) {
    if (!hasData) {
      return _buildStatus(Icons.schedule, Colors.grey.shade400, '暂无数据');
    }
    if (!isSuccess) {
      return _buildStatus(Icons.error, Colors.red.shade400, '更新失败');
    }
    if (lastUpdateTime == null) {
      return _buildStatus(Icons.schedule, Colors.grey.shade400, '未知');
    }
    final diff = DateTime.now().difference(lastUpdateTime!);
    if (diff.inHours < 24) {
      return _buildStatus(Icons.check_circle, Colors.green.shade600, '已更新');
    }
    return _buildStatus(Icons.schedule, Colors.orange.shade600, '待更新');
  }

  Widget _buildStatus(IconData icon, Color color, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 16, color: color),
        const SizedBox(width: 4),
        Text(label, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w500)),
      ],
    );
  }
}
```

- [ ] **步骤 3：创建通用更新卡片组件**

在状态指示器之前添加通用卡片组件：

```dart
class _UpdateCard extends StatelessWidget {
  final String title;
  final String description;
  final String lastUpdateLabel;
  final bool hasData;
  final bool isSuccess;
  final DateTime? lastUpdateTime;
  final List<_UpdateAction> actions;
  final VoidCallback? onStatusTap;

  const _UpdateCard({
    required this.title,
    required this.description,
    required this.lastUpdateLabel,
    this.hasData = false,
    this.isSuccess = true,
    this.lastUpdateTime,
    required this.actions,
    this.onStatusTap,
  });

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
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        description,
                        style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                      ),
                    ],
                  ),
                ),
                GestureDetector(
                  onTap: onStatusTap,
                  child: _UpdateStatusIndicator(
                    hasData: hasData,
                    isSuccess: isSuccess,
                    lastUpdateTime: lastUpdateTime,
                  ),
                ),
              ],
            ),
            const Divider(),
            if (lastUpdateTime != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  '上次更新: $lastUpdateLabel',
                  style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
                ),
              ),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: actions.map((action) {
                if (action.isSecondary) {
                  return OutlinedButton.icon(
                    onPressed: action.isLoading ? null : action.onTap,
                    icon: action.isLoading
                        ? const SizedBox(
                            width: 14,
                            height: 14,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Icon(action.icon, size: 16),
                    label: Text(action.label),
                  );
                }
                return FilledButton.icon(
                  onPressed: action.isLoading ? null : action.onTap,
                  icon: action.isLoading
                      ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(action.icon, size: 16),
                  label: Text(action.label),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }
}

class _UpdateAction {
  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final bool isLoading;
  final bool isSecondary;

  const _UpdateAction({
    required this.label,
    required this.icon,
    required this.onTap,
    this.isLoading = false,
    this.isSecondary = false,
  });
}
```

- [ ] **步骤 4：Commit**

```bash
git add flutter_app/lib/pages/admin/admin_page.dart
git commit -m "feat: create admin page skeleton with status indicator and update card components"
```

---

### 任务 5：实现球员信息更新模块

**文件：**
- 修改：`flutter_app/lib/pages/admin/admin_page.dart`

- [ ] **步骤 1：添加球员更新卡片组件**

在 `AdminPage` 类之前添加 `_PlayerUpdateCard` 组件：

```dart
class _PlayerUpdateCard extends ConsumerStatefulWidget {
  final WidgetRef ref;

  const _PlayerUpdateCard({required this.ref});

  @override
  ConsumerState<_PlayerUpdateCard> createState() => _PlayerUpdateCardState();
}

class _PlayerUpdateCardState extends ConsumerState<_PlayerUpdateCard> {
  bool _isUpdatingPlayers = false;
  bool _isUpdatingSummaries = false;
  bool _isUpdatingAbilities = false;

  Future<void> _updatePlayers() async {
    setState(() => _isUpdatingPlayers = true);
    try {
      final api = ref.read(apiServiceProvider);
      await api.triggerPlayerDataRefresh();
      ref.invalidate(adminFetchStatusProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('球员数据刷新已触发')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('球员数据刷新失败: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isUpdatingPlayers = false);
      }
    }
  }

  Future<void> _updateSummaries() async {
    setState(() => _isUpdatingSummaries = true);
    try {
      final api = ref.read(apiServiceProvider);
      await api.triggerSeasonSummariesRefresh();
      ref.invalidate(adminFetchStatusProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('球员赛季数据刷新已触发')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('球员赛季数据刷新失败: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isUpdatingSummaries = false);
      }
    }
  }

  Future<void> _updateAbilities() async {
    setState(() => _isUpdatingAbilities = true);
    try {
      final api = ref.read(apiServiceProvider);
      await api.triggerPlayerAbilitiesRefresh();
      ref.invalidate(adminFetchStatusProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('球员能力值刷新已触发')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('球员能力值刷新失败: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isUpdatingAbilities = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusAsync = ref.watch(adminDataSourceStatusProvider);

    return statusAsync.when(
      data: (status) {
        return _UpdateCard(
          title: '球员信息更新',
          description: '球队名单、赛季数据、能力值',
          lastUpdateLabel: status.lastUpdateLabel,
          hasData: status.hasData,
          lastUpdateTime: status.lastUpdateTime,
          actions: [
            _UpdateAction(
              label: '更新球员数据',
              icon: Icons.person,
              onTap: _updatePlayers,
              isLoading: _isUpdatingPlayers,
            ),
            _UpdateAction(
              label: '更新赛季数据',
              icon: Icons.bar_chart,
              onTap: _updateSummaries,
              isLoading: _isUpdatingSummaries,
              isSecondary: true,
            ),
            _UpdateAction(
              label: '更新能力值',
              icon: Icons.speed,
              onTap: _updateAbilities,
              isLoading: _isUpdatingAbilities,
              isSecondary: true,
            ),
          ],
        );
      },
      loading: () => const Card(
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Center(child: CircularProgressIndicator()),
        ),
      ),
      error: (e, _) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.error, color: Colors.red.shade400, size: 32),
                const SizedBox(height: 8),
                Text('获取状态失败', style: TextStyle(color: Colors.grey.shade600)),
                TextButton(
                  onPressed: () => ref.invalidate(adminFetchStatusProvider),
                  child: const Text('重试'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **步骤 2：Commit**

```bash
git add flutter_app/lib/pages/admin/admin_page.dart
git commit -m "feat: implement player data update module in admin page"
```

---

### 任务 6：实现比赛结果/积分榜更新模块

**文件：**
- 修改：`flutter_app/lib/pages/admin/admin_page.dart`

- [ ] **步骤 1：添加比赛结果和积分榜卡片组件**

在 `_PlayerUpdateCard` 之后添加：

```dart
class _MatchResultsCard extends ConsumerStatefulWidget {
  final WidgetRef ref;

  const _MatchResultsCard({required this.ref});

  @override
  ConsumerState<_MatchResultsCard> createState() => _MatchResultsCardState();
}

class _MatchResultsCardState extends ConsumerState<_MatchResultsCard> {
  bool _isUpdatingResults = false;
  bool _isUpdatingStandings = false;

  Future<void> _updateResults() async {
    setState(() => _isUpdatingResults = true);
    try {
      final api = ref.read(apiServiceProvider);
      await api.triggerMatchResultsRefresh();
      ref.invalidate(adminFetchStatusProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('比赛结果刷新已触发')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('比赛结果刷新失败: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isUpdatingResults = false);
      }
    }
  }

  Future<void> _updateStandings() async {
    setState(() => _isUpdatingStandings = true);
    try {
      final api = ref.read(apiServiceProvider);
      await api.triggerStandingsRefresh();
      ref.invalidate(adminFetchStatusProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('积分榜刷新已触发')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('积分榜刷新失败: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isUpdatingStandings = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final resultsAsync = ref.watch(adminMatchResultsStatusProvider);
    final standingsAsync = ref.watch(adminStandingsStatusProvider);

    return resultsAsync.when(
      data: (resultsStatus) {
        return standingsAsync.when(
          data: (standingsStatus) {
            final lastUpdate = resultsStatus.lastUpdateTime ?? standingsStatus.lastUpdateTime;
            final hasData = resultsStatus.hasData || standingsStatus.hasData;
            return _UpdateCard(
              title: '比赛结果/积分榜更新',
              description: '懂球帝赛程、比分、小组排名',
              lastUpdateLabel: lastUpdate != null
                  ? resultsStatus.lastUpdateLabel
                  : '从未更新',
              hasData: hasData,
              lastUpdateTime: lastUpdate,
              actions: [
                _UpdateAction(
                  label: '更新比赛结果',
                  icon: Icons.sports_soccer,
                  onTap: _updateResults,
                  isLoading: _isUpdatingResults,
                ),
                _UpdateAction(
                  label: '更新积分榜',
                  icon: Icons.table_chart,
                  onTap: _updateStandings,
                  isLoading: _isUpdatingStandings,
                  isSecondary: true,
                ),
              ],
            );
          },
          loading: () => const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Center(child: CircularProgressIndicator()),
            ),
          ),
          error: (e, _) => Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.error, color: Colors.red.shade400, size: 32),
                    const SizedBox(height: 8),
                    Text('获取状态失败', style: TextStyle(color: Colors.grey.shade600)),
                    TextButton(
                      onPressed: () => ref.invalidate(adminFetchStatusProvider),
                      child: const Text('重试'),
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
      loading: () => const Card(
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Center(child: CircularProgressIndicator()),
        ),
      ),
      error: (e, _) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.error, color: Colors.red.shade400, size: 32),
                const SizedBox(height: 8),
                Text('获取状态失败', style: TextStyle(color: Colors.grey.shade600)),
                TextButton(
                  onPressed: () => ref.invalidate(adminFetchStatusProvider),
                  child: const Text('重试'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **步骤 2：Commit**

```bash
git add flutter_app/lib/pages/admin/admin_page.dart
git commit -m "feat: implement match results and standings update module in admin page"
```

---

### 任务 7：实现赔率更新模块

**文件：**
- 修改：`flutter_app/lib/pages/admin/admin_page.dart`

- [ ] **步骤 1：添加赔率更新卡片组件**

在 `_MatchResultsCard` 之后添加：

```dart
class _OddsUpdateCard extends ConsumerStatefulWidget {
  final WidgetRef ref;

  const _OddsUpdateCard({required this.ref});

  @override
  ConsumerState<_OddsUpdateCard> createState() => _OddsUpdateCardState();
}

class _OddsUpdateCardState extends ConsumerState<_OddsUpdateCard> {
  bool _isUpdatingOdds = false;

  Future<void> _updateOdds() async {
    setState(() => _isUpdatingOdds = true);
    try {
      final api = ref.read(apiServiceProvider);
      await api.triggerOddsRefresh();
      ref.invalidate(adminFetchStatusProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('赔率数据刷新已触发')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('赔率数据刷新失败: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isUpdatingOdds = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final oddsAsync = ref.watch(adminOddsStatusProvider);

    return oddsAsync.when(
      data: (oddsStatus) {
        return _UpdateCard(
          title: '赔率更新',
          description: '博彩公司实时赔率',
          lastUpdateLabel: oddsStatus.lastUpdateLabel,
          hasData: oddsStatus.hasData,
          lastUpdateTime: oddsStatus.lastUpdateTime,
          actions: [
            _UpdateAction(
              label: '更新赔率',
              icon: Icons.monetization_on,
              onTap: _updateOdds,
              isLoading: _isUpdatingOdds,
            ),
          ],
        );
      },
      loading: () => const Card(
        child: Padding(
          padding: EdgeInsets.all(16),
          child: Center(child: CircularProgressIndicator()),
        ),
      ),
      error: (e, _) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.error, color: Colors.red.shade400, size: 32),
                const SizedBox(height: 8),
                Text('获取状态失败', style: TextStyle(color: Colors.grey.shade600)),
                TextButton(
                  onPressed: () => ref.invalidate(adminFetchStatusProvider),
                  child: const Text('重试'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
```

- [ ] **步骤 2：Commit**

```bash
git add flutter_app/lib/pages/admin/admin_page.dart
git commit -m "feat: implement odds update module in admin page"
```

---

### 任务 8：测试验证

**验证步骤：**

- [ ] **步骤 1：检查 Flutter 编译**

```bash
cd flutter_app
flutter analyze
```

预期：无 error，可能有少量 warning（可忽略）

- [ ] **步骤 2：运行 Web 测试**

```bash
cd flutter_app
flutter run -d web-server --web-port=9001
```

验证清单：
1. 打开 http://localhost:9001
2. 切换到"我的"页面，确认"管理面板"卡片显示
3. 点击"管理面板"，确认带滑动动画跳转到管理页
4. 确认三个模块卡片正常显示
5. 确认状态指示器显示正确
6. 点击各更新按钮，确认加载状态和 SnackBar 反馈
7. 点击返回按钮，确认返回个人中心

- [ ] **步骤 3：测试后端 API 连通性**

确保后端服务器运行在 http://127.0.0.1:9000

```bash
cd backend
python -m app.main
```

验证 API 端点：
```bash
curl http://127.0.0.1:9000/api/v1/data/fetch/status
curl -X POST http://127.0.0.1:9000/api/v1/data/fetch/results
curl -X POST "http://127.0.0.1:9000/api/v1/data/refresh/trigger?source=odds"
```

- [ ] **步骤 4：最终 Commit**

```bash
git add flutter_app/
git commit -m "feat: complete admin page with all data update modules"
```
