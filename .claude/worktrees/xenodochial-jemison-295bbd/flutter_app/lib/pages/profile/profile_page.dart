import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class ProfilePage extends ConsumerWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // User section
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              children: [
                CircleAvatar(
                  radius: 32,
                  backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                  child: Icon(Icons.person, size: 32, color: Theme.of(context).colorScheme.primary),
                ),
                const SizedBox(height: 8),
                Text('世界杯预测', style: Theme.of(context).textTheme.titleLarge),
                Text('2026 美加墨', style: TextStyle(color: Colors.grey.shade600)),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),

        // Data status
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('数据状态', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const Divider(),
                _dataStatusRow('球队数据', '2026-06-01', true),
                _dataStatusRow('Elo 评分', '2026-06-01', true),
                _dataStatusRow('赔率数据', '2026-06-10', true),
                const SizedBox(height: 12),
                FilledButton.tonalIcon(
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('数据刷新已触发')),
                    );
                  },
                  icon: const Icon(Icons.refresh),
                  label: const Text('刷新数据'),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),

        // About
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('关于', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                const Divider(),
                _aboutRow(Icons.analytics, '预测模型', '混合泊松-Elo'),
                _aboutRow(Icons.sports_soccer, '参赛球队', '48 队'),
                _aboutRow(Icons.calculate, '模拟次数', '10,000 次蒙特卡洛'),
                _aboutRow(Icons.code, '版本', '0.1.0'),
                const SizedBox(height: 8),
                Text(
                  '数据仅供参考，不构成投注建议。请理性投注。',
                  style: TextStyle(color: Colors.grey.shade500, fontSize: 12),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _dataStatusRow(String label, String date, bool isFresh) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          const Icon(Icons.check_circle, size: 14, color: Colors.green),
          const SizedBox(width: 8),
          Text(label, style: const TextStyle(fontSize: 13)),
          const Spacer(),
          Text(date, style: const TextStyle(fontSize: 12, color: Colors.grey)),
        ],
      ),
    );
  }

  Widget _aboutRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 16, color: Colors.grey),
          const SizedBox(width: 8),
          Text(label, style: const TextStyle(fontSize: 13)),
          const Spacer(),
          Text(value, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}
