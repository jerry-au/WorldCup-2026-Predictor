import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/providers.dart';

class DataRefreshStatus {
  final bool isMatchDay;
  final String refreshMode;
  final int refreshIntervalHours;
  final List<DataSourceStatus> sources;
  final List<RefreshLogEntry> recentLogs;
  final DateTime timestamp;

  DataRefreshStatus({
    required this.isMatchDay,
    required this.refreshMode,
    required this.refreshIntervalHours,
    required this.sources,
    required this.recentLogs,
    required this.timestamp,
  });

  factory DataRefreshStatus.fromJson(Map<String, dynamic> json) {
    final scheduler = json['scheduler'] as Map<String, dynamic>;
    final sourcesList = (json['sources'] as List<dynamic>?)
        ?.map((e) => DataSourceStatus.fromJson(e as Map<String, dynamic>))
        .toList() ?? [];
    final logs = (json['recent_logs'] as List<dynamic>?)
        ?.map((e) => RefreshLogEntry.fromJson(e as Map<String, dynamic>))
        .toList() ?? [];

    return DataRefreshStatus(
      isMatchDay: scheduler['match_day'] as bool? ?? false,
      refreshMode: scheduler['refresh_mode'] as String? ?? 'normal',
      refreshIntervalHours: scheduler['refresh_interval_hours'] as int? ?? 8,
      sources: sourcesList,
      recentLogs: logs,
      timestamp: DateTime.tryParse(json['timestamp'] as String? ?? '') ?? DateTime.now(),
    );
  }

  String get modeLabel {
    switch (refreshMode) {
      case 'match_day':
        return '比赛日模式';
      case 'normal':
        return '普通模式';
      default:
        return refreshMode;
    }
  }

  String get nextRefreshHint {
    if (isMatchDay) {
      return '每 $refreshIntervalHours 小时自动刷新';
    }
    return '每 $refreshIntervalHours 小时自动刷新';
  }
}

class DataSourceStatus {
  final String source;
  final DateTime? lastRefresh;
  final DateTime? nextScheduled;
  final bool isActive;
  final int refreshIntervalHours;
  final int matchDayIntervalHours;
  final bool needsRefresh;

  DataSourceStatus({
    required this.source,
    this.lastRefresh,
    this.nextScheduled,
    required this.isActive,
    required this.refreshIntervalHours,
    required this.matchDayIntervalHours,
    required this.needsRefresh,
  });

  factory DataSourceStatus.fromJson(Map<String, dynamic> json) {
    return DataSourceStatus(
      source: json['source'] as String,
      lastRefresh: json['last_refresh'] != null
          ? DateTime.tryParse(json['last_refresh'] as String)
          : null,
      nextScheduled: json['next_scheduled'] != null
          ? DateTime.tryParse(json['next_scheduled'] as String)
          : null,
      isActive: json['is_active'] as bool? ?? true,
      refreshIntervalHours: json['refresh_interval_hours'] as int? ?? 8,
      matchDayIntervalHours: json['match_day_interval_hours'] as int? ?? 4,
      needsRefresh: json['needs_refresh'] as bool? ?? false,
    );
  }

  String get displayName {
    switch (source) {
      case 'the-odds-api':
        return '博彩赔率';
      case 'football-data-org':
        return '球员数据';
      case 'dongqiudi':
        return '懂球帝';
      case 'internal':
        return '投注推荐';
      default:
        return source;
    }
  }

  String get lastRefreshLabel {
    if (lastRefresh == null) return '从未刷新';
    final diff = DateTime.now().difference(lastRefresh!);
    if (diff.inMinutes < 60) {
      return '${diff.inMinutes} 分钟前';
    } else if (diff.inHours < 24) {
      return '${diff.inHours} 小时前';
    } else {
      return '${diff.inDays} 天前';
    }
  }
}

class RefreshLogEntry {
  final int id;
  final String source;
  final String refreshType;
  final String status;
  final DateTime? startedAt;
  final DateTime? completedAt;
  final int recordsUpdated;
  final String? errorMessage;

  RefreshLogEntry({
    required this.id,
    required this.source,
    required this.refreshType,
    required this.status,
    this.startedAt,
    this.completedAt,
    required this.recordsUpdated,
    this.errorMessage,
  });

  factory RefreshLogEntry.fromJson(Map<String, dynamic> json) {
    return RefreshLogEntry(
      id: json['id'] as int? ?? 0,
      source: json['source'] as String,
      refreshType: json['refresh_type'] as String,
      status: json['status'] as String,
      startedAt: json['started_at'] != null
          ? DateTime.tryParse(json['started_at'] as String)
          : null,
      completedAt: json['completed_at'] != null
          ? DateTime.tryParse(json['completed_at'] as String)
          : null,
      recordsUpdated: json['records_updated'] as int? ?? 0,
      errorMessage: json['error_message'] as String?,
    );
  }

  String get durationLabel {
    if (startedAt == null || completedAt == null) return '-';
    final diff = completedAt!.difference(startedAt!);
    if (diff.inSeconds < 60) {
      return '${diff.inSeconds} 秒';
    }
    return '${diff.inMinutes} 分 ${diff.inSeconds % 60} 秒';
  }

  bool get isSuccess => status == 'success';
  bool get isFailed => status == 'failed';
  bool get isRunning => status == 'running';
}

final dataRefreshStatusProvider = FutureProvider.autoDispose<DataRefreshStatus>((ref) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.getDataRefreshStatus();
  return DataRefreshStatus.fromJson(data as Map<String, dynamic>);
});

final refreshLogsProvider = FutureProvider.autoDispose<List<RefreshLogEntry>>((ref) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.getDataRefreshLogs();
  final logs = (data['logs'] as List<dynamic>?)
      ?.map((e) => RefreshLogEntry.fromJson(e as Map<String, dynamic>))
      .toList();
  return logs ?? [];
});