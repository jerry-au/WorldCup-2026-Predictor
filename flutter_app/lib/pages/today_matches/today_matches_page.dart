import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:cached_network_image/cached_network_image.dart';

import '../../config/api_config.dart';
import '../../models/match_common.dart';
import '../../models/today_match.dart';
import '../../providers/today_matches_provider.dart';
import '../../widgets/common_widgets.dart';
import '../../widgets/odds_trend_chart.dart';
import '../prediction/prediction_page.dart';
import '../teams/team_detail_page.dart';

/// Build absolute image URL from API response (which may be relative path).
String _imagePathToUrl(String path) {
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  final base = ApiConfig.baseUrl.replaceAll('/api/v1', '');
  return '$base$path';
}

class TodayMatchesPage extends ConsumerWidget {
  const TodayMatchesPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final matchesAsync = ref.watch(todayMatchesProvider);

    return RefreshIndicator(
      onRefresh: () async => ref.refresh(todayMatchesProvider.future),
      child: matchesAsync.when(
        loading: () => const LoadingWidget(message: '加载今日赛事...'),
        error: (err, _) => ErrorWidgetView(
          message: '加载失败: ${err.toString()}',
          onRetry: () => ref.invalidate(todayMatchesProvider),
        ),
        data: (data) {
          if (data.matches.isEmpty) {
            return ListView(
              padding: const EdgeInsets.all(16),
              children: const [
                _EmptyMatchesCard(),
              ],
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: data.matches.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) =>
                _TodayMatchCard(match: data.matches[index]),
          );
        },
      ),
    );
  }
}

class _EmptyMatchesCard extends StatelessWidget {
  const _EmptyMatchesCard();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          children: [
            Icon(Icons.event_busy, size: 48, color: Colors.grey.shade400),
            const SizedBox(height: 12),
            Text(
              '今日暂无赛事',
              style: TextStyle(color: Colors.grey.shade600, fontSize: 16),
            ),
            const SizedBox(height: 4),
            Text(
              '请稍后查看最新赛程安排',
              style: TextStyle(color: Colors.grey.shade500, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }
}

class _TodayMatchCard extends StatelessWidget {
  final TodayMatch match;

  const _TodayMatchCard({required this.match});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _MatchHeader(match: match),
            const SizedBox(height: 16),
            _TeamRow(match: match),
            const SizedBox(height: 16),
            InkWell(
              borderRadius: BorderRadius.circular(12),
              onTap: () => _openPrediction(context),
              child: _PredictionSection(match: match),
            ),
            const SizedBox(height: 12),
            _OddsSection(match: match),
          ],
        ),
      ),
    );
  }

  void _openPrediction(BuildContext context) {
    if (match.home.code.isEmpty || match.away.code.isEmpty) return;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => PredictionPage(
          initialTeamA: match.home.code,
          initialTeamB: match.away.code,
          initialMatchType: match.matchType,
        ),
      ),
    );
  }
}

class _MatchHeader extends StatelessWidget {
  final TodayMatch match;

  const _MatchHeader({required this.match});

  @override
  Widget build(BuildContext context) {
    final timeText = match.commenceTime == null
        ? '时间待定'
        : DateFormat('HH:mm').format(match.commenceTime!.toLocal());
    final stageText = [match.stage, match.groupName]
        .where((text) => text != null && text.isNotEmpty)
        .join(' · ');

    return Row(
      children: [
        Icon(Icons.schedule, size: 16, color: Colors.grey.shade600),
        const SizedBox(width: 6),
        Text(
          timeText,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        if (stageText.isNotEmpty) ...[
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              stageText,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
            ),
          ),
        ] else
          const Spacer(),
      ],
    );
  }
}

class _TeamRow extends StatelessWidget {
  final TodayMatch match;

  const _TeamRow({required this.match});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(
            child: _TeamButton(
                team: match.home, alignment: CrossAxisAlignment.start)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Text(
            'VS',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: Colors.grey.shade500,
            ),
          ),
        ),
        Expanded(
            child: _TeamButton(
                team: match.away, alignment: CrossAxisAlignment.end)),
      ],
    );
  }
}

class _TeamButton extends StatelessWidget {
  final MatchTeam team;
  final CrossAxisAlignment alignment;

  const _TeamButton({required this.team, required this.alignment});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: team.code.isEmpty
          ? null
          : () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => TeamDetailPage(
                      teamCode: team.code,
                      teamName: team.nameCn?.isNotEmpty == true
                          ? team.nameCn!
                          : team.name),
                ),
              );
            },
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (team.flagUrl != null && team.flagUrl!.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: CircleAvatar(
                  radius: 12,
                  backgroundImage: CachedNetworkImageProvider(_imagePathToUrl(team.flagUrl!)),
                ),
              ),
            Flexible(
              child: Column(
                crossAxisAlignment: alignment,
                children: [
                  Text(
                    team.nameCn?.isNotEmpty == true ? team.nameCn! : team.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    team.code,
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PredictionSection extends StatelessWidget {
  final TodayMatch match;

  const _PredictionSection({required this.match});

  @override
  Widget build(BuildContext context) {
    final prediction = match.prediction;
    final colorScheme = Theme.of(context).colorScheme;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.analytics_outlined,
                  size: 16, color: colorScheme.primary),
              const SizedBox(width: 6),
              const Text('预测', style: TextStyle(fontWeight: FontWeight.w600)),
              const Spacer(),
              Text(
                '查看详情',
                style: TextStyle(fontSize: 12, color: colorScheme.primary),
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (prediction == null)
            Text(
              '暂无预测数据',
              style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
            )
          else
            Row(
              children: [
                Expanded(
                    child:
                        _ProbabilityItem(label: '主胜', value: prediction.win)),
                Expanded(
                    child:
                        _ProbabilityItem(label: '平局', value: prediction.draw)),
                Expanded(
                    child:
                        _ProbabilityItem(label: '客胜', value: prediction.lose)),
              ],
            ),
        ],
      ),
    );
  }
}

class _ProbabilityItem extends StatelessWidget {
  final String label;
  final double value;

  const _ProbabilityItem({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(label,
            style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
        const SizedBox(height: 4),
        Text(
          '${(value * 100).toStringAsFixed(0)}%',
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
}

class _OddsSection extends StatelessWidget {
  final TodayMatch match;

  const _OddsSection({required this.match});

  @override
  Widget build(BuildContext context) {
    final odds = match.odds;
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: odds == null
          ? null
          : () => OddsTrendChart.show(
                context,
                matchId: match.matchId,
                homeCode: match.home.code,
                awayCode: match.away.code,
                homeTeamName: match.home.displayName,
                awayTeamName: match.away.displayName,
                fallbackOdds: odds,
              ),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade200),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.trending_up, size: 16, color: Colors.green.shade700),
                const SizedBox(width: 6),
                const Text('赔率', style: TextStyle(fontWeight: FontWeight.w600)),
                const Spacer(),
                Text(
                  odds == null ? '暂无数据' : '${odds.providerCount} 家机构 · 查看曲线',
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                ),
              ],
            ),
            const SizedBox(height: 10),
            if (odds == null)
              Text(
                '暂无赔率数据',
                style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
              )
            else
              Row(
                children: [
                  Expanded(child: _OddsItem(label: '主胜', value: odds.avgWin)),
                  Expanded(child: _OddsItem(label: '平局', value: odds.avgDraw)),
                  Expanded(child: _OddsItem(label: '客胜', value: odds.avgLose)),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

// 赔率弹窗已提取到 ../../widgets/odds_trend_chart.dart (OddsTrendChart.show)

class _OddsItem extends StatelessWidget {
  final String label;
  final double? value;

  const _OddsItem({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(label,
            style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
        const SizedBox(height: 4),
        Text(
          value?.toStringAsFixed(2) ?? '-',
          style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ],
    );
  }
}
