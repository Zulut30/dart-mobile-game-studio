# Dart mastery references

The language toolkit that makes the agent write **excellent** Dart for mobile games. Read the file
that matches what you're writing; the SKILL.md workflow links here at the implement step. Everything
below targets Dart 3 / Flutter, analyzer-clean, with the **pure-Dart core** kept separable from any
renderer (Flutter widgets or Flame) so it unit-tests on the VM with no device.

| File | Read when you are… |
|---|---|
| [dart-language-essentials.md](dart-language-essentials.md) | writing any model/rule: sound null-safety, value-typed immutable classes (`const` + `copyWith`), `==`/`hashCode`, `enum`, collections, immutability, library privacy (`_`) |
| [dart-api-design.md](dart-api-design.md) | naming a type/method/field; designing a public surface; Effective-Dart naming; required vs optional/named params; making illegal states unrepresentable |
| [dart-sealed-pattern-matching.md](dart-sealed-pattern-matching.md) | modelling the state machine (`menu → playing → paused → win/lose`): `sealed`/`final`/`base` class modifiers, exhaustive `switch` expressions, records, destructuring & guard patterns |
| [dart-async-isolates.md](dart-async-isolates.md) | loading levels/assets, async work, never blocking the UI isolate: `Future`/`async`/`await`, `Stream`, `Isolate.run` for heavy CPU work, cancellation & error handling |
| [dart-flutter-mastery.md](dart-flutter-mastery.md) | building menus/HUD/settings or a Flutter-widgets-only game: granular rebuilds, `ValueNotifier`/`ChangeNotifier`, `CustomPainter`, gestures, `Semantics`, `dispose` |
| [dart-flame-mastery.md](dart-flame-mastery.md) | building a Flame or hybrid game: `FlameGame`/`Component`/`PositionComponent`, the `update(dt)`/`render(canvas)` loop, `HasGameReference`, `CollisionCallbacks`, `GameWidget` |
| [dart-patterns-idioms.md](dart-patterns-idioms.md) | reaching for factory constructors, `Comparable`, JSON `fromJson`/`toJson` for level data, extension methods, a seeded injected `Random`, pure state-machine reducers |

## The Dart quality bar (apply to every file you write)

1. **Immutable value models.** `final` fields, `const` constructors, `copyWith` for edits. Override
   `==`/`hashCode` (or use a `record`) so models compare by value, not identity — no missed rebuild
   because two equal boards compared `!=`.
2. **Sealed classes + pattern matching for state.** Model the state machine as a `sealed` type and
   branch with an exhaustive `switch` *expression*; the analyzer fails the build on a missing case,
   so adding a state is caught at compile time, not in QA.
3. **Sound null-safety; never force-unwrap external data.** Never `!` a value parsed from JSON,
   `SharedPreferences`, sensors, or the network. Use `?`, `??`, `?.`, or a `case` pattern
   (`if (json['par'] case final int par)`).
4. **Async off the UI isolate.** `async`/`await` for I/O; offload CPU-heavy work (level generation,
   large parses, pathfinding) to `Isolate.run`. A blocked UI isolate is a frozen frame — never do
   heavy synchronous work in `build`, `update`, or a gesture callback.
5. **`Semantics` on every control.** Provide `label`/`value`; merge or exclude redundant nodes; honor
   `MediaQuery.textScaler` and `MediaQuery.disableAnimations` (Reduce Motion). No silent buttons.
6. **No rebuild-the-world `setState`.** Drive the UI from the pure-Dart model via
   `ValueListenableBuilder` / `ListenableBuilder` / a tightly-scoped `setState`; never rebuild a
   whole screen for a one-field change, and never allocate in `build`.
7. **Dispose everything.** `AnimationController`, `Ticker`, `ValueNotifier`/`ChangeNotifier`,
   `StreamSubscription`, `FocusNode`, `TextEditingController` leak if not torn down in
   `State.dispose` (and Flame components in `onRemove`). Cancel timers and subscriptions too.
8. **Deterministic via injected `Random`.** Inject a seeded `Random` (the skill ships
   `assets/seeded_random.dart`) so shuffles, spawns, and procedural levels are reproducible and
   golden-testable. No bare `Random()` or `DateTime.now()` reached for inside game logic.
9. **Logic has no Flutter imports.** Models/rules/state-machine are plain Dart with **no
   `package:flutter` (and no `package:flame`) import**, so they run under `dart test` on the VM — no
   widget pump, no device. Flutter/Flame is the thin renderer over that core.
10. **Analyzer-clean under strong lints.** Zero analyzer issues with the shipped rule set; treat
    infos and warnings as errors in CI. `prefer_const_constructors`, `avoid_dynamic_calls`,
    `require_trailing_commas`, and friends stay on.

## Do / Don't (the bar in miniature)

```dart
// DON'T — mutable, identity-compared, force-unwrapped external data, Flutter in the model.
import 'package:flutter/material.dart';        // logic must not import Flutter
class Level {
  int par = 3;                                  // mutable shared state
  Level.fromJson(Map j) : par = j['par']!;      // ! on parsed data → runtime crash on a bad file
}

// DO — immutable value type, null-safe parse, pure Dart, value equality.
class Level {
  const Level({required this.par});
  final int par;

  factory Level.fromJson(Map<String, dynamic> json) =>
      Level(par: (json['par'] as num?)?.toInt() ?? 3); // defaulted; never throws on a missing key

  Level copyWith({int? par}) => Level(par: par ?? this.par);

  @override
  bool operator ==(Object other) => other is Level && other.par == par;
  @override
  int get hashCode => par.hashCode;
}
```

```dart
// State as a sealed type → an exhaustive switch the analyzer enforces. Pure Dart, no UI import.
sealed class GameState {
  const GameState();
}

final class Menu extends GameState {
  const Menu();
}

final class Playing extends GameState {
  const Playing(this.score);
  final int score;
}

final class Won extends GameState {
  const Won(this.score);
  final int score;
}

final class Lost extends GameState {
  const Lost();
}

String banner(GameState state) => switch (state) {
      Menu() => 'Tap to start',
      Playing(:final score) => 'Score $score',     // destructure inside the pattern
      Won(:final score) => 'You win — $score!',
      Lost() => 'Try again',
      // Add a 5th state and every non-exhaustive switch fails to compile.
    };
```

```dart
// Deterministic logic: inject the Random, don't reach for a global.
class Deck {
  const Deck(this.cards);
  final List<int> cards;

  // Same seed → same shuffle: the test is reproducible and the core has no Flutter dependency.
  Deck shuffled(Random rng) {
    final next = [...cards]..shuffle(rng);
    return Deck(next);
  }
}
```

## Enforce it mechanically

Format and analyze with the shipped config; CI runs the same on the example and templates.

```bash
dart format .                                   # 2-space indent; trailing commas → vertical layout
dart analyze --fatal-infos --fatal-warnings     # zero issues; infos & warnings are errors
dart test                                        # the pure-Dart core, on the VM — no device needed
```

The lint set is `very_good_analysis` (or `flutter_lints` as a lighter floor), wired via
`analysis_options.yaml`:

```yaml
include: package:very_good_analysis/analysis_options.yaml
analyzer:
  language:
    strict-casts: true
    strict-inference: true
    strict-raw-types: true
  errors:
    invalid_annotation_target: ignore
```