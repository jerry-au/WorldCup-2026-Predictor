import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/recommendation.dart';
import '../../providers/recommendations_provider.dart';
import '../../widgets/common_widgets.dart';

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
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ─── Value Bets Section ───────────────────────────
          SectionTitle(
            title: '今日价值场次',
            trailing: IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: () {
                ref.invalidate(valueBetsProvider);
                ref.invalidate(discrepanciesProvider);
              },
            ),
          ),
          valueBetsAsync.when(
            loading: () => const LoadingWidget(),
            error: (err, _) => ErrorWidgetView(
              message: '加载失败: ${err.toString()}',
              onRetry: () => ref.invalidate(valueBetsProvider),
            ),
            data: (bets) {
              if (bets.isEmpty) {
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Center(
                      child: Column(
                        children: [
                          Icon(Icons.check_circle_outline, size: 48, color: Colors.grey.shade400),
                          const SizedBox(height: 8),
                          Text('当前没有高价值投注机会', style: TextStyle(color: Colors.grey.shade600)),
                        ],
                      ),
                    ),
                  ),
                );
              }
              return Column(
                children: bets.map((bet) => _ValueBetCard(bet: bet)).toList(),
              );
            },
          ),

          const SizedBox(height: 24),

          // ─── Discrepancies Section ────────────────────────
          SectionTitle(
            title: '特别关注',
            trailing: Icon(Icons.warning_amber, color: Colors.orange.shade700),
          ),
          discrepanciesAsync.when(
            loading: () => const LoadingWidget(),
            error: (err, _) => ErrorWidgetView(
              message: '加载失败: ${err.toString()}',
              onRetry: () => ref.invalidate(discrepanciesProvider),
            ),
            data: (alerts) {
              if (alerts.isEmpty) {
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Center(
                      child: Column(
                        children: [
                          Icon(Icons.shield_outlined, size: 48, color: Colors.grey.shade400),
                          const SizedBox(height: 8),
                          Text('当前未检测到市场分歧', style: TextStyle(color: Colors.grey.shade600)),
                        ],
                      ),
                    ),
                  ),
                );
              }
              return Column(
                children: alerts.map((alert) => _DiscrepancyCard(alert: alert)).toList(),
              );
            },
          ),
        ],
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
      child: ListTile(
        leading: _ratingBadge(bet.starCount),
        title: Text('${bet.teamA} vs ${bet.teamB}', style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(
          '${bet.outcomeLabel} 赔率 ${bet.odds.toStringAsFixed(2)}',
          style: const TextStyle(fontSize: 13),
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              'EV ${(bet.ev * 100).toStringAsFixed(1)}%',
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 16,
                color: bet.ev >= 0.15 ? Colors.green : Colors.orange,
              ),
            ),
            Text(
              '系统 ${(bet.systemProb * 100).toStringAsFixed(0)}% / 市场 ${(bet.marketProb * 100).toStringAsFixed(0)}%',
              style: const TextStyle(fontSize: 10, color: Colors.grey),
            ),
          ],
        ),
      ),
    );
  }

  Widget _ratingBadge(int stars) {
    return Container(
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: stars >= 3 ? Colors.green.shade50 : Colors.amber.shade50,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          const Icon(Icons.star, size: 14, color: Colors.amber),
          Text('$stars', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.amber.shade700)),
        ],
      ),
    );
  }
}

class _DiscrepancyCard extends StatelessWidget {
  final DiscrepancyAlert alert;

  const _DiscrepancyCard({required this.alert});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      color: Colors.orange.shade50,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.warning_amber, size: 18, color: Colors.orange.shade700),
                const SizedBox(width: 6),
                Text('${alert.teamA} vs ${alert.teamB}',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                const Spacer(),
                Text(alert.group, style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
              ],
            ),
            const SizedBox(height: 8),
            if (alert.discrepancy['detail'] != null)
              Text(alert.discrepancy['detail'] as String,
                  style: TextStyle(color: Colors.orange.shade900, fontSize: 13)),
            if (alert.systemProbs.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                '系统预测: 胜 ${(alert.systemProbs['win']! * 100).toStringAsFixed(0)}% / '
                '平 ${(alert.systemProbs['draw']! * 100).toStringAsFixed(0)}% / '
                '负 ${(alert.systemProbs['lose']! * 100).toStringAsFixed(0)}%',
                style: const TextStyle(fontSize: 12),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
