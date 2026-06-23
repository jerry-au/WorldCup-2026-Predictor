import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/prediction.dart';
import '../services/providers.dart';

final predictionProvider = FutureProvider.autoDispose.family<MatchPrediction, PredictionParams>((ref, params) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.predictMatch(
    teamACode: params.teamACode,
    teamBCode: params.teamBCode,
    matchType: params.matchType,
  );
  if (data == null || data is! Map<String, dynamic>) {
    throw Exception('服务器返回了无效的预测数据');
  }
  return MatchPrediction.fromJson(data);
});

class PredictionParams {
  final String teamACode;
  final String teamBCode;
  final String matchType;

  const PredictionParams({
    required this.teamACode,
    required this.teamBCode,
    this.matchType = 'group',
  });

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PredictionParams &&
          runtimeType == other.runtimeType &&
          teamACode == other.teamACode &&
          teamBCode == other.teamBCode &&
          matchType == other.matchType;

  @override
  int get hashCode => Object.hash(teamACode, teamBCode, matchType);
}
