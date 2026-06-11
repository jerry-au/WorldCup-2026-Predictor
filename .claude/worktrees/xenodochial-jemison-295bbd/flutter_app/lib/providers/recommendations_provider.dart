import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/recommendation.dart';
import '../services/providers.dart';

final valueBetsProvider = FutureProvider.autoDispose<List<ValueBet>>((ref) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.getValueBets();
  return (data['matches'] as List<dynamic>)
      .map((e) => ValueBet.fromJson(e as Map<String, dynamic>))
      .toList();
});

final discrepanciesProvider = FutureProvider.autoDispose<List<DiscrepancyAlert>>((ref) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.getDiscrepancies();
  return (data['alerts'] as List<dynamic>)
      .map((e) => DiscrepancyAlert.fromJson(e as Map<String, dynamic>))
      .toList();
});
