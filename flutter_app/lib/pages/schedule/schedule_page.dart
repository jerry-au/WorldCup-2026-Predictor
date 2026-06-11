import 'package:flutter/material.dart';

/// 赛程页 — 小组积分表 + 今日赛程 + 淘汰赛对阵
/// TODO: 接入后端 API 后完善内容
class SchedulePage extends StatelessWidget {
  const SchedulePage({super.key});

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.calendar_month, size: 64, color: Colors.grey),
          SizedBox(height: 16),
          Text('赛程页', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          SizedBox(height: 8),
          Text('小组赛 / 淘汰赛 / 积分榜', style: TextStyle(color: Colors.grey, fontSize: 14)),
          SizedBox(height: 8),
          Text('即将上线...', style: TextStyle(color: Colors.grey, fontSize: 12)),
        ],
      ),
    );
  }
}
