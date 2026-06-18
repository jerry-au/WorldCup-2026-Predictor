import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../models/prediction.dart';
import '../../providers/prediction_provider.dart';
import '../../providers/teams_provider.dart';
import '../../services/share_service.dart';
import '../../widgets/probability_gauge.dart';
import '../../widgets/common_widgets.dart';
import '../../widgets/odds_trend_chart.dart';

class PredictionPage extends ConsumerStatefulWidget {
  final String? initialTeamA;
  final String? initialTeamB;
  final String? initialMatchType;

  const PredictionPage({
    super.key,
    this.initialTeamA,
    this.initialTeamB,
    this.initialMatchType,
  });

  @override
  ConsumerState<PredictionPage> createState() => _PredictionPageState();
}

class _PredictionPageState extends ConsumerState<PredictionPage> {
  String? _teamA;
  String? _teamB;
  String _matchType = 'group';

  @override
  void initState() {
    super.initState();
    _teamA = widget.initialTeamA;
    _teamB = widget.initialTeamB;
    if (widget.initialMatchType != null) {
      _matchType = widget.initialMatchType!;
    }
  }

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

    return Scaffold(
      appBar: AppBar(
        title: const Text('对战预测'),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: ListView(
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
      ),
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
        // Check if the current value is actually in the filtered list
        // If not (e.g. cached name instead of code), set value to null to avoid assertion error
        final validValue = value == null || filtered.any((t) => t.code == value);
        if (!validValue) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            onChanged(null);
          });
          value = null;
        }
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
              child: Text('${team.displayName} (${team.code})', style: const TextStyle(fontSize: 14)),
            );
          }).toList(),
          onChanged: onChanged,
          isExpanded: false,
          menuMaxHeight: 400,
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
        // ─── Team Data Cards ─────────────────────────────
        _TeamDataCard(teamA: prediction.teamA, teamB: prediction.teamB),
        const SizedBox(height: 12),

        // ─── Probability Gauges ────────────────────────────
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        '${prediction.teamA.displayName} vs ${prediction.teamB.displayName}',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.share),
                      onPressed: () {
                        ShareService.sharePrediction(
                          teamA: prediction.teamA.name,
                          teamB: prediction.teamB.name,
                          winProb: probs.win,
                          drawProb: probs.draw,
                          loseProb: probs.lose,
                          matchType: prediction.matchType,
                        );
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('预测结果已复制到剪贴板')),
                        );
                      },
                      tooltip: '分享预测',
                    ),
                  ],
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
                      label: '${prediction.teamB.displayName}\n胜',
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
        GestureDetector(
          onTap: () {
            final teamACode = prediction.teamA.code;
            final teamBCode = prediction.teamB.code;
            if (teamACode != null && teamBCode != null) {
              OddsTrendChart.show(
                context,
                matchId: '${teamACode}_$teamBCode',
                homeCode: teamACode,
                awayCode: teamBCode,
                homeTeamName: prediction.teamA.name,
                awayTeamName: prediction.teamB.name,
              );
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('球队代码不完整，无法加载赔率趋势')),
              );
            }
          },
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text('赔率对比 (${prediction.betting.oddsComparison.providerCount}家博彩公司)',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                      const Spacer(),
                      Icon(Icons.touch_app, size: 18, color: Colors.blue.shade400),
                      const SizedBox(width: 4),
                      Text('点击查看趋势', style: TextStyle(fontSize: 12, color: Colors.blue.shade400)),
                    ],
                  ),
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
                _BreakdownView(breakdown: prediction.breakdown),
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

class _BreakdownView extends StatelessWidget {
  final Map<String, dynamic> breakdown;

  const _BreakdownView({required this.breakdown});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: breakdown.entries.map((entry) {
        final value = entry.value;
        final displayValue = value is num ? value.toStringAsFixed(2) : value.toString();
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 3),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(_breakdownLabel(entry.key), style: const TextStyle(fontSize: 13)),
              Text(displayValue, style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 13)),
            ],
          ),
        );
      }).toList(),
    );
  }

  String _breakdownLabel(String key) {
    switch (key) {
      case 'elo_expected_a': return '主队 Elo 期望胜率';
      case 'expected_goals_a': return '主队期望进球';
      case 'expected_goals_b': return '客队期望进球';
      case 'strength_a': return '主队实力分 (DQ)';
      case 'strength_b': return '客队实力分 (DQ)';
      case 'market_value_a_m': return '主队总身价 (M EUR)';
      case 'market_value_b_m': return '客队总身价 (M EUR)';
      default: return key;
    }
  }
}

/// 球队数据对比卡片：展示 Elo、实力分、身价
class _TeamDataCard extends StatelessWidget {
  final TeamRef teamA;
  final TeamRef teamB;

  const _TeamDataCard({required this.teamA, required this.teamB});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('球队数据', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
            const Divider(),
            Row(
              children: [
                Expanded(child: _teamColumn(teamA, isLeft: true)),
                const Padding(padding: EdgeInsets.symmetric(horizontal: 8), child: Icon(Icons.compare_arrows_rounded, size: 20, color: Colors.grey)),
                Expanded(child: _teamColumn(teamB, isLeft: false)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _teamColumn(TeamRef team, {required bool isLeft}) {
    return Column(
      crossAxisAlignment: isLeft ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: [
        // 队名 + 代码
        Text(team.name, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        if (team.code != null)
          Text('(${team.code})', style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),

        const SizedBox(height: 10),

        // Elo
        if (team.elo != null)
          _dataRow('Elo', team.elo!.toStringAsFixed(0), isLeft),

        // 实力分
        if (team.dongqiudiStrength != null)
          _dataRow('实力分', team.dongqiudiStrength!.toStringAsFixed(1), isLeft),

        // 身价
        if (team.marketValueEur != null && team.marketValueEur! > 0)
          _dataRow('身价', team.marketValueDisplay, isLeft),
      ],
    );
  }

  Widget _dataRow(String label, String value, bool alignRight) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        mainAxisAlignment: alignRight ? MainAxisAlignment.end : MainAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (!alignRight) ...[
            Text(label, style: TextStyle(fontSize: 12, color: Colors.grey.shade700)),
            const SizedBox(width: 6),
            Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
          ] else ...[
            Text(value, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500)),
            const SizedBox(width: 6),
            Text(label, style: TextStyle(fontSize: 12, color: Colors.grey.shade700)),
          ],
        ],
      ),
    );
  }
}
