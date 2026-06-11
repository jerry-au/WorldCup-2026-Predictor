class TeamSummary {
  final String code;
  final String name;
  final String iso;
  final String confederation;
  final String groupName;
  final String? flagUrl;
  final double eloRating;
  final int fifaRank;

  TeamSummary({
    required this.code,
    required this.name,
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
      iso: json['iso'] as String,
      confederation: json['confederation'] as String,
      groupName: json['group_name'] as String,
      flagUrl: json['flag_url'] as String?,
      eloRating: (json['elo_rating'] as num).toDouble(),
      fifaRank: json['fifa_rank'] as int,
    );
  }
}

class Player {
  final String name;
  final int? jersey;
  final String? position;
  final String? clubName;
  final int? ageAtTournament;

  Player({
    required this.name,
    this.jersey,
    this.position,
    this.clubName,
    this.ageAtTournament,
  });

  factory Player.fromJson(Map<String, dynamic> json) {
    return Player(
      name: json['name'] as String,
      jersey: json['jersey'] as int?,
      position: json['position'] as String?,
      clubName: json['club_name'] as String?,
      ageAtTournament: json['age_at_tournament'] as int?,
    );
  }
}

class TeamDetail {
  final String code;
  final String name;
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

  TeamDetail({
    required this.code,
    required this.name,
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
  });

  factory TeamDetail.fromJson(Map<String, dynamic> json) {
    return TeamDetail(
      code: json['code'] as String,
      name: json['name'] as String,
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
    );
  }

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
