import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/today_match.dart';
import '../services/providers.dart';

final todayMatchesProvider = FutureProvider.autoDispose<TodayMatchesResponse>((ref) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.getTodayMatches();
  if (data == null || data is! Map<String, dynamic>) {
    throw Exception('服务器返回了无效的当日赛事数据');
  }
  return TodayMatchesResponse.fromJson(data);
});
