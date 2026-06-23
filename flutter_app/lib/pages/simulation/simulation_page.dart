import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../../models/simulation.dart';
import '../../providers/simulation_provider.dart';
import '../../widgets/common_widgets.dart';
import 'bracket_painter.dart';
import '../prediction/prediction_page.dart';
import '../teams/team_list_page.dart';

class SimulationPage extends ConsumerStatefulWidget {
  const SimulationPage({super.key});

  @override
  ConsumerState<SimulationPage> createState() => _SimulationPageState();
}

class _SimulationPageState extends ConsumerState<SimulationPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(simulationProvider.notifier).loadDefaultPresetName();
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(simulationProvider);
    final notifier = ref.read(simulationProvider.notifier);

    return RefreshIndicator(
      onRefresh: () async => notifier.reset(),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ─── Control Card ──────────────────────────────────
          _buildControlCard(context, state, notifier),
          const SizedBox(height: 16),

          // ─── Entry Cards ──────────────────────────────────
          _buildPredictionEntryCard(context),
          const SizedBox(height: 12),
          _buildTeamEntryCard(context),
          const SizedBox(height: 16),

          // ─── Loading / Results ──────────────────────────────
          if (state.isRunning) _buildProgress(context, state),
          if (state.error != null) ErrorWidgetView(
            message: state.error!,
            onRetry: () => notifier.startSimulation(),
          ),
          if (state.result != null) ...[
            _buildRankingTable(context, state.result!),
            const SizedBox(height: 16),
            if (state.result!.bracket.isNotEmpty)
              _buildBracket(context, state.result!),
          ],
        ],
      ),
    );
  }

  // ─── Control Card ──────────────────────────────────────────────

  Widget _buildControlCard(
    BuildContext context,
    SimulationState state,
    SimulationNotifier notifier,
  ) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Icon(Icons.bar_chart, size: 48, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 12),
            Text(
              '2026 世界杯赛事模拟',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              '基于混合泊松-Elo 模型 · 蒙特卡洛 10,000 次',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey),
            ),
            if (state.presetName != null) ...[
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: const Color(0xFFE8F5E9),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  '当前模拟预设：${state.presetName}',
                  style: const TextStyle(fontSize: 11, color: Color(0xFF2E7D32)),
                ),
              ),
            ],
            const SizedBox(height: 20),

            if (state.isRunning)
              Column(
                children: [
                  LinearProgressIndicator(value: state.progress),
                  const SizedBox(height: 8),
                  Text(
                    '模拟中... ${(state.progress * 100).toStringAsFixed(0)}%',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              )
            else ...[
              FilledButton.icon(
                onPressed: state.result != null
                    ? null
                    : () => notifier.startSimulation(),
                icon: const Icon(Icons.play_arrow),
                label: const Text('运行模拟'),
                style: FilledButton.styleFrom(
                  minimumSize: const Size(double.infinity, 48),
                ),
              ),
              if (state.result != null) ...[
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  onPressed: () => notifier.startSimulation(),
                  icon: const Icon(Icons.refresh),
                  label: const Text('重新模拟'),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  // ─── Entry Cards ──────────────────────────────────────────

  Widget _buildPredictionEntryCard(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const PredictionPage()),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Icon(Icons.sports_soccer, size: 40, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('对战预测', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text('选择两支球队，查看单场胜平负概率与比分预测', style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, color: Colors.grey.shade400),
            ],
          ),
        ),
      ),
    ).animate().fadeIn(delay: 50.ms);
  }

  Widget _buildTeamEntryCard(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const TeamListPage()),
        ),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Icon(Icons.groups, size: 40, color: Theme.of(context).colorScheme.primary),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('球队详情', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 4),
                    Text('浏览全部 48 支参赛球队数据，支持搜索、筛选与排序', style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, color: Colors.grey.shade400),
            ],
          ),
        ),
      ),
    ).animate().fadeIn(delay: 100.ms);
  }

  // ─── Progress ─────────────────────────────────────────────────

  Widget _buildProgress(BuildContext context, SimulationState state) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const SizedBox(
              width: 20, height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            const SizedBox(width: 12),
            Text('赛事模拟中... ${(state.progress * 100).toStringAsFixed(0)}%'),
          ],
        ),
      ),
    );
  }

  // ─── Ranking Table ────────────────────────────────────────────

  Widget _buildRankingTable(BuildContext context, SimulationResult result) {
    final sorted = List<TeamProbability>.from(result.standings)
      ..sort((a, b) => b.champion.compareTo(a.champion));

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '晋级概率排行榜',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
            ),
            const Divider(),
            ...sorted.take(20).map((team) => _rankRow(context, team)),
            if (sorted.length > 20)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Center(
                  child: Text(
                    '+ ${sorted.length - 20} 支球队',
                    style: TextStyle(color: Colors.grey.shade500, fontSize: 13),
                  ),
                ),
              ),
          ],
        ),
      ),
    ).animate().fadeIn(delay: 200.ms);
  }

  Widget _rankRow(BuildContext context, TeamProbability team) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              SizedBox(
                width: 28,
                child: Text(
                  team.teamCode,
                  style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
                ),
              ),
              Expanded(
                child: Text(
                  team.teamName,
                  style: const TextStyle(fontSize: 13),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Text(
                '${(team.champion * 100).toStringAsFixed(1)}%',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                  color: team.champion >= 0.05
                      ? Colors.green.shade700
                      : team.champion >= 0.01
                          ? Colors.orange
                          : Colors.grey,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: SizedBox(
              height: 6,
              child: Row(
                children: [
                  _barSegment(team.round32, Colors.grey.shade300),
                  _barSegment(team.round16, Colors.blue.shade200),
                  _barSegment(team.quarter, Colors.blue.shade400),
                  _barSegment(team.semi, Colors.orange.shade400),
                  _barSegment(team.final_, Colors.deepOrange.shade400),
                  _barSegment(team.champion, Colors.green.shade600),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _barSegment(double prob, Color color) {
    return Flexible(
      flex: (prob * 1000).round().clamp(0, 1000),
      child: Container(color: prob > 0 ? color : Colors.transparent),
    );
  }

  // ─── Bracket ──────────────────────────────────────────────────

  Widget _buildBracket(BuildContext context, SimulationResult result) {
    final bracketMatches = result.bracket.map((m) => BracketMatch(
      roundName: m.roundName,
      position: m.position,
      teamA: m.teamA,
      teamB: m.teamB,
      probA: m.probA,
      probB: m.probB,
    )).toList();

    final teamNames = {
      for (final t in result.standings)
        t.teamCode: t.teamName,
    };

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  '淘汰赛对阵图',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                _BracketControls(
                  onFitWidth: () {},
                  onZoomIn: () {},
                  onZoomOut: () {},
                  onFullscreen: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => _FullscreenBracketPage(
                          matches: bracketMatches,
                          teamNames: teamNames,
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
            const Divider(),
            SizedBox(
              height: 360,
              child: _InteractiveBracket(
                matches: bracketMatches,
                teamNames: teamNames,
              ),
            ),
          ],
        ),
      ),
    ).animate().fadeIn(delay: 400.ms);
  }
}

// ─── Bracket Controls ────────────────────────────────────────

class _BracketControls extends StatelessWidget {
  final VoidCallback onFitWidth;
  final VoidCallback onZoomIn;
  final VoidCallback onZoomOut;
  final VoidCallback onFullscreen;

  const _BracketControls({
    required this.onFitWidth,
    required this.onZoomIn,
    required this.onZoomOut,
    required this.onFullscreen,
  });

  @override
  Widget build(BuildContext context) {
    final color = Colors.grey.shade600;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Tooltip(
          message: '全图查看',
          child: InkWell(
            onTap: onFullscreen,
            borderRadius: BorderRadius.circular(4),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.fullscreen, size: 16, color: color),
                  const SizedBox(width: 4),
                  Text('全图', style: TextStyle(fontSize: 12, color: color)),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

// ─── Interactive Bracket Widget ─────────────────────────────

class _InteractiveBracket extends StatefulWidget {
  final List<BracketMatch> matches;
  final Map<String, String> teamNames;

  const _InteractiveBracket({
    required this.matches,
    required this.teamNames,
  });

  @override
  State<_InteractiveBracket> createState() => _InteractiveBracketState();
}

class _InteractiveBracketState extends State<_InteractiveBracket> {
  final TransformationController _controller = TransformationController();
  final GlobalKey _viewerKey = GlobalKey();
  double _currentScale = 1.0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _fitToWidth() {
    final bracket = BracketWidget(matches: widget.matches, teamNames: widget.teamNames);
    final contentW = bracket.contentSize.width;
    final renderBox = _viewerKey.currentContext?.findRenderObject() as RenderBox?;
    if (renderBox == null) return;
    final viewportW = renderBox.size.width;
    final scale = viewportW / contentW;
    _animateToScale(scale.clamp(0.3, 2.0));
  }

  void _zoomIn() {
    final next = (_currentScale * 1.3).clamp(0.3, 2.0);
    _animateToScale(next);
  }

  void _zoomOut() {
    final next = (_currentScale / 1.3).clamp(0.3, 2.0);
    _animateToScale(next);
  }

  void _animateToScale(double target) {
    final start = _controller.value.clone();
    final end = Matrix4.identity()..scale(target);

    final tween = Matrix4Tween(begin: start, end: end);
    final controller = AnimationController(
      vsync: Navigator.of(context),
      duration: const Duration(milliseconds: 200),
    );

    controller.addListener(() {
      _controller.value = tween.evaluate(controller);
      setState(() {
        _currentScale = _controller.value.getMaxScaleOnAxis();
      });
    });
    controller.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        controller.dispose();
      }
    });
    controller.forward();
  }

  void _handleDoubleTap(TapDownDetails details) {
    final isZoomedOut = _currentScale <= 0.9;
    _animateToScale(isZoomedOut ? 1.5 : 0.5);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          key: _viewerKey,
          child: GestureDetector(
            onDoubleTapDown: _handleDoubleTap,
            child: InteractiveViewer(
              transformationController: _controller,
              boundaryMargin: const EdgeInsets.all(60),
              minScale: 0.3,
              maxScale: 2.0,
              constrained: false,
              onInteractionUpdate: (details) {
                setState(() {
                  _currentScale = _controller.value.getMaxScaleOnAxis();
                });
              },
              child: BracketWidget(
                matches: widget.matches,
                teamNames: widget.teamNames,
              ),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            IconButton(
              icon: const Icon(Icons.zoom_out, size: 20),
              onPressed: _zoomOut,
              tooltip: '缩小',
              constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '${(_currentScale * 100).round()}%',
                style: TextStyle(fontSize: 12, color: Colors.grey.shade700, fontWeight: FontWeight.w500),
              ),
            ),
            IconButton(
              icon: const Icon(Icons.zoom_in, size: 20),
              onPressed: _zoomIn,
              tooltip: '放大',
              constraints: const BoxConstraints(minWidth: 36, minHeight: 36),
            ),
            const SizedBox(width: 8),
            TextButton.icon(
              onPressed: _fitToWidth,
              icon: const Icon(Icons.fit_screen, size: 18),
              label: const Text('适应宽度', style: TextStyle(fontSize: 12)),
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                minimumSize: const Size(44, 36),
              ),
            ),
          ],
        ),
        Text(
          '双击放大/缩小 · 双指缩放 · 拖动查看',
          style: TextStyle(fontSize: 11, color: Colors.grey.shade400),
        ),
      ],
    );
  }
}

// ─── Fullscreen Bracket Page ────────────────────────────────

class _FullscreenBracketPage extends StatefulWidget {
  final List<BracketMatch> matches;
  final Map<String, String> teamNames;

  const _FullscreenBracketPage({
    required this.matches,
    required this.teamNames,
  });

  @override
  State<_FullscreenBracketPage> createState() => _FullscreenBracketPageState();
}

class _FullscreenBracketPageState extends State<_FullscreenBracketPage> {
  final TransformationController _controller = TransformationController();
  final GlobalKey _viewerKey = GlobalKey();
  double _currentScale = 1.0;
  bool _initialFitDone = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _fitToWidth() {
    final bracket = BracketWidget(matches: widget.matches, teamNames: widget.teamNames);
    final contentW = bracket.contentSize.width;
    final renderBox = _viewerKey.currentContext?.findRenderObject() as RenderBox?;
    if (renderBox == null) return;
    final viewportW = renderBox.size.width - 32; // account for padding
    final scale = viewportW / contentW;
    _animateToScale(scale.clamp(0.2, 3.0));
  }

  void _fitToHeight() {
    final bracket = BracketWidget(matches: widget.matches, teamNames: widget.teamNames);
    final contentH = bracket.contentSize.height;
    final renderBox = _viewerKey.currentContext?.findRenderObject() as RenderBox?;
    if (renderBox == null) return;
    final viewportH = renderBox.size.height - 100; // account for app bar + controls
    final scale = viewportH / contentH;
    _animateToScale(scale.clamp(0.2, 3.0));
  }

  void _zoomIn() {
    final next = (_currentScale * 1.3).clamp(0.2, 3.0);
    _animateToScale(next);
  }

  void _zoomOut() {
    final next = (_currentScale / 1.3).clamp(0.2, 3.0);
    _animateToScale(next);
  }

  void _resetView() {
    _animateToScale(1.0);
  }

  void _animateToScale(double target) {
    final start = _controller.value.clone();
    final end = Matrix4.identity()..scale(target);

    final tween = Matrix4Tween(begin: start, end: end);
    final controller = AnimationController(
      vsync: Navigator.of(context),
      duration: const Duration(milliseconds: 250),
    );

    controller.addListener(() {
      _controller.value = tween.evaluate(controller);
      setState(() {
        _currentScale = _controller.value.getMaxScaleOnAxis();
      });
    });
    controller.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        controller.dispose();
      }
    });
    controller.forward();
  }

  void _handleDoubleTap(TapDownDetails details) {
    final isZoomedOut = _currentScale <= 0.8;
    _animateToScale(isZoomedOut ? 2.0 : 0.5);
  }

  @override
  Widget build(BuildContext context) {
    // Auto-fit to width on first build
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_initialFitDone && mounted) {
        _initialFitDone = true;
        _fitToWidth();
      }
    });

    return Scaffold(
      backgroundColor: Colors.black87,
      appBar: AppBar(
        backgroundColor: Colors.black87,
        foregroundColor: Colors.white,
        title: const Text('淘汰赛对阵图'),
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Column(
          children: [
            Expanded(
              key: _viewerKey,
              child: GestureDetector(
                onDoubleTapDown: _handleDoubleTap,
                child: InteractiveViewer(
                  transformationController: _controller,
                  boundaryMargin: const EdgeInsets.all(100),
                  minScale: 0.2,
                  maxScale: 3.0,
                  constrained: false,
                  onInteractionUpdate: (details) {
                    setState(() {
                      _currentScale = _controller.value.getMaxScaleOnAxis();
                    });
                  },
                  child: BracketWidget(
                    matches: widget.matches,
                    teamNames: widget.teamNames,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            SafeArea(
              top: false,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: Colors.grey.shade900,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                  children: [
                    _buildControlButton(
                      icon: Icons.zoom_out,
                      label: '缩小',
                      onTap: _zoomOut,
                    ),
                    _buildControlButton(
                      icon: Icons.zoom_in,
                      label: '放大',
                      onTap: _zoomIn,
                    ),
                    _buildControlButton(
                      icon: Icons.fit_screen,
                      label: '适应宽度',
                      onTap: _fitToWidth,
                    ),
                    _buildControlButton(
                      icon: Icons.height,
                      label: '适应高度',
                      onTap: _fitToHeight,
                    ),
                    _buildControlButton(
                      icon: Icons.refresh,
                      label: '重置',
                      onTap: _resetView,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '${(_currentScale * 100).round()}% · 双击切换缩放 · 双指缩放 · 拖动查看',
              style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildControlButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 20, color: Colors.white70),
            const SizedBox(height: 4),
            Text(label, style: const TextStyle(fontSize: 10, color: Colors.white70)),
          ],
        ),
      ),
    );
  }
}
