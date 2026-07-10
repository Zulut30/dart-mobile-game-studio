import 'package:flame/game.dart';
import 'package:flutter/foundation.dart' show ValueListenable;
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

class _GamePageState extends State<GamePage> with WidgetsBindingObserver {
  late final RunnerGame _game = RunnerGame(
    onPhaseChange: (_) {
      if (mounted) setState(() {});
    },
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) _game.pause();
  }

  @override
  Widget build(BuildContext context) {
    final phase = _game.state.phase;
    final canJump = phase == GamePhase.playing;
    return Scaffold(
      body: LayoutBuilder(
        builder: (context, constraints) {
          final horizontalPadding = constraints.maxWidth >= 700 ? 24.0 : 12.0;
          return Stack(
            children: [
              Positioned.fill(
                child: ExcludeSemantics(
                  excluding: !canJump,
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    excludeFromSemantics: true,
                    onTap: canJump ? _game.onJumpTap : null,
                    child: Semantics(
                      label: 'Jump',
                      hint: 'Tap anywhere to jump over obstacles',
                      button: true,
                      enabled: canJump,
                      onTap: canJump ? _game.onJumpTap : null,
                      child: GameWidget(game: _game),
                    ),
                  ),
                ),
              ),
              if (phase == GamePhase.playing)
                SafeArea(
                  child: _RunnerHud(
                    score: _game.score,
                    horizontalPadding: horizontalPadding,
                    onPause: _game.pause,
                  ),
                ),
              if (phase == GamePhase.menu)
                _PhasePanel(
                  title: 'Endless Runner',
                  subtitle: 'Tap to jump and clear every obstacle.',
                  primaryLabel: 'Play',
                  primaryIcon: Icons.play_arrow_rounded,
                  onPrimary: _game.start,
                ),
              if (phase == GamePhase.paused)
                _PhasePanel(
                  title: 'Paused',
                  subtitle: 'Score ${_game.state.score}',
                  primaryLabel: 'Resume',
                  primaryIcon: Icons.play_arrow_rounded,
                  onPrimary: _game.resume,
                  secondaryLabel: 'Menu',
                  secondaryIcon: Icons.home_rounded,
                  onSecondary: _game.quitToMenu,
                ),
              if (phase == GamePhase.gameOver)
                _PhasePanel(
                  title: 'Game Over',
                  subtitle: 'Score ${_game.state.score}',
                  primaryLabel: 'Play again',
                  primaryIcon: Icons.replay_rounded,
                  onPrimary: _game.restart,
                  secondaryLabel: 'Menu',
                  secondaryIcon: Icons.home_rounded,
                  onSecondary: _game.quitToMenu,
                  liveRegion: true,
                ),
            ],
          );
        },
      ),
    );
  }
}

class _RunnerHud extends StatelessWidget {
  const _RunnerHud({
    required this.score,
    required this.horizontalPadding,
    required this.onPause,
  });

  final ValueListenable<int> score;
  final double horizontalPadding;
  final VoidCallback onPause;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(horizontalPadding, 12, horizontalPadding, 0),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Flexible(
                child: Semantics(
                  liveRegion: true,
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      color: Colors.black87,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 8,
                      ),
                      child: ValueListenableBuilder<int>(
                        valueListenable: score,
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
              const Spacer(),
              IconButton.filledTonal(
                onPressed: onPause,
                icon: const Icon(Icons.pause_rounded),
                tooltip: 'Pause',
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PhasePanel extends StatelessWidget {
  const _PhasePanel({
    required this.title,
    required this.subtitle,
    required this.primaryLabel,
    required this.primaryIcon,
    required this.onPrimary,
    this.secondaryLabel,
    this.secondaryIcon,
    this.onSecondary,
    this.liveRegion = false,
  });

  final String title;
  final String subtitle;
  final String primaryLabel;
  final IconData primaryIcon;
  final VoidCallback onPrimary;
  final String? secondaryLabel;
  final IconData? secondaryIcon;
  final VoidCallback? onSecondary;
  final bool liveRegion;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ColoredBox(
      color: Colors.black54,
      child: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 360),
              child: Semantics(
                container: true,
                liveRegion: liveRegion,
                label: '$title. $subtitle',
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    ExcludeSemantics(
                      child: Column(
                        children: [
                          Text(
                            title,
                            textAlign: TextAlign.center,
                            style: theme.textTheme.headlineMedium?.copyWith(
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            subtitle,
                            textAlign: TextAlign.center,
                            style: theme.textTheme.bodyLarge?.copyWith(
                              color: Colors.white,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 24),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: onPrimary,
                        icon: Icon(primaryIcon),
                        label: Text(primaryLabel),
                      ),
                    ),
                    if (onSecondary != null &&
                        secondaryLabel != null &&
                        secondaryIcon != null) ...[
                      const SizedBox(height: 8),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: onSecondary,
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.white,
                            side: const BorderSide(color: Colors.white70),
                          ),
                          icon: Icon(secondaryIcon),
                          label: Text(secondaryLabel!),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
