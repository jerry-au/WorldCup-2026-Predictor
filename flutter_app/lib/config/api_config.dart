import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;

class ApiConfig {
  /// Platform-aware base URL:
  /// - Web / iOS Simulator → localhost:8001
  /// - Android Emulator    → 10.0.2.2:8001
  static String get baseUrl {
    if (kIsWeb) return 'http://127.0.0.1:9000';
    if (Platform.isAndroid) return 'http://10.0.2.2:9000';
    return 'http://127.0.0.1:9000';
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
  static const String valueBetsEndpoint = '/recommendations/value-bets';
  static const String discrepanciesEndpoint = '/recommendations/discrepancies';
  static const String oddsLatestEndpoint = '/odds/latest';
  static const String oddsProvidersEndpoint = '/odds/providers';
  static const String dataRefreshEndpoint = '/data/refresh';
  static const String dataRefreshStatusEndpoint = '/data/refresh/status';
  static const String dataRefreshLogsEndpoint = '/data/refresh/logs';
  // ─── Admin Data Management ──────────────────────────
  static const String fetchStatusEndpoint = '/data/fetch/status';
  static const String fetchPlayersEndpoint = '/data/refresh/trigger';
  static const String fetchResultsEndpoint = '/data/fetch/results';
  static const String fetchStandingsEndpoint = '/data/fetch/standings';
  static const String fetchOddsEndpoint = '/data/refresh/trigger';
  static const String fetchSeasonSummariesEndpoint = '/data/fetch/dongqiudi/player-season-summaries';
  static const String fetchPlayerAbilitiesEndpoint = '/data/fetch/dongqiudi/player-abilities';
}
