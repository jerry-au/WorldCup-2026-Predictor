import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../models/prediction.dart';
import '../../providers/prediction_provider.dart';
import '../../providers/teams_provider.dart';
import '../../widgets/probability_gauge.dart';
import '../../widgets/common_widgets.dart';

class PredictionPage extends ConsumerStatefulWidget {
  const PredictionPage({super.key});

  @override
  ConsumerState<PredictionPage> createState() => _PredictionPageState();
}

class _PredictionPageState extends ConsumerState<PredictionPage> {
  String? _teamA;
  String? _teamB;
  String _matchType = 'group';

  void _predict() {
    if (_teamA == null || _teamB == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请选择两支球队')),
      );
      return;
    }
    if (_teamA == _teamB) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请选择两支不同的球队')),
      );
      return;
    }
    ref.invalidate(predictionProvider(PredictionParams(
      teamACode: _teamA!,
      teamBCode: _teamB!,
      matchType: _matchType,
    )));
  }

  @override
  Widget build(BuildContext context) {
    final predictionAsync = _teamA != null && _teamB != null
        ? ref.watch(predictionProvider(PredictionParams(
            teamACode: _teamA!,
            teamBCode: _teamB!,
            matchType: _matchType,
          )))
        : null;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // ─── Team Selectors ─────────────────────────────────
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                _buildTeamSelector('主队 (A)', _teamA, (v) => setState(() => _teamA = v)),
                const SizedBox(height: 12),
                const Icon(Icons.swap_vert, color: Colors.grey),
                const SizedBox(height: 12),
                _buildTeamSelector('客队 (B)', _teamB, (v) => setState(() => _teamB = v)),
                const SizedBox(height: 16),
                // Match type toggle
                SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'group', label: Text('小组赛')),
                    ButtonSegment(value: 'knockout', label: Text('淘汰赛')),
                  ],
                  selected: {_matchType},
                  onSelectionChanged: (v) => setState(() => _matchType = v.first),
                ),
                const SizedBox(height: 16),
                FilledButton.icon(
                  onPressed: _predict,
                  icon: const Icon(Icons.travel_explore),
                  label: const Text('开始预测'),
                  style: FilledButton.styleFrom(
                    minimumSize: const Size(double.infinity, 48),
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),

        // ─── Prediction Result ──────────────────────────────
        if (predictionAsync != null)
          predictionAsync.when(
            loading: () => const LoadingWidget(message: '正在分析球队数据...'),
            error: (err, _) => ErrorWidgetView(
              message: '预测失败: ${err.toString()}',
              onRetry: _predict,
            ),
            data: (pred) => _PredictionResult(prediction: pred),
          ),
      ],
    );
  }

  Widget _buildTeamSelector(String label, String? value, ValueChanged<String?> onChanged) {
    final teamsAsync = ref.watch(teamsListProvider(const TeamsFilter()));

    return teamsAsync.when(
      loading: () => const SizedBox(
        height: 48,
        child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
      ),
      error: (err, _) => Text('加载失败', style: TextStyle(color: Colors.red.shade700)),
      data: (teams) {
        // Exclude already selected team (for away selector)
        final filtered = teams.where((t) => t.code != (label.contains('B') ? _teamA : _teamB)).toList();
        return DropdownButtonFormField<String>(
          value: value,
          decoration: InputDecoration(
            labelText: label,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          ),
          items: filtered.map((team) {
            return DropdownMenuItem(
              value: team.code,
              child: Text('${team.name} (${team.code})', style: const TextStyle(fontSize: 14)),
            );
          }).toList(),
          onChanged: onChanged,
        ).animate().fadeIn();
      },
    );
  }
}

// ─── Prediction Result Widget ──────────────────────────────────────────────

class _PredictionResult extends StatelessWidget {
  final MatchPrediction prediction;

  const _PredictionResult({required this.prediction});

  @override
  Widget build(BuildContext context) {
    final isKnockout = prediction.matchType == 'knockout';
    final probs = prediction.probabilities;

    return Column(
      children: [
        // ─── Probability Gauges ────────────────────────────
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Text(
                  '${prediction.teamA.name} vs ${prediction.teamB.name}',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                ConfidenceBadge(confidence: prediction.systemConfidence),
                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    ProbabilityGauge(
                      probability: probs.win,
                      label: '${prediction.teamA.name}\n胜',
                      color: Colors.green,
                    ),
                    if (!isKnockout)
                      ProbabilityGauge(
                        probability: probs.draw,
                        label: '平局',
                        color: Colors.orange,
                      ),
                    ProbabilityGauge(
                      probability: probs.lose,
                      label: '${prediction.teamB.name}\n胜',
                      color: Colors.red,
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),

        // ─── Betting Recommendations ────────────────────────
        if (prediction.betting.recommendations.isNotEmpty)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.generating_tokens, size: 20, color: Colors.amber.shade700),
                      const SizedBox(width: 8),
                      Text('投注建议',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                    ],
                  ),
                  const Divider(),
                  ...prediction.betting.recommendations.map((rec) => _BettingRecTile(rec: rec)),
                ],
              ),
            ),
          ),

        // ─── Odds Comparison ────────────────────────────────
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('赔率对比 (${prediction.betting.oddsComparison.providerCount}家博彩公司)',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const Divider(),
                _oddsRow('主胜', prediction.betting.oddsComparison.marketAvg['win']),
                if (!isKnockout) _oddsRow('平局', prediction.betting.oddsComparison.marketAvg['draw']),
                _oddsRow('客胜', prediction.betting.oddsComparison.marketAvg['lose']),
                if (prediction.betting.oddsComparison.bestOdds['win'] != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    '最佳赔率: ${prediction.betting.oddsComparison.bestOdds['provider']} 提供',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey),
                  ),
                ],
              ],
            ),
          ),
        ),

        // ─── Discrepancy Alert ──────────────────────────────
        if (prediction.betting.discrepancy?.detected == true)
          Card(
            color: Colors.orange.shade50,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  Icon(Icons.warning_amber, color: Colors.orange.shade700),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      prediction.betting.discrepancy?.detail ?? '市场存在分歧',
                      style: TextStyle(color: Colors.orange.shade900),
                    ),
                  ),
                ],
              ),
            ),
          ),
        const SizedBox(height: 12),

        // ─── Breakdown ──────────────────────────────────────
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('维度分解',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const Divider(),
                ...prediction.breakdown.entries.map((entry) {
                  final dim = entry.value as Map<String, dynamic>;
                  final a = (dim['a_score'] as num?)?.toDouble() ?? 0;
                  final b = (dim['b_score'] as num?)?.toDouble() ?? 0;
                  final contrib = (dim['contribution'] as num?)?.toDouble() ?? 0;
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(_dimLabel(entry.key), style: const TextStyle(fontWeight: FontWeight.w500)),
                            Text('权重 ${(contrib * 100).toStringAsFixed(0)}%',
                                style: const TextStyle(color: Colors.grey, fontSize: 12)),
                          ],
                        ),
                        const SizedBox(height: 4),
                        ProbabilityBar(
                          probability: a / (a + b),
                          label: prediction.teamA.name,
                          color: Colors.green,
                        ),
                        const SizedBox(height: 2),
                        ProbabilityBar(
                          probability: b / (a + b),
                          label: prediction.teamB.name,
                          color: Colors.red,
                        ),
                      ],
                    ),
                  );
                }),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _oddsRow(String label, double? value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(value?.toStringAsFixed(2) ?? '-', style: const TextStyle(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  String _dimLabel(String key) {
    switch (key) {
      case 'strength':
        return '综合实力';
      case 'history':
        return '历史交锋';
      case 'form':
        return '近期状态';
      case 'realtime':
        return '实时因素';
      default:
        return key;
    }
  }
}

class _BettingRecTile extends StatelessWidget {
  final BettingRecommendation rec;

  const _BettingRecTile({required this.rec});

  @override
  Widget build(BuildContext context) {
    return ListTile(
      dense: true,
      leading: _ratingChip(rec.rating),
      title: Text(rec.outcomeLabel, style: const TextStyle(fontWeight: FontWeight.w500)),
      subtitle: Text('系统 ${(rec.systemProb * 100).toStringAsFixed(0)}% vs 市场 ${(rec.marketProb * 100).toStringAsFixed(0)}%'),
      trailing: Text(
        'EV ${(rec.ev * 100).toStringAsFixed(1)}%',
        style: TextStyle(
          fontWeight: FontWeight.bold,
          color: rec.ev >= 0.15 ? Colors.green : Colors.orange,
        ),
      ),
    );
  }

  Widget _ratingChip(String rating) {
    final count = rating.contains('★★★') ? 3 : rating.contains('★★') ? 2 : 1;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: count == 3 ? Colors.green.shade100 : Colors.amber.shade100,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(count, (_) => const Icon(Icons.star, size: 12, color: Colors.amber)),
      ),
    );
  }
}
