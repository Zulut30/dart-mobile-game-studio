import 'package:flame/game.dart';
import 'package:flutter/material.dart';

import '../game/runner_game.dart';
import '../models/game_phase.dart';

/// Root of the Flame example. The Flame `GameWidget` renders the play surface;
/// thin Flutter widgets sit on top for the HUD and the game-over panel (overlays
/// driven by the phase, the model staying the source of truth).
class RunnerApp extends StatelessWidget {
  const RunnerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Endless Runner',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF2E3CC0)),
        useMaterial3: true,
      ),
      home: const GamePage(),
    );
  }
}

class GamePage extends StatefulWidget {
  const GamePage({super.key});

  @override
  State<GamePage> createState() => _GamePageState();
}

class _GamePageState extends State<GamePage> {
  late final RunnerGame _game = RunnerGame(
    onPhaseChange: (_) {
      if (mounted) setState(() {});
    },
  );

  void _restart() {
    _game.restart();
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final over = _game.state.phase == GamePhase.gameOver;
    return Scaffold(
      body: Stack(
        children: [
          Positioned.fill(
            child: GestureDetector(
              behavior: HitTestBehavior.opaque,
              onTap: _game.onJumpTap,
              child: GameWidget(game: _game),
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Align(
                alignment: Alignment.topLeft,
                child: Semantics(
                  liveRegion: true,
                  child: ValueListenableBuilder<int>(
                    valueListenable: _game.score,
                    builder: (context, value, _) => Text(
                      'Score $value',
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
          if (over) _GameOverPanel(score: _game.state.score, onRestart: _restart),
        ],
      ),
    );
  }
}

class _GameOverPanel extends StatelessWidget {
  const _GameOverPanel({required this.score, required this.onRestart});

  final int score;
  final VoidCallback onRestart;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ColoredBox(
      color: Colors.black54,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Game Over', style: theme.textTheme.headlineMedium?.copyWith(color: Colors.white)),
            const SizedBox(height: 8),
            Text('Score $score', style: const TextStyle(color: Colors.white, fontSize: 20)),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: onRestart,
              icon: const Icon(Icons.replay_rounded),
              label: const Text('Play again'),
            ),
          ],
        ),
      ),
    );
  }
}
