class SimulationPreset {
  final String id;
  final String name;
  final String? description;
  final bool isDefault;
  final bool isBuiltin;
  final SimulationPresetParameters parameters;

  const SimulationPreset({
    required this.id,
    required this.name,
    this.description,
    required this.isDefault,
    required this.isBuiltin,
    required this.parameters,
  });

  factory SimulationPreset.fromJson(Map<String, dynamic> json) {
    return SimulationPreset(
      id: json['id'] as String,
      name: json['name'] as String,
      description: json['description'] as String?,
      isDefault: json['is_default'] as bool? ?? false,
      isBuiltin: json['is_builtin'] as bool? ?? false,
      parameters: SimulationPresetParameters.fromJson(
        Map<String, dynamic>.from(json['parameters'] as Map),
      ),
    );
  }

  SimulationPreset copyWith({
    String? id,
    String? name,
    String? description,
    bool? isDefault,
    bool? isBuiltin,
    SimulationPresetParameters? parameters,
  }) {
    return SimulationPreset(
      id: id ?? this.id,
      name: name ?? this.name,
      description: description ?? this.description,
      isDefault: isDefault ?? this.isDefault,
      isBuiltin: isBuiltin ?? this.isBuiltin,
      parameters: parameters ?? this.parameters,
    );
  }

  Map<String, dynamic> toUpdateJson() => {
        'name': name,
        'description': description,
        'parameters': parameters.toJson(),
      };
}

class SimulationPresetParameters {
  final MotivationParameters motivation;
  final CollusionParameters collusion;
  final EnvironmentParameters environment;
  final DisciplineParameters discipline;

  const SimulationPresetParameters({
    required this.motivation,
    required this.collusion,
    required this.environment,
    required this.discipline,
  });

  factory SimulationPresetParameters.fromJson(Map<String, dynamic> json) {
    return SimulationPresetParameters(
      motivation: MotivationParameters.fromJson(Map<String, dynamic>.from(json['motivation'] as Map)),
      collusion: CollusionParameters.fromJson(Map<String, dynamic>.from(json['collusion'] as Map)),
      environment: EnvironmentParameters.fromJson(Map<String, dynamic>.from(json['environment'] as Map)),
      discipline: DisciplineParameters.fromJson(Map<String, dynamic>.from(json['discipline'] as Map)),
    );
  }

  SimulationPresetParameters copyWith({
    MotivationParameters? motivation,
    CollusionParameters? collusion,
    EnvironmentParameters? environment,
    DisciplineParameters? discipline,
  }) {
    return SimulationPresetParameters(
      motivation: motivation ?? this.motivation,
      collusion: collusion ?? this.collusion,
      environment: environment ?? this.environment,
      discipline: discipline ?? this.discipline,
    );
  }

  Map<String, dynamic> toJson() => {
        'motivation': motivation.toJson(),
        'collusion': collusion.toJson(),
        'environment': environment.toJson(),
        'discipline': discipline.toJson(),
      };
}

class MotivationParameters {
  final double qualifiedRotationMultiplier;
  final double eliminatedMoraleMultiplier;
  final double topSpotMotivationMultiplier;
  final double honorMatchRandomnessMultiplier;
  final double motivationMinCap;
  final double motivationMaxCap;

  const MotivationParameters({
    required this.qualifiedRotationMultiplier,
    required this.eliminatedMoraleMultiplier,
    required this.topSpotMotivationMultiplier,
    required this.honorMatchRandomnessMultiplier,
    required this.motivationMinCap,
    required this.motivationMaxCap,
  });

  factory MotivationParameters.fromJson(Map<String, dynamic> json) {
    return MotivationParameters(
      qualifiedRotationMultiplier: (json['qualified_rotation_multiplier'] as num).toDouble(),
      eliminatedMoraleMultiplier: (json['eliminated_morale_multiplier'] as num).toDouble(),
      topSpotMotivationMultiplier: (json['top_spot_motivation_multiplier'] as num).toDouble(),
      honorMatchRandomnessMultiplier: (json['honor_match_randomness_multiplier'] as num).toDouble(),
      motivationMinCap: (json['motivation_min_cap'] as num).toDouble(),
      motivationMaxCap: (json['motivation_max_cap'] as num).toDouble(),
    );
  }

  MotivationParameters copyWith({
    double? qualifiedRotationMultiplier,
    double? eliminatedMoraleMultiplier,
    double? topSpotMotivationMultiplier,
    double? honorMatchRandomnessMultiplier,
    double? motivationMinCap,
    double? motivationMaxCap,
  }) {
    return MotivationParameters(
      qualifiedRotationMultiplier: qualifiedRotationMultiplier ?? this.qualifiedRotationMultiplier,
      eliminatedMoraleMultiplier: eliminatedMoraleMultiplier ?? this.eliminatedMoraleMultiplier,
      topSpotMotivationMultiplier: topSpotMotivationMultiplier ?? this.topSpotMotivationMultiplier,
      honorMatchRandomnessMultiplier: honorMatchRandomnessMultiplier ?? this.honorMatchRandomnessMultiplier,
      motivationMinCap: motivationMinCap ?? this.motivationMinCap,
      motivationMaxCap: motivationMaxCap ?? this.motivationMaxCap,
    );
  }

  Map<String, dynamic> toJson() => {
        'qualified_rotation_multiplier': qualifiedRotationMultiplier,
        'eliminated_morale_multiplier': eliminatedMoraleMultiplier,
        'top_spot_motivation_multiplier': topSpotMotivationMultiplier,
        'honor_match_randomness_multiplier': honorMatchRandomnessMultiplier,
        'motivation_min_cap': motivationMinCap,
        'motivation_max_cap': motivationMaxCap,
      };
}

class CollusionParameters {
  final double mutualDrawBoost;
  final double opponentSelectionLossMultiplier;

  const CollusionParameters({
    required this.mutualDrawBoost,
    required this.opponentSelectionLossMultiplier,
  });

  factory CollusionParameters.fromJson(Map<String, dynamic> json) {
    return CollusionParameters(
      mutualDrawBoost: (json['mutual_draw_boost'] as num).toDouble(),
      opponentSelectionLossMultiplier: (json['opponent_selection_loss_multiplier'] as num).toDouble(),
    );
  }

  CollusionParameters copyWith({
    double? mutualDrawBoost,
    double? opponentSelectionLossMultiplier,
  }) {
    return CollusionParameters(
      mutualDrawBoost: mutualDrawBoost ?? this.mutualDrawBoost,
      opponentSelectionLossMultiplier: opponentSelectionLossMultiplier ?? this.opponentSelectionLossMultiplier,
    );
  }

  Map<String, dynamic> toJson() => {
        'mutual_draw_boost': mutualDrawBoost,
        'opponent_selection_loss_multiplier': opponentSelectionLossMultiplier,
      };
}

class EnvironmentParameters {
  final double homeAdvantageMultiplier;
  final double travelFatigueMultiplier;
  final double weatherAdaptationMultiplier;
  final double jetLagMultiplier;
  final double contextMinCap;
  final double contextMaxCap;

  const EnvironmentParameters({
    required this.homeAdvantageMultiplier,
    required this.travelFatigueMultiplier,
    required this.weatherAdaptationMultiplier,
    required this.jetLagMultiplier,
    required this.contextMinCap,
    required this.contextMaxCap,
  });

  factory EnvironmentParameters.fromJson(Map<String, dynamic> json) {
    return EnvironmentParameters(
      homeAdvantageMultiplier: (json['home_advantage_multiplier'] as num).toDouble(),
      travelFatigueMultiplier: (json['travel_fatigue_multiplier'] as num).toDouble(),
      weatherAdaptationMultiplier: (json['weather_adaptation_multiplier'] as num).toDouble(),
      jetLagMultiplier: (json['jet_lag_multiplier'] as num).toDouble(),
      contextMinCap: (json['context_min_cap'] as num).toDouble(),
      contextMaxCap: (json['context_max_cap'] as num).toDouble(),
    );
  }

  EnvironmentParameters copyWith({
    double? homeAdvantageMultiplier,
    double? travelFatigueMultiplier,
    double? weatherAdaptationMultiplier,
    double? jetLagMultiplier,
    double? contextMinCap,
    double? contextMaxCap,
  }) {
    return EnvironmentParameters(
      homeAdvantageMultiplier: homeAdvantageMultiplier ?? this.homeAdvantageMultiplier,
      travelFatigueMultiplier: travelFatigueMultiplier ?? this.travelFatigueMultiplier,
      weatherAdaptationMultiplier: weatherAdaptationMultiplier ?? this.weatherAdaptationMultiplier,
      jetLagMultiplier: jetLagMultiplier ?? this.jetLagMultiplier,
      contextMinCap: contextMinCap ?? this.contextMinCap,
      contextMaxCap: contextMaxCap ?? this.contextMaxCap,
    );
  }

  Map<String, dynamic> toJson() => {
        'home_advantage_multiplier': homeAdvantageMultiplier,
        'travel_fatigue_multiplier': travelFatigueMultiplier,
        'weather_adaptation_multiplier': weatherAdaptationMultiplier,
        'jet_lag_multiplier': jetLagMultiplier,
        'context_min_cap': contextMinCap,
        'context_max_cap': contextMaxCap,
      };
}

class DisciplineParameters {
  final double yellowCardCautionMultiplier;
  final double keyPlayerSuspensionMultiplier;

  const DisciplineParameters({
    required this.yellowCardCautionMultiplier,
    required this.keyPlayerSuspensionMultiplier,
  });

  factory DisciplineParameters.fromJson(Map<String, dynamic> json) {
    return DisciplineParameters(
      yellowCardCautionMultiplier: (json['yellow_card_caution_multiplier'] as num).toDouble(),
      keyPlayerSuspensionMultiplier: (json['key_player_suspension_multiplier'] as num).toDouble(),
    );
  }

  DisciplineParameters copyWith({
    double? yellowCardCautionMultiplier,
    double? keyPlayerSuspensionMultiplier,
  }) {
    return DisciplineParameters(
      yellowCardCautionMultiplier: yellowCardCautionMultiplier ?? this.yellowCardCautionMultiplier,
      keyPlayerSuspensionMultiplier: keyPlayerSuspensionMultiplier ?? this.keyPlayerSuspensionMultiplier,
    );
  }

  Map<String, dynamic> toJson() => {
        'yellow_card_caution_multiplier': yellowCardCautionMultiplier,
        'key_player_suspension_multiplier': keyPlayerSuspensionMultiplier,
      };
}
