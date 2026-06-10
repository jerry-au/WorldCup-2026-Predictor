import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../models/simulation.dart';
import '../../providers/simulation_provider.dart';
import '../../widgets/common_widgets.dart';
import 'bracket_painter.dart';

class SimulationPage extends ConsumerWidget {
  const SimulationPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(simulationProvider);
    final notifier = ref.read(simulationProvider.notifier);

    return RefreshIndicator(
      onRefresh: () async => notifier.reset(),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ─── Control Card ──────────────────────────────────
          _buildControlCard(context, state, notifier),
          const SizedBox(height: 16),

          // ─── Loading / Results ──────────────────────────────
          if (state.isRunning) _buildProgress(context, state),
          if (state.error != null) ErrorWidgetView(
            message: state.error!,
            onRetry: () => notifier.startSimulation(),
          ),
          if (state.result != null) ...[
            _buildRankingTable(context, state.result!),
            const SizedBox(height: 16),
            // Bracket placeholder — actual bracket data in P1+
            _buildBracketPlaceholder(context),
          ],
        ],
      ),
    );
  }

  // ─── Control Card ──────────────────────────────────────────────

  Widget _buildControlCard(
    BuildContext context,
    SimulationState state,
    SimulationNotifier notifier,
  ) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Icon(Icons.bar_chart, size: 48, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 12),
            Text(
              '2026 世界杯赛事模拟',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              '基于混合泊松-Elo 模型 · 蒙特卡洛 10,000 次',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey),
            ),
            const SizedBox(height: 20),

            if (state.isRunning)
              Column(
                children: [
                  LinearProgressIndicator(value: state.progress),
                  const SizedBox(height: 8),
                  Text(
                    '模拟中... ${(state.progress * 100).toStringAsFixed(0)}%',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              )
            else ...[
              FilledButton.icon(
                onPressed: state.result != null
                    ? null
                    : () => notifier.startSimulation(),
                icon: const Icon(Icons.play_arrow),
                label: const Text('运行模拟'),
                style: FilledButton.styleFrom(
                  minimumSize: const Size(double.infinity, 48),
                ),
              ),
              if (state.result != null) ...[
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () => notifier.startSimulation(),
                  icon: const Icon(Icons.refresh),
                  label: const Text('重新模拟'),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  // ─── Progress ─────────────────────────────────────────────────

  Widget _buildProgress(BuildContext context, SimulationState state) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const SizedBox(
              width: 20, height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: 12),
            Text('赛事模拟中... ${(state.progress * 100).toStringAsFixed(0)}%'),
          ],
        ),
      ),
    );
  }

  // ─── Ranking Table ────────────────────────────────────────────

  Widget _buildRankingTable(BuildContext context, SimulationResult result) {
    final sorted = List<TeamProbability>.from(result.standings)
      ..sort((a, b) => b.champion.compareTo(a.champion));

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '晋级概率排行榜',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const Divider(),
            ...sorted.take(20).map((team) => _rankRow(context, team)),
            if (sorted.length > 20)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Center(
                  child: Text(
                    '+ ${sorted.length - 20} 支球队',
                    style: TextStyle(color: Colors.grey.shade500, fontSize: 13),
                  ),
                ),
              ),
          ],
        ),
      ),
    ).animate().fadeIn(delay: 200.ms);
  }

  Widget _rankRow(BuildContext context, TeamProbability team) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SizedBox(
                width: 28,
                child: Text(
                  team.teamCode,
                  style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                ),
              ),
              Expanded(
                child: Text(
                  team.teamName,
                  style: const TextStyle(fontSize: 13),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Text(
                '${(team.champion * 100).toStringAsFixed(1)}%',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                  color: team.champion >= 0.05
                      ? Colors.green.shade700
                      : team.champion >= 0.01
                          ? Colors.orange
                          : Colors.grey,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: SizedBox(
              height: 6,
              child: Row(
                children: [
                  _barSegment(team.round32, Colors.grey.shade300),
                  _barSegment(team.round16, Colors.blue.shade200),
                  _barSegment(team.quarter, Colors.blue.shade400),
                  _barSegment(team.semi, Colors.orange.shade400),
                  _barSegment(team.final_, Colors.deepOrange.shade400),
                  _barSegment(team.champion, Colors.green.shade600),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _barSegment(double prob, Color color) {
    return Flexible(
      flex: (prob * 1000).round().clamp(0, 1000),
      child: Container(color: prob > 0 ? color : Colors.transparent),
    );
  }

  // ─── Bracket Placeholder ──────────────────────────────────────

  Widget _buildBracketPlaceholder(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  '淘汰赛对阵图',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                Icon(Icons.swipe, size: 16, color: Colors.grey.shade400),
                const SizedBox(width: 4),
                Text('左右滑动', style: TextStyle(fontSize: 12, color: Colors.grey.shade400)),
              ],
            ),
            const Divider(),
            SizedBox(
              height: 300,
              child: InteractiveViewer(
                boundaryMargin: const EdgeInsets.all(40),
                minScale: 0.3,
                maxScale: 2.0,
                child: _buildSampleBracket(),
              ),
            ),
          ],
        ),
      ),
    ).animate().fadeIn(delay: 400.ms);
  }

  Widget _buildSampleBracket() {
    // Build sample bracket from simulation results
    // For now, generate demo matches showing the layout
    final demoMatches = <BracketMatch>[
      for (int r = 0; r < 5; r++) ...[
        for (int p = 0; p < _roundMatchCount(r); p++)
          BracketMatch(
            roundName: _roundNames[r],
            position: p,
            teamA: _demoTeam(r, p, 0),
            teamB: _demoTeam(r, p, 1),
            probA: 0.5 + (p % 3) * 0.05,
            probB: 0.5 - (p % 3) * 0.05,
          ),
      ],
    ];

    return BracketWidget(
      matches: demoMatches,
      teamNames: _demoNames,
    );
  }
}

const _roundNames = ['round_32', 'round_16', 'quarter', 'semi', 'final'];

int _roundMatchCount(int round) {
  switch (round) {
    case 0: return 16;
    case 1: return 8;
    case 2: return 4;
    case 3: return 2;
    case 4: return 1;
    default: return 0;
  }
}

const _demoNames = {
  'BRA': 'Brazil', 'FRA': 'France', 'ESP': 'Spain', 'ARG': 'Argentina',
  'ENG': 'England', 'GER': 'Germany', 'NED': 'Netherlands', 'POR': 'Portugal',
  'ITA': 'Italy', 'CRO': 'Croatia', 'BEL': 'Belgium', 'SUI': 'Switzerland',
  'URU': 'Uruguay', 'COL': 'Colombia', 'MAR': 'Morocco', 'SEN': 'Senegal',
  'JPN': 'Japan', 'KOR': 'South Korea', 'MEX': 'Mexico', 'USA': 'USA',
  'CAN': 'Canada', 'AUS': 'Australia', 'CMR': 'Cameroon', 'GHA': 'Ghana',
  'TUN': 'Tunisia', 'EGY': 'Egypt', 'ECU': 'Ecuador', 'PAR': 'Paraguay',
  'IRN': 'Iran', 'KSA': 'Saudi Arabia', 'DEN': 'Denmark', 'SWE': 'Sweden',
};

String? _demoTeam(int round, int pos, int side) {
  // Return realistic-looking team codes for demo purposes
  const teams = [
    'BRA','FRA','ESP','ARG','ENG','GER','NED','POR',
    'ITA','CRO','BEL','SUI','URU','COL','MAR','SEN',
    'JPN','KOR','MEX','USA','CAN','AUS','CMR','GHA',
    'TUN','EGY','ECU','PAR','IRN','KSA','DEN','SWE',
  ];
  if (round == 4 && pos == 0) {
    return side == 0 ? 'BRA' : 'FRA';
  }
  // For demo, just cycle through teams
  final idx = (pos * 2 + side) % teams.length;
  return teams[idx];
}
