## What was built

Wrote the Dart-mastery reference at:
`/Users/zulut/Documents/swift-ios-game-studio/.agents/skills/dart-mobile-game-studio/references/dart/dart-patterns-idioms.md`

It is the Flutter/Dart analog of the Swift skill's `swift-patterns-idioms.md`, scoped exactly to what the sibling `dart/README.md` promises for this file (factory constructors, `Comparable`, JSON `fromJson`/`toJson` for level data, extension methods, a seeded injected `Random`, state-machine reducers) and deliberately non-overlapping with `dart-language-essentials.md` (which already covers sealed-class basics, null safety, records, enhanced enums, error handling).

### Sections
1. `copyWith` — derive a changed copy; `_unset` sentinel so a nullable field can actually be cleared (the `?? this.field` trap).
2. Factory & named constructors — validation, subtype selection via factory, `const`-cached canonical instances, redirecting constructors.
3. `Comparable` — multi-key `compareTo` (descending points, tie-break time then name); warns against subtracting doubles; consistency with `==`; `package:collection` sortedBy alternative.
4. JSON `fromJson`/`toJson` with `schemaVersion` + step-by-step forward `_migrate` (v1→v3 worked example), `if-case` shape validation, `MapEntry(:key, :value)` destructuring, and a tagged `sealed` `Entity.fromJson` factory.
5. Extension methods — safe `at()`, `lerpTo`, `Duration.clock`; notes static dispatch and that they can't add state.
6. State machine as a pure `reduce(state, event) -> state` — full `sealed GameState` × `sealed GameEvent` switch over the `(state, event)` pair; side-effects-outside-the-reducer rule; `events.fold(...)` test one-liner.
7. Seeded deterministic `Random` (SplitMix64) — a `SeededRandom implements Random` using `BigInt` for exact 64-bit math (web-safe), drop-in for `shuffle`/`nextInt`, with an injection example and a golden test pinning the sequence.
8. Small value type `Vec2` for the model (value equality via `Object.hash`), converted to `Offset`/Flame `Vector2` only at the renderer edge.
9. "Avoid these" list mirroring the Swift file's closing section.

Every section has tiny do/don't snippets, 2-space indent, `const` constructors, trailing commas, and no `package:flutter`/`package:flame` imports (pure-Dart core, VM-testable), matching the established voice of the sibling files.

## Grounding / API accuracy (verified, not invented)
- Context7 `/flame-engine/flame`: confirmed `FlameGame`, `PositionComponent` + `render(Canvas)`, the modern `HasGameReference<T>` mixin (with `game` accessor) and `CollisionCallbacks` (`onCollision`/`onCollisionEnd`), and that Flame exposes a replaceable `Random` for seeded determinism. These names are referenced for cross-file consistency; the doc itself stays framework-free.
- dart.dev/language/patterns: switch expressions, sealed-class exhaustiveness, record/object patterns, `if-case` — used as written.
- `dart:math` `Random` (api.dart.dev): confirmed the interface is `nextInt`/`nextDouble`/`nextBool` and is *implementable* by a custom class — so `SeededRandom implements Random` is correct and injectable.

## Cross-references
The file links forward to `dart-flame-mastery.md` (Flame's mutable `Vector2`) and relies on `dart-language-essentials.md` for sealed/switch basics, matching the names in `dart/README.md`. Note: `README.md` lists `dart-sealed-pattern-matching.md`, `dart-flutter-mastery.md`, and `dart-flame-mastery.md`, none of which exist on disk yet — they appear to be planned siblings, so my forward references use the README's naming.

## Commands run + real output
- `mcp query-docs /flame-engine/flame` (x2) — returned current Flame component/collision/HasGameReference examples.
- `WebFetch` dart.dev patterns page and api.dart.dev `Random` — confirmed syntax and the implementable `Random` interface.
- `which dart` → "dart not found" (`NO_DART_TOOLCHAIN`).

## Honest verification status
No Dart toolchain is installed in this environment, so I could NOT run `dart format`, `dart analyze --fatal-infos --fatal-warnings`, or `dart test` to mechanically confirm the snippets are analyzer-clean and correctly formatted. Snippets were reviewed by hand for Dart 3 syntax and against the cited docs. Recommended before handoff, on a machine with the Dart SDK: drop the larger snippets (SeededRandom, the reducer, the SaveData migration, copyWith sentinel) into a scratch package and run `dart analyze --fatal-infos --fatal-warnings` + `dart format --output=none --set-exit-if-changed .`.

## Open risks / next steps
- `SeededRandom` uses `BigInt` for exactness on web (JS doubles are 53-bit); this is correct but slower than native 64-bit int math. If the skill targets native-only and per-frame RNG throughput matters, a separate fast `int`-based variant could be offered — flagged, not added, to avoid web-platform truncation bugs.
- The doc says the skill "ships `assets/seeded_random.dart`" (consistent with README line 35), but no such asset file exists under the dart skill yet. Creating `assets/seeded_random.dart` containing the `SeededRandom` class is a sensible follow-up so the reference and the shipped asset stay in sync.
- After editing, the canonical→tool-copy sync still needs running (`.agents/skills/.../scripts/sync-skill.sh`) per CLAUDE.md, if/when the dart skill has a sync script.