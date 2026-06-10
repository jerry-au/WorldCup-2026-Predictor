import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../config/api_config.dart';

class ApiService {
  late final Dio _dio;

  ApiService() {
    _dio = Dio(BaseOptions(
      baseUrl: ApiConfig.apiBase,
      connectTimeout: ApiConfig.normalTimeout,
      receiveTimeout: ApiConfig.normalTimeout,
      headers: {'Content-Type': 'application/json'},
    ));

    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      logPrint: (obj) => debugPrint('[API] $obj'),
    ));
  }

  // ─── Teams ───────────────────────────────────────────────

  Future<dynamic> getTeams({String? confederation, String? group, String sortBy = 'elo_rating'}) async {
    final params = <String, dynamic>{'sort_by': sortBy};
    if (confederation != null) params['confederation'] = confederation;
    if (group != null) params['group'] = group;
    final resp = await _dio.get(ApiConfig.teamsEndpoint, queryParameters: params);
    return resp.data;
  }

  Future<dynamic> getTeamDetail(String code) async {
    final resp = await _dio.get('${ApiConfig.teamDetailEndpoint}/$code');
    return resp.data;
  }

  // ─── Prediction ──────────────────────────────────────────

  Future<dynamic> predictMatch({
    required String teamACode,
    required String teamBCode,
    String matchType = 'group',
  }) async {
    final resp = await _dio.post(
      ApiConfig.predictMatchEndpoint,
      data: {
        'team_a_code': teamACode,
        'team_b_code': teamBCode,
        'match_type': matchType,
      },
      options: Options(
        sendTimeout: ApiConfig.matchPredictTimeout,
        receiveTimeout: ApiConfig.matchPredictTimeout,
      ),
    );
    return resp.data;
  }

  Future<dynamic> startTournamentSimulation() async {
    final resp = await _dio.post(
      ApiConfig.predictTournamentEndpoint,
      options: Options(
        sendTimeout: ApiConfig.simulationTimeout,
        receiveTimeout: ApiConfig.simulationTimeout,
      ),
    );
    return resp.data;
  }

  Future<dynamic> getTaskProgress(String taskId) async {
    final resp = await _dio.get('${ApiConfig.predictTaskEndpoint}/$taskId');
    return resp.data;
  }

  // ─── Recommendations ─────────────────────────────────────

  Future<dynamic> getValueBets({double minEv = 0.05, int page = 1, int pageSize = 20}) async {
    final resp = await _dio.get(
      ApiConfig.valueBetsEndpoint,
      queryParameters: {'min_ev': minEv, 'page': page, 'page_size': pageSize},
    );
    return resp.data;
  }

  Future<dynamic> getDiscrepancies({double minDelta = 0.12}) async {
    final resp = await _dio.get(
      ApiConfig.discrepanciesEndpoint,
      queryParameters: {'min_delta': minDelta},
    );
    return resp.data;
  }

  // ─── Odds ────────────────────────────────────────────────

  Future<dynamic> getLatestOdds() async {
    final resp = await _dio.get(ApiConfig.oddsLatestEndpoint);
    return resp.data;
  }

  Future<dynamic> getOddsProviders() async {
    final resp = await _dio.get(ApiConfig.oddsProvidersEndpoint);
    return resp.data;
  }

  // ─── Data ────────────────────────────────────────────────

  Future<dynamic> refreshData() async {
    final resp = await _dio.post(ApiConfig.dataRefreshEndpoint);
    return resp.data;
  }
}
