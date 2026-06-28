import 'dart:ui';

import 'package:flame/components.dart';
import 'package:flame/game.dart';
import 'package:flutter/foundation.dart';

import '../models/game_phase.dart';
import '../models/run_config.dart';
import '../models/run_state.dart';
import '../systems/physics.dart';
import '../systems/run_logic.dart';
import '../systems/seeded_random.dart';

/// The Flame renderer over the pure-Dart core. It owns the game loop and a single
/// data-driven scene; every rule decision is delegated to `RunLogic`. Obstacles
/// are *data* in `RunState` (not components), so there is no component churn to
/// pool — the scene just draws the current list each frame.
class RunnerGame extends FlameGame {
  RunnerGame({required this.onPhaseChange});

  /// Called when the phase changes (e.g. → gameOver) so the Flutter shell can
  /// show/hide overlays.
  final void Function(GamePhase phase) onPhaseChange;

  final RunConfig config = const RunConfig();

  /// Fraction of the screen height where the ground sits.
  static const double groundFraction = 0.82;

  /// Live score for the HUD overlay (one notifier, watched by `ValueListenableBuilder`).
  final ValueNotifier<int> score = ValueNotifier<int>(0);

  // Seeded at the UI edge (clock), not in the pure core — so the core stays
  // deterministic and testable. Re-seeded on restart.
  SeededRandom _rng = SeededRandom(1);
  late RunState state = RunLogic.start(config, _rng);

  @override
  Future<void> onLoad() async {
    _reseed();
    await add(_Scene());
  }

  void _reseed() {
    _rng = SeededRandom(DateTime.now().millisecondsSinceEpoch & 0x7fffffff);
    state = RunLogic.start(config, _rng);
    score.value = 0;
  }

  @override
  void onRemove() {
    score.dispose();
    super.onRemove();
  }

  /// Restart from the menu/game-over overlay.
  void restart() {
    _reseed();
    onPhaseChange(state.phase);
  }

  /// Tap handler (wired from the Flutter shell): jump.
  void onJumpTap() {
    state = RunLogic.jump(state);
  }

  @override
  void update(double dt) {
    super.update(dt);
    if (state.phase != GamePhase.playing) return;
    final previous = state.phase;
    // Clamp dt here in the loop (Flame does NOT) — RunLogic also clamps, so this
    // is idempotent; keeping it visible where the loop lives is the right habit.
    final step = dt.clamp(0.0, Physics.maxStep);
    state = RunLogic.advance(state, step, _rng);
    score.value = state.score;
    if (state.phase != previous) onPhaseChange(state.phase);
  }
}

/// Draws the whole `RunState` each frame. Paints are fields (no per-frame
/// allocation in `render` — the #1 Flame perf rule).
class _Scene extends Component with HasGameReference<RunnerGame> {
  final Paint _sky = Paint()..color = const Color(0xFF9BD2F0);
  final Paint _ground = Paint()..color = const Color(0xFF6B8E23);
  final Paint _player = Paint()..color = const Color(0xFF2E3CC0);
  final Paint _obstacle = Paint()..color = const Color(0xFFCC3A3A);

  @override
  void render(Canvas canvas) {
    // Paints are fields (no Paint()/Vector2() churn here). The `Rect`s below are
    // the unavoidable lightweight args to canvas.drawRect — not the heavy per-frame
    // allocation the doctrine warns about.
    final s = game.state;
    final c = game.config;
    final w = game.size.x;
    final h = game.size.y;
    final groundTop = h * RunnerGame.groundFraction;

    canvas.drawRect(Rect.fromLTWH(0, 0, w, h), _sky);
    canvas.drawRect(Rect.fromLTWH(0, groundTop, w, h - groundTop), _ground);

    // World y is height above the ground (up positive); screen y grows downward.
    final ps = c.playerSize;
    final playerTop = groundTop - s.runner.y - ps;
    canvas.drawRect(Rect.fromLTWH(c.playerX, playerTop, ps, ps), _player);

    for (final o in s.obstacles) {
      canvas.drawRect(
        Rect.fromLTWH(o.x, groundTop - o.height, c.obstacleWidth, o.height),
        _obstacle,
      );
    }
  }
}
