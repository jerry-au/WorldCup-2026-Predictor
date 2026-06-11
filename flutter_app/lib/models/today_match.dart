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

class MatchTeam {
  final String code;
  final String name;
  final String? nameCn;
  final String? flagUrl;

  MatchTeam({required this.code, required this.name, this.nameCn, this.flagUrl});

  factory MatchTeam.fromJson(Map<String, dynamic> json) {
    return MatchTeam(
      code: json['code'] as String? ?? '',
      name: json['name'] as String? ?? '',
      nameCn: json['name_cn'] as String?,
      flagUrl: json['flag_url'] as String?,
    );
  }
}

class MatchPredictionSummary {
  final double win;
  final double draw;
  final double lose;
  final double systemConfidence;

  MatchPredictionSummary({
    required this.win,
    required this.draw,
    required this.lose,
    required this.systemConfidence,
  });

  factory MatchPredictionSummary.fromJson(Map<String, dynamic> json) {
    return MatchPredictionSummary(
      win: (json['win'] as num?)?.toDouble() ?? 0,
      draw: (json['draw'] as num?)?.toDouble() ?? 0,
      lose: (json['lose'] as num?)?.toDouble() ?? 0,
      systemConfidence: (json['system_confidence'] as num?)?.toDouble() ?? 0,
    );
  }
}

class MatchOddsSummary {
  final double? avgWin;
  final double? avgDraw;
  final double? avgLose;
  final double? bestWin;
  final double? bestDraw;
  final double? bestLose;
  final String? bestWinProvider;
  final String? bestDrawProvider;
  final String? bestLoseProvider;
  final int providerCount;
  final DateTime? updatedAt;

  MatchOddsSummary({
    this.avgWin,
    this.avgDraw,
    this.avgLose,
    this.bestWin,
    this.bestDraw,
    this.bestLose,
    this.bestWinProvider,
    this.bestDrawProvider,
    this.bestLoseProvider,
    required this.providerCount,
    this.updatedAt,
  });

  factory MatchOddsSummary.fromJson(Map<String, dynamic> json) {
    return MatchOddsSummary(
      avgWin: (json['avg_win'] as num?)?.toDouble(),
      avgDraw: (json['avg_draw'] as num?)?.toDouble(),
      avgLose: (json['avg_lose'] as num?)?.toDouble(),
      bestWin: (json['best_win'] as num?)?.toDouble(),
      bestDraw: (json['best_draw'] as num?)?.toDouble(),
      bestLose: (json['best_lose'] as num?)?.toDouble(),
      bestWinProvider: json['best_win_provider'] as String?,
      bestDrawProvider: json['best_draw_provider'] as String?,
      bestLoseProvider: json['best_lose_provider'] as String?,
      providerCount: (json['provider_count'] as num?)?.toInt() ?? 0,
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? ''),
    );
  }
}

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
