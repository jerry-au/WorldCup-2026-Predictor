import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class ShareService {
  static Future<void> sharePrediction({
    required String teamA,
    required String teamB,
    required double winProb,
    required double drawProb,
    required double loseProb,
    required String matchType,
  }) async {
    final emoji = _getMatchTypeEmoji(matchType);
    final result = _getPredictionResult(winProb, drawProb, loseProb, teamA);

    final text = '''
$emoji 世界杯预测分享 $emoji

🇺🇸 $teamA vs $teamB

📊 预测概率:
• 主胜: ${(winProb * 100).toStringAsFixed(1)}%
• 平局: ${(drawProb * 100).toStringAsFixed(1)}%
• 客胜: ${(loseProb * 100).toStringAsFixed(1)}%

🏆 推荐: $result

---
⚽ 数据来源: WorldCup 2026 Predictor
💡 仅供参考，不构成投注建议
''';

    await Clipboard.setData(ClipboardData(text: text));
    _showCopiedSnackbar();
  }

  static Future<void> shareSimulationResult({
    required String champion,
    required double championProb,
    required String runnerUp,
    required double runnerUpProb,
    required String bestTeam,
    required double bestTeamProb,
  }) async {
    final text = '''
🏆 世界杯模拟结果 🏆

🥇 冠军: $champion (${(championProb * 100).toStringAsFixed(1)}%)
🥈 亚军: $runnerUp (${(runnerUpProb * 100).toStringAsFixed(1)}%)
⭐ 表现最佳: $bestTeam (${(bestTeamProb * 100).toStringAsFixed(1)}%)

---
⚽ 10,000次蒙特卡洛模拟
💡 仅供参考，不构成投注建议
⚽ WorldCup 2026 Predictor
''';

    await Clipboard.setData(ClipboardData(text: text));
    _showCopiedSnackbar();
  }

  static Future<void> shareValueBet({
    required String teamA,
    required String teamB,
    required String outcome,
    required double odds,
    required double ev,
    required int stars,
  }) async {
    final starsStr = '⭐' * stars;

    final text = '''
📈 价值投注分享 📈

⚽ $teamA vs $teamB

🎯 推荐投注: $outcome
📊 赔率: ${odds.toStringAsFixed(2)}
💰 期望值: ${(ev * 100).toStringAsFixed(1)}%
$starsStr 推荐等级

---
⚽ WorldCup 2026 Predictor
⚠️ 请理性投注，仅供参考
''';

    await Clipboard.setData(ClipboardData(text: text));
    _showCopiedSnackbar();
  }

  static String _getMatchTypeEmoji(String matchType) {
    switch (matchType.toLowerCase()) {
      case 'group':
        return '🔵';
      case 'round_of_16':
        return '🟠';
      case 'quarter_final':
        return '🟡';
      case 'semi_final':
        return '🟣';
      case 'final':
        return '🏆';
      default:
        return '⚽';
    }
  }

  static String _getPredictionResult(
    double winProb,
    double drawProb,
    double loseProb,
    String teamA,
  ) {
    final maxProb = [winProb, drawProb, loseProb].reduce((a, b) => a > b ? a : b);

    if (maxProb == winProb) {
      return '$teamA 主胜';
    } else if (maxProb == drawProb) {
      return '平局';
    } else {
      return '客胜';
    }
  }

  static void _showCopiedSnackbar() {
    debugPrint('已复制到剪贴板');
  }
}

class ShareButton extends StatelessWidget {
  final VoidCallback onShare;
  final IconData icon;
  final String? label;

  const ShareButton({
    super.key,
    required this.onShare,
    this.icon = Icons.share,
    this.label,
  });

  @override
  Widget build(BuildContext context) {
    if (label != null) {
      return TextButton.icon(
        onPressed: onShare,
        icon: Icon(icon, size: 18),
        label: Text(label!),
      );
    }

    return IconButton(
      onPressed: onShare,
      icon: Icon(icon),
      tooltip: '分享',
    );
  }
}
