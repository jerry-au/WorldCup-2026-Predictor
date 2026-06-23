import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../../config/api_config.dart';
import '../../models/team.dart';
import '../../providers/teams_provider.dart';
import '../../widgets/common_widgets.dart';
import '../../widgets/animated_widgets.dart';
import 'team_detail_page.dart';

class TeamListPage extends ConsumerStatefulWidget {
  const TeamListPage({super.key});

  @override
  ConsumerState<TeamListPage> createState() => _TeamListPageState();
}

class _TeamListPageState extends ConsumerState<TeamListPage> {
  String? _filterConfederation;
  String _sortBy = 'elo_rating';
  final _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final filter = TeamsFilter(confederation: _filterConfederation, sortBy: _sortBy);
    final teamsAsync = ref.watch(teamsListProvider(filter));

    return Scaffold(
      appBar: AppBar(
        title: const Text('球队列表'),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      body: Column(
      children: [
        FadeInWidget(
          delay: const Duration(milliseconds: 100),
          child: Card(
            margin: const EdgeInsets.all(12),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                children: [
                  TextField(
                    controller: _searchController,
                    decoration: InputDecoration(
                      hintText: '搜索球队...',
                      prefixIcon: const Icon(Icons.search),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      suffixIcon: _searchController.text.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear),
                              onPressed: () {
                                _searchController.clear();
                                setState(() {});
                              },
                            )
                          : null,
                    ),
                    onChanged: (_) => setState(() {}),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String?>(
                          value: _filterConfederation,
                          decoration: InputDecoration(
                            labelText: '洲际',
                            contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                          isDense: true,
                          items: [
                            const DropdownMenuItem(value: null, child: Text('全部')),
                            ...TeamDetail.confederations.map((c) => DropdownMenuItem(
                                  value: c,
                                  child: Text(TeamDetail.confederationNames[c] ?? c, style: const TextStyle(fontSize: 13)),
                                )),
                          ],
                          onChanged: (v) => setState(() => _filterConfederation = v),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: _sortBy,
                          decoration: InputDecoration(
                            labelText: '排序',
                            contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                          ),
                          isDense: true,
                          items: const [
                            DropdownMenuItem(value: 'elo_rating', child: Text('Elo 评分', style: TextStyle(fontSize: 13))),
                            DropdownMenuItem(value: 'fifa_rank', child: Text('FIFA 排名', style: TextStyle(fontSize: 13))),
                            DropdownMenuItem(value: 'name', child: Text('名称', style: TextStyle(fontSize: 13))),
                          ],
                          onChanged: (v) => setState(() => _sortBy = v ?? 'elo_rating'),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),

        Expanded(
          child: teamsAsync.when(
            loading: () => const LoadingWidget(message: '加载球队数据...'),
            error: (err, _) => ErrorWidgetView(
              message: '加载失败: ${err.toString()}',
              onRetry: () => ref.invalidate(teamsListProvider(filter)),
            ),
            data: (teams) {
              final filtered = _searchController.text.isNotEmpty
                  ? teams.where((t) => t.displayName.toLowerCase().contains(_searchController.text.toLowerCase())).toList()
                  : teams;

              if (filtered.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.search_off, size: 64, color: Colors.grey.shade400),
                      const SizedBox(height: 16),
                      Text('未找到球队', style: TextStyle(color: Colors.grey.shade500, fontSize: 16)),
                    ],
                  ),
                );
              }

              return RefreshIndicator(
                onRefresh: () async => ref.invalidate(teamsListProvider(filter)),
                child: ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  itemCount: filtered.length,
                  itemBuilder: (context, index) {
                    final team = filtered[index];
                    return StaggeredListItem(
                      index: index,
                      baseDelay: const Duration(milliseconds: 30),
                      child: _TeamCard(team: team),
                    );
                  },
                ),
              );
            },
          ),
        ),
      ],
      ),
    );
  }
}

class _TeamCard extends StatelessWidget {
  final TeamSummary team;

  const _TeamCard({required this.team});

  String _imagePathToUrl(String path) {
    if (path.startsWith('http')) return path;
    return '${ApiConfig.baseUrl}$path';
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        leading: Hero(
          tag: 'team_${team.code}',
          child: CircleAvatar(
            backgroundColor: Theme.of(context).colorScheme.primaryContainer,
            backgroundImage: team.flagUrl != null
                ? CachedNetworkImageProvider(_imagePathToUrl(team.flagUrl!))
                : null,
            child: team.flagUrl == null
                ? Text(
                    team.code,
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Theme.of(context).colorScheme.primary,
                      fontSize: 12,
                    ),
                  )
                : null,
          ),
        ),
        title: Text(
          team.displayName,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Text(
          '${TeamDetail.confederationNames[team.confederation] ?? team.confederation} · ${team.groupName}组',
          style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              'Elo ${team.eloRating.toStringAsFixed(0)}',
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
            Text(
              'FIFA #${team.fifaRank}',
              style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
            ),
          ],
        ),
        onTap: () {
          Navigator.of(context).push(
            PageRouteBuilder(
              pageBuilder: (context, animation, secondaryAnimation) =>
                  TeamDetailPage(teamCode: team.code, teamName: team.displayName),
              transitionsBuilder: (context, animation, secondaryAnimation, child) {
                return FadeTransition(
                  opacity: animation,
                  child: child,
                );
              },
              transitionDuration: const Duration(milliseconds: 300),
            ),
          );
        },
      ),
    );
  }
}
