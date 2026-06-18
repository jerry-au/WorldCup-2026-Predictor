import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/admin_data_provider.dart';
import '../../services/api_service.dart';
import '../../services/providers.dart';

// ─── Constants ──────────────────────────────────────────────

const _kCardIds = {
  'players': 'players',
  'matches': 'matches',
  'odds': 'odds',
};

// ─── Main Page ─────────────────────────────────────────────

class AdminPage extends ConsumerWidget {
  const AdminPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F0),
      appBar: AppBar(
        title: const Text('数据管理'),
        elevation: 0,
        backgroundColor: Colors.white,
        foregroundColor: const Color(0xFF1B5E20),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          _PlayerUpdateCard(),
          SizedBox(height: 16),
          _MatchResultsCard(),
          SizedBox(height: 16),
          _OddsUpdateCard(),
          SizedBox(height: 16),
          _SystemInfoCard(),
        ],
      ),
    );
  }
}

// ─── Shared Components ──────────────────────────────────────

class _UpdateCard extends ConsumerWidget {
  final String title;
  final String description;
  final String lastUpdateLabel;
  final bool hasData;
  final bool isSuccess;
  final DateTime? lastUpdateTime;
  final Widget? progressBar;
  final List<Widget> actions;
  // 卡片 ID，用于独立追踪进度
  final String cardId;

  const _UpdateCard({
    required this.title,
    required this.description,
    required this.lastUpdateLabel,
    this.hasData = false,
    this.isSuccess = true,
    this.lastUpdateTime,
    this.progressBar,
    required this.actions,
    required this.cardId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // 监听此卡片的进度状态（独立）
    final progress = ref.watch(cardProgressProviderFamily(cardId));
    // 监听此卡片的持久化结果（独立）
    final result = ref.watch(cardResultProviderFamily(cardId));

    return Card(
      elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      color: Colors.white,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 标题行：标题 + 右侧状态指示器
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title,
                          style: Theme.of(context)
                              .textTheme
                              .titleMedium
                              ?.copyWith(fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      Text(description,
                          style:
                              TextStyle(color: Colors.grey[600], fontSize: 13)),
                    ],
                  ),
                ),
                // 右侧状态指示器 — 持久化显示，不消失
                _buildStatusIndicator(context, progress, result, hasData),
              ],
            ),
            const SizedBox(height: 4),
            // 进度条（仅在 running 时显示）
            if (progress != null && progress.isRunning) ...[
              _CardProgressBar(progress: progress),
            ],
            // 成功/失败结果条（持久化，直到下次操作）
            if (progress != null &&
                !progress.isRunning &&
                progress.taskId.isNotEmpty) ...[
              _ResultBar(progress: progress),
            ],
            // 操作按钮
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 8,
              children: actions.map((action) {
                return action;
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  /// 右侧状态指示器 — 持久化显示操作结果和时间
  Widget _buildStatusIndicator(BuildContext context, TaskProgress? progress,
      CardOperationResult? result, bool hasData) {
    // 正在执行中
    if (progress != null && progress.isRunning) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: const Color(0xFFE8F5E9),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                    strokeWidth: 2, color: const Color(0xFF2E7D32))),
            const SizedBox(width: 6),
            Text('更新中...',
                style: TextStyle(
                    fontSize: 11,
                    color: const Color(0xFF2E7D32),
                    fontWeight: FontWeight.w500)),
          ],
        ),
      );
    }

    // 有持久化结果 — 显示结果
    if (result != null) {
      if (result.success) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.check_circle, color: Colors.green.shade600, size: 16),
            const SizedBox(height: 2),
            Text(
              result.recordCount != null
                  ? '已更新 ${result.recordCount} 条'
                  : '更新成功',
              style: TextStyle(fontSize: 11, color: Colors.green.shade700),
            ),
            Text(
              '${result.time.hour.toString().padLeft(2, '0')}:${result.time.minute.toString().padLeft(2, '0')} 完成',
              style: TextStyle(fontSize: 10, color: Colors.grey.shade500),
            ),
          ],
        );
      } else {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error, color: Colors.red.shade600, size: 16),
            const SizedBox(height: 2),
            Text('更新失败',
                style: TextStyle(fontSize: 11, color: Colors.red.shade700)),
            Text(result.message,
                style: TextStyle(fontSize: 10, color: Colors.grey.shade500),
                overflow: TextOverflow.ellipsis),
          ],
        );
      }
    }

    // 默认静态状态
    if (!hasData) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: const Color(0xFFFFF3E0),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.info_outline, size: 14, color: Colors.orange.shade800),
            const SizedBox(width: 4),
            Text('暂无数据',
                style: TextStyle(fontSize: 11, color: Colors.orange.shade900)),
          ],
        ),
      );
    } else {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: const Color(0xFFE8F5E9),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.check_circle_outline,
                size: 14, color: Colors.green.shade700),
            const SizedBox(width: 4),
            Flexible(
                child: Text(lastUpdateLabel,
                    style:
                        TextStyle(fontSize: 11, color: Colors.green.shade800))),
          ],
        ),
      );
    }
  }
}

/// 进度条组件（仅 running 时使用）
class _CardProgressBar extends StatelessWidget {
  final TaskProgress progress;
  const _CardProgressBar({required this.progress});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(4),
        child: LinearProgressIndicator(
          minHeight: 6,
          backgroundColor: const Color(0xFFE0E0E0),
          valueColor: AlwaysStoppedAnimation<Color>(
              Theme.of(context).colorScheme.primary),
        ),
      ),
    );
  }
}

/// 结果条（完成后持久化显示）
class _ResultBar extends StatelessWidget {
  final TaskProgress progress;
  const _ResultBar({required this.progress});

  @override
  Widget build(BuildContext context) {
    if (progress.isSuccess) {
      return Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: const Color(0xFFE8F5E9),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Icon(Icons.check_circle, color: Colors.green.shade600, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  progress.recordsUpdated != null
                      ? '更新完成！已处理 ${progress.recordsUpdated} 条记录'
                      : '更新完成！',
                  style: TextStyle(
                      color: Colors.green.shade700,
                      fontSize: 13,
                      fontWeight: FontWeight.w500),
                ),
              ),
            ],
          ),
        ),
      );
    }
    if (progress.isFailed) {
      return Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: const Color(0xFFFFEBEE),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Row(
            children: [
              Icon(Icons.error, color: Colors.red.shade600, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  progress.errorMessage ?? '更新失败',
                  style: TextStyle(color: Colors.red.shade700, fontSize: 13),
                ),
              ),
            ],
          ),
        ),
      );
    }
    return const SizedBox.shrink();
  }
}

// ─── Player Update Card ─────────────────────────────────────

class _PlayerUpdateCard extends ConsumerStatefulWidget {
  const _PlayerUpdateCard();

  @override
  ConsumerState<_PlayerUpdateCard> createState() => _PlayerUpdateCardState();
}

class _PlayerUpdateCardState extends ConsumerState<_PlayerUpdateCard> {
  static const String cardId = 'players';

  bool _isUpdatingPlayers = false;
  bool _isUpdatingSummaries = false;
  bool _isUpdatingAbilities = false;

  Future<void> _updatePlayers() async {
    setState(() => _isUpdatingPlayers = true);
    // 立即显示 running 状态
    ref.read(cardProgressProviderFamily(cardId).notifier).startRunning();
    try {
      final api = ref.read(apiServiceProvider);
      final taskId = await api.triggerPlayerDataRefresh();
      if (taskId.isNotEmpty && mounted) {
        ref
            .read(cardProgressProviderFamily(cardId).notifier)
            .startTracking(taskId);
      }
      ref.invalidate(adminFetchStatusProvider);
    } catch (e) {
      if (mounted) {
        ref
            .read(cardResultProviderFamily(cardId).notifier)
            .setResult(CardOperationResult(
              success: false,
              message: e.toString(),
              time: DateTime.now(),
            ));
        ref.read(cardProgressProviderFamily(cardId).notifier).stopTracking();
      }
    } finally {
      if (mounted) setState(() => _isUpdatingPlayers = false);
    }
  }

  Future<void> _updateSummaries() async {
    setState(() => _isUpdatingSummaries = true);
    ref.read(cardProgressProviderFamily(cardId).notifier).startRunning();
    try {
      final api = ref.read(apiServiceProvider);
      final taskId = await api.triggerSeasonSummariesRefresh();
      if (taskId.isNotEmpty && mounted) {
        ref
            .read(cardProgressProviderFamily(cardId).notifier)
            .startTracking(taskId);
      }
      ref.invalidate(adminFetchStatusProvider);
    } catch (e) {
      if (mounted) {
        ref
            .read(cardResultProviderFamily(cardId).notifier)
            .setResult(CardOperationResult(
              success: false,
              message: e.toString(),
              time: DateTime.now(),
            ));
        ref.read(cardProgressProviderFamily(cardId).notifier).stopTracking();
      }
    } finally {
      if (mounted) setState(() => _isUpdatingSummaries = false);
    }
  }

  Future<void> _updateAbilities() async {
    setState(() => _isUpdatingAbilities = true);
    ref.read(cardProgressProviderFamily(cardId).notifier).startRunning();
    try {
      final api = ref.read(apiServiceProvider);
      final taskId = await api.triggerPlayerAbilitiesRefresh();
      if (taskId.isNotEmpty && mounted) {
        ref
            .read(cardProgressProviderFamily(cardId).notifier)
            .startTracking(taskId);
      }
      ref.invalidate(adminFetchStatusProvider);
    } catch (e) {
      if (mounted) {
        ref
            .read(cardResultProviderFamily(cardId).notifier)
            .setResult(CardOperationResult(
              success: false,
              message: e.toString(),
              time: DateTime.now(),
            ));
        ref.read(cardProgressProviderFamily(cardId).notifier).stopTracking();
      }
    } finally {
      if (mounted) setState(() => _isUpdatingAbilities = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusAsync = ref.watch(adminDataSourceStatusProvider);
    final progress = ref.watch(cardProgressProviderFamily(cardId));

    // 当进度变为成功时，写入持久化结果
    if (progress?.isSuccess == true) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref
            .read(cardResultProviderFamily(cardId).notifier)
            .setResult(CardOperationResult(
              success: true,
              message: '',
              recordCount: progress!.recordsUpdated,
              time: DateTime.now(),
            ));
      });
    }
    if (progress?.isFailed == true) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref
            .read(cardResultProviderFamily(cardId).notifier)
            .setResult(CardOperationResult(
              success: false,
              message: progress!.errorMessage ?? '未知错误',
              time: DateTime.now(),
            ));
      });
    }

    return statusAsync.when(
      data: (status) => _UpdateCard(
        title: '球员信息更新',
        description: '球队名单、赛季数据、能力值',
        lastUpdateLabel: status.lastUpdateLabel,
        hasData: status.hasData,
        isSuccess: status.hasData,
        lastUpdateTime: status.lastUpdateTime,
        cardId: cardId,
        actions: [
          ElevatedButton.icon(
            onPressed: _isUpdatingPlayers ||
                    _isUpdatingSummaries ||
                    _isUpdatingAbilities
                ? null
                : _updatePlayers,
            icon: _isUpdatingPlayers
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.person_add, size: 18),
            label: Text(_isUpdatingPlayers ? '更新中...' : '更新球员数据'),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1B5E20),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20)),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            ),
          ),
          OutlinedButton.icon(
            onPressed: _isUpdatingPlayers ||
                    _isUpdatingSummaries ||
                    _isUpdatingAbilities
                ? null
                : _updateSummaries,
            icon: _isUpdatingSummaries
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.bar_chart, size: 18),
            label: Text(_isUpdatingSummaries ? '更新中...' : '更新赛季数据'),
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(0xFF1B5E20),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20)),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            ),
          ),
          OutlinedButton.icon(
            onPressed: _isUpdatingPlayers ||
                    _isUpdatingSummaries ||
                    _isUpdatingAbilities
                ? null
                : _updateAbilities,
            icon: _isUpdatingAbilities
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.auto_awesome, size: 18),
            label: Text(_isUpdatingAbilities ? '更新中...' : '更新能力值'),
            style: OutlinedButton.styleFrom(
              foregroundColor: const Color(0xFF1B5E20),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20)),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            ),
          ),
        ],
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('加载失败: $e')),
    );
  }
}

// ─── Match Results Card ─────────────────────────────────────

class _MatchResultsCard extends ConsumerStatefulWidget {
  const _MatchResultsCard();

  @override
  ConsumerState<_MatchResultsCard> createState() => _MatchResultsCardState();
}

class _MatchResultsCardState extends ConsumerState<_MatchResultsCard> {
  static const String cardId = 'matches';

  bool _isUpdatingResults = false;
  bool _isUpdatingStandings = false;

  Future<void> _updateResults() async {
    setState(() => _isUpdatingResults = true);
    ref.read(cardProgressProviderFamily(cardId).notifier).startRunning();
    try {
      final api = ref.read(apiServiceProvider);
      final taskId = await api.triggerMatchResultsRefresh();
      if (taskId.isNotEmpty && mounted) {
        ref
            .read(cardProgressProviderFamily(cardId).notifier)
            .startTracking(taskId);
      }
      ref.invalidate(adminFetchStatusProvider);
    } catch (e) {
      if (mounted) {
        ref
            .read(cardResultProviderFamily(cardId).notifier)
            .setResult(CardOperationResult(
              success: false,
              message: e.toString(),
              time: DateTime.now(),
            ));
        ref.read(cardProgressProviderFamily(cardId).notifier).stopTracking();
      }
    } finally {
      if (mounted) setState(() => _isUpdatingResults = false);
    }
  }

  Future<void> _updateStandings() async {
    setState(() => _isUpdatingStandings = true);
    ref.read(cardProgressProviderFamily(cardId).notifier).startRunning();
    try {
      final api = ref.read(apiServiceProvider);
      final taskId = await api.triggerStandingsRefresh();
      if (taskId.isNotEmpty && mounted) {
        ref
            .read(cardProgressProviderFamily(cardId).notifier)
            .startTracking(taskId);
      }
      ref.invalidate(adminFetchStatusProvider);
    } catch (e) {
      if (mounted) {
        ref
            .read(cardResultProviderFamily(cardId).notifier)
            .setResult(CardOperationResult(
              success: false,
              message: e.toString(),
              time: DateTime.now(),
            ));
        ref.read(cardProgressProviderFamily(cardId).notifier).stopTracking();
      }
    } finally {
      if (mounted) setState(() => _isUpdatingStandings = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final resultsStatusAsync = ref.watch(adminMatchResultsStatusProvider);
    final standingsStatusAsync = ref.watch(adminStandingsStatusProvider);
    final progress = ref.watch(cardProgressProviderFamily(cardId));

    // 持久化结果
    if (progress?.isSuccess == true) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref
            .read(cardResultProviderFamily(cardId).notifier)
            .setResult(CardOperationResult(
              success: true,
              message: '',
              recordCount: progress!.recordsUpdated,
              time: DateTime.now(),
            ));
      });
    }
    if (progress?.isFailed == true) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref
            .read(cardResultProviderFamily(cardId).notifier)
            .setResult(CardOperationResult(
              success: false,
              message: progress!.errorMessage ?? '未知错误',
              time: DateTime.now(),
            ));
      });
    }

    return resultsStatusAsync.when(
      data: (resultsStatus) => standingsStatusAsync.when(
        data: (standingsStatus) {
          final hasData = resultsStatus.hasData || standingsStatus.hasData;
          DateTime? lastUpdate;
          if (resultsStatus.lastUpdateTime != null &&
              (lastUpdate == null ||
                  resultsStatus.lastUpdateTime!.isAfter(lastUpdate!))) {
            lastUpdate = resultsStatus.lastUpdateTime;
          }
          if (standingsStatus.lastUpdateTime != null &&
              (lastUpdate == null ||
                  standingsStatus.lastUpdateTime!.isAfter(lastUpdate!))) {
            lastUpdate = standingsStatus.lastUpdateTime;
          }
          return _UpdateCard(
            title: '比赛结果/积分榜更新',
            description: '懂球帝赛程、比分、小组排名',
            lastUpdateLabel:
                lastUpdate != null ? resultsStatus.lastUpdateLabel : '从未更新',
            hasData: hasData,
            isSuccess: hasData,
            lastUpdateTime: lastUpdate,
            cardId: cardId,
            actions: [
              ElevatedButton.icon(
                onPressed: _isUpdatingResults || _isUpdatingStandings
                    ? null
                    : _updateResults,
                icon: _isUpdatingResults
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.sports_soccer, size: 18),
                label: Text(_isUpdatingResults ? '更新中...' : '更新比赛结果'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1B5E20),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20)),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                ),
              ),
              OutlinedButton.icon(
                onPressed: _isUpdatingResults || _isUpdatingStandings
                    ? null
                    : _updateStandings,
                icon: _isUpdatingStandings
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Icon(Icons.table_chart, size: 18),
                label: Text(_isUpdatingStandings ? '更新中...' : '更新积分榜'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF1B5E20),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20)),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                ),
              ),
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => resultsStatus.hasData
            ? _UpdateCard(
                title: '比赛结果/积分榜更新',
                description: '懂球帝赛程、比分、小组排名',
                lastUpdateLabel: resultsStatus.lastUpdateLabel,
                hasData: resultsStatus.hasData,
                isSuccess: resultsStatus.hasData,
                lastUpdateTime: resultsStatus.lastUpdateTime,
                cardId: cardId,
                actions: [
                  ElevatedButton.icon(
                    onPressed: _isUpdatingResults || _isUpdatingStandings
                        ? null
                        : _updateResults,
                    icon: const Icon(Icons.sports_soccer, size: 18),
                    label: const Text('更新比赛结果'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF1B5E20),
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20)),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 10),
                    ),
                  ),
                  OutlinedButton.icon(
                    onPressed: _isUpdatingResults || _isUpdatingStandings
                        ? null
                        : _updateStandings,
                    icon: const Icon(Icons.table_chart, size: 18),
                    label: const Text('更新积分榜'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: const Color(0xFF1B5E20),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20)),
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 10),
                    ),
                  ),
                ],
              )
            : const Center(child: Text('加载失败')),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('加载失败: $e')),
    );
  }
}

// ─── Odds Update Card ───────────────────────────────────────

class _OddsUpdateCard extends ConsumerStatefulWidget {
  const _OddsUpdateCard();

  @override
  ConsumerState<_OddsUpdateCard> createState() => _OddsUpdateCardState();
}

class _OddsUpdateCardState extends ConsumerState<_OddsUpdateCard> {
  static const String cardId = 'odds';

  bool _isUpdatingOdds = false;

  Future<void> _updateOdds() async {
    setState(() => _isUpdatingOdds = true);
    ref.read(cardProgressProviderFamily(cardId).notifier).startRunning();
    try {
      final api = ref.read(apiServiceProvider);
      final taskId = await api.triggerOddsRefresh();
      if (taskId.isNotEmpty && mounted) {
        ref
            .read(cardProgressProviderFamily(cardId).notifier)
            .startTracking(taskId);
      }
      ref.invalidate(adminFetchStatusProvider);
    } catch (e) {
      if (mounted) {
        ref
            .read(cardResultProviderFamily(cardId).notifier)
            .setResult(CardOperationResult(
              success: false,
              message: e.toString(),
              time: DateTime.now(),
            ));
        ref.read(cardProgressProviderFamily(cardId).notifier).stopTracking();
      }
    } finally {
      if (mounted) setState(() => _isUpdatingOdds = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final oddsStatusAsync = ref.watch(adminOddsStatusProvider);
    final progress = ref.watch(cardProgressProviderFamily(cardId));

    // 持久化结果
    if (progress?.isSuccess == true) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref
            .read(cardResultProviderFamily(cardId).notifier)
            .setResult(CardOperationResult(
              success: true,
              message: '',
              recordCount: progress!.recordsUpdated,
              time: DateTime.now(),
            ));
      });
    }
    if (progress?.isFailed == true) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        ref
            .read(cardResultProviderFamily(cardId).notifier)
            .setResult(CardOperationResult(
              success: false,
              message: progress!.errorMessage ?? '未知错误',
              time: DateTime.now(),
            ));
      });
    }

    return oddsStatusAsync.when(
      data: (oddsStatus) => _UpdateCard(
        title: '赔率更新',
        description: '博彩公司实时赔率',
        lastUpdateLabel: oddsStatus.lastUpdateLabel,
        hasData: oddsStatus.hasData,
        isSuccess: oddsStatus.hasData,
        lastUpdateTime: oddsStatus.lastUpdateTime,
        cardId: cardId,
        actions: [
          ElevatedButton.icon(
            onPressed: _isUpdatingOdds ? null : _updateOdds,
            icon: _isUpdatingOdds
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Icon(Icons.casino, size: 18),
            label: Text(_isUpdatingOdds ? '更新中...' : '更新赔率'),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1B5E20),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20)),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            ),
          ),
        ],
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('加载失败: $e')),
    );
  }
}

// ─── System Info Card ───────────────────────────────────────

class _SystemInfoCard extends ConsumerWidget {
  const _SystemInfoCard();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statusAsync = ref.watch(adminFetchStatusProvider);

    return statusAsync.when(
      data: (status) {
        final dqd =
            status['dongqiudi_national_rosters'] as Map<String, dynamic>? ?? {};
        final players = dqd['players'] as int? ?? 0;
        final matched = dqd['matched_players'] as int? ?? 0;
        final matches = status['dongqiudi_matches'] as int? ?? 0;
        final completedMatches =
            status['dongqiudi_completed_matches'] as int? ?? 0;
        final queue = status['queue'] as Map<String, dynamic>? ?? {};
        final odds = queue['odds'] as int? ?? 0;

        return Card(
          elevation: 0,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          color: Colors.white,
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('系统数据概览',
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                _InfoRow(label: '球员总数', value: '$players 人'),
                _InfoRow(
                    label: '已匹配球员',
                    value:
                        '$matched 人 (${players > 0 ? ((matched / players * 100)).toStringAsFixed(1) : 0}%)'),
                _InfoRow(
                    label: '比赛场次', value: '$matches 场 ($completedMatches 已完赛)'),
                _InfoRow(label: '赔率记录', value: '$odds 条'),
              ],
            ),
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('加载失败: $e')),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TextStyle(color: Colors.grey[600], fontSize: 13)),
          Text(value,
              style:
                  const TextStyle(fontWeight: FontWeight.w500, fontSize: 13)),
        ],
      ),
    );
  }
}
