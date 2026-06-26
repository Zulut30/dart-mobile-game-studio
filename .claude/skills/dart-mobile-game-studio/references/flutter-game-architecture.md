# Flutter game architecture

How to structure a simple 2D mobile game (iOS + Android) so it stays testable, adaptable,
and small. Dart analog of the Swift iOS architecture: the same doctrine — separate logic from
rendering — mapped to Flutter widgets, Flame, and `dart test`.

## Core principle: separate logic from rendering

Put all rules and mutable state in **pure Dart** with no `package:flutter` import. The renderer
reads from the model and forwards input back to it. A pure-Dart core is unit-testable with
`dart test` on the Dart VM — no device, no emulator, no widget pump — and lets you swap the
renderer (Flutter widgets ⇄ Flame) without touching the rules.

```
┌──────────────────┐    intents / input    ┌──────────────────┐
│  Render layer    │ ─────────────────────► │   Game model     │  (pure Dart)
│  Flutter widgets │                        │  state + rules   │
│  / Flame         │ ◄───────────────────── │  state machine   │
└──────────────────┘   observable snapshot  └──────────────────┘
```

The litmus test: a file under `lib/models/` or `lib/systems/` that imports `package:flutter` or
`package:flame` has leaked rendering into the core. Move the offending logic out, or move the
file into `lib/game/` or `lib/widgets/`.

## Layers

1. **Model** — plain Dart data + rules. `Board`, `Card`, `Piece`, `LevelData`, `Score`. Prefer
   immutable classes with `const` constructors and `copyWith`; pure functions
   (`applyMove(Move) -> MoveResult`, `bool get isWon`, `List<Move> get legalMoves`). Compare with
   `==`/`hashCode` (hand-written or via a small `equatable`-style mixin — your call on the dep).
2. **Game state machine** — an explicit `enum GameStatus { menu, playing, paused, won, lost }`
   plus a controller that owns the legal transitions. The controller is still pure Dart; it
   exposes change notifications via the thinnest mechanism that works (see *State management*).
3. **Systems** — focused, independently testable units: `InputSystem`, `SpawnSystem`,
   `ScoreSystem`, `CollisionSystem`, `AudioSystem`, `SaveSystem`. Each does one job. Inject a
   seeded `Random` (the skill ships `assets/seeded_random.dart`) so spawns/shuffles are
   reproducible in tests.
4. **Render layer** — Flutter widgets (`CustomPainter`, gesture detectors) and/or Flame
   `Component`s. Thin: read the model, draw it, translate gestures/taps into model intents. No
   game rules here.
5. **Persistence** — a small `toJson`/`fromJson` save model written via `shared_preferences` or a
   JSON file under the app documents directory (`path_provider`). Version it (`schemaVersion`) and
   tolerate missing keys. `jsonEncode`/`jsonDecode` live in `dart:convert` — no Flutter needed, so
   the save *model* stays pure Dart; only the *I/O* call touches a plugin.

## The pure-Dart state machine

```dart
// lib/models/game_status.dart  — no package:flutter, no package:flame
enum GameStatus { menu, playing, paused, won, lost }

/// Pure rules + transitions. Unit-tested with `dart test`, no device.
class GameController {
  GameController({required this.level, Random? random})
      : _random = random ?? Random(),
        _board = Board.fromLevel(level);

  final LevelData level;
  final Random _random;
  Board _board;

  GameStatus _status = GameStatus.menu;
  GameStatus get status => _status;
  Board get board => _board;

  void start() {
    assert(_status == GameStatus.menu || _status == GameStatus.won || _status == GameStatus.lost);
    _board = Board.fromLevel(level);
    _status = GameStatus.playing;
  }

  void pause() {
    if (_status == GameStatus.playing) _status = GameStatus.paused;
  }

  void resume() {
    if (_status == GameStatus.paused) _status = GameStatus.playing;
  }

  /// Returns the result so the renderer can react (sound, haptic) without re-deriving rules.
  MoveResult applyMove(Move move) {
    if (_status != GameStatus.playing) return MoveResult.ignored;
    final result = _board.applyMove(move); // pure
    _board = result.board;
    if (_board.isWon) {
      _status = GameStatus.won;
    } else if (_board.isLost) {
      _status = GameStatus.lost;
    }
    return result;
  }
}
```

Test it on the VM with no Flutter binding:

```dart
// test/game_controller_test.dart
import 'package:test/test.dart';

void main() {
  test('winning move transitions playing -> won', () {
    final c = GameController(level: solvableLevel, random: Random(42))..start();
    expect(c.status, GameStatus.playing);
    c.applyMove(winningMove);
    expect(c.status, GameStatus.won);
  });
}
```

## State management: keep it thin over the model

The model is the single source of truth. State management is only the *notification wire*
between that model and the render layer — it never holds authoritative rules. Pick the lightest
option that fits; you can wrap the controller without changing it.

| Option | What it is | Use when | Notes |
|---|---|---|---|
| `setState` | Rebuild one `StatefulWidget` | State lives in a single screen; tiny games | No cross-widget sharing; the model can still be pure and held as a field |
| `ValueNotifier` + `ValueListenableBuilder` | Flutter-only single-value notifier | One or few observable values (score, status); minimal deps | Recommended starting point. Rebuilds only the builder subtree |
| `ChangeNotifier` + `provider` | Notifier broadcast through `InheritedWidget` | Several screens read the same controller | `provider` is one small, well-supported dep; mixin onto a controller wrapper |
| Riverpod | Compile-safe providers, no `BuildContext` to read | Larger games, many independent slices, you want testable providers | More concepts; heavier than a 3-screen game needs |
| Bloc / `flutter_bloc` | Event → state streams | You want an explicit event log / time-travel and a strict unidirectional flow | Most ceremony; justify it for a *simple* game |

Doctrine for this skill: **start with `ValueNotifier`**, graduate to `provider` +
`ChangeNotifier` only when multiple screens share state. Riverpod/Bloc are allowed but must be
justified — they are rarely needed for coloring books, sliding puzzles, or a lite runner.

Crucially, the state-management object **wraps** the pure controller; it does not absorb its
rules. The `ChangeNotifier` is a thin adapter — the rules stay in pure Dart and stay VM-tested:

```dart
// lib/game/game_notifier.dart  — adapter only; rules live in GameController
import 'package:flutter/foundation.dart';

class GameNotifier extends ChangeNotifier {
  GameNotifier(this._controller);
  final GameController _controller; // pure Dart, no flutter import

  GameStatus get status => _controller.status;
  Board get board => _controller.board;

  void applyMove(Move move) {
    final result = _controller.applyMove(move); // rule lives in the pure core
    if (result != MoveResult.ignored) notifyListeners();
  }

  void pause() { _controller.pause(); notifyListeners(); }
  void resume() { _controller.resume(); notifyListeners(); }
}
```

A `ValueNotifier<GameStatus>` works the same way for the simplest games: hold one in the
controller wrapper, drive a `ValueListenableBuilder` over it for the HUD, and call
`notifier.value = newStatus` after each transition.

## Rendering mode decision table

| Need | Mode |
|---|---|
| Turn-based / static board, tap & drag, no per-frame motion (coloring, sliding puzzle, memory match, board games) | **Flutter widgets only** — `CustomPainter`/`Canvas` + `GestureDetector` |
| Continuous motion, a game loop, gravity, collisions, particles, many moving entities (lite runner, tap-reaction, light platformer) | **Flame** — `FlameGame` + `Component`s, `update`/`render` each tick |
| Action gameplay **and** rich Flutter menus/HUD/settings/transitions | **Hybrid** — Flame `GameWidget` embedded in a Flutter tree, Flutter overlays for UI |

When unsure, pick the simpler mode that still delivers the core loop at 60 fps. A puzzle that
*looks* animated (tween a tile sliding) usually does not need Flame — `AnimatedPositioned` or an
`AnimationController` over a widget tree is enough. Reach for Flame when you need a real **game
loop** (`update(double dt)`) and per-frame simulation.

### Mode 1 — Flutter widgets only

`CustomPainter` reads the model and paints; a gesture detector turns input into intents. No
Flame dependency at all.

```dart
class BoardPainter extends CustomPainter {
  BoardPainter(this.board);
  final Board board; // pure Dart snapshot

  @override
  void paint(Canvas canvas, Size size) {
    // draw tiles from `board` using canvas.drawRect / drawPath ...
  }

  @override
  bool shouldRepaint(covariant BoardPainter old) => old.board != board;
}
```

### Mode 2 — Flame (`FlameGame` + components)

`FlameGame` owns the loop. Components subclass `Component`/`PositionComponent`, override
`onLoad`, `update(double dt)`, and `render(Canvas)`. A component reaches the game via the
`HasGameReference<T>` mixin (`game` getter). Keep the rules in the pure controller and read it
from `update`; the component only mirrors state into positions/sprites.

```dart
import 'package:flame/components.dart';
import 'package:flame/game.dart';

class RunnerGame extends FlameGame {
  RunnerGame(this.controller); // pure Dart core injected
  final GameController controller;

  @override
  Future<void> onLoad() async {
    await add(PlayerComponent());
  }

  @override
  void update(double dt) {
    super.update(dt); // advances children first
    controller.advance(dt); // pure simulation step; no flutter/flame inside
  }
}

class PlayerComponent extends PositionComponent
    with HasGameReference<RunnerGame> {
  PlayerComponent() : super(size: Vector2.all(48), anchor: Anchor.center);

  @override
  void update(double dt) {
    // Mirror the authoritative model position onto this component.
    position.setFrom(game.controller.playerPosition);
  }
}
```

For collisions, add `HasCollisionDetection` to the `FlameGame` and the `CollisionCallbacks`
mixin (with a `hitbox`, e.g. `RectangleHitbox`) to components; override `onCollisionStart`.
Forward the *event* to the controller — the verdict (did it end the run?) belongs in the model.

### Mode 3 — Hybrid (Flame + Flutter overlays)

Embed the game with `GameWidget` and drive menus/HUD with Flame's **overlays**: register an
`overlayBuilderMap` of identifier → Flutter widget, then `game.overlays.add/remove/toggle(id)`.
Pause the loop with `pauseEngine()` / `resumeEngine()` (or the `paused` field) when showing a
menu so simulation stops cleanly. The state machine drives which overlay is active.

```dart
GameWidget<RunnerGame>.controlled(
  gameFactory: () => RunnerGame(GameController(level: level)),
  overlayBuilderMap: {
    'MainMenu': (context, game) => MainMenuOverlay(game: game),
    'Paused': (context, game) => PausedOverlay(game: game),
    'GameOver': (context, game) => GameOverOverlay(game: game),
  },
  initialActiveOverlays: const ['MainMenu'],
);

// In the game, on a status change:
void onPaused() {
  pauseEngine();              // GameLoop stops; update/render halt
  overlays.add('Paused');
}
void onResumed() {
  overlays.remove('Paused');
  resumeEngine();
}
```

(Verified against Flame docs: `GameWidget`, `overlayBuilderMap`, `overlays.add/remove/toggle`,
`pauseEngine`/`resumeEngine`/`paused`, `HasGameReference`, `HasCollisionDetection`,
`PositionComponent`, the `onGameResize → onLoad → onMount → update/render → onRemove` lifecycle,
and `onLoad` running once vs `onMount` running on every add.)

## Recommended folder layout

```
game_name/
├─ lib/
│  ├─ main.dart            // runApp(); wires router/root widget. The only required entry.
│  ├─ models/             // PURE DART: rules, entities, level data, save model, state machine
│  ├─ systems/            // PURE DART: input, spawn, score, collision, audio policy, save logic
│  ├─ game/               // Flame: FlameGame + Components (Mode 2/3 only); state-mgmt adapters
│  ├─ widgets/            // Flutter: menu, HUD, settings, CustomPainter, game container
│  └─ style/              // colors, text styles, Semantics helpers (optional)
├─ assets/
│  ├─ levels/            // level JSON (data, not code)
│  └─ images/  audio/    // placeholder vector/SF-symbol-equivalent or user-owned assets only
├─ test/                  // `dart test` unit tests for models/ + systems/ (no device)
└─ pubspec.yaml           // deps (flutter, flame); assets declared here
```

`models/` and `systems/` must stay import-clean of `package:flutter` and `package:flame`.
`game/` and `widgets/` are the only places those imports appear. For a Mode 1 (widgets-only)
game, omit `lib/game/` and the `flame` dependency entirely.

This mirrors the Flutter Casual Games Toolkit's feature-first split (it uses `flame_game/`,
`main_menu/`, `settings/`, `audio/`, `style/`, `level_selection/`) while enforcing this skill's
stricter rule: a **rendering-free core** under `models/`+`systems/`, not just feature folders.

## When to extract a separate pure-Dart package for the core

The Swift analog is a Swift Package Manager target for the model. In Dart, the equivalent is a
**separate package** (its own `pubspec.yaml`) that depends only on `dart:core` and small pure
libraries — never on `flutter`. Two shapes:

- **Single-package, layered** (default for simple games): one Flutter app package; the core lives
  in `lib/models/` + `lib/systems/` and is kept pure by convention + an analyzer/CI check. Tested
  with `dart test`. This is enough for a coloring book or sliding puzzle.
- **Multi-package (melos / path dependency)**: a standalone `game_core` package (pure Dart,
  `dart test`-only) that the Flutter app depends on via a `path:` dependency. Extract this when
  one or more of:
  - the core is reused by **more than one front end** (e.g. a Flutter app *and* a CLI solver or a
    server-side level validator);
  - you want the core's CI to run as a **pure `dart test`** job with zero Flutter SDK, for speed
    and to make the "no flutter import" rule structurally impossible to break (the package simply
    has no `flutter` dependency to import);
  - the team is large enough that a hard package boundary beats a lint rule;
  - the rules engine is substantial and you want independent versioning.

  ```
  workspace/
  ├─ packages/game_core/    // pure Dart: models + systems; pubspec has NO flutter dep
  │  ├─ lib/  test/         // `dart test` only
  └─ app/                   // Flutter app; pubspec: game_core: {path: ../packages/game_core}
     └─ lib/ (game/, widgets/)
  ```

Default to the single-package layout and only split when a concrete reason above appears.
Premature splitting adds path-dependency and tooling overhead a small game does not need —
but the import discipline is identical either way, so promoting later is mechanical.

## Time and the loop

- **Flame** calls `update(double dt)` each tick with seconds elapsed. Clamp `dt` against stalls
  (e.g. `dt = min(dt, 1 / 30)`) before advancing the simulation, so a dropped frame can't
  teleport entities. Advance pure systems by `dt`; let `super.update(dt)` advance children.
- **Flutter-only** continuous animation: use an `AnimationController` / `Ticker`, or
  `AnimatedBuilder`. Only reach for a per-frame ticker when you genuinely need it; for a tile
  slide or fade, an implicit animation (`AnimatedPositioned`, `AnimatedOpacity`) is simpler and
  cheaper. Static/turn-based games need no ticker at all — repaint on state change.

## Input

- **Flutter widgets**: `GestureDetector` (`onTapDown`, `onPanUpdate`) → translate the hit point to
  a board coordinate → emit a model intent (`applyMove`). Hit-testing lives in the widget; the
  *verdict* (legal? scored?) lives in the model.
- **Flame**: add the relevant detector mixin to the `FlameGame` (e.g. `TapCallbacks` /
  `DragCallbacks` on a component, or a top-level gesture) and forward to the controller. A
  `JoystickComponent` is built in for directional control.
- Normalize coordinates at the boundary; keep authoritative decisions in pure Dart so they are
  testable without simulating a gesture.

## Accessibility & kids-safety hooks (architecture-level)

- Wrap interactive widgets in `Semantics(label:, value:, button:/onTap:)` so screen readers
  announce them; this is a render-layer concern but the *labels* (e.g. "3 of 12 matched") come
  from the pure model, so expose them as plain getters.
- Honour `MediaQuery.of(context).disableAnimations` (Reduce Motion) and text scaling at the render
  layer; the model is unaffected.
- Offline-first falls out of this architecture for free: no networking layer exists. Keep it that
  way — no analytics/ads/tracking SDKs, no advertising id (IDFA/GAID), no accounts. Persistence is
  local JSON only.

See the skill's mode-specific pattern references for concrete `CustomPainter`, `FlameGame`, and
overlay code, and `assets/seeded_random.dart` for the injectable RNG used to keep logic
deterministic and tests reproducible.