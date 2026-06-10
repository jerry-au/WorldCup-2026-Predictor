import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class SimulationPage extends ConsumerStatefulWidget {
  const SimulationPage({super.key});

  @override
  ConsumerState<SimulationPage> createState() => _SimulationPageState();
}

class _SimulationPageState extends ConsumerState<SimulationPage> {
  bool _isRunning = false;
  double _progress = 0;
  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // ─── Header ──────────────────────────────────────────
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                Icon(Icons.bar_chart, size: 48, color: Theme.of(context).colorScheme.primary),
                const SizedBox(height: 12),
                Text('2026 世界杯赛事模拟',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 8),
                Text(
                  '基于混合泊松-Elo 模型，蒙特卡洛模拟 10,000 次',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 20),

                if (_isRunning) ...[
                  LinearProgressIndicator(value: _progress),
                  const SizedBox(height: 8),
                  Text('模拟中... ${(_progress * 100).toStringAsFixed(0)}%'),
                ] else ...[
                  FilledButton.icon(
                    onPressed: _startSimulation,
                    icon: const Icon(Icons.play_arrow),
                    label: const Text('运行模拟'),
                    style: FilledButton.styleFrom(minimumSize: const Size(double.infinity, 48)),
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),

        // ─── Placeholder Groups ──────────────────────────────
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('小组赛分组', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const Divider(),
                Text(
                  '48 支球队分为 12 个小组，每组 4 队\n'
                  '小组前两名进入 32 强淘汰赛',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.grey),
                ),
              ],
            ),
          ),
        ),

        // ─── Placeholder Results ─────────────────────────────
        if (!_isRunning)
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('晋级概率排行榜', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                  const Divider(),
                  const SizedBox(height: 40),
                  Center(
                    child: Text(
                      '运行模拟后显示各队晋级概率',
                      style: TextStyle(color: Colors.grey.shade500, fontSize: 16),
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }

  void _startSimulation() {
    setState(() {
      _isRunning = true;
      _progress = 0;
    });

    // Simulate progress for now
    _simulateProgress();
  }

  void _simulateProgress() async {
    for (int i = 1; i <= 100; i++) {
      await Future.delayed(const Duration(milliseconds: 80));
      if (!mounted) return;
      setState(() => _progress = i / 100);
    }
    if (!mounted) return;
    setState(() => _isRunning = false);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('模拟完成！')),
    );
  }
}
