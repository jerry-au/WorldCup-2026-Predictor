import 'dart:math' as math;
import 'package:flutter/material.dart';

/// Data for a single match node in the bracket.
class BracketMatch {
  final String roundName;
  final int position;
  final String? teamA;
  final String? teamB;
  final double? probA;
  final double? probB;

  const BracketMatch({
    required this.roundName,
    required this.position,
    this.teamA,
    this.teamB,
    this.probA,
    this.probB,
  });
}

/// Round display labels (Chinese).
const Map<String, String> roundLabels = {
  'round_32': '32强',
  'round_16': '16强',
  'quarter': '八强',
  'semi': '四强',
  'final': '决赛',
};

/// Renders a horizontal knockout bracket using CustomPainter.
///
/// Layout: round_32 → round_16 → quarter → semi → final
/// Each match is a rounded rectangle with connector lines to the next round.
class BracketWidget extends StatelessWidget {
  final List<BracketMatch> matches;
  final Map<String, String> teamNames;

  const BracketWidget({
    super.key,
    required this.matches,
    this.teamNames = const {},
  });

  /// Calculate the intrinsic content size of the bracket.
  Size get contentSize {
    final roundSizes = _countPerRound();
    final maxMatches = roundSizes.values.reduce(math.max);
    final rounds = roundSizes.length;

    const nodeW = 100.0;
    const nodeH = 36.0;
    const gapX = 100.0;
    const gapY = 4.0;
    const roundHeaderH = 28.0; // round label height

    final height = maxMatches * (nodeH + gapY * 2) + 40 + roundHeaderH;
    final totalWidth = rounds * (nodeW + gapX) - gapX + 40;

    return Size(totalWidth, height);
  }

  @override
  Widget build(BuildContext context) {
    final roundSizes = _countPerRound();
    final rounds = roundSizes.length;

    const nodeW = 100.0;
    const nodeH = 36.0;
    const gapX = 100.0;
    const gapY = 4.0;
    const roundHeaderH = 28.0;

    final roundSpacing = <double>[gapX, gapX, gapX, gapX, gapX];
    final maxMatches = roundSizes.values.reduce(math.max);
    final height = maxMatches * (nodeH + gapY * 2) + 40 + roundHeaderH;
    final totalWidth = rounds * (nodeW + gapX) - gapX + 40;

    return SizedBox(
      width: totalWidth,
      height: height,
      child: CustomPaint(
        painter: _BracketPainter(
          matches: matches,
          teamNames: teamNames,
          nodeWidth: nodeW,
          nodeHeight: nodeH,
          roundSpacing: roundSpacing,
          gapY: gapY,
          rounds: rounds,
          roundSizes: roundSizes,
          roundHeaderHeight: roundHeaderH,
          isDark: Theme.of(context).brightness == Brightness.dark,
        ),
      ),
    );
  }

  Map<String, int> _countPerRound() {
    final map = <String, int>{};
    for (final m in matches) {
      map[m.roundName] = (map[m.roundName] ?? 0) + 1;
    }
    return map;
  }
}

class _BracketPainter extends CustomPainter {
  final List<BracketMatch> matches;
  final Map<String, String> teamNames;
  final double nodeWidth;
  final double nodeHeight;
  final List<double> roundSpacing;
  final double gapY;
  final int rounds;
  final Map<String, int> roundSizes;
  final double roundHeaderHeight;
  final bool isDark;

  final Map<String, Offset> _nodePositions = {};

  _BracketPainter({
    required this.matches,
    required this.teamNames,
    required this.nodeWidth,
    required this.nodeHeight,
    required this.roundSpacing,
    required this.gapY,
    required this.rounds,
    required this.roundSizes,
    required this.roundHeaderHeight,
    required this.isDark,
  });

  static const _roundOrder = [
    'round_32', 'round_16', 'quarter', 'semi', 'final'
  ];

  @override
  void paint(Canvas canvas, Size size) {
    _nodePositions.clear();

    final byRound = <String, List<BracketMatch>>{};
    for (final m in matches) {
      byRound.putIfAbsent(m.roundName, () => []).add(m);
    }

    final roundKeys = _roundOrder.where((r) => byRound.containsKey(r)).toList();
    if (roundKeys.isEmpty) return;

    const xStart = 20.0;
    final contentTop = roundHeaderHeight + 10; // space below round labels

    // Draw round header labels
    _drawRoundHeaders(canvas, roundKeys, xStart, size.width);

    // Draw matches per round
    for (int ri = 0; ri < roundKeys.length; ri++) {
      final roundName = roundKeys[ri];
      final roundMatches = byRound[roundName]!;
      roundMatches.sort((a, b) => a.position.compareTo(b.position));
      final count = roundMatches.length;
      final roundX = xStart + ri * (nodeWidth + roundSpacing[ri]);

      for (int mi = 0; mi < count; mi++) {
        final match = roundMatches[mi];
        final cy = contentTop + _matchCenterY(ri, count, mi, size.height - contentTop);

        final topY = cy - nodeHeight / 2;

        _nodePositions['${match.roundName}_${match.position}'] = Offset(roundX + nodeWidth / 2, cy);

        _drawNode(
          canvas,
          roundX,
          topY,
          nodeWidth,
          nodeHeight / 2 - 1,
          match.teamA,
          match.probA,
          teamNames,
          Colors.blue.shade700,
          topHalf: true,
        );

        _drawNode(
          canvas,
          roundX,
          topY + nodeHeight / 2 + 1,
          nodeWidth,
          nodeHeight / 2 - 1,
          match.teamB,
          match.probB,
          teamNames,
          Colors.red.shade700,
          topHalf: false,
        );
      }
    }

    // Draw connectors
    for (int ri = 0; ri < roundKeys.length - 1; ri++) {
      final currentRound = roundKeys[ri];
      final nextRound = roundKeys[ri + 1];
      final currentMatches = byRound[currentRound]!..sort((a, b) => a.position.compareTo(b.position));
      final nextMatches = byRound[nextRound]!..sort((a, b) => a.position.compareTo(b.position));

      for (int ni = 0; ni < nextMatches.length; ni++) {
        final topMatchIdx = ni * 2;
        final bottomMatchIdx = ni * 2 + 1;

        if (topMatchIdx < currentMatches.length && bottomMatchIdx < currentMatches.length) {
          final topKey = '${currentRound}_${currentMatches[topMatchIdx].position}';
          final bottomKey = '${currentRound}_${currentMatches[bottomMatchIdx].position}';
          final nextKey = '${nextRound}_${nextMatches[ni].position}';

          final topPos = _nodePositions[topKey];
          final bottomPos = _nodePositions[bottomKey];
          final nextPos = _nodePositions[nextKey];

          if (topPos != null && bottomPos != null && nextPos != null) {
            final currentX = topPos.dx - nodeWidth / 2;
            final nextX = nextPos.dx - nodeWidth / 2;
            final midX = (currentX + nodeWidth + nextX) / 2;
            _drawConnector(canvas, topPos, bottomPos, nextPos, midX);
          }
        }
      }
    }
  }

  void _drawRoundHeaders(Canvas canvas, List<String> roundKeys, double xStart, double totalWidth) {
    final labelColor = isDark ? Colors.grey.shade300 : Colors.grey.shade700;
    final lineColor = isDark ? Colors.grey.shade700 : Colors.grey.shade200;

    for (int ri = 0; ri < roundKeys.length; ri++) {
      final roundX = xStart + ri * (nodeWidth + roundSpacing[ri]);
      final label = roundLabels[roundKeys[ri]] ?? roundKeys[ri];

      final tp = TextPainter(
        text: TextSpan(
          text: label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: labelColor,
          ),
        ),
        textDirection: TextDirection.ltr,
        textAlign: TextAlign.center,
      );
      tp.layout(maxWidth: nodeWidth);
      tp.paint(canvas, Offset(roundX + (nodeWidth - tp.width) / 2, 6));

      // Divider line below label
      final linePaint = Paint()
        ..color = lineColor
        ..strokeWidth = 1;
      canvas.drawLine(
        Offset(roundX - 4, roundHeaderHeight - 2),
        Offset(roundX + nodeWidth + 4, roundHeaderHeight - 2),
        linePaint,
      );
    }
  }

  void _drawConnector(
    Canvas canvas,
    Offset fromTop,
    Offset fromBottom,
    Offset toNode,
    double midX,
  ) {
    final paint = Paint()
      ..color = isDark ? Colors.grey.shade600 : Colors.grey.shade300
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;

    final path = Path();

    path.moveTo(fromTop.dx + nodeWidth / 2, fromTop.dy);
    path.lineTo(midX, fromTop.dy);

    path.moveTo(fromBottom.dx + nodeWidth / 2, fromBottom.dy);
    path.lineTo(midX, fromBottom.dy);

    path.moveTo(midX, fromTop.dy);
    path.lineTo(midX, fromBottom.dy);

    path.moveTo(midX, (fromTop.dy + fromBottom.dy) / 2);
    path.lineTo(toNode.dx - nodeWidth / 2, toNode.dy);

    canvas.drawPath(path, paint);
  }

  double _matchCenterY(int ri, int count, int mi, double availableH) {
    final totalSlots = roundSizes[_roundOrder[ri]] ?? count;
    final slotH = nodeHeight + gapY * 2;
    final totalH = totalSlots * slotH;
    final startY = (availableH - totalH) / 2 + slotH / 2;
    return startY + (count > 1 ? mi * (totalH / count) : availableH / 2);
  }

  void _drawNode(
    Canvas canvas,
    double x,
    double y,
    double w,
    double h,
    String? teamCode,
    double? prob,
    Map<String, String> names,
    Color accent, {
    bool topHalf = true,
  }) {
    final bgColor = isDark ? Colors.grey.shade800 : Colors.white;
    final rRect = RRect.fromRectAndRadius(
      Rect.fromLTWH(x, y, w, h),
      const Radius.circular(4),
    );

    canvas.drawRRect(
      rRect,
      Paint()..color = bgColor,
    );

    canvas.drawRRect(
      rRect,
      Paint()
        ..color = accent.withOpacity(0.4)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1,
    );

    if (teamCode == null) return;

    final name = names[teamCode] ?? teamCode;
    final label = name.length > 4 ? name.substring(0, 4) : name;

    final probColor = isDark ? Colors.grey.shade300 : Colors.grey.shade700;

    final tp = TextPainter(
      text: TextSpan(
        text: label,
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w600,
          color: accent,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    tp.layout(maxWidth: w - 28);
    tp.paint(canvas, Offset(x + 4, y + 2));

    if (prob != null) {
      final probPct = (prob * 100).round();
      final pp = TextPainter(
        text: TextSpan(
          text: '$probPct%',
          style: TextStyle(
            fontSize: 9,
            fontWeight: FontWeight.bold,
            color: probColor,
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      pp.layout(maxWidth: 28);
      pp.paint(canvas, Offset(x + w - pp.width - 4, y + 2));
    }
  }

  @override
  bool shouldRepaint(covariant _BracketPainter oldDelegate) {
    return oldDelegate.matches != matches
        || oldDelegate.isDark != isDark;
  }
}
