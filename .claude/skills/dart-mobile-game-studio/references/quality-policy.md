# Quality policy

The bar every change in a Dart/Flutter game project must clear. This is the rule set `code-reviewer`
and `code-auditor` enforce; `gameplay-programmer` writes to it by default. It complements the Dart
language craft in `references/dart/README.md` (read both).

## Non-negotiables
1. **Layer separation.** Three layers, never mixed in one file: **game logic** (pure Dart, no
   `package:flutter` import — `lib/models/`, `lib/systems/`), **UI** (`lib/widgets/`), and the
   **render/engine** layer (Flame in `lib/game/`). Game rules are testable with `dart test` on the
   VM — no widget pump, no device. A `package:flutter` import inside `lib/models/` is a blocking bug.
2. **Null-safe, no force-unwrap on external data.** Sound null safety on. `!`, `as`, and `[]` on
   parsed JSON / asset loads / nullable lookups are blocking — use `?.`, `??`, pattern matching, or
   `whereType`. `!` is acceptable only on a code-guaranteed invariant with a comment saying why.
3. **`flutter analyze` clean, `dart format` applied.** CI runs
   `dart format --output=none --set-exit-if-changed .` and `dart analyze`/`flutter analyze`
   (use the shipped `assets/analysis_options.yaml`, which promotes key issues to errors). Zero
   warnings ship.
4. **Const & immutability.** `const` constructors wherever possible; immutable value-typed models
   (`final` fields, `==`/`hashCode`, `copyWith`); sealed classes / enums for state — illegal states
   unrepresentable, not validated at runtime.
5. **Never block the UI isolate.** No synchronous heavy work in `build()` or a frame callback. CPU
   work (level gen, big decode) goes to an `Isolate`/`Isolate.run`/`compute`. I/O is `async`.
6. **Deterministic where tested.** Inject a seeded `Random` (`assets/seeded_random.dart`); never call
   global `Random()` in game logic. Same seed → same sequence, asserted in tests.
7. **Dispose everything.** `AnimationController`, `StreamSubscription`, `ChangeNotifier`/
   `ValueNotifier`, `FocusNode`, `TextEditingController`, timers, Flame components — disposed/cancelled
   in `dispose()`/`onRemove`. Leaks are blocking (the analyzer flags `close_sinks`/`cancel_subscriptions`).
8. **No rebuild-the-world.** Don't `setState` a whole screen for a local change. Scope rebuilds with
   `ValueListenableBuilder`/`ListenableBuilder`/`Selector`; wrap stable subtrees in `const` and
   `RepaintBoundary` (see `performance-checklist.md`).
9. **Accessibility on every control.** `Semantics(label/value/button)`; respect text scaling and
   reduce-motion; TalkBack + VoiceOver navigable; 48dp targets; not color-alone
   (`accessibility-child-safety.md`).
10. **Tested.** New model rules/state transitions have `dart test` coverage; non-trivial widgets have
    `flutter_test` coverage; critical flows have Patrol E2E. No new logic ships untested.

## Code shape
- Small, single-purpose files; one widget/class per concern. Prefer composition over inheritance.
- Effective-Dart naming: `lowerCamelCase` members, `UpperCamelCase` types, boolean getters read as
  assertions (`isMatched`, `canTap`). Named/factory constructors; `required` named params.
- Documentation comments (`///`) on public APIs that aren't self-evident — explain the contract, not
  the code.
- No stray `print` in the play path (use a logger gated to debug); no commented-out code; no TODOs
  left unresolved in shipped paths.

## Forbidden
- Mixing Flutter-UI rendering and Flame in the same screen without the decision rule
  (`flutter-flame-patterns.md`) — pick a mode and justify it.
- Adding a dependency without `package-policy.md`.
- Putting game rules in a widget's `build()` or in a Flame component's `render`.
- Shipping with analyzer warnings, unformatted code, or failing tests, and claiming it passed without
  running it.
- Ignoring testing, performance, monetization, or release because "it's just a prototype."

## How an agent reports quality
A `code-reviewer`/`code-auditor` finding reads: `severity — file:line — what's wrong → the
consequence → the fix`, naming the rule above. Route fixes to `gameplay-programmer`. Run the gate:
```bash
dart format --output=none --set-exit-if-changed .
flutter analyze         # or: dart analyze
dart test               # pure model
flutter test            # widgets
scripts/dart-doctor.py <project>
```
