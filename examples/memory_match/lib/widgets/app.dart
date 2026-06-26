import 'package:flutter/material.dart';

import 'menu_screen.dart';

/// Root of the reference game. Thin shell: one `MaterialApp`, one theme, the menu
/// as home. All game rules live in the pure-Dart core (`lib/models`, `lib/systems`).
class MemoryMatchApp extends StatelessWidget {
  const MemoryMatchApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Memory Match',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4C6FFF)),
        useMaterial3: true,
      ),
      home: const MenuScreen(),
    );
  }
}
