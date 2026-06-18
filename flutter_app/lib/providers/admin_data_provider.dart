import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/providers.dart';

class AdminDataSourceStatus {
  final String name;
  final String displayName;
  final DateTime? lastUpdateTime;
  final bool hasData;
  final bool lastUpdateSuccess;
  final int? recordCount;
  // 持久化的最后操作结果
  final String? lastOperationStatus; // 'success' | 'failed' | null
  final String? lastOperationMessage;
  final DateTime? lastOperationTime;
  final int? lastOperationRecords;

  AdminDataSourceStatus({
    required this.name,
    required this.displayName,
    this.lastUpdateTime,
    this.hasData = false,
    this.lastUpdateSuccess = true,
    this.recordCount,
    this.lastOperationStatus,
    this.lastOperationMessage,
    this.lastOperationTime,
    this.lastOperationRecords,
  });

  AdminDataSourceStatus copyWith({
    String? lastOperationStatus,
    String? lastOperationMessage,
    DateTime? lastOperationTime,
    int? lastOperationRecords,
  }) {
    return AdminDataSourceStatus(
      name: name,
      displayName: displayName,
      lastUpdateTime: lastUpdateTime,
      hasData: hasData,
      lastUpdateSuccess: lastUpdateSuccess,
      recordCount: recordCount,
      lastOperationStatus: lastOperationStatus ?? this.lastOperationStatus,
      lastOperationMessage: lastOperationMessage ?? this.lastOperationMessage,
      lastOperationTime: lastOperationTime ?? this.lastOperationTime,
      lastOperationRecords: lastOperationRecords ?? this.lastOperationRecords,
    );
  }

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

// ─── Task Progress State ──────────────────────────────────

class TaskProgress {
  final String taskId;
  final String status; // running / success / failed / not_found
  final double progress; // 0.0 ~ 100.0
  final String? source;
  final String? refreshType;
  final int? recordsUpdated;
  final String? errorMessage;

  const TaskProgress({
    required this.taskId,
    this.status = 'not_found',
    this.progress = 0.0,
    this.source,
    this.refreshType,
    this.recordsUpdated,
    this.errorMessage,
  });

  bool get isRunning => status == 'running';
  bool get isSuccess => status == 'success';
  bool get isFailed => status == 'failed';
}

// ─── Per-Card Progress Notifier Family ─────────────────────
// 每个卡片独立追踪自己的进度，互不干扰

final cardProgressProviderFamily =
    StateNotifierProvider.family<CardProgressNotifier, TaskProgress?, String>((ref, cardId) {
  return CardProgressNotifier(ref, cardId);
});

class CardProgressNotifier extends StateNotifier<TaskProgress?> {
  final Ref ref;
  final String cardId;
  Timer? _pollTimer;

  CardProgressNotifier(this.ref, this.cardId) : super(null);

  /// 立即设置 running 状态（点击按钮时调用，不等 API 返回）
  void startRunning() {
    _pollTimer?.cancel();
    state = const TaskProgress(
      taskId: '',
      status: 'running',
      progress: 0.0,
    );
  }

  Future<void> startTracking(String taskId) async {
    _pollTimer?.cancel();

    state = TaskProgress(
      taskId: taskId,
      status: 'running',
      progress: 0.0,
    );

    // Start polling every 2 seconds
    _pollTimer = Timer.periodic(const Duration(seconds: 2), (_) async {
      await _pollProgress(taskId);
    });

    // Also poll immediately
    await _pollProgress(taskId);
  }

  Future<void> _pollProgress(String taskId) async {
    try {
      final api = ref.read(apiServiceProvider);
      final data = await api.getDataTaskProgress(taskId);
      final progress = TaskProgress(
        taskId: data['task_id'] ?? taskId,
        status: data['status'] ?? 'not_found',
        progress: (data['progress'] as num?)?.toDouble() ?? 0.0,
        source: data['source'],
        refreshType: data['refresh_type'],
        recordsUpdated: data['records_updated'],
        errorMessage: data['error_message'],
      );

      state = progress;

      // Stop polling when done - 但保留结果状态不清理！
      if (progress.isSuccess || progress.isFailed || progress.status == 'not_found') {
        _pollTimer?.cancel();
        _pollTimer = null;
      }
    } catch (e) {
      // Keep current state on error
    }
  }

  void stopTracking() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}

// ─── Card Operation Result State (持久化) ──────────────────

/// 每个卡片的持久化操作结果（成功/失败/记录数/时间）
final cardResultProviderFamily =
    StateNotifierProvider.family<CardResultNotifier, CardOperationResult?, String>((ref, cardId) {
  return CardResultNotifier();
});

class CardResultNotifier extends StateNotifier<CardOperationResult?> {
  CardResultNotifier() : super(null);

  void setResult(CardOperationResult result) {
    state = result;
  }

  void clear() {
    state = null;
  }
}

class CardOperationResult {
  final bool success;
  final String message;
  final int? recordCount;
  final DateTime time;

  const CardOperationResult({
    required this.success,
    required this.message,
    this.recordCount,
    required this.time,
  });
}

// ─── Fetch Status Provider ─────────────────────────────────

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
