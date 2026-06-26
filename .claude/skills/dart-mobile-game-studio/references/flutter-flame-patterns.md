# Flutter + Flame patterns

Concrete game-loop, collision, input, and embedding patterns for mobile (iOS + Android). Copyable
snippets; adapt names to the project. All rules live in the **pure Dart core** (no
`package:flutter` import); Flame or `CustomPainter` is the thin renderer.

API names here are verified against the Flame docs (`docs.flame-engine.org`) and the Flutter SDK.
Do not invent members — if you need one not shown, check the docs first.

## Choosing a rendering mode
| Need | Mode |
|---|---|
| Turn-based / static board, tap & drag, no per-frame motion | **Flutter widgets only** (`CustomPainter` + gestures) |
| Continuous motion, many entities, collisions, particles | **Flame** (`FlameGame` + components) |
| Action gameplay **and** real menus / HUD / settings | **Hybrid** (`GameWidget` + `overlayBuilderMap`) |

When unsure, pick the simpler mode that still hits the core loop at 60 fps. The pure model is
identical across all three — only the renderer changes.

---

## The pure Dart core (shared by every mode)
No Flutter/Flame imports, so `dart test` runs it on the VM with no device. Inject a seeded
`Random` (the skill ships `assets/seeded_random.dart`) so spawns/shuffles are reproducible.

```dart
// lib/model/game_model.dart — NO 'package:flutter' import anywhere in this file.
enum GameState { menu, playing, paused, won, lost }

class GameModel {
  GameModel({required this.rng});

  final Random rng;            // injected; seeded in tests, time-seeded in prod
  GameState state = GameState.menu;
  double playerX = 0;
  double velocity = 0;
  int score = 0;

  /// Advance the simulation by [dt] seconds. Pure: same inputs → same outputs.
  void update(double dt) {
    if (state != GameState.playing) return;
    velocity += 900 * dt;            // gravity from tuning data, not magic here
    playerX += velocity * dt;
    if (_hitFloor()) state = GameState.lost;
  }

  void flap() => velocity = -300;    // an intent the renderer forwards
  bool _hitFloor() => playerX > 600;
}
```

```dart
// test/game_model_test.dart — runs with `dart test`, no Flutter binding needed.
import 'package:test/test.dart';
test('deterministic fall ends the run', () {
  final m = GameModel(rng: Random(42))..state = GameState.playing;
  for (var i = 0; i < 100; i++) {
    m.update(1 / 60);
  }
  expect(m.state, GameState.lost);
});
```

---

## Flame: the game loop
`FlameGame` drives a `Component` tree. Each frame Flame calls `update(double dt)` then `render`
top-down. **Flame supplies `dt` in seconds but does NOT cap it** — the loop forwards the raw
`Ticker` delta, so after a stall or a return from background the first `dt` can be huge. **Always
clamp `dt` yourself** before advancing your model (e.g. `dt.clamp(0.0, 1 / 30)`), or fast objects
tunnel through walls and physics explodes.

```dart
import 'package:flame/components.dart';
import 'package:flame/game.dart';

class MyGame extends FlameGame {
  MyGame() : super();
  final model = GameModel(rng: Random.secure());

  @override
  void update(double dt) {
    super.update(dt);                 // advances the component tree first
    final step = dt.clamp(0.0, 1 / 30); // survive frame stalls
    model.update(step);               // pure logic
    // components read model state in their own update()/render()
  }
}

void main() => runApp(GameWidget(game: MyGame()));
```

- `FlameGame` is the root and is itself a `Component`; add children with `add(component)` (or
  `world.add(...)` when using a `World`). `onLoad()` is the async place to load sprites/levels.
- Never put rules in `update`. The scene advances the model and mirrors the result — the model
  decides win/lose/score.

## Components & PositionComponent
`Component` is the base (logic-only); `PositionComponent` adds `position`, `size`, `scale`,
`angle`, and `anchor` (a `Vector2` / `Anchor`). `SpriteComponent` extends it to draw an image.

```dart
class Player extends PositionComponent {
  Player() : super(size: Vector2.all(48), anchor: Anchor.center);

  @override
  void render(Canvas canvas) {
    canvas.drawCircle(Offset.zero, size.x / 2, Paint()..color = const Color(0xFF4C8DFF));
  }
}
```

- Position is in **world** units; `anchor: Anchor.center` makes `position` the middle, which keeps
  rotation and collision math simple.
- Prefer composing many small components over one giant `update`.

## HasGameReference — reach the game/model from a component
Add the `HasGameReference<T extends FlameGame>` mixin; it exposes a typed `game` getter so a
component can read the shared model. (Older code uses `HasGameRef` with a `gameRef` getter — same
idea; `HasGameReference` is the current name.)

```dart
class PlayerView extends PositionComponent with HasGameReference<MyGame> {
  @override
  void update(double dt) {
    position.x = game.model.playerX;   // typed access, no casting
  }
}
```

## World & CameraComponent
`FlameGame(world: ..., camera: ...)` separates *what* exists (the `World`) from *how it's viewed*
(the `CameraComponent`). The camera's `viewfinder` controls where it looks and the anchor.

```dart
final game = FlameGame(
  world: MyWorld(),
  camera: CameraComponent.withFixedResolution(width: 800, height: 600), // letterboxes
);
// In onLoad, top-left coordinates feel natural for 2D:
camera.viewfinder.anchor = Anchor.topLeft;
camera.follow(player);   // keep a component centered
```

`withFixedResolution` is the simplest way to get a consistent logical canvas across the wildly
varied iOS/Android screen sizes — design to 800×600 (or your choice) and let Flame scale it.

---

## Collisions (Flame's built-in detection)
Add `HasCollisionDetection` to the game, `CollisionCallbacks` to colliding components, and a
hitbox child. Keep the **decision** (did the player die? did we score?) in the model.

```dart
import 'package:flame/collisions.dart';

class MyGame extends FlameGame with HasCollisionDetection { /* ... */ }

class Player extends PositionComponent with CollisionCallbacks, HasGameReference<MyGame> {
  Player() : super(size: Vector2.all(48), anchor: Anchor.center);

  @override
  Future<void> onLoad() async {
    add(CircleHitbox());            // sized to the component by default
  }

  @override
  void onCollisionStart(Set<Vector2> points, PositionComponent other) {
    super.onCollisionStart(points, other);
    if (other is Coin) {
      game.model.score += 1;       // model owns the rule
      other.removeFromParent();
    } else if (other is Hazard) {
      game.model.state = GameState.lost;
    }
  }
}
```

- Callbacks: `onCollisionStart(Set<Vector2> intersectionPoints, PositionComponent other)`,
  `onCollision(...)` (every frame of contact), `onCollisionEnd(PositionComponent other)`.
- Hitbox shapes: `RectangleHitbox`, `CircleHitbox`, `PolygonHitbox` (convex only). Prefer the
  cheap circle/rectangle over polygons for perf.
- `CollisionType` on a hitbox tunes cost: `active` (collides with active + passive — the default),
  `passive` (only reacts to active hitboxes — use for static ground/walls), `inactive` (off).
  Marking static geometry `passive` skips active-vs-active checks.

## Physics with flame_forge2d (only when you need real dynamics)
For stacking, joints, restitution, or realistic bouncing, add the **separate** `flame_forge2d`
package and extend `Forge2DGame` (which itself extends `FlameGame`). Each physical entity is a
`BodyComponent` that builds a Box2D `Body` from a `BodyDef` + `FixtureDef` + `Shape`. Justify the
extra dependency — most simple games (memory, sliding puzzle, tap-reaction, light platformer) do
**not** need it; Flame's own collision callbacks plus model math are enough.

```dart
import 'package:flame_forge2d/flame_forge2d.dart';

class MyPhysicsGame extends Forge2DGame {
  MyPhysicsGame() : super(gravity: Vector2(0, 10)); // +y pulls down
}

class Ball extends BodyComponent {
  Ball(this.start);
  final Vector2 start;

  @override
  Body createBody() {
    final shape = CircleShape()..radius = 0.5;
    final fixture = FixtureDef(shape, restitution: 0.6, density: 1.0);
    final bodyDef = BodyDef(position: start, type: BodyType.dynamic, userData: this);
    return world.createBody(bodyDef)..createFixture(fixture);
  }
}
```

Forge2D contacts come through the `ContactCallbacks` mixin (`beginContact` / `endContact`) — but
still route the *gameplay verdict* into the model. Forge2D works in meters; keep its zoom/scale in
tuning data.

---

## Input in Flame: tap & drag
Mix input callbacks into the components that should receive them. Flame hit-tests against the
component's `size`/`anchor`, so set a size or override `containsLocalPoint`. Events carry both
`localPosition` (component space) and `canvasPosition` (whole-game space).

```dart
import 'package:flame/events.dart';

// Tap: TapCallbacks → onTapDown/onTapUp/onTapCancel/onLongTapDown.
class TapButton extends PositionComponent with TapCallbacks, HasGameReference<MyGame> {
  TapButton() : super(size: Vector2(120, 48));

  @override
  void onTapDown(TapDownEvent event) {
    game.model.flap();               // forward intent; model decides
  }
}

// Drag: DragCallbacks → onDragStart/onDragUpdate/onDragEnd; use event.localDelta to move.
class DraggablePiece extends PositionComponent with DragCallbacks {
  DraggablePiece() : super(size: Vector2.all(80));
  bool _dragging = false;

  @override
  void onDragStart(DragStartEvent event) {
    super.onDragStart(event);
    _dragging = true;
    priority = 100;                  // float above siblings while dragging
  }

  @override
  void onDragUpdate(DragUpdateEvent event) {
    if (_dragging) position.add(event.localDelta);
  }

  @override
  void onDragEnd(DragEndEvent event) {
    super.onDragEnd(event);
    _dragging = false;
    // ask the MODEL for the nearest valid slot, then snap or bounce back
  }
}
```

Keep hit-testing and coordinate math in the component; keep "is this placement legal / scored" in
the model.

---

## Hybrid: GameWidget in a Scaffold with overlays for HUD/menus
Embed the game in the normal Flutter tree and draw menus/HUD as **Flutter widgets** via
`overlayBuilderMap`. This gives you real, accessible Flutter UI (buttons, `Semantics`, Dynamic
Type) over the Flame canvas — the recommended split for action games that also need menus.

```dart
import 'package:flame/game.dart';
import 'package:flutter/material.dart';

class GameScreen extends StatelessWidget {
  const GameScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final game = MyGame();
    return Scaffold(
      body: GameWidget<MyGame>(
        game: game,
        initialActiveOverlays: const ['Menu'],
        overlayBuilderMap: {
          'Menu': (context, g) => MenuOverlay(
                onPlay: () {
                  g.model.state = GameState.playing;
                  g.overlays.remove('Menu');
                },
              ),
          'Hud': (context, g) => HudOverlay(game: g),
          'Pause': (context, g) => PauseOverlay(game: g),
        },
      ),
    );
  }
}
```

- Toggle overlays from anywhere with a `game` reference: `game.overlays.add('Pause')`,
  `.remove('Pause')`, `.toggle('Pause')`, `.isActive('Pause')`. The builder signature is
  `Widget Function(BuildContext, T game)`.
- Mirror live model values into the HUD with a `ValueNotifier` / `ChangeNotifier` the game updates
  and an `AnimatedBuilder` / `ValueListenableBuilder` in the overlay listens to — avoids rebuilding
  the whole tree each frame.

## Pausing & lifecycle (both modes)
- Pause the engine **and** the model clock so `dt` doesn't spike on resume:
  `game.pauseEngine()` / `game.resumeEngine()` (or set `game.paused`). When paused the
  `GameLoop` stops issuing `update`/`render`.
- Respond to app lifecycle (`AppLifecycleState.paused`) by pausing the engine and audio; set
  `model.state = GameState.paused` so resuming is a clean transition, not a teleport.

---

## Flutter-widgets-only path (no Flame)
For static/turn-based games, skip Flame entirely. Drive the same pure model and paint with
`CustomPainter`. Two sub-cases:

### Discrete updates (memory, matching, sliding puzzle) — no per-frame loop
Most board games never need a frame loop. Mutate the model on a gesture, then `setState` /
`ValueNotifier` to repaint. Animate transitions with `AnimatedPositioned` / `AnimatedOpacity` or
implicit animations — no `Ticker` required.

```dart
import 'package:flutter/material.dart';

class BoardView extends StatefulWidget {
  const BoardView({super.key});
  @override
  State<BoardView> createState() => _BoardViewState();
}

class _BoardViewState extends State<BoardView> {
  final model = GameModel(rng: Random(7));

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapUp: (d) => setState(() => model.flap()), // forward intent → repaint
      child: CustomPaint(
        size: Size.infinite,
        painter: BoardPainter(model),
      ),
    );
  }
}

class BoardPainter extends CustomPainter {
  BoardPainter(this.model);
  final GameModel model;

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = const Color(0xFF4C8DFF);
    canvas.drawCircle(Offset(size.width / 2, model.playerX), 24, paint);
  }

  // Repaint only when state that affects drawing changed.
  @override
  bool shouldRepaint(BoardPainter old) => old.model.score != model.score;
}
```

### Continuous animation without Flame — Ticker + AnimatedBuilder
When you genuinely need per-frame motion in a widget-only game, drive it with a
`Ticker` (via `SingleTickerProviderStateMixin`) feeding a model `update(dt)`, and repaint through
an `AnimatedBuilder` on a `ValueNotifier`. Clamp `dt` yourself — the raw `Ticker` elapsed delta is
unbounded across a stall.

```dart
class _RunnerState extends State<Runner> with SingleTickerProviderStateMixin {
  final model = GameModel(rng: Random(1));
  final repaint = ValueNotifier<int>(0);
  late final Ticker _ticker;
  Duration _last = Duration.zero;

  @override
  void initState() {
    super.initState();
    _ticker = createTicker((elapsed) {
      final dt = ((elapsed - _last).inMicroseconds / 1e6).clamp(0.0, 1 / 30);
      _last = elapsed;
      model.update(dt);          // pure logic
      repaint.value++;           // nudge AnimatedBuilder to repaint
    })..start();
  }

  @override
  void dispose() {
    _ticker.dispose();           // always dispose tickers
    repaint.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => model.flap(),
      child: AnimatedBuilder(
        animation: repaint,
        builder: (_, __) => CustomPaint(painter: BoardPainter(model), size: Size.infinite),
      ),
    );
  }
}
```

`AnimationController` (also a `Ticker` under the hood) is fine for short, bounded UI motion; use a
raw `Ticker` when *you* own the simulation clock. Prefer the discrete `setState` path whenever the
game doesn't actually move between inputs — it's simpler and cheaper.

---

## Input → intents (all modes)
- **Flame:** `TapCallbacks` / `DragCallbacks` on the component; forward the event to a model
  method (`flap()`, `tryPlace(slot)`); never decide rules in the callback.
- **Widget-only:** `GestureDetector` (`onTapUp`, `onPanUpdate`, …) → the same model methods.
- Normalize coordinates and keep hit-testing in the view layer; keep the verdict (legal? scored?)
  in the model. Same model, two front ends — that's the point of the pure core.

## Adapting to many screens (iOS + Android)
- Don't hardcode pixel positions. In Flame use `CameraComponent.withFixedResolution` (or read
  `game.size` in `onLoad`/`onGameResize`); in widgets use `LayoutBuilder` / `MediaQuery` and a
  design canvas you scale to the safe area.
- Support portrait and landscape; recompute layout on resize, never assume one orientation.

## Accessibility & kids-safety reminders
- Put interactive controls in **Flutter widgets** (menus, HUD buttons via overlays) and wrap them
  in `Semantics(label/value/button)` — the Flame canvas itself is not screen-reader-navigable, so
  critical actions should have a widget equivalent.
- Honor `MediaQuery.disableAnimations` (Reduce Motion) and text scaling.
- No tracking/ads/analytics, no advertising IDs (IDFA/GAID), no external links or accounts, no
  personal data; offline-first. This spans **both** the Apple Kids Category and Google Play
  Families requirements.

## Style
`dart format` (2-space indent), `const` constructors where possible, analyzer-clean under
`very_good_analysis` / flutter lints. Small, focused files: `lib/model/` (pure Dart),
`lib/game/` (Flame components), `lib/ui/` (Flutter widgets/overlays), `test/` (`dart test`).
