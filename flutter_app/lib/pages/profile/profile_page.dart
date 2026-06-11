import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/data_refresh_provider.dart';
import '../../services/providers.dart';
import '../../pages/admin/admin_page.dart';

class ProfilePage extends ConsumerWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final refreshStatusAsync = ref.watch(dataRefreshStatusProvider);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                CircleAvatar(
                  radius: 32,
                  backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                  child: Icon(Icons.person, size: 32, color: Theme.of(context).colorScheme.primary),
                ),
                const SizedBox(height: 8),
                Text('世界杯预测', style: Theme.of(context).textTheme.titleLarge),
                Text('2026 美加墨', style: TextStyle(color: Colors.grey.shade600)),
              ],
            ),
          ),
        ),
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
        const SizedBox(height: 12),

        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text('数据刷新状态', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                    const Spacer(),
                    refreshStatusAsync.when(
                      loading: () => const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                      error: (_, __) => Icon(Icons.error, color: Colors.red.shade400, size: 16),
                      data: (status) => _RefreshModeChip(status: status),
                    ),
                  ],
                ),
                const Divider(),

                refreshStatusAsync.when(
                  loading: () => const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                  error: (err, _) => Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        Icon(Icons.cloud_off, color: Colors.grey.shade400, size: 40),
                        const SizedBox(height: 8),
                        Text('无法获取刷新状态', style: TextStyle(color: Colors.grey.shade600)),
                        TextButton(
                          onPressed: () => ref.invalidate(dataRefreshStatusProvider),
                          child: const Text('重试'),
                        ),
                      ],
                    ),
                  ),
                  data: (status) => Column(
                    children: [
                      _DataSourceList(sources: status.sources),
                      const SizedBox(height: 12),
                      _RecentLogsSection(logs: status.recentLogs),
                    ],
                  ),
                ),

                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.tonalIcon(
                        onPressed: () async {
                          final api = ref.read(apiServiceProvider);
                          await api.refreshData();
                          ref.invalidate(dataRefreshStatusProvider);
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('数据刷新已触发')),
                            );
                          }
                        },
                        icon: const Icon(Icons.refresh),
                        label: const Text('刷新数据'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    IconButton.filled(
                      onPressed: () => ref.invalidate(dataRefreshStatusProvider),
                      icon: const Icon(Icons.sync),
                      tooltip: '刷新状态',
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),

        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('关于', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const Divider(),
                _aboutRow(Icons.analytics, '预测模型', '混合泊松-Elo'),
                _aboutRow(Icons.sports_soccer, '参赛球队', '48 队'),
                _aboutRow(Icons.calculate, '模拟次数', '10,000 次蒙特卡洛'),
                _aboutRow(Icons.code, '版本', '0.2.0'),
                const SizedBox(height: 8),
                Text(
                  '数据仅供参考，不构成投注建议。请理性投注。',
                  style: TextStyle(color: Colors.grey.shade500, fontSize: 12),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _aboutRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 16, color: Colors.grey),
          const SizedBox(width: 8),
          Text(label, style: const TextStyle(fontSize: 13)),
          const Spacer(),
          Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}

class _RefreshModeChip extends StatelessWidget {
  final DataRefreshStatus status;

  const _RefreshModeChip({required this.status});

  @override
  Widget build(BuildContext context) {
    final isMatchDay = status.isMatchDay;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: isMatchDay ? Colors.orange.shade100 : Colors.blue.shade100,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isMatchDay ? Icons.stadium : Icons.schedule,
            size: 12,
            color: isMatchDay ? Colors.orange.shade700 : Colors.blue.shade700,
          ),
          const SizedBox(width: 4),
          Text(
            status.modeLabel,
            style: TextStyle(
              fontSize: 11,
              color: isMatchDay ? Colors.orange.shade700 : Colors.blue.shade700,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _DataSourceList extends StatelessWidget {
  final List<DataSourceStatus> sources;

  const _DataSourceList({required this.sources});

  @override
  Widget build(BuildContext context) {
    if (sources.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text('暂无数据源', style: TextStyle(color: Colors.grey.shade500)),
      );
    }

    return Column(
      children: sources.map((source) => _DataSourceRow(source: source)).toList(),
    );
  }
}

class _DataSourceRow extends StatelessWidget {
  final DataSourceStatus source;

  const _DataSourceRow({required this.source});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          _StatusIndicator(needsRefresh: source.needsRefresh),
          const SizedBox(width: 8),
          Expanded(
            child: Text(source.displayName, style: const TextStyle(fontSize: 13)),
          ),
          Text(
            source.lastRefreshLabel,
            style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
          ),
        ],
      ),
    );
  }
}

class _StatusIndicator extends StatelessWidget {
  final bool needsRefresh;

  const _StatusIndicator({required this.needsRefresh});

  @override
  Widget build(BuildContext context) {
    if (needsRefresh) {
      return Icon(Icons.sync, size: 14, color: Colors.orange.shade600);
    }
    return Icon(Icons.check_circle, size: 14, color: Colors.green.shade600);
  }
}

class _RecentLogsSection extends StatelessWidget {
  final List<RefreshLogEntry> logs;

  const _RecentLogsSection({required this.logs});

  @override
  Widget build(BuildContext context) {
    if (logs.isEmpty) {
      return const SizedBox.shrink();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Divider(),
        Text(
          '最近刷新记录',
          style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontWeight: FontWeight.w500),
        ),
        const SizedBox(height: 4),
        ...logs.take(3).map((log) => _RefreshLogRow(log: log)),
      ],
    );
  }
}

class _RefreshLogRow extends StatelessWidget {
  final RefreshLogEntry log;

  const _RefreshLogRow({required this.log});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Icon(
            log.isSuccess
                ? Icons.check_circle
                : log.isFailed
                    ? Icons.error
                    : Icons.sync,
            size: 12,
            color: log.isSuccess
                ? Colors.green.shade400
                : log.isFailed
                    ? Colors.red.shade400
                    : Colors.blue.shade400,
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              '${_getSourceLabel(log.source)} - ${log.refreshType}',
              style: const TextStyle(fontSize: 11),
            ),
          ),
          Text(
            log.durationLabel,
            style: TextStyle(fontSize: 10, color: Colors.grey.shade500),
          ),
        ],
      ),
    );
  }

  String _getSourceLabel(String source) {
    switch (source) {
      case 'the-odds-api':
        return '赔率';
      case 'football-data-org':
        return '球员';
      case 'dongqiudi':
        return '懂球帝';
      case 'internal':
        return '推荐';
      default:
        return source;
    }
  }
}