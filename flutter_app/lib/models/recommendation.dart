class ValueBet {
  final String teamA;
  final String teamB;
  final String teamAcode;
  final String teamBcode;
  final String outcome;
  final double odds;
  final double ev;
  final String rating;
  final double systemProb;
  final double marketProb;

  ValueBet({
    required this.teamA,
    required this.teamB,
    required this.teamAcode,
    required this.teamBcode,
    required this.outcome,
    required this.odds,
    required this.ev,
    required this.rating,
    required this.systemProb,
    required this.marketProb,
  });

  factory ValueBet.fromJson(Map<String, dynamic> json) {
    return ValueBet(
      teamA: json['team_a'] as String? ?? '',
      teamB: json['team_b'] as String? ?? '',
      teamAcode: json['team_a_code'] as String? ?? '',
      teamBcode: json['team_b_code'] as String? ?? '',
      outcome: json['outcome'] as String? ?? '',
      odds: (json['odds'] as num?)?.toDouble() ?? 0,
      ev: (json['ev'] as num?)?.toDouble() ?? 0,
      rating: json['rating'] as String? ?? '',
      systemProb: (json['system_prob'] as num?)?.toDouble() ?? 0,
      marketProb: (json['market_prob'] as num?)?.toDouble() ?? 0,
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

  int get starCount {
    return rating.contains('★★★') ? 3 : rating.contains('★★') ? 2 : rating.contains('★') ? 1 : 0;
  }
}

class DiscrepancyAlert {
  final String teamA;
  final String teamB;
  final String teamAcode;
  final String teamBcode;
  final String group;
  final Map<String, dynamic> discrepancy;
  final Map<String, double> systemProbs;
  final Map<String, double>? marketProbs;

  DiscrepancyAlert({
    required this.teamA,
    required this.teamB,
    required this.teamAcode,
    required this.teamBcode,
    required this.group,
    required this.discrepancy,
    required this.systemProbs,
    this.marketProbs,
  });

  factory DiscrepancyAlert.fromJson(Map<String, dynamic> json) {
    return DiscrepancyAlert(
      teamA: json['team_a'] as String? ?? '',
      teamB: json['team_b'] as String? ?? '',
      teamAcode: json['team_a_code'] as String? ?? '',
      teamBcode: json['team_b_code'] as String? ?? '',
      group: json['group'] as String? ?? '',
      discrepancy: (json['discrepancy'] as Map<String, dynamic>?) ?? {},
      systemProbs: (json['system_probs'] as Map<String, dynamic>?)
          ?.map((k, v) => MapEntry(k, (v as num).toDouble())) ?? {'win': 0, 'draw': 0, 'lose': 0},
      marketProbs: (json['market_probs'] as Map<String, dynamic>?)
          ?.map((k, v) => MapEntry(k, (v as num).toDouble())),
    );
  }
}
