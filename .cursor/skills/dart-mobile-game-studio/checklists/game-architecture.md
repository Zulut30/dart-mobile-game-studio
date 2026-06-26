# Game architecture checklist

Tick-list a reviewer or agent runs against a Dart/Flutter mobile game's architecture. Derived
from `references/flutter-game-architecture.md`, `references/flutter-games-toolkit.md`,
`references/dart/dart-api-design.md`, and `assets/seeded_random.dart`. Each item is verifiable by
reading code or running a command — not by judgement. Fail any box → fix before handoff.

## Pure-Dart core (no rendering import)
- [ ] Every file under `lib/models/` and `lib/systems/` has zero `import 'package:flutter/...'`.
- [ ] Every file under `lib/models/` and `lib/systems/` has zero `import 'package:flame/...'`.
- [ ] `grep -rlE "package:(flutter|flame)" lib/models lib/systems` returns no files (run it; empty = pass).
- [ ] `package:flutter` / `package:flame` imports appear only under `lib/game/` and `lib/widgets/`.
- [ ] Rules, entities, level data, save model, and the state machine all live in the pure core, not in widgets/components.
- [ ] If extracted as a standalone `game_core` package, its `pubspec.yaml` declares NO `flutter` dependency (rule is structurally unbreakable).
- [ ] Multi-package split is used only for a stated reason (reused by >1 front end, pure `dart test` CI, hard team boundary, substantial rules engine); otherwise single-package layered is the default.

## Explicit state machine
- [ ] A named status type exists, e.g. `enum GameStatus { menu, playing, paused, won, lost }`, in pure Dart.
- [ ] One controller owns the legal transitions; widgets/components never reassign status directly.
- [ ] Transition guards reject illegal moves (e.g. `applyMove` is a no-op / returns `ignored` unless `status == playing`).
- [ ] `pause`/`resume` only act from the matching source state (`playing`→`paused`, `paused`→`playing`).
- [ ] `start` re-initialises the board and is allowed only from `menu`/`won`/`lost`.
- [ ] Win/lose transitions are derived from the model (`board.isWon` / `board.isLost`), not set ad hoc by the renderer.
- [ ] Contradictory boolean flags are replaced by an `enum` or `sealed` class so illegal states can't compile.
- [ ] The full menu → playing → paused → win/lose → menu cycle is covered by `dart test` cases.

## Mode chosen and justified
- [ ] The chosen rendering mode is recorded: Flutter-widgets-only, Flame, or hybrid `GameWidget`.
- [ ] The choice matches the decision table: widgets-only for turn-based/static (no per-frame motion); Flame for a real `update(dt)` loop / simulation; hybrid for action gameplay that also needs rich Flutter menus/HUD.
- [ ] A one-line justification ties the mode to the core loop (e.g. "tile slide → `AnimatedPositioned`, no Flame needed").
- [ ] Flame is NOT pulled in for a puzzle that only tweens (implicit animation / `AnimationController` suffices).
- [ ] Widgets-only games omit `lib/game/` and have no `flame` entry in `pubspec.yaml`.
- [ ] Hybrid games register an `overlayBuilderMap` (menu/HUD as Flutter overlays) and the state machine drives which overlay is active.

## Thin render layer (widgets / components)
- [ ] No game rules live in any `CustomPainter`, `Widget`, or Flame `Component` — they only read the model and draw / forward intents.
- [ ] `CustomPainter.shouldRepaint` compares the model snapshot (`old.board != board`), not `=> true`.
- [ ] Input handlers (`GestureDetector` / Flame `TapCallbacks`/`DragCallbacks`) translate hit points to a board coordinate, then emit a model intent — the verdict (legal? scored?) lives in pure Dart.
- [ ] Flame components mirror authoritative model state into positions/sprites in `update`; they do not own simulation.
- [ ] Collision/tap events are forwarded to the controller; the outcome is decided in the model, not the component.
- [ ] State-management object (`ChangeNotifier`/`ValueNotifier`) is a thin adapter that *wraps* the pure controller and calls `notifyListeners()` after transitions — it holds no authoritative rules.
- [ ] State-management choice is the lightest that fits (`ValueNotifier` default; `provider`+`ChangeNotifier` only when multiple screens share state); Riverpod/Bloc are present only with a written justification.

## Seams (seeded Random / clock / persistence injected)
- [ ] A `Random` is injected into the controller/systems (constructor param, defaulting allowed) — no bare `Random()` or `DateTime.now()`-seeded RNG buried in the rules.
- [ ] All shuffles/spawns/random draws go through the injected RNG; tests pass a fixed seed (e.g. `SeededRandom(42)`) and assert stable outcomes.
- [ ] RNG use stays inside the VM-tested core (web `int` is 53-bit, so `SeededRandom` is not relied on for web-build reproducibility).
- [ ] Time is injected, not read inline: Flame `update(double dt)` advances pure systems; any wall-clock dependency is passed in so logic is testable without a real clock.
- [ ] Persistence I/O is isolated behind a `SaveSystem` seam; the save *model* (`toJson`/`fromJson`, `dart:convert`) is pure Dart and the only plugin touch is the `shared_preferences` / `path_provider` call.
- [ ] The save model carries a `schemaVersion` and tolerates missing keys on load.
- [ ] No networking/analytics/ads/account seam exists (offline-first); there is no IDFA/GAID or remote-log dependency to inject.

## Levels as JSON data (not code)
- [ ] Levels are declared as data files under `assets/levels/`, not hardcoded as Dart literals in source.
- [ ] Level JSON is parsed through a pure-Dart `LevelData.fromJson` (in `lib/models/`), validated, and throws a typed error on malformed/missing levels (no silent sentinel).
- [ ] Level assets are declared in `pubspec.yaml` under `flutter: assets:`.
- [ ] At least one test loads a real level fixture and asserts it is parseable and solvable (or validity-checked).

## Small, focused files & folder layout
- [ ] Repo follows the layout: `lib/{main.dart, models/, systems/, game/, widgets/, style/}`, `assets/{levels/, images/, audio/}`, `test/`, `pubspec.yaml`.
- [ ] `main.dart` only wires the router/root widget — it holds no game rules.
- [ ] Each system file does one job (`InputSystem`, `SpawnSystem`, `ScoreSystem`, `CollisionSystem`, `AudioSystem`, `SaveSystem`) and is independently testable.
- [ ] Files are small and single-purpose; no god-file mixing model + rendering + persistence.
- [ ] Filenames are `lowercase_with_underscores.dart`; types are `UpperCamelCase`.

## Deterministic, testable logic
- [ ] Core rules are expressed as pure functions / value updates (`applyMove(Move) -> MoveResult`, `bool get isWon`, `List<Move> get legalMoves`) with no hidden global state.
- [ ] Model/value types use `const` constructors, `final` fields, and value `==`/`hashCode` (hand-written or `equatable`-style); updates return new values via `copyWith` where practical.
- [ ] Public surface exposes reads only; private mutable collections are returned as `UnmodifiableListView` or a copy — no leaked internals.
- [ ] In a Flame loop, `dt` is clamped against stalls before advancing the simulation (e.g. `dt = min(dt, 1/30)`) — Flame does NOT clamp for you.
- [ ] Same seed + same inputs produce the same result; a `dart test` reproduces a full play-through deterministically on the VM (no device, no widget pump).
- [ ] `dart analyze` is clean and `dart format --output=none --set-exit-if-changed .` passes (2-space, const, null-safe); any `dispose()`-requiring object is disposed by its owner.
