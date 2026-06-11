import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/team.dart';
import '../../providers/teams_provider.dart';
import '../../widgets/common_widgets.dart';
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

    return Column(
      children: [
        // Search and filter bar
        Card(
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
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
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
                        decoration: const InputDecoration(
                          labelText: '洲际',
                          contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          border: OutlineInputBorder(),
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
                        decoration: const InputDecoration(
                          labelText: '排序',
                          contentPadding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          border: OutlineInputBorder(),
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

        // Team list
        Expanded(
          child: teamsAsync.when(
            loading: () => const LoadingWidget(message: '加载球队数据...'),
            error: (err, _) => ErrorWidgetView(
              message: '加载失败: ${err.toString()}',
              onRetry: () => ref.invalidate(teamsListProvider(filter)),
            ),
            data: (teams) {
              final filtered = _searchController.text.isNotEmpty
                  ? teams.where((t) => t.name.toLowerCase().contains(_searchController.text.toLowerCase())).toList()
                  : teams;

              if (filtered.isEmpty) {
                return Center(
                  child: Text('未找到球队', style: TextStyle(color: Colors.grey.shade500)),
                );
              }

              return RefreshIndicator(
                onRefresh: () async => ref.invalidate(teamsListProvider(filter)),
                child: ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  itemCount: filtered.length,
                  itemBuilder: (context, index) {
                    final team = filtered[index];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        leading: CircleAvatar(
                          backgroundColor: Colors.grey.shade200,
                          child: Text(
                            team.code,
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              color: Theme.of(context).colorScheme.primary,
                              fontSize: 12,
                            ),
                          ),
                        ),
                        title: Text(team.name, style: const TextStyle(fontWeight: FontWeight.w500)),
                        subtitle: Text(
                          '${TeamDetail.confederationNames[team.confederation] ?? team.confederation} · ${team.groupName}组',
                          style: const TextStyle(fontSize: 12),
                        ),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text('Elo ${team.eloRating.toStringAsFixed(0)}',
                                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                            Text('FIFA #${team.fifaRank}', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                          ],
                        ),
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (_) => TeamDetailPage(teamCode: team.code, teamName: team.name),
                            ),
                          );
                        },
                      ),
                    );
                  },
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
