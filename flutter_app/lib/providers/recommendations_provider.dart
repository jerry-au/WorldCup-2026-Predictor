import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/recommendation.dart';
import '../services/providers.dart';

final valueBetsProvider = FutureProvider.autoDispose<List<ValueBet>>((ref) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.getValueBets();
  if (data == null || data is! Map<String, dynamic>) {
    throw Exception('Invalid response format for value bets');
  }
  final matches = data['matches'];
  if (matches is! List) throw Exception('Missing matches list in value bets');
  return matches
      .map((e) => ValueBet.fromJson(e as Map<String, dynamic>))
      .toList();
});

final discrepanciesProvider = FutureProvider.autoDispose<List<DiscrepancyAlert>>((ref) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.getDiscrepancies();
  if (data == null || data is! Map<String, dynamic>) {
    throw Exception('Invalid response format for discrepancies');
  }
  final alerts = data['alerts'];
  if (alerts is! List) throw Exception('Missing alerts list in discrepancies');
  return alerts
      .map((e) => DiscrepancyAlert.fromJson(e as Map<String, dynamic>))
      .toList();
});
