import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../models/team.dart';
import '../../providers/teams_provider.dart';
import '../../widgets/common_widgets.dart';

class TeamDetailPage extends ConsumerWidget {
  final String teamCode;
  final String teamName;

  const TeamDetailPage({
    super.key,
    required this.teamCode,
    required this.teamName,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(teamDetailProvider(teamCode));

    return Scaffold(
      appBar: AppBar(
        title: Text(teamName),
      ),
      body: detailAsync.when(
        loading: () => const LoadingWidget(message: '加载球队详情...'),
        error: (err, _) => ErrorWidgetView(
          message: '加载失败: ${err.toString()}',
          onRetry: () => ref.invalidate(teamDetailProvider(teamCode)),
        ),
        data: (team) => _TeamDetailContent(team: team),
      ),
    );
  }
}

class _TeamDetailContent extends StatelessWidget {
  final TeamDetail team;

  const _TeamDetailContent({required this.team});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Header card
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                CircleAvatar(
                  radius: 32,
                  backgroundColor: Colors.grey.shade200,
                  child: Text(
                    team.code,
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(team.name, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text(
                  '${TeamDetail.confederationNames[team.confederation] ?? team.confederation} · ${team.groupName}组',
                  style: TextStyle(color: Colors.grey.shade600),
                ),
                const SizedBox(height: 16),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _statItem(context, 'Elo 评分', team.eloRating.toStringAsFixed(0), Colors.blue),
                    _statItem(context, 'FIFA 排名', '#${team.fifaRank}', Colors.orange),
                    _statItem(context, '总身价', _formatValue(team.marketValueEur), Colors.green),
                  ],
                ),
                if (team.coachName != null) ...[
                  const SizedBox(height: 12),
                  Divider(color: Colors.grey.shade200),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.person, size: 16, color: Colors.grey),
                      const SizedBox(width: 6),
                      Text('主教练: ${team.coachName}'),
                      if (team.coachCountry != null) Text(' (${team.coachCountry})'),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ).animate().fadeIn().slideY(begin: 0.1),

        const SizedBox(height: 16),

        // Starting XI section
        if (team.startingXi.isNotEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('首发 11 人 (4-3-3)', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                  const Divider(),
                  _buildFormationView(context, team.startingXi),
                ],
              ),
            ),
          ).animate().fadeIn(delay: 50.ms),

        const SizedBox(height: 16),

        // Players section
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('球员名单', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const Divider(),
                if (team.players.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(16),
                    child: Center(child: Text('暂无球员数据')),
                  )
                else
                  ...team.players.map((player) {
                    final hasStats = player.seasonStats.isNotEmpty;
                    return ExpansionTile(
                      tilePadding: EdgeInsets.zero,
                      childrenPadding: const EdgeInsets.only(left: 56, bottom: 8),
                      dense: true,
                      leading: CircleAvatar(
                        radius: 16,
                        child: Text('${player.jersey ?? '?'}', style: const TextStyle(fontSize: 11)),
                      ),
                      title: Text(player.name, style: const TextStyle(fontWeight: FontWeight.w500)),
                      subtitle: Text(
                        [
                          if (player.position != null) player.position!,
                          if (player.clubName != null) player.clubName!,
                        ].join(' · '),
                        style: const TextStyle(fontSize: 12),
                      ),
                      trailing: player.ageAtTournament != null
                          ? Text('${player.ageAtTournament}岁', style: const TextStyle(fontSize: 12, color: Colors.grey))
                          : (hasStats ? const Icon(Icons.expand_more, size: 18) : null),
                      children: hasStats
                          ? player.seasonStats.map((stat) => Padding(
                              padding: const EdgeInsets.symmetric(vertical: 2),
                              child: Text(
                                '${stat.competitionName ?? stat.competitionCode}: '
                                '${stat.appearances}场 ${stat.goals}球 ${stat.assists}助 ${stat.minutesPlayed}分钟',
                                style: TextStyle(fontSize: 11, color: Colors.grey.shade700),
                              ),
                            )).toList()
                          : [],
                    );
                  }),
              ],
            ),
          ),
        ).animate().fadeIn(delay: 100.ms),
      ],
    );
  }

  Widget _buildFormationView(BuildContext context, List<Player> xi) {
    final gk = xi.where((p) => p.position == 'GK').toList();
    final df = xi.where((p) => p.position == 'DF').toList();
    final mf = xi.where((p) => p.position == 'MF').toList();
    final fw = xi.where((p) => p.position == 'FW').toList();

    return Column(
      children: [
        if (fw.isNotEmpty) _positionRow(context, fw, Colors.red),
        const SizedBox(height: 12),
        if (mf.isNotEmpty) _positionRow(context, mf, Colors.green),
        const SizedBox(height: 12),
        if (df.isNotEmpty) _positionRow(context, df, Colors.blue),
        const SizedBox(height: 12),
        if (gk.isNotEmpty) _positionRow(context, gk, Colors.orange),
      ],
    );
  }

  Widget _positionRow(BuildContext context, List<Player> players, Color color) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: players.map((p) => _playerBubble(context, p, color)).toList(),
    );
  }

  Widget _playerBubble(BuildContext context, Player player, Color color) {
    return Column(
      children: [
        CircleAvatar(
          radius: 20,
          backgroundColor: color.withOpacity(0.15),
          child: Text(
            '${player.jersey ?? '?'}',
            style: TextStyle(fontWeight: FontWeight.bold, color: color, fontSize: 14),
          ),
        ),
        const SizedBox(height: 4),
        SizedBox(
          width: 60,
          child: Text(
            player.name,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w500),
          ),
        ),
      ],
    );
  }

  Widget _statItem(BuildContext context, String label, String value, Color color) {
    return Column(
      children: [
        Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color)),
        Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
      ],
    );
  }

  String _formatValue(double value) {
    if (value >= 1e9) return '€${(value / 1e9).toStringAsFixed(1)}B';
    if (value >= 1e6) return '€${(value / 1e6).toStringAsFixed(0)}M';
    if (value >= 1e3) return '€${(value / 1e3).toStringAsFixed(0)}K';
    return '€${value.toStringAsFixed(0)}';
  }
}
