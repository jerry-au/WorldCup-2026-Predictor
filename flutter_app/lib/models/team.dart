class TeamSummary {
  final String code;
  final String name;
  final String? nameCn;
  final String iso;
  final String confederation;
  final String groupName;
  final String? flagUrl;
  final double eloRating;
  final int fifaRank;

  TeamSummary({
    required this.code,
    required this.name,
    this.nameCn,
    required this.iso,
    required this.confederation,
    required this.groupName,
    this.flagUrl,
    required this.eloRating,
    required this.fifaRank,
  });

  factory TeamSummary.fromJson(Map<String, dynamic> json) {
    return TeamSummary(
      code: json['code'] as String,
      name: json['name'] as String,
      nameCn: json['name_cn'] as String?,
      iso: json['iso'] as String,
      confederation: json['confederation'] as String,
      groupName: json['group_name'] as String,
      flagUrl: json['flag_url'] as String?,
      eloRating: (json['elo_rating'] as num).toDouble(),
      fifaRank: json['fifa_rank'] as int,
    );
  }

  String get displayName => nameCn ?? name;
}

class PlayerSeasonStats {
  final String competitionCode;
  final String? competitionName;
  final int goals;
  final int assists;
  final int appearances;
  final int minutesPlayed;

  PlayerSeasonStats({
    required this.competitionCode,
    this.competitionName,
    required this.goals,
    required this.assists,
    required this.appearances,
    required this.minutesPlayed,
  });

  factory PlayerSeasonStats.fromJson(Map<String, dynamic> json) {
    return PlayerSeasonStats(
      competitionCode: json['competition_code'] as String,
      competitionName: json['competition_name'] as String?,
      goals: json['goals'] as int? ?? 0,
      assists: json['assists'] as int? ?? 0,
      appearances: json['appearances'] as int? ?? 0,
      minutesPlayed: json['minutes_played'] as int? ?? 0,
    );
  }
}

class Player {
  final String name;
  final int? jersey;
  final String? position;
  final String? clubName;
  final int? ageAtTournament;
  final List<PlayerSeasonStats> seasonStats;
  final String? bestPosition;
  final String? photoUrl;

  Player({
    required this.name,
    this.jersey,
    this.position,
    this.clubName,
    this.ageAtTournament,
    this.seasonStats = const [],
    this.bestPosition,
    this.photoUrl,
  });

  factory Player.fromJson(Map<String, dynamic> json) {
    return Player(
      name: json['name'] as String,
      jersey: json['jersey'] as int?,
      position: json['position'] as String?,
      clubName: json['club_name'] as String?,
      ageAtTournament: json['age_at_tournament'] as int?,
      seasonStats: (json['season_stats'] as List<dynamic>?)
              ?.map((e) => PlayerSeasonStats.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      bestPosition: json['best_position'] as String?,
      photoUrl: json['photo_url'] as String?,
    );
  }
}

class TeamDetail {
  final String code;
  final String name;
  final String? nameCn;
  final String iso;
  final String confederation;
  final String groupName;
  final String? flagUrl;
  final double eloRating;
  final int fifaRank;
  final double marketValueEur;
  final String? coachName;
  final String? coachCountry;
  final List<Player> players;
  final List<Player> startingXi;

  TeamDetail({
    required this.code,
    required this.name,
    this.nameCn,
    required this.iso,
    required this.confederation,
    required this.groupName,
    this.flagUrl,
    required this.eloRating,
    required this.fifaRank,
    required this.marketValueEur,
    this.coachName,
    this.coachCountry,
    required this.players,
    required this.startingXi,
  });

  factory TeamDetail.fromJson(Map<String, dynamic> json) {
    return TeamDetail(
      code: json['code'] as String,
      name: json['name'] as String,
      nameCn: json['name_cn'] as String?,
      iso: json['iso'] as String,
      confederation: json['confederation'] as String,
      groupName: json['group_name'] as String,
      flagUrl: json['flag_url'] as String?,
      eloRating: (json['elo_rating'] as num).toDouble(),
      fifaRank: json['fifa_rank'] as int,
      marketValueEur: (json['market_value_eur'] as num).toDouble(),
      coachName: json['coach_name'] as String?,
      coachCountry: json['coach_country'] as String?,
      players: (json['players'] as List<dynamic>?)
              ?.map((e) => Player.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      startingXi: (json['starting_xi'] as List<dynamic>?)
              ?.map((e) => Player.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  String get displayName => nameCn ?? name;

  static List<String> get confederations => ['AFC', 'CAF', 'CONCACAF', 'CONMEBOL', 'OFC', 'UEFA'];
  static const Map<String, String> confederationNames = {
    'AFC': '亚洲',
    'CAF': '非洲',
    'CONCACAF': '中北美及加勒比海',
    'CONMEBOL': '南美洲',
    'OFC': '大洋洲',
    'UEFA': '欧洲',
  };
}
