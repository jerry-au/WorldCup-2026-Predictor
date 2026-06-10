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

class SimulationResult {
  final List<TeamProbability> standings;

  SimulationResult({required this.standings});

  factory SimulationResult.fromJson(Map<String, dynamic> json) {
    final raw = json['standings'] as List<dynamic>;
    return SimulationResult(
      standings:
          raw.map((e) => TeamProbability.fromJson(e as Map<String, dynamic>)).toList(),
    );
  }
}
