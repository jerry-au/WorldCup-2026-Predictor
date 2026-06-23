import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

class ApiConfig {
  /// 后端 API 地址
  /// - 生产环境: 远程服务器
  /// - 本地开发: 127.0.0.1
  static const String _serverUrl = 'http://43.135.94.112:9000';
  static const String _localUrl = 'http://127.0.0.1:9000';

  static String get baseUrl {
    // 支持通过 --dart-define=API_BASE_URL=... 覆盖，用于测试前端
    const override = String.fromEnvironment('API_BASE_URL');
    if (override.isNotEmpty) return override;

    // 默认使用远程服务器（生产设置）
    return _serverUrl;
  }

  static const String apiPrefix = '/api/v1';
  static String get apiBase => '$baseUrl$apiPrefix';

  // Timeouts
  static const Duration matchPredictTimeout = Duration(seconds: 10);
  static const Duration simulationTimeout = Duration(seconds: 60);
  static const Duration normalTimeout = Duration(seconds: 15);

  // Endpoints
  static const String teamsEndpoint = '/teams';
  static const String teamDetailEndpoint = '/teams';
  static const String predictMatchEndpoint = '/predict/match';
  static const String predictTournamentEndpoint = '/predict/tournament';
  static const String predictTaskEndpoint = '/predict/task';
  static const String simulationPresetsEndpoint = '/simulation/presets';
  static const String simulationDefaultPresetEndpoint = '/simulation/presets/default';
  static const String valueBetsEndpoint = '/recommendations/value-bets';
  static const String discrepanciesEndpoint = '/recommendations/discrepancies';
  static const String oddsLatestEndpoint = '/odds/latest';
  static const String oddsProvidersEndpoint = '/odds/providers';
  static const String dataRefreshEndpoint = '/data/refresh';
  static const String dataRefreshStatusEndpoint = '/data/refresh/status';
  static const String dataRefreshLogsEndpoint = '/data/refresh/logs';
  static const String dataRefreshProgressEndpoint = '/data/refresh/progress';
  // ─── Admin Data Management ──────────────────────────
  static const String fetchStatusEndpoint = '/data/fetch/status';
  static const String fetchPlayersEndpoint = '/data/refresh/trigger';
  static const String fetchResultsEndpoint = '/data/fetch/results';
  static const String fetchStandingsEndpoint = '/data/fetch/standings';
  static const String fetchOddsEndpoint = '/data/refresh/trigger';
  static const String fetchSeasonSummariesEndpoint = '/data/fetch/dongqiudi/player-season-summaries';
  static const String fetchPlayerAbilitiesEndpoint = '/data/fetch/dongqiudi/player-abilities';
  static const String todayMatchesEndpoint = '/matches/today';
  static const String allMatchesEndpoint = '/matches/all';
  static String oddsHistoryEndpoint(String matchId) => '/matches/$matchId/odds-history';
}
