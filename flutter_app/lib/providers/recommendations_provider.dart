import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/recommendation.dart';
import '../services/providers.dart';

final valueBetsProvider = FutureProvider.autoDispose<List<ValueBet>>((ref) async {
  final api = ref.read(apiServiceProvider);
  try {
    final data = await api.getValueBets();
    if (data == null || data is! Map<String, dynamic>) {
      return [];
    }
    final matches = data['matches'];
    if (matches is! List) return [];
    return matches
        .map((e) => ValueBet.fromJson(e as Map<String, dynamic>))
        .toList();
  } catch (e) {
    debugPrint('[Provider] valueBets error: $e');
    return [];
  }
});

final discrepanciesProvider = FutureProvider.autoDispose<List<DiscrepancyAlert>>((ref) async {
  final api = ref.read(apiServiceProvider);
  try {
    final data = await api.getDiscrepancies();
    if (data == null || data is! Map<String, dynamic>) {
      return [];
    }
    final alerts = data['alerts'];
    if (alerts is! List) return [];
    return alerts
        .map((e) => DiscrepancyAlert.fromJson(e as Map<String, dynamic>))
        .toList();
  } catch (e) {
    debugPrint('[Provider] discrepancies error: $e');
    return [];
  }
});
