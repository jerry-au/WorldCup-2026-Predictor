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
