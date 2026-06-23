import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/simulation_preset.dart';
import '../services/providers.dart';

class SimulationPresetState {
  final List<SimulationPreset> presets;
  final SimulationPreset? selectedPreset;
  final bool isLoading;
  final bool isSaving;
  final String? error;
  final String? successMessage;

  const SimulationPresetState({
    this.presets = const [],
    this.selectedPreset,
    this.isLoading = false,
    this.isSaving = false,
    this.error,
    this.successMessage,
  });

  SimulationPresetState copyWith({
    List<SimulationPreset>? presets,
    SimulationPreset? selectedPreset,
    bool? isLoading,
    bool? isSaving,
    String? error,
    String? successMessage,
    bool clearMessages = false,
  }) {
    return SimulationPresetState(
      presets: presets ?? this.presets,
      selectedPreset: selectedPreset ?? this.selectedPreset,
      isLoading: isLoading ?? this.isLoading,
      isSaving: isSaving ?? this.isSaving,
      error: clearMessages ? null : error,
      successMessage: clearMessages ? null : successMessage,
    );
  }
}

class SimulationPresetNotifier extends StateNotifier<SimulationPresetState> {
  SimulationPresetNotifier(this.ref) : super(const SimulationPresetState());

  final Ref ref;

  Future<void> loadPresets() async {
    state = state.copyWith(isLoading: true, clearMessages: true);
    try {
      final api = ref.read(apiServiceProvider);
      final presets = await api.getSimulationPresets();
      SimulationPreset? selected;
      for (final preset in presets) {
        if (preset.isDefault) {
          selected = preset;
          break;
        }
      }
      selected ??= presets.isNotEmpty ? presets.first : null;
      state = state.copyWith(
        presets: presets,
        selectedPreset: selected,
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void selectPreset(String id) {
    SimulationPreset? selected;
    for (final preset in state.presets) {
      if (preset.id == id) {
        selected = preset;
        break;
      }
    }
    if (selected == null) return;
    state = state.copyWith(selectedPreset: selected, clearMessages: true);
  }

  void updateDraft(SimulationPreset preset) {
    state = state.copyWith(selectedPreset: preset, clearMessages: true);
  }

  Future<void> saveSelected() async {
    final selected = state.selectedPreset;
    if (selected == null) return;
    state = state.copyWith(isSaving: true, clearMessages: true);
    try {
      final api = ref.read(apiServiceProvider);
      final updated = await api.updateSimulationPreset(selected);
      final presets = state.presets
          .map((preset) => preset.id == updated.id ? updated : preset)
          .toList();
      state = state.copyWith(
        presets: presets,
        selectedPreset: updated,
        isSaving: false,
        successMessage: '保存成功',
      );
    } catch (e) {
      state = state.copyWith(isSaving: false, error: e.toString());
    }
  }

  Future<void> setDefaultSelected() async {
    final selected = state.selectedPreset;
    if (selected == null) return;
    state = state.copyWith(isSaving: true, clearMessages: true);
    try {
      final api = ref.read(apiServiceProvider);
      final updated = await api.setDefaultSimulationPreset(selected.id);
      final presets = state.presets
          .map((preset) => preset.id == updated.id
              ? updated
              : preset.copyWith(isDefault: false))
          .toList();
      state = state.copyWith(
        presets: presets,
        selectedPreset: updated,
        isSaving: false,
        successMessage: '已设为默认',
      );
    } catch (e) {
      state = state.copyWith(isSaving: false, error: e.toString());
    }
  }

  Future<void> duplicateSelected(String name) async {
    final selected = state.selectedPreset;
    if (selected == null) return;
    state = state.copyWith(isSaving: true, clearMessages: true);
    try {
      final api = ref.read(apiServiceProvider);
      final duplicate = await api.duplicateSimulationPreset(selected.id, name);
      state = state.copyWith(
        presets: [...state.presets, duplicate],
        selectedPreset: duplicate,
        isSaving: false,
        successMessage: '复制成功',
      );
    } catch (e) {
      state = state.copyWith(isSaving: false, error: e.toString());
    }
  }

  Future<void> resetSelected() async {
    final selected = state.selectedPreset;
    if (selected == null) return;
    state = state.copyWith(isSaving: true, clearMessages: true);
    try {
      final api = ref.read(apiServiceProvider);
      final reset = await api.resetSimulationPreset(selected.id);
      final presets = state.presets
          .map((preset) => preset.id == reset.id ? reset : preset)
          .toList();
      state = state.copyWith(
        presets: presets,
        selectedPreset: reset,
        isSaving: false,
        successMessage: '已重置',
      );
    } catch (e) {
      state = state.copyWith(isSaving: false, error: e.toString());
    }
  }
}

final simulationPresetProvider =
    StateNotifierProvider<SimulationPresetNotifier, SimulationPresetState>((ref) {
  return SimulationPresetNotifier(ref);
});
