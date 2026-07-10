// flame_game_template.dart  (template)
// Dart Mobile Game Studio — Flame FlameGame starter (Mode 2).
//
// A thin FlameGame that RENDERS a pure-Dart model and forwards input as
// intents. The game loop advances the model with a clamped dt; components only
// mirror authoritative model state into positions/sizes — they hold no rules.
//
// Doctrine:
//   * Copy flame_game_model_template.dart into lib/models/. Keep ALL rules/state
//     there so it is unit-tested with `dart test` on the Dart VM.
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
import 'dart:ui' show Canvas, Offset, Paint;

import 'package:flame/components.dart';
import 'package:flame/events.dart';
import 'package:flame/game.dart';
import 'package:flutter/material.dart' show Colors;

// Adjust this relative import after copying the two templates into your app.
import 'flame_game_model_template.dart';

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
    model.advance(clamped); // authoritative state first
    // Components now mirror the current frame, not the previous one.
    super.update(clamped);
  }

  @override
  void onTapDown(TapDownEvent event) {
    // Map the canvas tap to model (world) coordinates, then forward as intent.
    if (size.x <= 0 || size.y <= 0) return;
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
  static const _center = Offset(_kEntitySize / 2, _kEntitySize / 2);

  @override
  void update(double dt) {
    super.update(dt);
    // Read the authoritative model and map world units -> canvas pixels.
    final model = game.model;
    final scaleX = game.size.x / model.worldWidth;
    final scaleY = game.size.y / model.worldHeight;
    position.setValues(model.entityX * scaleX, model.entityY * scaleY);
  }

  @override
  void render(Canvas canvas) {
    // Placeholder vector art — no copyrighted assets.
    canvas.drawCircle(_center, _kEntitySize / 2, _paint);
    super.render(canvas);
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
