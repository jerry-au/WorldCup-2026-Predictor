import 'match_common.dart';

class OddsHistoryResponse {
  final String matchId;
  final String homeCode;
  final String awayCode;
  final MatchOddsSummary? latestOdds;
  final List<OddsHistoryPoint> points;

  OddsHistoryResponse({
    required this.matchId,
    required this.homeCode,
    required this.awayCode,
    required this.latestOdds,
    required this.points,
  });

  factory OddsHistoryResponse.fromJson(Map<String, dynamic> json) {
    final rawPoints = json['points'];
    return OddsHistoryResponse(
      matchId: json['match_id'] as String? ?? '',
      homeCode: json['home_code'] as String? ?? '',
      awayCode: json['away_code'] as String? ?? '',
      latestOdds: json['latest_odds'] is Map<String, dynamic>
          ? MatchOddsSummary.fromJson(
              json['latest_odds'] as Map<String, dynamic>)
          : null,
      points: rawPoints is List
          ? rawPoints
              .map((e) => OddsHistoryPoint.fromJson(e as Map<String, dynamic>))
              .toList()
          : const [],
    );
  }
}

class OddsHistoryPoint {
  final DateTime? recordedAt;
  final double? avgWin;
  final double? avgDraw;
  final double? avgLose;
  final int providerCount;

  OddsHistoryPoint({
    this.recordedAt,
    this.avgWin,
    this.avgDraw,
    this.avgLose,
    required this.providerCount,
  });

  factory OddsHistoryPoint.fromJson(Map<String, dynamic> json) {
    return OddsHistoryPoint(
      recordedAt: DateTime.tryParse(json['recorded_at'] as String? ?? ''),
      avgWin: (json['avg_win'] as num?)?.toDouble(),
      avgDraw: (json['avg_draw'] as num?)?.toDouble(),
      avgLose: (json['avg_lose'] as num?)?.toDouble(),
      providerCount: (json['provider_count'] as num?)?.toInt() ?? 0,
    );
  }
}
