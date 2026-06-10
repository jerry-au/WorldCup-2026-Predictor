import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/team.dart';
import '../services/providers.dart';

final teamsListProvider = FutureProvider.family<List<TeamSummary>, TeamsFilter>((ref, filter) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.getTeams(
    confederation: filter.confederation,
    group: filter.group,
    sortBy: filter.sortBy,
  );
  return (data as List<dynamic>)
      .map((e) => TeamSummary.fromJson(e as Map<String, dynamic>))
      .toList();
});

class TeamsFilter {
  final String? confederation;
  final String? group;
  final String sortBy;

  const TeamsFilter({
    this.confederation,
    this.group,
    this.sortBy = 'elo_rating',
  });

  TeamsFilter copyWith({String? confederation, String? group, String? sortBy}) {
    return TeamsFilter(
      confederation: confederation ?? this.confederation,
      group: group ?? this.group,
      sortBy: sortBy ?? this.sortBy,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is TeamsFilter &&
          runtimeType == other.runtimeType &&
          confederation == other.confederation &&
          group == other.group &&
          sortBy == other.sortBy;

  @override
  int get hashCode => Object.hash(confederation, group, sortBy);
}

final teamDetailProvider = FutureProvider.family<TeamDetail, String>((ref, code) async {
  final api = ref.read(apiServiceProvider);
  final data = await api.getTeamDetail(code);
  return TeamDetail.fromJson(data as Map<String, dynamic>);
});
