import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'dart:convert';
import '../config/api_config.dart';

class ApiService {
  late final Dio _dio;

  ApiService() {
    _dio = Dio(BaseOptions(
      baseUrl: ApiConfig.apiBase,
      connectTimeout: ApiConfig.normalTimeout,
      receiveTimeout: ApiConfig.normalTimeout,
      sendTimeout: ApiConfig.normalTimeout,
      headers: {'Content-Type': 'application/json'},
      receiveDataWhenStatusError: true,
      validateStatus: (status) => status != null && status < 500,
    ));

    // 添加响应转换拦截器：兼容 Web 平台 resp.data 为 String 的情况
    _dio.interceptors.add(InterceptorsWrapper(
      onResponse: (response, handler) {
        final data = response.data;
        if (data != null && data is String && data.isNotEmpty) {
          try {
            response.data = jsonDecode(data);
          } catch (e) {
            debugPrint('[API] jsonDecode failed: $e');
          }
        }
        if (response.data == null) {
          debugPrint(
              '[API] Warning: null response for ${response.requestOptions.uri}');
        }
        handler.next(response);
      },
    ));

    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      logPrint: (obj) => debugPrint('[API] $obj'),
    ));
  }

  // ─── Teams ───────────────────────────────────────────────

  Future<dynamic> getTeams(
      {String? confederation,
      String? group,
      String sortBy = 'elo_rating'}) async {
    final params = <String, dynamic>{'sort_by': sortBy};
    if (confederation != null) params['confederation'] = confederation;
    if (group != null) params['group'] = group;
    final resp =
        await _dio.get(ApiConfig.teamsEndpoint, queryParameters: params);
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
    debugPrint('[API] predictMatch: $teamACode vs $teamBCode ($matchType)');
    try {
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
      debugPrint(
          '[API] predictMatch response status: ${resp.statusCode}, dataType: ${resp.data.runtimeType}');
      return resp.data;
    } catch (e, st) {
      debugPrint('[API] predictMatch error: $e\n$st');
      rethrow;
    }
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

  Future<dynamic> getValueBets(
      {double minEv = 0.05, int page = 1, int pageSize = 20}) async {
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

  Future<dynamic> getDataRefreshStatus() async {
    final resp = await _dio.get(ApiConfig.dataRefreshStatusEndpoint);
    return resp.data;
  }

  Future<dynamic> getDataRefreshLogs({int limit = 20}) async {
    final resp = await _dio.get(
      ApiConfig.dataRefreshLogsEndpoint,
      queryParameters: {'limit': limit},
    );
    return resp.data;
  }
}
