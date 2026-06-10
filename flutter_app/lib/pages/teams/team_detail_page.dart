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
                  ...team.players.map((player) => ListTile(
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
                            : null,
                      )),
              ],
            ),
          ),
        ).animate().fadeIn(delay: 100.ms),
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
