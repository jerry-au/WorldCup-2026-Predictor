import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/teams_provider.dart';

class TeamSelector extends ConsumerWidget {
  final String? selectedCode;
  final ValueChanged<String?> onSelected;

  const TeamSelector({
    super.key,
    this.selectedCode,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final teamsAsync = ref.watch(teamsListProvider(const TeamsFilter()));

    return teamsAsync.when(
      loading: () => const SizedBox(
        width: 24,
        height: 24,
        child: CircularProgressIndicator(strokeWidth: 2),
      ),
      error: (err, stack) => Text('加载失败', style: TextStyle(color: Colors.red.shade700)),
      data: (teams) => DropdownButtonFormField<String>(
        value: selectedCode,
        decoration: InputDecoration(
          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          labelText: '选择球队',
        ),
        items: teams.map((team) {
          return DropdownMenuItem(
            value: team.code,
            child: Text(
              '${team.flagUrl ?? ""} ${team.name} (${team.code})',
              style: const TextStyle(fontSize: 14),
            ),
          );
        }).toList(),
        onChanged: onSelected,
      ),
    );
  }
}
