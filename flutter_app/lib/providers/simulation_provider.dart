import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/simulation.dart';
import '../services/api_service.dart';
import '../services/providers.dart';

/// Simulation page state.
class SimulationState {
  final bool isRunning;
  final double progress;
  final SimulationResult? result;
  final String? error;

  const SimulationState({
    this.isRunning = false,
    this.progress = 0.0,
    this.result,
    this.error,
  });

  SimulationState copyWith({
    bool? isRunning,
    double? progress,
    SimulationResult? result,
    String? error,
  }) {
    return SimulationState(
      isRunning: isRunning ?? this.isRunning,
      progress: progress ?? this.progress,
      result: result ?? this.result,
      error: error,
    );
  }
}

class SimulationNotifier extends StateNotifier<SimulationState> {
  SimulationNotifier(this._api) : super(const SimulationState());

  final ApiService _api;
  Timer? _pollTimer;
  int _consecutiveFailures = 0;

  Future<void> startSimulation() async {
    _consecutiveFailures = 0;
    state = state.copyWith(isRunning: true, progress: 0.0, result: null, error: null);
    try {
      final taskData = await _api.startTournamentSimulation();
      final taskId = taskData['task_id'] as String;
      _pollTask(taskId);
    } catch (e) {
      state = state.copyWith(isRunning: false, error: e.toString());
    }
  }

  void _pollTask(String taskId) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(milliseconds: 500), (_) async {
      try {
        final data = await _api.getTaskProgress(taskId);
        _consecutiveFailures = 0;
        final status = data['status'] as String;
        final progress = (data['progress'] as num?)?.toDouble() ?? 0;

        if (status == 'completed') {
          _pollTimer?.cancel();
          final result = SimulationResult.fromJson(data['result'] as Map<String, dynamic>);
          state = state.copyWith(isRunning: false, progress: 1.0, result: result);
        } else if (status == 'failed') {
          _pollTimer?.cancel();
          state = state.copyWith(isRunning: false, error: data['error'] as String?);
        } else {
          state = state.copyWith(isRunning: true, progress: progress);
        }
      } catch (_) {
        _consecutiveFailures++;
        if (_consecutiveFailures >= 10) {
          _pollTimer?.cancel();
          state = state.copyWith(
            isRunning: false,
            error: '模拟超时，请检查网络后重试',
          );
        }
      }
    });
  }

  void reset() {
    _pollTimer?.cancel();
    state = const SimulationState();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}

final simulationProvider =
    StateNotifierProvider.autoDispose<SimulationNotifier, SimulationState>((ref) {
  return SimulationNotifier(ref.read(apiServiceProvider));
});
