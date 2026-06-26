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
//   * `_TileGameModel` / `GameStatus` — PURE Dart, no `package:flutter`.
//     Owns the rules and the menu -> playing -> paused -> won state machine.
//     Unit-test it with `dart test` on the VM (no device, no widget pump).
//   * `GameController extends ValueNotifier<GameStatus>` — a thin adapter
//     that wraps the pure model and notifies the view. It holds NO rules.
//   * Widgets (`GameScreen`, `_Playfield`, `_HudPainter`, ...) — read the
//     model, paint it, forward taps back as intents. No rules here.
//
// Replace `_TileGameModel` with your real model and keep this structure.
// In a real project these layers live in separate files:
//   lib/models/ (pure)  ->  lib/game/ (adapter)  ->  lib/widgets/ (render).
// A seeded `Random` is injected so the shuffle is reproducible in tests; the
// skill ships `assets/seeded_random.dart` (a `Random` implementation) for the
// production wrapper. Here we use `dart:math`'s `Random([seed])` directly.

import 'dart:math' as math;

import 'package:flutter/material.dart';

void main() => runApp(const TileGameApp());

// =============================================================================
// PURE MODEL — no `package:flutter` / `package:flame`. Fully VM-testable.
// =============================================================================

/// The whole game's state machine: menu -> playing -> paused -> won -> menu.
enum GameStatus { menu, playing, paused, won }

/// One board tile. Immutable; the model rebuilds the list on each change so the
/// renderer can diff old vs new cheaply.
@immutable
class Tile {
  const Tile({
    required this.id,
    required this.colorValue,
    this.matched = false,
  });

  /// Stable position id (0-based), used as the [Semantics] index too.
  final int id;

  /// Plain ARGB int (e.g. `0xFFEF5350`), NOT a `dart:ui` Color — keeps the
  /// model `flutter`-free. The renderer wraps it in `Color(colorValue)`.
  final int colorValue;

  /// Whether this tile has been tapped/cleared.
  final bool matched;

  Tile copyWith({bool? matched}) => Tile(
    id: id,
    colorValue: colorValue,
    matched: matched ?? this.matched,
  );
}

/// Pure rules + transitions. The single source of truth. No rendering, no
/// plugins, no globals — inject a seeded [math.Random] for a reproducible
/// deal.
class _TileGameModel {
  _TileGameModel({required this.palette, this.tileCount = 12, math.Random? rng})
    : _rng = rng ?? math.Random(),
      assert(palette.isNotEmpty, 'palette must not be empty'),
      assert(tileCount > 0, 'tileCount must be positive');

  /// ARGB ints to draw the tiles from (cycled if smaller than [tileCount]).
  final List<int> palette;
  final int tileCount;
  final math.Random _rng;

  GameStatus _status = GameStatus.menu;
  GameStatus get status => _status;

  List<Tile> _tiles = const <Tile>[];
  List<Tile> get tiles => List<Tile>.unmodifiable(_tiles);

  int _score = 0;
  int get score => _score;

  /// Progress, derived not stored. `progress` (0..1) feeds the visual bar;
  /// `progressLabel` feeds the HUD text and Semantics.
  int get matchedCount => _tiles.where((t) => t.matched).length;
  double get progress => tileCount == 0 ? 0 : matchedCount / tileCount;
  String get progressLabel => '$matchedCount of $tileCount cleared';

  /// Deal a fresh board and begin play. Legal from menu or after a win
  /// (the "play again" path).
  void start() {
    assert(_status == GameStatus.menu || _status == GameStatus.won);
    _tiles = _deal();
    _score = 0;
    _status = GameStatus.playing;
  }

  void pause() {
    if (_status == GameStatus.playing) _status = GameStatus.paused;
  }

  void resume() {
    if (_status == GameStatus.paused) _status = GameStatus.playing;
  }

  /// Return to the menu from any state (e.g. the system backgrounding the app).
  void quitToMenu() => _status = GameStatus.menu;

  /// Forward a tap intent. Ignored unless playing and the tile is still open;
  /// returns true iff the board actually changed (so the view can react with
  /// sound/haptic without re-deriving the rule).
  bool tapTile(int id) {
    if (_status != GameStatus.playing) return false;
    final index = _tiles.indexWhere((t) => t.id == id);
    if (index < 0 || _tiles[index].matched) return false;

    _tiles = List<Tile>.of(_tiles)
      ..[index] = _tiles[index].copyWith(matched: true);
    _score++;
    if (_tiles.every((t) => t.matched)) _status = GameStatus.won;
    return true;
  }

  List<Tile> _deal() {
    final dealt = List<Tile>.generate(
      tileCount,
      (i) => Tile(id: i, colorValue: palette[i % palette.length]),
    );
    _shuffle(dealt); // seeded Fisher–Yates: same seed => same board.
    // Reassign ids to grid order so position == id after the shuffle.
    return List<Tile>.generate(
      tileCount,
      (i) => Tile(id: i, colorValue: dealt[i].colorValue),
    );
  }

  /// Deterministic in-place Fisher–Yates using the injected [math.Random].
  void _shuffle(List<Tile> list) {
    for (var i = list.length - 1; i > 0; i--) {
      final j = _rng.nextInt(i + 1);
      final tmp = list[i];
      list[i] = list[j];
      list[j] = tmp;
    }
  }
}

// =============================================================================
// CONTROLLER — thin adapter. Wraps the pure model; holds NO rules.
// =============================================================================

/// Bridges the pure [_TileGameModel] to the widget tree. Extends
/// [ValueNotifier] so a [ValueListenableBuilder] rebuilds only the subtree
/// that reads it. Every mutator delegates to the model, then notifies.
class GameController extends ValueNotifier<GameStatus> {
  GameController({required List<int> palette, int tileCount = 12, int? seed})
    : _model = _TileGameModel(
        palette: palette,
        tileCount: tileCount,
        rng: seed == null ? null : math.Random(seed),
      ),
      super(GameStatus.menu);

  final _TileGameModel _model;

  // Read-only passthroughs for the view.
  GameStatus get status => _model.status;
  List<Tile> get tiles => _model.tiles;
  int get score => _model.score;
  double get progress => _model.progress;
  String get progressLabel => _model.progressLabel;

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

  // No fixed seed => fresh board each session. Pass `seed:` for a fixed deal.
  late final GameController _controller = GameController(
    palette: _palette,
    tileCount: 12,
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
                    Text(
                      'Score $score',
                      style: theme.textTheme.titleMedium,
                    ),
                    const SizedBox(height: 6),
                    SizedBox(
                      height: 8,
                      child: CustomPaint(
                        size: const Size(double.infinity, 8),
                        painter: _HudPainter(
                          progress: progress,
                          trackColor:
                              theme.colorScheme.surfaceContainerHighest,
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
      // The GestureDetector below is the real hit target; exclude its implicit
      // semantics so the screen reader reads only this node.
      excludeSemantics: true,
      child: GestureDetector(
        onTap: tile.matched ? null : onTap,
        child: AnimatedContainer(
          duration: reduceMotion
              ? Duration.zero
              : const Duration(milliseconds: 180),
          decoration: BoxDecoration(
            color: Color(tile.colorValue).withValues(
              alpha: tile.matched ? 0.35 : 1.0,
            ),
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
// Won
// -----------------------------------------------------------------------------

class _ResultView extends StatelessWidget {
  const _ResultView({
    required this.progressLabel,
    required this.score,
    required this.onPlayAgain,
  });

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
            label: 'You did it! Score $score. $progressLabel.',
            child: ExcludeSemantics(
              child: Column(
                children: [
                  Text('You did it!', style: theme.textTheme.headlineMedium),
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
