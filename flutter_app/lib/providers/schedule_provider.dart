import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/providers.dart';
import '../models/schedule_match.dart';

/// 获取所有赛程的 Provider（支持分页）
final allMatchesProvider = FutureProvider.autoDispose.family<AllMatchesResponse, ScheduleFilter>((ref, filter) async {
  final api = ref.watch(apiServiceProvider);
  final json = await api.getAllMatches(
    stage: filter.stage,
    status: filter.status,
    page: filter.page,
    pageSize: filter.pageSize,
  );
  return AllMatchesResponse.fromJson(json);
});

/// 筛选条件
class ScheduleFilter {
  final String? stage;
  final String? status;
  final int page;
  final int pageSize;

  const ScheduleFilter({
    this.stage,
    this.status,
    this.page = 1,
    this.pageSize = 20,
  });

  ScheduleFilter copyWith({
    String? stage,
    String? status,
    int? page,
    int? pageSize,
  }) {
    return ScheduleFilter(
      stage: stage ?? this.stage,
      status: status ?? this.status,
      page: page ?? this.page,
      pageSize: pageSize ?? this.pageSize,
    );
  }
}
