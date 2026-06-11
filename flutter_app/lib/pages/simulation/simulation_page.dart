import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../models/simulation.dart';
import '../../providers/simulation_provider.dart';
import '../../widgets/common_widgets.dart';
import 'bracket_painter.dart';
import '../prediction/prediction_page.dart';
import '../teams/team_list_page.dart';

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

          // ─── Entry Cards ──────────────────────────────────
          _buildPredictionEntryCard(context),
          const SizedBox(height: 12),
          _buildTeamEntryCard(context),
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
            if (state.result!.bracket.isNotEmpty)
              _buildBracket(context, state.result!),
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

  // ─── Entry Cards ──────────────────────────────────────────

  Widget _buildPredictionEntryCard(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const PredictionPage()),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Icon(Icons.sports_soccer, size: 40, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('对战预测', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text('选择两支球队，查看单场胜平负概率与比分预测', style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, color: Colors.grey.shade400),
            ],
          ),
        ),
      ),
    ).animate().fadeIn(delay: 50.ms);
  }

  Widget _buildTeamEntryCard(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const TeamListPage()),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Icon(Icons.groups, size: 40, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('球队详情', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text('浏览全部 48 支参赛球队数据，支持搜索、筛选与排序', style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, color: Colors.grey.shade400),
            ],
          ),
        ),
      ),
    ).animate().fadeIn(delay: 100.ms);
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

  // ─── Bracket ──────────────────────────────────────────────────

  Widget _buildBracket(BuildContext context, SimulationResult result) {
    final bracketMatches = result.bracket.map((m) => BracketMatch(
      roundName: m.roundName,
      position: m.position,
      teamA: m.teamA,
      teamB: m.teamB,
      probA: m.probA,
      probB: m.probB,
    )).toList();

    final teamNames = {
      for (final t in result.standings)
        t.teamCode: t.teamName,
    };

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
                child: BracketWidget(
                  matches: bracketMatches,
                  teamNames: teamNames,
                ),
              ),
            ),
          ],
        ),
      ),
    ).animate().fadeIn(delay: 400.ms);
  }
}
