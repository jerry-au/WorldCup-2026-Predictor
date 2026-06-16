class MatchPrediction {
  final TeamRef teamA;
  final TeamRef teamB;
  final MatchProbabilities probabilities;
  final Map<String, dynamic> breakdown;
  final double systemConfidence;
  final String matchType;
  final BettingInfo betting;

  MatchPrediction({
    required this.teamA,
    required this.teamB,
    required this.probabilities,
    required this.breakdown,
    required this.systemConfidence,
    required this.matchType,
    required this.betting,
  });

  factory MatchPrediction.fromJson(Map<String, dynamic> json) {
    return MatchPrediction(
      teamA: TeamRef.fromJson(json['team_a'] as Map<String, dynamic>),
      teamB: TeamRef.fromJson(json['team_b'] as Map<String, dynamic>),
      probabilities:
          MatchProbabilities.fromJson(json['probabilities'] as Map<String, dynamic>),
      breakdown: json['breakdown'] as Map<String, dynamic>,
      systemConfidence: (json['system_confidence'] as num).toDouble(),
      matchType: json['match_type'] as String,
      betting: BettingInfo.fromJson(json['betting'] as Map<String, dynamic>),
    );
  }
}

class TeamRef {
  final String name;
  final String? flag;
  final String? code;
  final double? elo;
  final double? dongqiudiStrength;
  final double? marketValueEur;

  TeamRef({
    required this.name,
    this.flag,
    this.code,
    this.elo,
    this.dongqiudiStrength,
    this.marketValueEur,
  });

  factory TeamRef.fromJson(Map<String, dynamic> json) {
    return TeamRef(
      name: json['name'] as String,
      flag: json['flag'] as String?,
      code: json['code'] as String?,
      elo: (json['elo'] as num?)?.toDouble(),
      dongqiudiStrength: (json['dongqiudi_strength'] as num?)?.toDouble(),
      marketValueEur: (json['market_value_eur'] as num?)?.toDouble(),
    );
  }

  String get displayName => name;

  /// 格式化身价显示 (亿 EUR)
  String get marketValueDisplay {
    if (marketValueEur == null || marketValueEur! <= 0) return '-';
    final yi = marketValueEur! / 100; // 百万 -> 亿
    if (yi >= 1) return '${yi.toStringAsFixed(1)}亿';
    return '${marketValueEur!.toStringAsFixed(0)}M';
  }
}

class MatchProbabilities {
  final double win;
  final double draw;
  final double lose;

  MatchProbabilities({required this.win, required this.draw, required this.lose});

  factory MatchProbabilities.fromJson(Map<String, dynamic> json) {
    return MatchProbabilities(
      win: (json['win'] as num).toDouble(),
      draw: (json['draw'] as num).toDouble(),
      lose: (json['lose'] as num).toDouble(),
    );
  }

  bool get isKnockout => draw == 0;
}

class BettingInfo {
  final double systemConfidence;
  final OddsComparison oddsComparison;
  final List<BettingRecommendation> recommendations;
  final DiscrepancyInfo? discrepancy;

  BettingInfo({
    required this.systemConfidence,
    required this.oddsComparison,
    required this.recommendations,
    this.discrepancy,
  });

  factory BettingInfo.fromJson(Map<String, dynamic> json) {
    return BettingInfo(
      systemConfidence: (json['system_confidence'] as num?)?.toDouble() ?? 0,
      oddsComparison: json['odds_comparison'] != null
          ? OddsComparison.fromJson(json['odds_comparison'] as Map<String, dynamic>)
          : OddsComparison.empty(),
      recommendations: (json['recommendations'] as List<dynamic>?)
              ?.map((e) => BettingRecommendation.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      discrepancy: json['discrepancy'] != null
          ? DiscrepancyInfo.fromJson(json['discrepancy'] as Map<String, dynamic>)
          : null,
    );
  }
}

class OddsComparison {
  final int providerCount;
  final Map<String, double> marketAvg;
  final Map<String, dynamic> bestOdds;
  final Map<String, double> marketImplied;

  OddsComparison({
    required this.providerCount,
    required this.marketAvg,
    required this.bestOdds,
    required this.marketImplied,
  });

  factory OddsComparison.empty() => OddsComparison(
        providerCount: 0,
        marketAvg: {},
        bestOdds: {},
        marketImplied: {},
      );

  factory OddsComparison.fromJson(Map<String, dynamic> json) {
    return OddsComparison(
      providerCount: json['provider_count'] as int,
      marketAvg: (json['market_avg'] as Map<String, dynamic>)
          .map((k, v) => MapEntry(k, (v as num).toDouble())),
      bestOdds: json['best_odds'] as Map<String, dynamic>,
      marketImplied: (json['market_implied'] as Map<String, dynamic>)
          .map((k, v) => MapEntry(k, (v as num).toDouble())),
    );
  }
}

class BettingRecommendation {
  final String outcome;
  final double odds;
  final double ev;
  final String rating;
  final double systemProb;
  final double marketProb;

  BettingRecommendation({
    required this.outcome,
    required this.odds,
    required this.ev,
    required this.rating,
    required this.systemProb,
    required this.marketProb,
  });

  factory BettingRecommendation.fromJson(Map<String, dynamic> json) {
    return BettingRecommendation(
      outcome: json['outcome'] as String,
      odds: (json['odds'] as num?)?.toDouble() ?? 0,
      ev: (json['ev'] as num).toDouble(),
      rating: json['rating'] as String,
      systemProb: (json['system_prob'] as num).toDouble(),
      marketProb: (json['market_prob'] as num).toDouble(),
    );
  }

  String get outcomeLabel {
    switch (outcome) {
      case 'win':
        return '主胜';
      case 'draw':
        return '平局';
      case 'lose':
        return '客胜';
      default:
        return outcome;
    }
  }
}

class DiscrepancyInfo {
  final bool detected;
  final double? maxDelta;
  final double? systemConfidence;
  final String? detail;

  DiscrepancyInfo({
    required this.detected,
    this.maxDelta,
    this.systemConfidence,
    this.detail,
  });

  factory DiscrepancyInfo.fromJson(Map<String, dynamic> json) {
    return DiscrepancyInfo(
      detected: json['detected'] as bool,
      maxDelta: (json['max_delta'] as num?)?.toDouble(),
      systemConfidence: (json['system_confidence'] as num?)?.toDouble(),
      detail: json['detail'] as String?,
    );
  }
}
