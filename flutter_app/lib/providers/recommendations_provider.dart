import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/recommendation.dart';
import '../services/providers.dart';

final valueBetsProvider = FutureProvider.autoDispose<List<ValueBet>>((ref) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.getValueBets();
  if (data == null || data is! Map<String, dynamic>) {
    throw Exception('服务器返回了无效的投注推荐数据');
  }
  final matches = data['matches'];
  if (matches is! List) return [];
  return matches
      .map((e) => ValueBet.fromJson(e as Map<String, dynamic>))
      .toList();
});

final discrepanciesProvider = FutureProvider.autoDispose<List<DiscrepancyAlert>>((ref) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.getDiscrepancies();
  if (data == null || data is! Map<String, dynamic>) {
    throw Exception('服务器返回了无效的偏差检测数据');
  }
  final alerts = data['alerts'];
  if (alerts is! List) return [];
  return alerts
      .map((e) => DiscrepancyAlert.fromJson(e as Map<String, dynamic>))
      .toList();
});
