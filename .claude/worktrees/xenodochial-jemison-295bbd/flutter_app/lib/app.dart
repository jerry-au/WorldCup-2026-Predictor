import 'package:flutter/material.dart';
import 'pages/home_page.dart';

class WorldCupApp extends StatelessWidget {
  const WorldCupApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '世界杯预测',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1B5E20),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        appBarTheme: const AppBarTheme(
          centerTitle: true,
        ),
        cardTheme: CardTheme(
          elevation: 2,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      home: const HomePage(),
    );
  }
}
