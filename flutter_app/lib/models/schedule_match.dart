import 'match_common.dart';

class AllMatchesResponse {
  final List<ScheduleMatch> matches;
  final int total;
  final int page;
  final int pageSize;
  final int totalPages;
  final ScheduleCache cache;

  AllMatchesResponse({
    required this.matches,
    required this.total,
    required this.page,
    required this.pageSize,
    required this.totalPages,
    required this.cache,
  });

  factory AllMatchesResponse.fromJson(Map<String, dynamic> json) {
    final rawMatches = json['matches'];
    return AllMatchesResponse(
      matches: rawMatches is List
          ? rawMatches.map((e) => ScheduleMatch.fromJson(e as Map<String, dynamic>)).toList()
          : const [],
      total: (json['total'] as num?)?.toInt() ?? 0,
      page: (json['page'] as num?)?.toInt() ?? 1,
      pageSize: (json['page_size'] as num?)?.toInt() ?? 20,
      totalPages: (json['total_pages'] as num?)?.toInt() ?? 1,
      cache: ScheduleCache.fromJson((json['cache'] as Map<String, dynamic>?) ?? const {}),
    );
  }

  bool get hasMorePages => page < totalPages;
}

class ScheduleMatch {
  final String matchId;
  final MatchTeam home;
  final MatchTeam away;
  final String? stage;
  final String? groupName;
  final DateTime? commenceTime;
  final String? status;
  final String? stadium;
  final MatchScore? score;
  final MatchPredictionSummary? prediction;
  final MatchOddsSummary? odds;

  ScheduleMatch({
    required this.matchId,
    required this.home,
    required this.away,
    this.stage,
    this.groupName,
    this.commenceTime,
    this.status,
    this.stadium,
    this.score,
    this.prediction,
    this.odds,
  });

  factory ScheduleMatch.fromJson(Map<String, dynamic> json) {
    return ScheduleMatch(
      matchId: json['match_id'] as String? ?? '',
      home: MatchTeam.fromJson((json['home'] as Map<String, dynamic>?) ?? const {}),
      away: MatchTeam.fromJson((json['away'] as Map<String, dynamic>?) ?? const {}),
      stage: json['stage'] as String?,
      groupName: json['group_name'] as String?,
      commenceTime: DateTime.tryParse(json['commence_time'] as String? ?? ''),
      status: json['status'] as String?,
      stadium: json['stadium'] as String?,
      score: json['score'] is Map<String, dynamic>
          ? MatchScore.fromJson(json['score'] as Map<String, dynamic>)
          : null,
      prediction: json['prediction'] is Map<String, dynamic>
          ? MatchPredictionSummary.fromJson(json['prediction'] as Map<String, dynamic>)
          : null,
      odds: json['odds'] is Map<String, dynamic>
          ? MatchOddsSummary.fromJson(json['odds'] as Map<String, dynamic>)
          : null,
    );
  }

  bool get isCompleted => status == 'completed';
  bool get isLive => status == 'live';
  bool get isUpcoming => status == 'upcoming' || status == null;

  String get matchType {
    switch (stage) {
      case 'group_stage':
        return 'group';
      case 'round_of_16':
      case 'quarter':
      case 'semi':
      case 'final':
        return 'knockout';
      default:
        return 'group';
    }
  }

  String get stageDisplayName {
    switch (stage) {
      case 'group_stage':
        return '小组赛';
      case 'round_of_16':
        return '1/8 决赛';
      case 'quarter':
        return '1/4 决赛';
      case 'semi':
        return '半决赛';
      case 'final':
        return '决赛';
      default:
        return stage ?? '未知';
    }
  }
}

class MatchScore {
  final int home;
  final int away;
  final int? homeEt;
  final int? awayEt;
  final int? homePenalties;
  final int? awayPenalties;

  MatchScore({
    required this.home,
    required this.away,
    this.homeEt,
    this.awayEt,
    this.homePenalties,
    this.awayPenalties,
  });

  factory MatchScore.fromJson(Map<String, dynamic> json) {
    return MatchScore(
      home: (json['home'] as num?)?.toInt() ?? 0,
      away: (json['away'] as num?)?.toInt() ?? 0,
      homeEt: (json['home_et'] as num?)?.toInt(),
      awayEt: (json['away_et'] as num?)?.toInt(),
      homePenalties: (json['home_penalties'] as num?)?.toInt(),
      awayPenalties: (json['away_penalties'] as num?)?.toInt(),
    );
  }

  /// 格式化比分显示
  String get displayScore {
    if (homePenalties != null) {
      return '$home - $away ($homePenalties - $awayPenalties 点球)';
    }
    if (homeEt != null) {
      return '$home - $away (加时 $homeEt - $awayEt)';
    }
    return '$home - $away';
  }
}

// MatchTeam, MatchPredictionSummary, MatchOddsSummary 定义在 match_common.dart

class ScheduleCache {
  final DateTime? updatedAt;
  final int ttlSeconds;

  ScheduleCache({this.updatedAt, required this.ttlSeconds});

  factory ScheduleCache.fromJson(Map<String, dynamic> json) {
    return ScheduleCache(
      updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? ''),
      ttlSeconds: (json['ttl_seconds'] as num?)?.toInt() ?? 300,
    );
  }
}
