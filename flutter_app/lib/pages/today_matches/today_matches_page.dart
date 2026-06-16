import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../config/api_config.dart';
import '../../models/odds_history.dart';
import '../../models/today_match.dart';
import '../../providers/today_matches_provider.dart';
import '../../services/providers.dart';
import '../../widgets/common_widgets.dart';
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
                  backgroundImage: NetworkImage(_imagePathToUrl(team.flagUrl!)),
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

class _OddsSection extends ConsumerWidget {
  final TodayMatch match;

  const _OddsSection({required this.match});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final odds = match.odds;
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: odds == null ? null : () => _showOddsHistory(context, ref, match),
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

  Future<void> _showOddsHistory(
      BuildContext context, WidgetRef ref, TodayMatch match) async {
    showDialog<void>(
      context: context,
      builder: (_) => _OddsHistoryDialog(match: match, ref: ref),
    );
  }
}

class _OddsHistoryDialog extends StatelessWidget {
  final TodayMatch match;
  final WidgetRef ref;

  const _OddsHistoryDialog({required this.match, required this.ref});

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<dynamic>(
      future: ref.read(apiServiceProvider).getOddsHistory(
            matchId: match.matchId,
            homeCode: match.home.code,
            awayCode: match.away.code,
          ),
      builder: (context, snapshot) {
        final title =
            '${match.home.displayName} vs ${match.away.displayName}';
        Widget content;
        if (snapshot.connectionState != ConnectionState.done) {
          content = const SizedBox(
              height: 220, child: Center(child: CircularProgressIndicator()));
        } else if (snapshot.hasError ||
            snapshot.data is! Map<String, dynamic>) {
          content = const SizedBox(
              height: 180, child: Center(child: Text('赔率历史加载失败')));
        } else {
          final history = OddsHistoryResponse.fromJson(
              snapshot.data as Map<String, dynamic>);
          content =
              _OddsHistoryContent(history: history, fallbackOdds: match.odds);
        }

        return AlertDialog(
          title: Text(title, style: const TextStyle(fontSize: 16)),
          content: SizedBox(width: 520, child: content),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('关闭'),
            ),
          ],
        );
      },
    );
  }
}

class _OddsHistoryContent extends StatelessWidget {
  final OddsHistoryResponse history;
  final MatchOddsSummary? fallbackOdds;

  const _OddsHistoryContent(
      {required this.history, required this.fallbackOdds});

  @override
  Widget build(BuildContext context) {
    final currentOdds = history.latestOdds ?? fallbackOdds;
    final latestTime = currentOdds?.updatedAt ??
        (history.points.isNotEmpty ? history.points.last.recordedAt : null);

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _LatestOddsSummary(
            odds: currentOdds,
            fallbackPoint:
                history.points.isNotEmpty ? history.points.last : null),
        const SizedBox(height: 12),
        if (history.points.isEmpty)
          const SizedBox(height: 150, child: Center(child: Text('暂无赔率变化记录')))
        else if (history.points.length == 1)
          const SizedBox(
              height: 150, child: Center(child: Text('暂无曲线变化，当前只有 1 个记录点')))
        else ...[
          SizedBox(height: 260, child: _OddsLineChart(points: history.points)),
          const SizedBox(height: 12),
          const Wrap(
            spacing: 16,
            runSpacing: 6,
            children: [
              _LegendDot(color: Colors.green, label: '主胜'),
              _LegendDot(color: Colors.orange, label: '平局'),
              _LegendDot(color: Colors.blue, label: '客胜'),
            ],
          ),
        ],
        const SizedBox(height: 8),
        Text(
          '最新赔率来自当前赛事接口 · 共 ${history.points.length} 个历史点${latestTime == null ? '' : ' · 最新更新 ${DateFormat('MM-dd HH:mm').format(latestTime)}'}',
          style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
        ),
      ],
    );
  }
}

class _LatestOddsSummary extends StatelessWidget {
  final MatchOddsSummary? odds;
  final OddsHistoryPoint? fallbackPoint;

  const _LatestOddsSummary({required this.odds, required this.fallbackPoint});

  @override
  Widget build(BuildContext context) {
    final win = odds?.avgWin ?? fallbackPoint?.avgWin;
    final draw = odds?.avgDraw ?? fallbackPoint?.avgDraw;
    final lose = odds?.avgLose ?? fallbackPoint?.avgLose;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.green.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.green.shade100),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('最新赔率',
              style: TextStyle(
                  fontWeight: FontWeight.w700, color: Colors.green.shade800)),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(child: _OddsItem(label: '主胜', value: win)),
              Expanded(child: _OddsItem(label: '平局', value: draw)),
              Expanded(child: _OddsItem(label: '客胜', value: lose)),
            ],
          ),
        ],
      ),
    );
  }
}

class _OddsLineChart extends StatelessWidget {
  final List<OddsHistoryPoint> points;

  const _OddsLineChart({required this.points});

  @override
  Widget build(BuildContext context) {
    final values = <double>[
      for (final point in points) ...[
        if (point.avgWin != null) point.avgWin!,
        if (point.avgDraw != null) point.avgDraw!,
        if (point.avgLose != null) point.avgLose!,
      ],
    ];
    final minY = values.reduce((a, b) => a < b ? a : b) - 0.2;
    final maxY = values.reduce((a, b) => a > b ? a : b) + 0.2;

    LineChartBarData line(
        List<double?> Function(OddsHistoryPoint) selector, Color color) {
      return LineChartBarData(
        spots: [
          for (var i = 0; i < points.length; i++)
            if (selector(points[i]).first != null)
              FlSpot(i.toDouble(), selector(points[i]).first!),
        ],
        isCurved: true,
        color: color,
        barWidth: 2.5,
        dotData: const FlDotData(show: true),
      );
    }

    return LineChart(
      LineChartData(
        minY: minY < 0 ? 0 : minY,
        maxY: maxY,
        gridData: const FlGridData(
            show: true, drawVerticalLine: false, horizontalInterval: 0.5),
        titlesData: FlTitlesData(
          topTitles:
              const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles:
              const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 28,
              interval:
                  points.length > 6 ? (points.length / 4).ceilToDouble() : 1,
              getTitlesWidget: (value, meta) {
                final index = value.toInt();
                if (index < 0 || index >= points.length) {
                  return const SizedBox.shrink();
                }
                final time = points[index].recordedAt;
                return Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    time == null ? '' : DateFormat('HH:mm').format(time),
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
            ),
          ),
          leftTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: true, reservedSize: 36)),
        ),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          line((point) => [point.avgWin], Colors.green),
          line((point) => [point.avgDraw], Colors.orange),
          line((point) => [point.avgLose], Colors.blue),
        ],
      ),
    );
  }
}

class _LegendDot extends StatelessWidget {
  final Color color;
  final String label;

  const _LegendDot({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
            width: 10,
            height: 10,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
        const SizedBox(width: 4),
        Text(label, style: const TextStyle(fontSize: 12)),
      ],
    );
  }
}

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
