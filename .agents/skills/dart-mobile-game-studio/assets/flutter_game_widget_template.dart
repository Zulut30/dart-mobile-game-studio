// flutter_game_widget_template.dart
// dart-mobile-game-studio — Flutter-widgets-only game starter (Mode 1).
//
// A thin Flutter shell driving a PURE, testable Dart model through a
// ValueNotifier controller. No `package:flame` dependency, no game loop:
// the board is static/turn-based, so it repaints on state change only.
//
// Genre shown: a tap-to-match grid (a memory/coloring-style board). Swap the
// model for your own — the layering is what matters, not this rule set.
//
// Layering (see references/flutter-game-architecture.md):
//   * `TileGameModel` / `GameStatus` — PURE Dart in
//     tile_game_model_template.dart, with no `package:flutter` import.
//     Owns the rules and the menu -> playing -> paused -> won/lost state machine.
//     Unit-test it with `dart test` on the VM (no device, no widget pump).
//   * `GameController extends ValueNotifier<GameStatus>` — a thin adapter
//     that wraps the pure model and notifies the view. It holds NO rules.
//   * Widgets (`GameScreen`, `_Playfield`, `_HudPainter`, ...) — read the
//     model, paint it, forward taps back as intents. No rules here.
//
// Replace `TileGameModel` with your real model and keep this structure.
// In a real project these layers live in separate files:
//   lib/models/ (pure)  ->  lib/game/ (adapter)  ->  lib/widgets/ (render).
// A seeded `Random` is required so the shuffle is reproducible in tests. The
// renderer chooses/persists the seed; the core never creates randomness itself.

import 'dart:math' as math;

import 'package:flutter/material.dart';

// Adjust this relative import after copying the two templates into your app.
import 'tile_game_model_template.dart';

void main() => runApp(const TileGameApp());

// =============================================================================
// CONTROLLER — thin adapter. Wraps the pure model; holds NO rules.
// =============================================================================

/// Bridges the pure [TileGameModel] to the widget tree. Extends
/// [ValueNotifier] so a [ValueListenableBuilder] rebuilds only the subtree
/// that reads it. Every mutator delegates to the model, then notifies.
class GameController extends ValueNotifier<GameStatus> {
  GameController({
    required List<int> palette,
    required math.Random rng,
    int tileCount = 12,
  })  : _model =
            TileGameModel(palette: palette, tileCount: tileCount, rng: rng),
        super(GameStatus.menu);

  final TileGameModel _model;

  // Read-only passthroughs for the view.
  GameStatus get status => _model.status;
  List<Tile> get tiles => _model.tiles;
  int get score => _model.score;
  double get progress => _model.progress;
  int get matchedCount => _model.matchedCount;
  int get tileCount => _model.tileCount;
  String get progressLabel => '$matchedCount of $tileCount cleared';

  void start() {
    _model.start();
    value = _model.status; // notifies listeners
  }

  void pause() {
    _model.pause();
    value = _model.status;
  }

  void resume() {
    _model.resume();
    value = _model.status;
  }

  void lose() {
    _model.lose();
    value = _model.status;
  }

  void quitToMenu() {
    _model.quitToMenu();
    value = _model.status;
  }

  void tapTile(int id) {
    final previous = value;
    if (!_model.tapTile(id)) return;
    if (_model.status != previous) {
      // Status changed (e.g. last tile -> won): the value setter notifies.
      value = _model.status;
    } else {
      // Still playing, but the tile list moved — `value` is unchanged, so the
      // setter would not notify. Repaint the board explicitly.
      notifyListeners();
    }
  }
}

// =============================================================================
// RENDER LAYER — Flutter widgets only. Reads the model; forwards intents.
// =============================================================================

class TileGameApp extends StatelessWidget {
  const TileGameApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Tile Game',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: const Color(0xFF4F86C6),
        useMaterial3: true,
      ),
      home: const GameScreen(),
    );
  }
}

class GameScreen extends StatefulWidget {
  const GameScreen({super.key});

  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> with WidgetsBindingObserver {
  // Placeholder vector palette only — no copyrighted assets. ARGB ints.
  static const List<int> _palette = <int>[
    0xFFEF5350, // red
    0xFFFFA726, // orange
    0xFFFFEE58, // yellow
    0xFF66BB6A, // green
    0xFF42A5F5, // blue
    0xFFAB47BC, // purple
  ];

  // Replace 1 with a persisted level/session seed for fresh but replayable deals.
  late final GameController _controller = GameController(
    palette: _palette,
    tileCount: 12,
    rng: math.Random(1),
  );

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Auto-pause when the app leaves the foreground (kids-safe, no data loss).
    if (state != AppLifecycleState.resumed) _controller.pause();
  }

  @override
  Widget build(BuildContext context) {
    // Reduce Motion: honour the OS accessibility setting. `disableAnimationsOf`
    // rebuilds only when this flag changes, not on every MediaQuery change.
    final reduceMotion = MediaQuery.disableAnimationsOf(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Tile Game')),
      body: SafeArea(
        child: ValueListenableBuilder<GameStatus>(
          valueListenable: _controller,
          builder: (context, status, _) {
            final body = switch (status) {
              GameStatus.menu => _MenuView(onPlay: _controller.start),
              GameStatus.playing => _PlayingView(
                  controller: _controller,
                  reduceMotion: reduceMotion,
                  onPause: _controller.pause,
                ),
              GameStatus.paused => _PlayingView(
                  controller: _controller,
                  reduceMotion: reduceMotion,
                  onPause: _controller.pause,
                  pausedOverlay: _PausedOverlay(onResume: _controller.resume),
                ),
              GameStatus.won => _ResultView(
                  title: 'You did it!',
                  progressLabel: _controller.progressLabel,
                  score: _controller.score,
                  onPlayAgain: _controller.start,
                ),
              GameStatus.lost => _ResultView(
                  title: 'Try again',
                  progressLabel: _controller.progressLabel,
                  score: _controller.score,
                  onPlayAgain: _controller.start,
                ),
            };

            // Cross-fade between top-level states; instant when Reduce Motion.
            return AnimatedSwitcher(
              duration: reduceMotion
                  ? Duration.zero
                  : const Duration(milliseconds: 250),
              child: KeyedSubtree(
                key: ValueKey<GameStatus>(status),
                child: body,
              ),
            );
          },
        ),
      ),
    );
  }
}

// -----------------------------------------------------------------------------
// Menu
// -----------------------------------------------------------------------------

class _MenuView extends StatelessWidget {
  const _MenuView({required this.onPlay});

  final VoidCallback onPlay;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('Tile Game', style: Theme.of(context).textTheme.headlineMedium),
          const SizedBox(height: 24),
          Semantics(
            button: true,
            label: 'Play',
            child: FilledButton(
              onPressed: onPlay,
              child: const Padding(
                padding: EdgeInsets.symmetric(horizontal: 32, vertical: 8),
                child: Text('Play'),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// -----------------------------------------------------------------------------
// Playing (HUD + grid of tappable tiles), with an optional paused overlay.
// -----------------------------------------------------------------------------

class _PlayingView extends StatelessWidget {
  const _PlayingView({
    required this.controller,
    required this.reduceMotion,
    required this.onPause,
    this.pausedOverlay,
  });

  final GameController controller;
  final bool reduceMotion;
  final VoidCallback onPause;
  final Widget? pausedOverlay;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Column(
          children: [
            _Hud(
              score: controller.score,
              progress: controller.progress,
              progressLabel: controller.progressLabel,
              onPause: onPause,
            ),
            Expanded(
              child: _Playfield(
                controller: controller,
                reduceMotion: reduceMotion,
              ),
            ),
          ],
        ),
        if (pausedOverlay != null) Positioned.fill(child: pausedOverlay!),
      ],
    );
  }
}

/// HUD: a small [CustomPainter] progress bar plus the score and a pause button.
/// Demonstrates the Canvas/CustomPainter technique alongside the tile grid.
class _Hud extends StatelessWidget {
  const _Hud({
    required this.score,
    required this.progress,
    required this.progressLabel,
    required this.onPause,
  });

  final int score;
  final double progress; // 0..1
  final String progressLabel;
  final VoidCallback onPause;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Expanded(
            child: Semantics(
              // Combine children so VoiceOver/TalkBack reads one phrase.
              container: true,
              label: 'Score $score, $progressLabel',
              child: ExcludeSemantics(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Score $score', style: theme.textTheme.titleMedium),
                    const SizedBox(height: 6),
                    SizedBox(
                      height: 8,
                      child: CustomPaint(
                        size: const Size(double.infinity, 8),
                        painter: _HudPainter(
                          progress: progress,
                          trackColor: theme.colorScheme.surfaceContainerHighest,
                          fillColor: theme.colorScheme.primary,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 12),
          Semantics(
            button: true,
            label: 'Pause',
            child: IconButton.filledTonal(
              onPressed: onPause,
              icon: const Icon(Icons.pause),
              tooltip: 'Pause',
            ),
          ),
        ],
      ),
    );
  }
}

/// Draws a rounded progress track + fill. Pure Canvas; repaints only when the
/// inputs change.
class _HudPainter extends CustomPainter {
  const _HudPainter({
    required this.progress,
    required this.trackColor,
    required this.fillColor,
  });

  final double progress; // 0..1
  final Color trackColor;
  final Color fillColor;

  @override
  void paint(Canvas canvas, Size size) {
    final radius = Radius.circular(size.height / 2);
    final track = RRect.fromRectAndRadius(Offset.zero & size, radius);
    canvas.drawRRect(track, Paint()..color = trackColor);

    if (progress <= 0) return;
    final fillWidth = size.width * progress.clamp(0.0, 1.0);
    final fill = RRect.fromRectAndRadius(
      Offset.zero & Size(fillWidth, size.height),
      radius,
    );
    canvas.drawRRect(fill, Paint()..color = fillColor);
  }

  @override
  bool shouldRepaint(_HudPainter old) =>
      old.progress != progress ||
      old.trackColor != trackColor ||
      old.fillColor != fillColor;
}

/// The board: a grid of tappable tiles. Each tile is a [Semantics] button so
/// screen readers announce position and state; never conveys state by colour
/// alone (a check mark is drawn on cleared tiles).
class _Playfield extends StatelessWidget {
  const _Playfield({required this.controller, required this.reduceMotion});

  final GameController controller;
  final bool reduceMotion;

  @override
  Widget build(BuildContext context) {
    final tiles = controller.tiles;
    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 3,
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
      ),
      itemCount: tiles.length,
      itemBuilder: (context, index) {
        final tile = tiles[index];
        return _TileButton(
          tile: tile,
          index: index,
          total: tiles.length,
          reduceMotion: reduceMotion,
          onTap: () => controller.tapTile(tile.id),
        );
      },
    );
  }
}

class _TileButton extends StatelessWidget {
  const _TileButton({
    required this.tile,
    required this.index,
    required this.total,
    required this.reduceMotion,
    required this.onTap,
  });

  final Tile tile;
  final int index;
  final int total;
  final bool reduceMotion;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      enabled: !tile.matched,
      selected: tile.matched,
      label: 'Tile ${index + 1} of $total',
      value: tile.matched ? 'cleared' : 'open',
      onTap: tile.matched ? null : onTap,
      // The GestureDetector below is the real hit target; exclude its implicit
      // semantics so the screen reader reads only this node.
      excludeSemantics: true,
      child: GestureDetector(
        onTap: tile.matched ? null : onTap,
        child: AnimatedContainer(
          duration:
              reduceMotion ? Duration.zero : const Duration(milliseconds: 180),
          decoration: BoxDecoration(
            color: Color(tile.colorValue).withAlpha(tile.matched ? 89 : 255),
            borderRadius: BorderRadius.circular(16),
          ),
          child: tile.matched
              ? const Center(
                  child: Icon(Icons.check, color: Colors.white, size: 32),
                )
              : null,
        ),
      ),
    );
  }
}

class _PausedOverlay extends StatelessWidget {
  const _PausedOverlay({required this.onResume});

  final VoidCallback onResume;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.black54,
      child: Center(
        child: Semantics(
          button: true,
          label: 'Resume',
          child: FilledButton(
            onPressed: onResume,
            child: const Padding(
              padding: EdgeInsets.symmetric(horizontal: 32, vertical: 8),
              child: Text('Resume'),
            ),
          ),
        ),
      ),
    );
  }
}

// -----------------------------------------------------------------------------
// Result
// -----------------------------------------------------------------------------

class _ResultView extends StatelessWidget {
  const _ResultView({
    required this.title,
    required this.progressLabel,
    required this.score,
    required this.onPlayAgain,
  });

  final String title;
  final String progressLabel;
  final int score;
  final VoidCallback onPlayAgain;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Semantics(
            container: true,
            label: '$title. Score $score. $progressLabel.',
            child: ExcludeSemantics(
              child: Column(
                children: [
                  Text(title, style: theme.textTheme.headlineMedium),
                  const SizedBox(height: 8),
                  Text('Score $score', style: theme.textTheme.titleMedium),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          Semantics(
            button: true,
            label: 'Play again',
            child: FilledButton(
              onPressed: onPlayAgain,
              child: const Padding(
                padding: EdgeInsets.symmetric(horizontal: 32, vertical: 8),
                child: Text('Play again'),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
