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

// Provider for players status
final adminDataSourceStatusProvider = Provider.autoDispose<AsyncValue<AdminDataSourceStatus>>((ref) {
  final statusAsync = ref.watch(adminFetchStatusProvider);
  return statusAsync.when(
    data: (data) {
      final dqd = data['dongqiudi_national_rosters'] as Map<String, dynamic>? ?? {};
      final players = dqd['players'] as int? ?? 0;
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
final adminMatchResultsStatusProvider = Provider.autoDispose<AsyncValue<AdminDataSourceStatus>>((ref) {
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
final adminStandingsStatusProvider = Provider.autoDispose<AsyncValue<AdminDataSourceStatus>>((ref) {
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
final adminOddsStatusProvider = Provider.autoDispose<AsyncValue<AdminDataSourceStatus>>((ref) {
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
