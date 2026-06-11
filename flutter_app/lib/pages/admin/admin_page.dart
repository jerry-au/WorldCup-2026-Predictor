import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class AdminPage extends ConsumerWidget {
  const AdminPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('数据管理'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          _UpdateCard(
            title: '球员数据',
            description: '从懂球帝、football-data.org 拉取球员信息、身价和赛季数据',
            dataType: 'players',
          ),
          SizedBox(height: 12),
          _UpdateCard(
            title: '赛事数据',
            description: '同步比赛赛程、比分和历史对战记录',
            dataType: 'matches',
          ),
          SizedBox(height: 12),
          _UpdateCard(
            title: '赔率数据',
            description: '从 The Odds API 获取最新博彩公司赔率',
            dataType: 'odds',
          ),
        ],
      ),
    );
  }
}

/// 更新卡片：展示数据类型、状态、操作按钮
class _UpdateCard extends ConsumerWidget {
  final String title;
  final String description;
  final String dataType;

  const _UpdateCard({
    required this.title,
    required this.description,
    required this.dataType,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // TODO: 从 API 获取各数据类型的最后更新时间
    final hasData = false;
    final isSuccess = false;
    final lastUpdated = DateTime.now().subtract(const Duration(hours: 2));

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                _UpdateStatusIndicator(
                  hasData: hasData,
                  isSuccess: isSuccess,
                  lastUpdated: lastUpdated,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                      Text(
                        description,
                        style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () => _UpdateAction.triggerUpdate(context, ref, dataType),
                    icon: const Icon(Icons.sync),
                    label: const Text('更新'),
                  ),
                ),
                const SizedBox(width: 8),
                OutlinedButton(
                  onPressed: () => _UpdateAction.showDetails(context, dataType),
                  child: const Text('详情'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// 状态指示器：根据 hasData / isSuccess / 最近更新时间显示不同图标和颜色
class _UpdateStatusIndicator extends StatelessWidget {
  final bool hasData;
  final bool isSuccess;
  final DateTime lastUpdated;

  const _UpdateStatusIndicator({
    required this.hasData,
    required this.isSuccess,
    required this.lastUpdated,
  });

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final diff = now.difference(lastUpdated);
    final isRecent = diff.inMinutes < 30;

    IconData icon;
    Color color;

    if (!hasData) {
      icon = Icons.cloud_off;
      color = Colors.grey.shade400;
    } else if (isRecent) {
      icon = Icons.check_circle;
      color = Colors.green.shade600;
    } else if (!isSuccess) {
      icon = Icons.error;
      color = Colors.red.shade400;
    } else {
      icon = Icons.schedule;
      color = Colors.orange.shade600;
    }

    return Icon(icon, size: 28, color: color);
  }
}

/// 更新操作辅助类
class _UpdateAction {
  static void triggerUpdate(BuildContext context, WidgetRef ref, String dataType) {
    // TODO: 调用 API 触发更新
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('已触发 $dataType 更新')),
    );
  }

  static void showDetails(BuildContext context, String dataType) {
    // TODO: 显示详细更新日志
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('查看 $dataType 更新详情')),
    );
  }
}
