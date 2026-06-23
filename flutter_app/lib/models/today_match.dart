import 'match_common.dart';

class TodayMatchesResponse {
  final List<TodayMatch> matches;
  final int total;
  final TodayMatchesCache cache;

  TodayMatchesResponse({
    required this.matches,
    required this.total,
    required this.cache,
  });

  factory TodayMatchesResponse.fromJson(Map<String, dynamic> json) {
    final rawMatches = json['matches'];
    return TodayMatchesResponse(
      matches: rawMatches is List
          ? rawMatches.map((e) => TodayMatch.fromJson(e as Map<String, dynamic>)).toList()
          : const [],
      total: (json['total'] as num?)?.toInt() ?? 0,
      cache: TodayMatchesCache.fromJson((json['cache'] as Map<String, dynamic>?) ?? const {}),
    );
  }
}

class TodayMatch {
  final String matchId;
  final MatchTeam home;
  final MatchTeam away;
  final String? stage;
  final String? groupName;
  final DateTime? commenceTime;
  final MatchPredictionSummary? prediction;
  final MatchOddsSummary? odds;

  TodayMatch({
    required this.matchId,
    required this.home,
    required this.away,
    this.stage,
    this.groupName,
    this.commenceTime,
    this.prediction,
    this.odds,
  });

  factory TodayMatch.fromJson(Map<String, dynamic> json) {
    return TodayMatch(
      matchId: json['match_id'] as String? ?? '',
      home: MatchTeam.fromJson((json['home'] as Map<String, dynamic>?) ?? const {}),
      away: MatchTeam.fromJson((json['away'] as Map<String, dynamic>?) ?? const {}),
      stage: json['stage'] as String?,
      groupName: json['group_name'] as String?,
      commenceTime: DateTime.tryParse(json['commence_time'] as String? ?? ''),
      prediction: json['prediction'] is Map<String, dynamic>
          ? MatchPredictionSummary.fromJson(json['prediction'] as Map<String, dynamic>)
          : null,
      odds: json['odds'] is Map<String, dynamic>
          ? MatchOddsSummary.fromJson(json['odds'] as Map<String, dynamic>)
          : null,
    );
  }

  String get matchType => stage != null && stage!.contains('group') ? 'group' : 'knockout';
}

// MatchTeam, MatchPredictionSummary, MatchOddsSummary 定义在 match_common.dart
class TodayMatchesCache {
  final DateTime? updatedAt;
  final int ttlSeconds;

  TodayMatchesCache({this.updatedAt, required this.ttlSeconds});

  factory TodayMatchesCache.fromJson(Map<String, dynamic> json) {
    return TodayMatchesCache(
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? ''),
      ttlSeconds: (json['ttl_seconds'] as num?)?.toInt() ?? 300,
    );
  }
}
