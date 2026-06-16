import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../models/odds_history.dart';
import '../../models/today_match.dart';
import '../../services/providers.dart';

/// 赔率趋势图 - 展示历史赔率变化（AlertDialog 形式，与当日赛事页一致）
class OddsTrendChart extends StatelessWidget {
  final String matchId;
  final String homeCode;
  final String awayCode;
  final String homeTeamName;
  final String awayTeamName;

  const OddsTrendChart({
    super.key,
    required this.matchId,
    required this.homeCode,
    required this.awayCode,
    required this.homeTeamName,
    required this.awayTeamName,
  });

  /// 显示赔率趋势图的 Dialog
  static void show(BuildContext context, {
    required String matchId,
    required String homeCode,
    required String awayCode,
    required String homeTeamName,
    required String awayTeamName,
  }) {
    showDialog<void>(
      context: context,
      builder: (_) => OddsTrendChart(
        matchId: matchId,
        homeCode: homeCode,
        awayCode: awayCode,
        homeTeamName: homeTeamName,
        awayTeamName: awayTeamName,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return _OddsHistoryDialog(
      matchId: matchId,
      homeCode: homeCode,
      awayCode: awayCode,
      homeTeamName: homeTeamName,
      awayTeamName: awayTeamName,
    );
  }
}

class _OddsHistoryDialog extends ConsumerWidget {
  final String matchId;
  final String homeCode;
  final String awayCode;
  final String homeTeamName;
  final String awayTeamName;

  const _OddsHistoryDialog({
    required this.matchId,
    required this.homeCode,
    required this.awayCode,
    required this.homeTeamName,
    required this.awayTeamName,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return FutureBuilder<dynamic>(
      future: ref.read(apiServiceProvider).getOddsHistory(
            matchId: matchId,
            homeCode: homeCode,
            awayCode: awayCode,
          ),
      builder: (context, snapshot) {
        final title = '$homeTeamName vs $awayTeamName';
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
          content = _OddsHistoryContent(history: history);
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

  const _OddsHistoryContent({required this.history});

  @override
  Widget build(BuildContext context) {
    final currentOdds = history.latestOdds;
    final latestTime = currentOdds?.updatedAt ??
        (history.points.isNotEmpty ? history.points.last.recordedAt : null);

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _LatestOddsSummary(
          odds: currentOdds,
          fallbackPoint:
              history.points.isNotEmpty ? history.points.last : null,
        ),
        const SizedBox(height: 12),
        if (history.points.isEmpty)
          const SizedBox(
              height: 150,
              child: Center(child: Text('暂无赔率变化记录')))
        else if (history.points.length == 1)
          const SizedBox(
              height: 150,
              child: Center(
                  child: Text('暂无曲线变化，当前只有 1 个记录点')))
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
          '共 ${history.points.length} 个历史点${latestTime == null ? '' : ' · 最新更新 ${DateFormat('MM-dd HH:mm').format(latestTime)}'}',
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
