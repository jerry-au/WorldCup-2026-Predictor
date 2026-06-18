import 'dart:convert';
import 'package:flutter/foundation.dart';

class CacheService {
  static final Map<String, _CacheEntry> _memoryCache = {};
  static const int _defaultMaxAgeMinutes = 30;

  static T? get<T>(String key) {
    final entry = _memoryCache[key];
    if (entry == null) return null;

    if (DateTime.now().difference(entry.timestamp) > entry.maxAge) {
      _memoryCache.remove(key);
      return null;
    }

    return entry.value as T?;
  }

  static void set<T>(String key, T value, {Duration? maxAge}) {
    _memoryCache[key] = _CacheEntry(
      value: value,
      timestamp: DateTime.now(),
      maxAge: maxAge ?? const Duration(minutes: _defaultMaxAgeMinutes),
    );
  }

  static void invalidate(String key) {
    _memoryCache.remove(key);
  }

  static void clear() {
    _memoryCache.clear();
  }

  static void invalidatePrefix(String prefix) {
    _memoryCache.removeWhere((key, _) => key.startsWith(prefix));
  }

  static int get size => _memoryCache.length;

  static String generateKey(String... parts) {
    return parts.join(':');
  }
}

class _CacheEntry {
  final dynamic value;
  final DateTime timestamp;
  final Duration maxAge;

  _CacheEntry({
    required this.value,
    required this.timestamp,
    required this.maxAge,
  });
}

class JsonCache {
  static String? getString(String key) {
    final value = CacheService.get<String>(key);
    return value;
  }

  static Map<String, dynamic>? getJson(String key) {
    final str = getString(key);
    if (str == null) return null;
    try {
      return jsonDecode(str) as Map<String, dynamic>;
    } catch (e) {
      debugPrint('JsonCache decode error: $e');
      return null;
    }
  }

  static List<Map<String, dynamic>>? getJsonList(String key) {
    final str = getString(key);
    if (str == null) return null;
    try {
      final list = jsonDecode(str) as List<dynamic>;
      return list.cast<Map<String, dynamic>>();
    } catch (e) {
      debugPrint('JsonCache decode error: $e');
      return null;
    }
  }

  static void setJson(String key, Map<String, dynamic> value, {Duration? maxAge}) {
    CacheService.set(key, jsonEncode(value), maxAge: maxAge);
  }

  static void setJsonList(String key, List<Map<String, dynamic>> value, {Duration? maxAge}) {
    CacheService.set(key, jsonEncode(value), maxAge: maxAge);
  }
}

class RequestCache {
  static const String teamsKey = 'teams';
  static const String predictionsKey = 'predictions';
  static const String oddsKey = 'odds';
  static const Duration shortCache = Duration(minutes: 5);
  static const Duration mediumCache = Duration(minutes: 30);
  static const Duration longCache = Duration(hours: 2);

  static String teamDetail(String code) => CacheService.generateKey('team', code);
  static String prediction(String a, String b, String type) =>
      CacheService.generateKey('pred', a, b, type);
  static String odds(String a, String b) => CacheService.generateKey('odds', a, b);
  static String valueBets(double minEv) => CacheService.generateKey('valuebets', minEv.toString());
  static String discrepancies(double minDelta) =>
      CacheService.generateKey('discrepancies', minDelta.toString());
}
