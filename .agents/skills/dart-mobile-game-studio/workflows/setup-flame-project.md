# Workflow: Set Up a Flame Project (FlameGame + GameWidget host)

**Goal (1 line):** Stand up a minimal, analyzer-clean Flame game — `FlameGame` + `GameWidget` inside a `Scaffold`, overlays for menu/HUD, a `World` + `CameraComponent`, and a pure-Dart model the game reads — ready to grow a genre on top.

## When to use
- The chosen mode is **Flame** or **hybrid GameWidget** (motion, per-frame `update(dt)`, sprites, physics, particles, many moving entities). See `references/flutter-game-architecture` for the mode decision.
- **Do NOT use** for static/turn-based or form-like games (coloring, tap-grid memory, simple sliding puzzle with no animation) — those are Flutter-widgets mode; use `workflows/setup-flutter-widget-game.md` instead.

## Prerequisites
- A Flutter app scaffold already exists (`flutter create` done, app runs). If not, do that first.
- Flutter SDK on PATH; `flutter doctor` clean for your target platforms (iOS + iPadOS + Android).
- You have read `references/package-policy` (any dep must be justified) and `references/flutter-flame-patterns` (component lifecycle, `dt` clamping, seeded `Random`).
- Reference template: `assets/flame_game_template.dart` (copy structure from there; this workflow explains the moving parts and the order to build them).

---

## STEPS

### 1. Add the `flame` dependency (per package-policy)
`flame` is the **one justified game-engine dependency** for Flame mode (Apache-2.0, official `flame-engine` org, kids-safe — no ads/tracking/network). Pin a caret range; do not pull optional bridge packages (`flame_audio`, `flame_forge2d`, …) unless the genre template calls for them.

```bash
flutter pub add flame
flutter pub get
```

Verify in `pubspec.yaml`:
```yaml
dependencies:
  flutter:
    sdk: flutter
  flame: ^1.x.x   # pin the resolved version; record it
```
> Decision: if the game needs **no** per-frame motion, stop here and switch to widgets mode. Adding Flame to a static game is unjustified weight (`references/package-policy`, `references/quality-policy`).

### 2. Decide where the pure model lives (do this BEFORE touching Flame)
The **pure-Dart core has NO `package:flame` and NO `package:flutter` import** — so it is testable with `dart test` and reusable. Flame components *read from* and *send intents to* the model; they never own the rules.

```
lib/
  game/
    my_game.dart          # FlameGame subclass (engine glue only)
    world/
      game_world.dart     # World subclass: spawns/owns components
    components/           # SpriteComponent / PositionComponent subclasses (rendering + input)
  model/                  # PURE DART — no flutter, no flame
    game_state.dart       # state machine: menu→playing→paused→won→lost
    entities.dart         # plain data types (positions as your own Vec2 or records)
    rules.dart            # step(state, dt, input) -> state ; collisions, scoring
  overlays/
    main_menu.dart        # Flutter widgets drawn over the canvas
    hud.dart
    pause_menu.dart
  main.dart
```
- Model owns `dt`-driven simulation where practical (`step(state, dt)`); the Flame component layer interpolates/renders it. For action games where physics lives in components, keep at least the **state machine, scoring, win/lose, and level data** pure.
- Inject the RNG: model takes a `Random` in its constructor (see `assets/seeded_random.dart`), so tests are deterministic. Never call `Random()` with no seed inside the model.

Cross-link: `references/flutter-game-architecture` (layering), `references/algorithms-for-games` (step/collision).

### 3. Create the `World` (owns the game's components)
`World` is the renderable root of game content; the camera looks at it. Keep spawn logic here.

```dart
// lib/game/world/game_world.dart
import 'package:flame/components.dart';
import '../components/player.dart';

class GameWorld extends World {
  @override
  Future<void> onLoad() async {
    await add(Player());          // add() is async; await it in onLoad
    // spawn level entities from your pure model's level data here
  }
}
```

### 4. Create the `FlameGame` subclass (engine glue only)
The game wires the world + camera, holds a reference to the pure model, and drives the state machine by toggling overlays. **Clamp `dt` yourself** — large frames (app resumes, slow devices) must not tunnel through your simulation.

```dart
// lib/game/my_game.dart
import 'package:flame/components.dart';
import 'package:flame/game.dart';
import 'world/game_world.dart';
import '../model/game_state.dart';

const kMaxDt = 1 / 30; // clamp; never simulate more than ~33ms per frame

class MyGame extends FlameGame<GameWorld> {
  MyGame()
      : super(
          world: GameWorld(),
          // Fixed logical resolution -> identical layout on phone & iPad.
          camera: CameraComponent.withFixedResolution(
            width: 800,
            height: 600,
          ),
        );

  final GameState state = GameState.initial();

  @override
  void update(double dt) {
    final clamped = dt > kMaxDt ? kMaxDt : dt;
    state.step(clamped);     // advance the PURE model
    super.update(clamped);   // then let components render/move
  }
}
```
> API note (grounded): `FlameGame` accepts `world:` and `camera:` constructor params; `CameraComponent.withFixedResolution(width:, height:)` keeps a constant logical canvas and letterboxes on other aspect ratios — the single best lever for iPhone/iPad/Android consistency (`references/flame-engine` camera docs). Choose a logical resolution your model reasons in; render scales to fit.

### 5. Host the game in a `Scaffold` with `GameWidget` + overlays
Overlays are **Flutter widgets drawn on top of the canvas**, toggled at runtime via `game.overlays`. Use them for menu, HUD, and pause — never paint UI chrome with Flame components. Builder signature is `(BuildContext context, T game) => Widget`.

```dart
// lib/main.dart
import 'package:flame/game.dart';
import 'package:flutter/material.dart';
import 'game/my_game.dart';
import 'overlays/main_menu.dart';
import 'overlays/hud.dart';
import 'overlays/pause_menu.dart';

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: Scaffold(
        body: GameWidget<MyGame>.controlled(
          gameFactory: MyGame.new,
          overlayBuilderMap: {
            'menu': (context, game) => MainMenu(game: game),
            'hud': (context, game) => Hud(game: game),
            'pause': (context, game) => PauseMenu(game: game),
          },
          initialActiveOverlays: const ['menu'],
        ),
      ),
    );
  }
}
```
> API notes (grounded):
> - `GameWidget<T>.controlled(gameFactory:, overlayBuilderMap:, initialActiveOverlays:)` builds and owns the game instance for you (preferred for simple apps — survives widget rebuilds). `overlayBuilderMap` is `Map<String, Widget Function(BuildContext, T game)>`; `initialActiveOverlays` is the list shown once load finishes.
> - Plain `GameWidget(game: instance, …)` is fine when you must hold the instance yourself; then you own its lifecycle.
> - Optional: `loadingBuilder` (shown while `onLoad` runs) and `errorBuilder` (catch load errors) — wire these for production polish.

### 6. Drive the state machine by toggling overlays
The overlay manager is the bridge between the model's state and the Flutter UI. Methods (grounded): `overlays.add(String)`, `overlays.remove(String)`, `overlays.toggle(String)`, `overlays.isActive(String)`, `overlays.activeOverlays`.

```dart
// inside MyGame — called by overlay buttons / win-lose transitions
void startPlaying() {
  overlays.remove('menu');
  overlays.add('hud');
  state.toState(Phase.playing);
}

void togglePause() {
  final paused = overlays.isActive('pause');
  overlays.toggle('pause');
  state.toState(paused ? Phase.playing : Phase.paused);
  // also gate update(): skip state.step(dt) while Phase.paused
}
```
Overlay widgets call back into the game: a "Play" button runs `game.startPlaying()`; a HUD reads `game.state.score`. Keep overlay widgets thin — read state, fire intents, no rules. Example menu/HUD widgets: `assets/flutter_game_widget_template.dart` and the genre file in `references/game-templates`.

### 7. Gate the simulation on phase + handle lifecycle
- In `update`, **early-return before `state.step` when paused** so the world freezes but overlays still paint.
- App backgrounding produces a huge first `dt` on resume — the clamp in Step 4 already protects you; additionally pause on `AppLifecycleState.paused` (auto-pause is also a kids-safety nicety).
- `dispose()` is handled by `GameWidget.controlled`; if you hold timers/streams in components, cancel them in their `onRemove`.

### 8. Run the analyzer + format + smoke-test (do NOT skip)
```bash
dart format .            # 2-space indent (enforced)
dart analyze             # MUST be clean — zero issues
dart test                # pure-model tests (Step 9) run with NO device
flutter run              # smoke: menu shows, Play -> HUD, pause toggles
```
> Honesty rule (`references/quality-policy`): only claim it builds/runs if you saw this output. If no device/toolchain is available here, say so and hand off these exact commands.

### 9. Write the first tests (pure model — no Flutter binding needed)
Because the model has no Flutter/Flame import, these run fast under plain `dart test`:
- **State machine:** `menu→playing→paused→playing→won/lost→menu` legal transitions; illegal ones rejected.
- **Determinism:** same seed + same inputs ⇒ identical `step` output (proves injected `Random`).
- **dt clamping:** a giant `dt` advances the model by at most the clamp.
- **Win/lose + scoring** boundary conditions.

For widget/golden coverage of overlays and a Flame `GameWidget` pump test, see `references/testing-and-release` and `references/testing-e2e-patrol`.

---

## Done when
- [ ] `flame` added with a recorded pinned version and a one-line justification (Step 1).
- [ ] Pure model directory exists with **no `package:flutter` / `package:flame` imports**; RNG is injected.
- [ ] App launches to the `menu` overlay; **Play** swaps `menu`→`hud`; **pause** toggles cleanly; world freezes while paused.
- [ ] `CameraComponent.withFixedResolution` gives identical layout on an iPhone, an iPad, and an Android device/emulator.
- [ ] `dt` is clamped in `update`.
- [ ] `dart format .`, `dart analyze` (clean), and `dart test` (model tests green) all run and were observed.

## Common pitfalls
- **Painting UI with Flame components.** Menus, HUD text, buttons → Flutter overlays. Flame draws the *game world*, not the chrome.
- **Logic in the game/components layer.** Rules belong in the pure model; components render and forward input. If you can't `dart test` a rule without a device, it's in the wrong layer.
- **Unclamped / unseeded simulation.** No clamp ⇒ resume-from-background tunneling and physics blow-ups. Bare `Random()` ⇒ non-deterministic, untestable runs. Both fail review.
- **Holding a `GameWidget(game:)` instance that gets recreated on rebuild.** Prefer `GameWidget.controlled(gameFactory:)` so the engine owns lifecycle; otherwise store the instance in a `State` and reuse it.
- **`add()` not awaited in `onLoad`.** Component `add` is async — `await` it so children are present before the first frame.
- **Pulling Flame bridge packages "just in case."** Each extra dep needs a package-policy justification; audio/physics/tiled come in only when the genre template requires them.
- **Forgetting `Material(color: Colors.transparent)` wrapper** in overlay widgets — text styling/ink effects misbehave without a `Material` ancestor over the canvas.

## Cross-links
- `references/flutter-game-architecture` — layering, mode choice (widgets vs Flame vs hybrid).
- `references/flutter-flame-patterns` — component lifecycle, `dt`, camera/world idioms.
- `references/game-templates` + `templates/*` — pick your genre and scaffold its world/components on top of this host.
- `references/package-policy` / `references/quality-policy` — dependency justification, analyzer/format bar, honesty rule.
- `references/accessibility-child-safety` — overlay `Semantics`, auto-pause, no tracking/ads (Apple Kids + Google Play Families).
- `references/testing-and-release`, `references/testing-e2e-patrol` — widget/golden/E2E beyond the pure-model tests.
- `assets/flame_game_template.dart`, `assets/seeded_random.dart`, `checklists/*` — copy-runnable starting points and the pre-handoff checklist.
