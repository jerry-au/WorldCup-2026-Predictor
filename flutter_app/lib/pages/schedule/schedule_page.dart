import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/schedule_match.dart';
import '../../providers/schedule_provider.dart';
import '../../widgets/animated_widgets.dart';
import '../prediction/prediction_page.dart';

/// 比赛状态常量
class MatchStatus {
  static const String completed = 'completed';
  static const String live = 'live';
  static const String upcoming = 'upcoming';
}

/// 赛程页面 - 显示所有已知比赛赛程（支持分页）
class SchedulePage extends ConsumerStatefulWidget {
  const SchedulePage({super.key});

  @override
  ConsumerState<SchedulePage> createState() => _SchedulePageState();
}

class _SchedulePageState extends ConsumerState<SchedulePage> {
  String? _selectedStage;
  String? _selectedStatus;
  int _currentPage = 1;
  final List<ScheduleMatch> _allMatches = [];
  int _totalMatches = 0;
  int _totalPages = 1;
  bool _hasInitialized = false;

  static const _stageOptions = [
    DropdownMenuItem(value: null, child: Text('全部阶段')),
    DropdownMenuItem(value: 'group_stage', child: Text('小组赛')),
    DropdownMenuItem(value: 'round_of_16', child: Text('1/8 决赛')),
    DropdownMenuItem(value: 'quarter', child: Text('1/4 决赛')),
    DropdownMenuItem(value: 'semi', child: Text('半决赛')),
    DropdownMenuItem(value: 'final', child: Text('决赛')),
  ];

  static const _statusOptions = [
    DropdownMenuItem(value: null, child: Text('全部状态')),
    DropdownMenuItem(value: 'upcoming', child: Text('未开始')),
    DropdownMenuItem(value: 'live', child: Text('进行中')),
    DropdownMenuItem(value: 'completed', child: Text('已结束')),
  ];

  void _resetPagination() {
    if (mounted) {
      setState(() {
        _currentPage = 1;
        _allMatches.clear();
        _totalMatches = 0;
        _totalPages = 1;
        _hasInitialized = false;
      });
    }
  }

  void _loadMore() {
    if (_currentPage >= _totalPages) return;
    setState(() {
      _currentPage++;
    });
  }

  @override
  Widget build(BuildContext context) {
    final filter = ScheduleFilter(
      stage: _selectedStage,
      status: _selectedStatus,
      page: _currentPage,
      pageSize: 20,
    );

    return Column(
      children: [
        FadeInWidget(
          delay: const Duration(milliseconds: 100),
          child: Card(
            margin: const EdgeInsets.all(12),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String?>(
                      value: _selectedStage,
                      decoration: InputDecoration(
                        labelText: '阶段',
                        contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      isDense: true,
                      items: _stageOptions,
                      onChanged: (v) {
                        _resetPagination();
                        setState(() => _selectedStage = v);
                      },
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: DropdownButtonFormField<String?>(
                      value: _selectedStatus,
                      decoration: InputDecoration(
                        labelText: '状态',
                        contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                      ),
                      isDense: true,
                      items: _statusOptions,
                      onChanged: (v) {
                        _resetPagination();
                        setState(() => _selectedStatus = v);
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),

        Expanded(
          child: _ScheduleMatchList(
            filter: filter,
            allMatches: _allMatches,
            totalMatches: _totalMatches,
            totalPages: _totalPages,
            currentPage: _currentPage,
            onLoadMore: _loadMore,
            onDataLoaded: (data) {
              // 只在首次加载或翻页时更新数据（不触发 setState 避免循环）
              if (!_hasInitialized || data.page != 1) {
                _hasInitialized = true;
                if (mounted) {
                  setState(() {
                    if (data.page == 1) {
                      _allMatches.clear();
                    }
                    _allMatches.addAll(data.matches);
                    _totalMatches = data.total;
                    _totalPages = data.totalPages;
                  });
                }
              }
            },
          ),
        ),
      ],
    );
  }
}

/// 比赛列表组件 - 独立组件避免无限循环
class _ScheduleMatchList extends ConsumerWidget {
  final ScheduleFilter filter;
  final List<ScheduleMatch> allMatches;
  final int totalMatches;
  final int totalPages;
  final int currentPage;
  final VoidCallback onLoadMore;
  final Function(AllMatchesResponse) onDataLoaded;

  const _ScheduleMatchList({
    required this.filter,
    required this.allMatches,
    required this.totalMatches,
    required this.totalPages,
    required this.currentPage,
    required this.onLoadMore,
    required this.onDataLoaded,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final matchesAsync = ref.watch(allMatchesProvider(filter));

    return matchesAsync.when(
      loading: () => allMatches.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : _buildListView(allMatches, null),
      error: (err, _) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 48, color: Colors.red.shade300),
            const SizedBox(height: 16),
            Text('加载失败', style: TextStyle(color: Colors.grey.shade600)),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: () => ref.invalidate(allMatchesProvider(filter)),
              child: const Text('重试'),
            ),
          ],
        ),
      ),
      data: (data) {
        // 通知父组件数据已加载（延迟到下一帧避免循环）
        WidgetsBinding.instance.addPostFrameCallback((_) {
          onDataLoaded(data);
        });

        final displayMatches = currentPage == 1 ? data.matches : allMatches;
        return _buildListView(displayMatches, data);
      },
    );
  }

  Widget _buildListView(List<ScheduleMatch> matches, AllMatchesResponse? data) {
    if (matches.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.event_note, size: 64, color: Colors.grey.shade400),
            const SizedBox(height: 16),
            Text('暂无赛程数据', style: TextStyle(color: Colors.grey.shade500, fontSize: 16)),
          ],
        ),
      );
    }

    final hasMore = data != null && data.hasMorePages;

    return RefreshIndicator(
      onRefresh: () async {
        // 通过回调通知父组件重置分页
      },
      child: ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        itemCount: matches.length + (hasMore ? 1 : 0),
        itemBuilder: (context, index) {
          if (index >= matches.length) {
            return Padding(
              padding: const EdgeInsets.all(16),
              child: OutlinedButton.icon(
                onPressed: onLoadMore,
                icon: const Icon(Icons.arrow_downward, size: 18),
                label: Text('加载更多 (${totalMatches - matches.length} 场)'),
                style: OutlinedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
              ),
            );
          }

          final match = matches[index];
          return StaggeredListItem(
            index: index,
            baseDelay: const Duration(milliseconds: 20),
            child: _ScheduleMatchCard(match: match),
          );
        },
      ),
    );
  }
}

/// 单场比赛卡片
class _ScheduleMatchCard extends StatelessWidget {
  final ScheduleMatch match;

  const _ScheduleMatchCard({required this.match});

  @override
  Widget build(BuildContext context) {
    final isCompleted = match.status == MatchStatus.completed;
    final isLive = match.status == MatchStatus.live;

    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: () => _navigateToPrediction(context),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 头部信息行
              Row(
                children: [
                  // 阶段标签
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: Colors.blue.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      _getStageLabel(match.stage),
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Colors.blue),
                    ),
                  ),
                  const SizedBox(width: 8),
                  // 状态标签
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: _getStatusColor(match.status ?? '').withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      _getStatusText(match.status ?? ''),
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: _getStatusColor(match.status ?? '')),
                    ),
                  ),
                  const Spacer(),
                  // 时间
                  Text(
                    _formatTime(match.commenceTime ?? DateTime.now()),
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                  ),
                ],
              ),

              const SizedBox(height: 14),

              // 主队 vs 客队
              Row(
                children: [
                  // 主队
                  Expanded(
                    child: Column(
                      children: [
                        ClipOval(
                          child: Image.network(
                            match.home.flagUrl ?? '',
                            width: 40,
                            height: 40,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Container(width: 40, height: 40, color: Colors.grey.shade200, child: Icon(Icons.flag, size: 24, color: Colors.grey)),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          match.home.nameCn ?? match.home.name,
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),

                  // 比分 / VS
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: isCompleted
                        ? Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                '${match.score?.home ?? "-"} : ${match.score?.away ?? "-"}',
                                style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold, color: Colors.green),
                              ),
                              if (match.score != null && (match.score!.homeEt != null || match.score!.homePenalties != null))
                                Padding(
                                  padding: const EdgeInsets.only(top: 4),
                                  child: Text(
                                    _getExtraScoreText(match.score!),
                                    style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                                  ),
                                ),
                            ],
                          )
                        : Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text('VS', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.grey.shade400)),
                              const SizedBox(height: 4),
                              if (match.prediction != null)
                                Text(
                                  '${match.prediction!.win.toStringAsFixed(0)}% / ${match.prediction!.draw.toStringAsFixed(0)}% / ${match.prediction!.lose.toStringAsFixed(0)}%',
                                  style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                                ),
                            ],
                          ),
                  ),

                  // 客队
                  Expanded(
                    child: Column(
                      children: [
                        ClipOval(
                          child: Image.network(
                            match.away.flagUrl ?? '',
                            width: 40,
                            height: 40,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Container(width: 40, height: 40, color: Colors.grey.shade200, child: Icon(Icons.flag, size: 24, color: Colors.grey)),
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          match.away.nameCn ?? match.away.name,
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    ),
                  ),
                ],
              ),

              // 底部额外信息
              if (match.stadium != null || match.groupName != null) ...[
                const SizedBox(height: 10),
                Divider(height: 1, color: Colors.grey.shade200),
                const SizedBox(height: 8),
                Row(
                  children: [
                    if (match.groupName != null) ...[
                      Icon(Icons.group, size: 14, color: Colors.grey.shade500),
                      const SizedBox(width: 4),
                      Text(match.groupName!, style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                    ],
                    if (match.stadium != null) ...[
                      const Spacer(),
                      Icon(Icons.stadium, size: 14, color: Colors.grey.shade500),
                      const SizedBox(width: 4),
                      Flexible(child: Text(match.stadium!, style: TextStyle(fontSize: 11, color: Colors.grey.shade600))),
                    ],
                  ],
                ),
              ],

              // 进行中比赛特殊标记
              if (isLive) ...[
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(colors: [Colors.orange.shade400, Colors.red.shade400]),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      SizedBox(width: 8, height: 8, child: CircularProgressIndicator(strokeWidth: 1.5, color: Colors.white)),
                      const SizedBox(width: 6),
                      const Text('进行中', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12)),
                    ],
                  ),
                ),
              ],

              // 点击提示
              const SizedBox(height: 6),
              Center(
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.analytics_outlined, size: 14, color: Colors.blue.shade300),
                    const SizedBox(width: 4),
                    Text(
                      '点击查看详细预测',
                      style: TextStyle(fontSize: 11, color: Colors.blue.shade300),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _navigateToPrediction(BuildContext context) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => PredictionPage(
          initialTeamA: match.home.code,
          initialTeamB: match.away.code,
          initialMatchType: match.matchType,
        ),
      ),
    );
  }

  String _getStageLabel(String? stage) {
    switch (stage) {
      case 'group_stage': return '小组赛';
      case 'round_of_16': return '1/8 决赛';
      case 'quarter': return '1/4 决赛';
      case 'semi': return '半决赛';
      case 'final': return '决赛';
      default: return stage ?? '';
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case MatchStatus.completed: return Colors.green;
      case MatchStatus.live: return Colors.orange;
      default: return Colors.blue;
    }
  }

  String _getStatusText(String status) {
    switch (status) {
      case MatchStatus.completed: return '已结束';
      case MatchStatus.live: return '进行中';
      default: return '未开始';
    }
  }

  String _formatTime(DateTime time) {
    final now = DateTime.now().toUtc();
    final diff = time.difference(now);

    if (diff.inDays > 7) {
      return '${time.month}/${time.day}';
    } else if (diff.inDays > 0) {
      return '${diff.inDays}天后';
    } else if (diff.inHours > 0) {
      return '${diff.inHours}小时后';
    } else if (diff.inMinutes > 0) {
      return '${diff.inMinutes}分钟后';
    } else {
      return '即将开始';
    }
  }

  String _getExtraScoreText(MatchScore score) {
    final parts = <String>[];
    if (score.homeEt != null && score.awayEt != null) {
      parts.add('加时 ${score.homeEt}-${score.awayEt}');
    }
    if (score.homePenalties != null && score.awayPenalties != null) {
      parts.add('点球 ${score.homePenalties}-${score.awayPenalties}');
    }
    return parts.join(', ');
  }
}
