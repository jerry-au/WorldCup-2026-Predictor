class TeamProbability {
  final String teamCode;
  final String teamName;
  final double round32;
  final double round16;
  final double quarter;
  final double semi;
  final double final_;
  final double champion;

  TeamProbability({
    required this.teamCode,
    required this.teamName,
    required this.round32,
    required this.round16,
    required this.quarter,
    required this.semi,
    required this.final_,
    required this.champion,
  });

  factory TeamProbability.fromJson(Map<String, dynamic> json) {
    return TeamProbability(
      teamCode: json['team_code'] as String,
      teamName: json['team_name'] as String,
      round32: (json['round_32'] as num).toDouble(),
      round16: (json['round_16'] as num).toDouble(),
      quarter: (json['quarter'] as num).toDouble(),
      semi: (json['semi'] as num).toDouble(),
      final_: (json['final_'] as num).toDouble(),
      champion: (json['champion'] as num).toDouble(),
    );
  }

  /// All rounds' probabilities as a list for bar rendering.
  List<double> get roundProbs =>
      [round32, round16, quarter, semi, final_, champion];
}

class KnockoutMatch {
  final String roundName;
  final int position;
  final String? teamA;
  final String? teamB;
  final double? probA;
  final double? probB;

  KnockoutMatch({
    required this.roundName,
    required this.position,
    this.teamA,
    this.teamB,
    this.probA,
    this.probB,
  });

  factory KnockoutMatch.fromJson(Map<String, dynamic> json) {
    return KnockoutMatch(
      roundName: json['round_name'] as String,
      position: json['position'] as int,
      teamA: json['team_a'] as String?,
      teamB: json['team_b'] as String?,
      probA: (json['prob_a'] as num?)?.toDouble(),
      probB: (json['prob_b'] as num?)?.toDouble(),
    );
  }
}

class SimulationResult {
  final List<TeamProbability> standings;
  final List<KnockoutMatch> bracket;

  SimulationResult({required this.standings, required this.bracket});

  factory SimulationResult.fromJson(Map<String, dynamic> json) {
    final raw = json['standings'] as List<dynamic>;
    final bracketRaw = json['bracket'] as List<dynamic>? ?? [];
    return SimulationResult(
      standings:
          raw.map((e) => TeamProbability.fromJson(e as Map<String, dynamic>)).toList(),
      bracket:
          bracketRaw.map((e) => KnockoutMatch.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }
}
