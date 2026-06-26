// flame_game_template.dart  (template)
// Dart Mobile Game Studio — Flame FlameGame starter (Mode 2).
//
// A thin FlameGame that RENDERS a pure-Dart model and forwards input as
// intents. The game loop advances the model with a clamped dt; components only
// mirror authoritative model state into positions/sizes — they hold no rules.
//
// Doctrine:
//   * Keep ALL rules/state in the pure model below (no package:flutter,
//     no package:flame imports there) so it is unit-tested with `dart test`
//     on the Dart VM — no device, no widget pump.
//   * Inject a seeded Random (assets/seeded_random.dart) into the model so
//     spawns/shuffles are reproducible in tests. Here we keep the placeholder
//     model RNG-free; add `SeededRandom` when your genre needs it.
//   * Replace `GameModel` and the placeholder entity with your real types.
//
// To run: embed in a Flutter tree with `GameWidget(game: PlaceholderGame())`.
//
// dart format (2-space); analyzer-clean (very_good_analysis / flutter lints);
// const where possible.

import 'dart:math' as math;

import 'package:flame/components.dart';
import 'package:flame/events.dart';
import 'package:flame/game.dart';
import 'package:flutter/material.dart' show Colors;

// ---------------------------------------------------------------------------
// PURE MODEL — no package:flutter, no package:flame. Unit-tested with
// `dart test`. Replace with your real model; this placeholder drives a single
// dot that drifts right and can be nudged up by a tap intent.
// ---------------------------------------------------------------------------

/// Explicit game state machine: menu -> playing -> paused -> won/lost -> menu.
enum GameStatus { menu, playing, paused, won, lost }

/// A pure intent emitted by the renderer; the model decides the outcome.
///
/// Carries the tap location in *model* coordinates so hit-testing stays in the
/// pure core and is testable without simulating a gesture.
class TapIntent {
  const TapIntent(this.x, this.y);

  final double x;
  final double y;
}

/// Pure, deterministic game model. No rendering imports.
///
/// All units are abstract "world" units the renderer maps to pixels. Owns the
/// rules, the state machine, and the single source of truth for entity state.
class GameModel {
  GameModel({this.worldWidth = 400, this.worldHeight = 600});

  /// Logical play-field size in world units. The renderer scales to the canvas.
  final double worldWidth;
  final double worldHeight;

  /// Placeholder entity position (world units). Replace with your entities.
  double entityX = 40;
  double entityY = 300;

  /// Horizontal drift speed in world units per second.
  static const double _driftPerSecond = 60;

  /// How far a tap nudges the entity upward, in world units.
  static const double _tapNudge = 48;

  GameStatus _status = GameStatus.menu;
  GameStatus get status => _status;

  /// Begin (or restart) a run. Legal from menu / won / lost.
  void start() {
    assert(
      _status == GameStatus.menu ||
          _status == GameStatus.won ||
          _status == GameStatus.lost,
      'start() called from $_status',
    );
    entityX = 40;
    entityY = worldHeight / 2;
    _status = GameStatus.playing;
  }

  void pause() {
    if (_status == GameStatus.playing) _status = GameStatus.paused;
  }

  void resume() {
    if (_status == GameStatus.paused) _status = GameStatus.playing;
  }

  /// Advance the simulation by [dt] seconds. Pure: no rendering, no I/O.
  ///
  /// Called once per frame by the renderer with an already-clamped [dt].
  void advance(double dt) {
    if (_status != GameStatus.playing) return;
    entityX += _driftPerSecond * dt;
    if (entityX >= worldWidth) {
      entityX = worldWidth;
      _status = GameStatus.won; // reached the right edge — placeholder rule
    }
  }

  /// Apply a tap intent. The model — not the renderer — decides the effect.
  ///
  /// Placeholder rule: a tap above the entity nudges it up, a tap below nudges
  /// it down. Replace with your real intent handling (jump, place, select…).
  void handleTap(TapIntent intent) {
    if (_status != GameStatus.playing) return;
    final direction = intent.y < entityY ? -1.0 : 1.0;
    entityY = (entityY + direction * _tapNudge).clamp(0.0, worldHeight);
  }
}

// ---------------------------------------------------------------------------
// FLAME LAYER — thin renderer. Owns the loop; mirrors model state; forwards
// taps as intents. No game rules live here.
// ---------------------------------------------------------------------------

/// Diameter of the placeholder entity, in pixels.
const double _kEntitySize = 32;

/// Thin FlameGame: advances the pure model and mirrors it into components.
///
/// `TapCallbacks` on the game makes the whole canvas tappable; each tap is
/// translated to model coordinates and forwarded as a [TapIntent].
class PlaceholderGame extends FlameGame with TapCallbacks {
  PlaceholderGame({GameModel? model}) : model = model ?? GameModel();

  /// The authoritative pure-Dart core. Injected so tests can supply their own.
  final GameModel model;

  @override
  Future<void> onLoad() async {
    await super.onLoad();
    await add(EntityComponent());
    model.start();
  }

  @override
  void update(double dt) {
    // Clamp dt so a dropped frame / debugger stall can't teleport entities.
    final clamped = math.min(dt, 1 / 30);
    super.update(clamped); // advance children first
    model.advance(clamped); // pure simulation step — no flutter/flame inside
  }

  @override
  void onTapDown(TapDownEvent event) {
    // Map the canvas tap to model (world) coordinates, then forward as intent.
    final scaleX = model.worldWidth / size.x;
    final scaleY = model.worldHeight / size.y;
    final local = event.localPosition;
    model.handleTap(TapIntent(local.x * scaleX, local.y * scaleY));
  }
}

/// Mirrors [GameModel] entity state onto the canvas. Holds no rules.
class EntityComponent extends PositionComponent
    with HasGameReference<PlaceholderGame> {
  EntityComponent()
    : super(size: Vector2.all(_kEntitySize), anchor: Anchor.center);

  static final _paint = Paint()..color = Colors.deepOrange;

  @override
  void update(double dt) {
    // Read the authoritative model and map world units -> canvas pixels.
    final model = game.model;
    final scaleX = game.size.x / model.worldWidth;
    final scaleY = game.size.y / model.worldHeight;
    position.setValues(model.entityX * scaleX, model.entityY * scaleY);
  }

  @override
  void render(Canvas canvas) {
    // Placeholder vector art — no copyrighted assets.
    canvas.drawCircle(
      (size / 2).toOffset(),
      _kEntitySize / 2,
      _paint,
    );
  }
}

// ---------------------------------------------------------------------------
// Accessibility note
// ---------------------------------------------------------------------------
// Flame draws to a raw Canvas, so screen readers cannot see these components.
// In the HYBRID shell, expose state to assistive tech at the Flutter layer:
//   * Wrap `GameWidget` in `Semantics(label: ..., value: ...)`, sourcing the
//     value from pure-model getters (e.g. "entity 240 of 400").
//   * Provide a large, labeled Flutter overlay button as the accessible tap
//     target (Semantics(button: true, label: 'Tap to act')) instead of relying
//     only on the bare canvas tap.
//   * Honour Reduce Motion (`MediaQuery.disableAnimations`) and Dynamic Type at
//     the Flutter layer; the pure model is unaffected.
// Kids-safety: offline-first, no tracking/ads/analytics, no advertising id
// (IDFA/GAID), no accounts, no external links — none of which this loop adds.
