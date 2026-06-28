# endless_runner — Flame reference game

The **Flame-mode** worked example for the dart-mobile-game-studio skill — the counterpart to
[`examples/memory_match`](../memory_match) (widgets mode). A lite endless runner: auto-run, tap to
jump, dodge obstacles, score by distance, crash to end. It proves the Flame doctrine with **working,
tested code**.

**Mode:** Flame (`FlameGame` + `GameWidget`), hybrid shell — Flame draws the play surface, thin
Flutter widgets sit on top for the HUD and game-over panel.

## What it demonstrates

- **Pure-Dart core, zero Flame/Flutter import.** All rules live in [`lib/models/`](lib/models) +
  [`lib/systems/`](lib/systems) and are unit-tested on the VM. `grep -r "package:flame\|package:flutter" lib/models lib/systems` is empty.
- **`dt` clamped — Flame does NOT.** `Physics.clampDt` (max step `1/30`) is the single source of truth;
  `RunLogic.advance` clamps before integrating, so a hitch can't teleport the player. A test asserts a
  5-second frame doesn't tunnel.
- **Frame-rate independence.** All motion scales by `dt`; a test proves two `1/120` steps equal one
  `1/60` step (ramp off → exact).
- **Clearable spawns from an injected seeded `Random`.** `Spawner` guarantees every obstacle is below
  the jump apex and gaps are wide enough to clear — asserted across 100 seeds. Same seed → identical run.
- **Pure AABB collision** (`Collision.hits`) decides the crash — the authoritative verdict in plain Dart.
- **No per-frame allocation in `render`.** The scene's `Paint`s are fields; obstacles are *data* in
  `RunState` (not components), so there's no component churn to pool — the scene draws the list each frame.
- **Model-notifier → overlay.** A `ValueNotifier<int>` score (disposed in `onRemove`) feeds a Flutter
  `ValueListenableBuilder` HUD with a `liveRegion` for screen readers.

## Layout

```
lib/
  main.dart
  models/                 PURE Dart — no Flame/Flutter import
    game_phase.dart       menu | playing | gameOver  (no 'won' — it's infinite)
    run_config.dart       immutable tuning (speed, gravity, jump, sizes)
    runner.dart           player vertical state (y, vy, grounded)
    obstacle.dart         a scrolling obstacle (id, x, height)
    run_state.dart        the whole run; ==/hashCode + copyWith
  systems/                PURE Dart — the rules
    seeded_random.dart    SplitMix64 deterministic Random (skill asset)
    physics.dart          clampDt + semi-implicit Euler integrate
    spawner.dart          clearable gaps + heights from an injected Random
    collision.dart        AABB player-vs-obstacle
    run_logic.dart        advance(state, dt, rng) / jump / start reducer
  game/runner_game.dart   FlameGame: owns RunState, update(dt)→advance, data-driven _Scene
  widgets/app.dart        GameWidget + HUD + game-over overlay (tap → jump)
test/                     spawner, physics, collision, run_logic (pure, VM-tested)
```

## Run it

```bash
flutter pub get
flutter analyze                 # zero issues — proves the Flame layer compiles against real flame
flutter test                    # pure-core unit tests (spawn/physics/collision/run-logic)
flutter run                     # play it
```

CI (`.github/workflows/ci.yml`, the `example` job, matrix entry `endless_runner`) runs `flutter pub
get` → `flutter analyze` → `flutter test` on every push — a green check is the end-to-end proof that
the Flame-mode architecture compiles (against the real `flame` package) and the rules pass.

> The Flame layer is deliberately thin (data-driven render, pure-Dart collision). Production Flame
> games add `HasCollisionDetection` hitboxes, `ComponentPool` for component-per-entity spawners, and a
> `World`/`CameraComponent` for scrolling/zoom — see [`references/flutter-flame-patterns.md`](../../.agents/skills/dart-mobile-game-studio/references/flutter-flame-patterns.md)
> and [`templates/endless-runner.md`](../../.agents/skills/dart-mobile-game-studio/templates/endless-runner.md).
