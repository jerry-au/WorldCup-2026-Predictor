import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/recommendation.dart';
import '../../providers/recommendations_provider.dart';
import '../../widgets/common_widgets.dart';
import 'dart:math' as math;

class BettingPage extends ConsumerWidget {
  const BettingPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final valueBetsAsync = ref.watch(valueBetsProvider);
    final discrepanciesAsync = ref.watch(discrepanciesProvider);

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(valueBetsProvider);
        ref.invalidate(discrepanciesProvider);
      },
      child: CustomScrollView(
        slivers: [
          SliverAppBar(
            pinned: true,
            title: const Text('投注推荐'),
            centerTitle: true,
            actions: [
              IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: () {
                  ref.invalidate(valueBetsProvider);
                  ref.invalidate(discrepanciesProvider);
                },
              ),
            ],
          ),
          SliverPadding(
            padding: const EdgeInsets.all(16),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                Builder(
                  builder: (context) {
                    return valueBetsAsync.when(
                      loading: () => const SizedBox.shrink(),
                      error: (_, __) => const SizedBox.shrink(),
                      data: (bets) {
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Row(
                            children: [
                              Icon(Icons.schedule, size: 14, color: Colors.grey.shade500),
                              const SizedBox(width: 4),
                              Text(
                                '推荐数据每 8 小时自动更新',
                                style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
                              ),
                            ],
                          ),
                        );
                      },
                    );
                  },
                ),
                const SectionTitle(
                  title: '今日价值场次',
                  subtitle: '系统预测 vs 市场赔率',
                ),
                valueBetsAsync.when(
                  loading: () => const LoadingWidget(),
                  error: (err, _) => ErrorWidgetView(
                    message: '加载失败: ${err.toString()}',
                    onRetry: () => ref.invalidate(valueBetsProvider),
                  ),
                  data: (bets) {
                    if (bets.isEmpty) {
                      return const EmptyStateCard(
                        icon: Icons.check_circle_outline,
                        title: '当前没有高价值投注机会',
                        subtitle: '系统未发现期望值为正的投注',
                      );
                    }
                    return Column(
                      children: [
                        _ValueBetStatsCard(bets: bets),
                        ...bets.map((bet) => _ValueBetCard(bet: bet)).toList(),
                      ],
                    );
                  },
                ),
                const SizedBox(height: 24),
                const SectionTitle(
                  title: '特别关注',
                  subtitle: '系统与市场存在重大分歧',
                  icon: Icons.warning_amber,
                ),
                discrepanciesAsync.when(
                  loading: () => const LoadingWidget(),
                  error: (err, _) => ErrorWidgetView(
                    message: '加载失败: ${err.toString()}',
                    onRetry: () => ref.invalidate(discrepanciesProvider),
                  ),
                  data: (alerts) {
                    if (alerts.isEmpty) {
                      return const EmptyStateCard(
                        icon: Icons.shield_outlined,
                        title: '当前未检测到市场分歧',
                        subtitle: '系统与市场观点一致',
                      );
                    }
                    return Column(
                      children: alerts.map((alert) => _DiscrepancyCard(alert: alert)).toList(),
                    );
                  },
                ),
                const SizedBox(height: 40),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

class SectionTitle extends StatelessWidget {
  final String title;
  final String? subtitle;
  final IconData? icon;

  const SectionTitle({
    super.key,
    required this.title,
    this.subtitle,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          if (icon != null)
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: Icon(icon, color: Colors.orange.shade700, size: 20),
            ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                if (subtitle != null)
                  Text(
                    subtitle!,
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade500),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class EmptyStateCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;

  const EmptyStateCard({
    super.key,
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Center(
          child: Column(
            children: [
              Icon(icon, size: 48, color: Colors.grey.shade400),
              const SizedBox(height: 12),
              Text(title, style: TextStyle(color: Colors.grey.shade600, fontSize: 16)),
              const SizedBox(height: 4),
              Text(subtitle, style: TextStyle(color: Colors.grey.shade400, fontSize: 13)),
            ],
          ),
        ),
      ),
    );
  }
}

class _ValueBetStatsCard extends StatelessWidget {
  final List<ValueBet> bets;

  const _ValueBetStatsCard({required this.bets});

  @override
  Widget build(BuildContext context) {
    final totalEv = bets.fold(0.0, (sum, bet) => sum + bet.ev);
    final avgEv = totalEv / bets.length;
    final highValueCount = bets.where((b) => b.starCount >= 3).length;

    return Card(
      color: Colors.blue.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Expanded(
              child: Column(
                children: [
                  Text('${bets.length}', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                  const Text('价值场次', style: TextStyle(fontSize: 12, color: Colors.grey)),
                ],
              ),
            ),
            VerticalDivider(color: Colors.blue.shade200),
            Expanded(
              child: Column(
                children: [
                  Text('${(avgEv * 100).toStringAsFixed(1)}%', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                  const Text('平均 EV', style: TextStyle(fontSize: 12, color: Colors.grey)),
                ],
              ),
            ),
            VerticalDivider(color: Colors.blue.shade200),
            Expanded(
              child: Column(
                children: [
                  Text('$highValueCount', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                  const Text('强烈推荐', style: TextStyle(fontSize: 12, color: Colors.grey)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ValueBetCard extends StatelessWidget {
  final ValueBet bet;

  const _ValueBetCard({required this.bet});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            Row(
              children: [
                _ratingBadge(bet.starCount),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${bet.teamA} vs ${bet.teamB}',
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
                      ),
                      Text(
                        '${bet.outcomeLabel} @ ${bet.odds.toStringAsFixed(2)}',
                        style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      'EV ${(bet.ev * 100).toStringAsFixed(1)}%',
                      style: TextStyle(
                        fontWeight: FontWeight.bold,
                        fontSize: 18,
                        color: bet.ev >= 0.15 ? Colors.green : bet.ev >= 0.05 ? Colors.orange : Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '系统 ${(bet.systemProb * 100).toStringAsFixed(0)}%',
                      style: const TextStyle(fontSize: 11, color: Colors.blue),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 8),
            _ProbabilityChart(systemProb: bet.systemProb, marketProb: bet.marketProb),
          ],
        ),
      ),
    );
  }

  Widget _ratingBadge(int stars) {
    Color bgColor;
    Color textColor;
    switch (stars) {
      case 3:
        bgColor = Colors.green.shade100;
        textColor = Colors.green.shade700;
        break;
      case 2:
        bgColor = Colors.amber.shade100;
        textColor = Colors.amber.shade700;
        break;
      case 1:
        bgColor = Colors.blue.shade100;
        textColor = Colors.blue.shade700;
        break;
      default:
        bgColor = Colors.grey.shade100;
        textColor = Colors.grey.shade600;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        children: [
          const Icon(Icons.star, size: 12, color: Colors.amber),
          const SizedBox(width: 2),
          Text('${'★' * stars}', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: textColor)),
        ],
      ),
    );
  }
}

class _ProbabilityChart extends StatelessWidget {
  final double systemProb;
  final double marketProb;

  const _ProbabilityChart({required this.systemProb, required this.marketProb});

  @override
  Widget build(BuildContext context) {
    final maxProb = math.max(systemProb, marketProb);

    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('概率对比', style: TextStyle(fontSize: 11, color: Colors.grey)),
              const SizedBox(height: 4),
              Stack(
                children: [
                  Container(
                    height: 8,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade200,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  Container(
                    height: 8,
                    width: (systemProb / maxProb) * 100,
                    decoration: BoxDecoration(
                      color: Colors.blue,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                  Container(
                    height: 8,
                    width: (marketProb / maxProb) * 100,
                    decoration: BoxDecoration(
                      color: Colors.orange,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  const Text('系统', style: TextStyle(fontSize: 10, color: Colors.blue)),
                  const SizedBox(width: 12),
                  Text('市场 ${(marketProb * 100).toStringAsFixed(0)}%', style: TextStyle(fontSize: 10, color: Colors.orange)),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DiscrepancyCard extends StatelessWidget {
  final DiscrepancyAlert alert;

  const _DiscrepancyCard({required this.alert});

  @override
  Widget build(BuildContext context) {
    final delta = (alert.discrepancy['max_delta'] as num?)?.toDouble() ?? 0;
    final confidence = (alert.discrepancy['system_confidence'] as num?)?.toDouble() ?? 0;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: Colors.orange.shade50,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: Colors.orange.shade200,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(Icons.warning_amber, size: 16, color: Colors.orange.shade700),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${alert.teamA} vs ${alert.teamB}',
                        style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 15),
                      ),
                      Text('${alert.group}组', style: TextStyle(fontSize: 12, color: Colors.grey)),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      '分歧 ${(delta * 100).toStringAsFixed(0)}%',
                      style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.orange.shade700),
                    ),
                    Text(
                      '置信度 ${(confidence * 100).toStringAsFixed(0)}%',
                      style: TextStyle(fontSize: 11, color: Colors.grey),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (alert.discrepancy['detail'] != null)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Text(
                  alert.discrepancy['detail'] as String,
                  style: TextStyle(color: Colors.orange.shade800, fontSize: 13),
                ),
              ),
            _DiscrepancyProbRow(alert: alert),
          ],
        ),
      ),
    );
  }
}

class _DiscrepancyProbRow extends StatelessWidget {
  final DiscrepancyAlert alert;

  const _DiscrepancyProbRow({required this.alert});

  @override
  Widget build(BuildContext context) {
    final win = alert.systemProbs['win'] ?? 0;
    final draw = alert.systemProbs['draw'] ?? 0;
    final lose = alert.systemProbs['lose'] ?? 0;

    final marketWin = alert.marketProbs?['win'] ?? 0;
    final marketDraw = alert.marketProbs?['draw'] ?? 0;
    final marketLose = alert.marketProbs?['lose'] ?? 0;

    return Row(
      children: [
        Expanded(
          child: Column(
            children: [
              Text('${(win * 100).toStringAsFixed(0)}%', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.blue)),
              const Text('主胜', style: TextStyle(fontSize: 10, color: Colors.grey)),
              if (marketWin > 0)
                Text('市场 ${(marketWin * 100).toStringAsFixed(0)}%', style: TextStyle(fontSize: 9, color: Colors.orange)),
            ],
          ),
        ),
        Expanded(
          child: Column(
            children: [
              Text('${(draw * 100).toStringAsFixed(0)}%', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.blue)),
              const Text('平局', style: TextStyle(fontSize: 10, color: Colors.grey)),
              if (marketDraw > 0)
                Text('市场 ${(marketDraw * 100).toStringAsFixed(0)}%', style: TextStyle(fontSize: 9, color: Colors.orange)),
            ],
          ),
        ),
        Expanded(
          child: Column(
            children: [
              Text('${(lose * 100).toStringAsFixed(0)}%', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.blue)),
              const Text('客胜', style: TextStyle(fontSize: 10, color: Colors.grey)),
              if (marketLose > 0)
                Text('市场 ${(marketLose * 100).toStringAsFixed(0)}%', style: TextStyle(fontSize: 9, color: Colors.orange)),
            ],
          ),
        ),
      ],
    );
  }
}