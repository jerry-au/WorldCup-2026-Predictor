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

  @override
  Widget build(BuildContext context) {
    // Compute canvas size from match count per round
    final roundSizes = _countPerRound();
    final maxMatches = roundSizes.values.reduce(math.max);
    final rounds = roundSizes.length;

    const nodeW = 100.0;
    const nodeH = 36.0;
    const gapX = 100.0;
    const gapY = 4.0;

    // Round 32 → R16 → QF → SF → F  gets tighter spacing for inner rounds
    final roundSpacing = <double>[gapX, gapX, gapX, gapX, gapX];
    final height = maxMatches * (nodeH + gapY * 2) + 40;
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

  _BracketPainter({
    required this.matches,
    required this.teamNames,
    required this.nodeWidth,
    required this.nodeHeight,
    required this.roundSpacing,
    required this.gapY,
    required this.rounds,
    required this.roundSizes,
  });

  static const _roundOrder = [
    'round_32', 'round_16', 'quarter', 'semi', 'final'
  ];

  @override
  void paint(Canvas canvas, Size size) {
    // Group matches by round
    final byRound = <String, List<BracketMatch>>{};
    for (final m in matches) {
      byRound.putIfAbsent(m.roundName, () => []).add(m);
    }

    final roundKeys = _roundOrder.where((r) => byRound.containsKey(r)).toList();
    if (roundKeys.isEmpty) return;

    const xStart = 20.0;

    // Draw matches per round
    for (int ri = 0; ri < roundKeys.length; ri++) {
      final roundName = roundKeys[ri];
      final roundMatches = byRound[roundName]!;
      // Sort by position to ensure correct order
      roundMatches.sort((a, b) => a.position.compareTo(b.position));
      final count = roundMatches.length;
      final roundX = xStart + ri * (nodeWidth + roundSpacing[ri]);

      // Compute vertical centers considering connector position
      for (int mi = 0; mi < count; mi++) {
        final match = roundMatches[mi];
        final cy = _matchCenterY(ri, count, mi, roundKeys, size.height);

        final topY = cy - nodeHeight / 2;

        // Draw team A (top half)
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

        // Draw team B (bottom half)
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
  }

  double _matchCenterY(int ri, int count, int mi, List<String> roundKeys, double canvasH) {
    final totalSlots = roundSizes[_roundOrder[ri]] ?? count;
    final slotH = nodeHeight + gapY * 2;
    final totalH = totalSlots * slotH;
    final startY = (canvasH - totalH) / 2 + slotH / 2;
    // Place at evenly distributed positions within the round
    return startY + (count > 1 ? mi * (totalH / (count)) : canvasH / 2);
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
    final rRect = RRect.fromRectAndRadius(
      Rect.fromLTWH(x, y, w, h),
      const Radius.circular(4),
    );

    // Background
    canvas.drawRRect(
      rRect,
      Paint()..color = Colors.white,
    );

    // Border
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

    // Team code text
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

    // Probability text
    if (prob != null) {
      final probPct = (prob * 100).round();
      final pp = TextPainter(
        text: TextSpan(
          text: '$probPct%',
          style: TextStyle(
            fontSize: 9,
            fontWeight: FontWeight.bold,
            color: Colors.grey.shade700,
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
    return oldDelegate.matches != matches;
  }
}
