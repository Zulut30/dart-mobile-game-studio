# memory_match — reference game

The worked example for the **dart-mobile-game-studio** skill: a complete, buildable, tested
memory-match game that embodies the skill's doctrine. Copy its architecture for new games.

It is **Flutter-widgets-only** (no Flame): a turn/tap-based board with no per-frame loop — the mode the
skill picks for static/discrete games (see [`choose-game-architecture`](../../.agents/skills/dart-mobile-game-studio/workflows/choose-game-architecture.md)).

## What it demonstrates

- **Pure-Dart core, zero Flutter imports.** All rules live in [`lib/models/`](lib/models) +
  [`lib/systems/`](lib/systems) and are unit-tested on the VM — no device, no widget pump.
  `grep -r package:flutter lib/models lib/systems` is empty.
- **Explicit state machine** — `GamePhase { menu, playing, paused, won }` (no `lost`: memory-match is
  no-fail).
- **Pure reducer** — `GameLogic.flip(state, index)` / `resolveMismatch(state)` are
  `(state, action) -> state` with no I/O, no `Random`, no clock. Same input → same output.
- **Immutable value types** — `MemoryCard`, `GameState` with `==`/`hashCode` + `copyWith` (and the
  `clearFirstFlipped`/`clearPendingMismatch` flags for the nullable-field trap).
- **Injected seeded RNG** — `BoardFactory.newGame` takes a `Random`; tests pass `SeededRandom(seed)`
  for reproducible layouts. The clock seed lives at the UI edge (`GameScreen`), never in the core.
- **Thin UI** — one `StatefulWidget` (`GameScreen`) owns the state + the mismatch `Timer` (disposed);
  everything else is `const` `StatelessWidget`s reading the model.
- **Accessibility** — `Semantics` (label/value/button) on every card; symbols differ by shape **and**
  color (color-blind safe); Reduce Motion collapses the flip animation; a `liveRegion` HUD.
- **Kids-safe** — no ads/analytics/tracking/network; placeholder art (Material icons), no copyrighted
  assets. Passes `dart-doctor.py` clean across architecture, dart-quality, kids-safety, accessibility.

## Layout

```
lib/
  main.dart                  app entry
  models/                    PURE Dart — no Flutter import
    game_phase.dart          the lifecycle enum
    memory_card.dart         immutable card value type
    game_state.dart          immutable whole-game state
  systems/                   PURE Dart — the rules
    seeded_random.dart       SplitMix64 deterministic Random (skill asset)
    board_factory.dart       deals a shuffled board from an injected Random
    game_logic.dart          flip / resolveMismatch / togglePause reducer
  widgets/                   thin Flutter UI
    app.dart  menu_screen.dart  game_screen.dart  card_tile.dart  status_bar.dart
test/
  game_state_test.dart  board_factory_test.dart  game_logic_test.dart  widget_test.dart
```

## Run it

```bash
flutter pub get
flutter analyze                 # zero issues
flutter test                    # pure-core unit tests + a widget smoke test
flutter run                     # play it on a device/emulator

# the pure core can also run on the bare Dart VM (add `test` as a dev-dep):
dart test test/game_logic_test.dart
```

CI (`.github/workflows/ci.yml`, the `example` job) runs `flutter pub get` → `flutter analyze` →
`flutter test` on every push — a green check is the end-to-end proof that the skill's architecture
compiles and passes.

> No store-approval or compliance guarantees — this is a reference implementation, not a shipping
> title. See the skill's [`assets/review-checklist.md`](../../.agents/skills/dart-mobile-game-studio/assets/review-checklist.md).
