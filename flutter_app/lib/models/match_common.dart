/// 比赛相关的共享模型类，供 today_match 和 schedule_match 复用。
///
/// 包含 MatchTeam, MatchPredictionSummary, MatchOddsSummary 三个类。

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

  String get displayName => nameCn ?? name;
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
