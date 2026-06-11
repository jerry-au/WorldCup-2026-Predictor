import 'dart:math';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

class ProbabilityGauge extends StatelessWidget {
  final double probability;
  final String label;
  final Color? color;

  const ProbabilityGauge({
    super.key,
    required this.probability,
    required this.label,
    this.color,
  });

  Color _defaultColor(double p) {
    if (p >= 0.6) return Colors.green;
    if (p >= 0.4) return Colors.orange;
    return Colors.red;
  }

  @override
  Widget build(BuildContext context) {
    final gaugeColor = color ?? _defaultColor(probability);
    final percentage = (probability * 100).toStringAsFixed(0);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 80,
          height: 80,
          child: CustomPaint(
            painter: _GaugePainter(probability: probability, color: gaugeColor),
            child: Center(
              child: Text(
                '$percentage%',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: gaugeColor,
                ),
              ),
            ),
          ),
        ).animate().fadeIn().scale(delay: 200.ms),
        const SizedBox(height: 4),
        Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.w500,
              ),
        ),
      ],
    );
  }
}

class _GaugePainter extends CustomPainter {
  final double probability;
  final Color color;

  _GaugePainter({required this.probability, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = min(size.width, size.height) / 2 - 4;

    // Background arc
    final bgPaint = Paint()
      ..color = Colors.grey.shade200
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -pi / 2,
      2 * pi,
      false,
      bgPaint,
    );

    // Foreground arc
    final fgPaint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 8
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -pi / 2,
      2 * pi * probability,
      false,
      fgPaint,
    );
  }

  @override
  bool shouldRepaint(covariant _GaugePainter oldDelegate) =>
      oldDelegate.probability != probability || oldDelegate.color != color;
}
