# Dart code-quality checklist

A tick-list a reviewer or agent runs over changed Dart before calling it done. Each item is
verifiable from the diff or from one command. Derived from `references/dart/*` (the Dart quality
bar) and the toolkit/testing references — see those for the *why*. Two commands back most of this:

```bash
dart format --output=none --set-exit-if-changed .   # no diff
dart analyze --fatal-infos --fatal-warnings         # zero issues
```

## Tooling gates (run these first)

- [ ] `dart format --output=none --set-exit-if-changed .` produces **no diff** (2-space indent).
- [ ] `dart analyze --fatal-infos --fatal-warnings` reports **zero issues** — infos and warnings
      fail, not just errors.
- [ ] `analysis_options.yaml` includes a strong lint set (`very_good_analysis`, or `flutter_lints`
      as the lighter floor) with `strict-casts` / `strict-inference` / `strict-raw-types` on.
- [ ] No `// ignore:` / `// ignore_for_file:` added without a one-line justification comment.
- [ ] `dart test` passes for the pure-Dart core (see layer separation below).

## Null-safety & external data

- [ ] No `!` (null-assertion) on data you don't control — `jsonDecode` output, `SharedPreferences`,
      asset bundles, sensors, gestures, map lookups. `!` is allowed only on an invariant the local
      code guarantees.
- [ ] External shapes are validated before use: `if (json case {'rows': final int rows, ...})`, or
      `(x as T?) ?? fallback` — never a bare `x['k']! as T` (throws twice: on null and on wrong type).
- [ ] No blind `as` cast on `dynamic`/untrusted input without a preceding `is` check or `as T?` + `??`.
- [ ] Nullable handled deliberately: `?`, `??`, `?.`, `??=`, `if (x != null)` promotion, or a `case`
      pattern — not ignored.
- [ ] No `.first` / `.single` / `list[i]` / `values.byName(s)` on unproven input; use
      `firstWhereOrNull`, an `isNotEmpty`/bounds guard, or catch the throw at the boundary.

## Immutability & const

- [ ] Model/value types are immutable: `final` fields + `const` constructor; edits via `copyWith`,
      not in-place mutation.
- [ ] Value types override `==` **and** `hashCode` together (via `Object.hash` / `Object.hashAll`),
      or are a `record` — so they compare by value, not identity. No hand-rolled prime-multiply hash.
- [ ] `const` used wherever it compiles (constructors, literals, fixed config); `prefer_const_*`
      lints clean.
- [ ] `final` by default for locals/fields; `var` only where genuinely reassigned.
- [ ] Public surface doesn't leak mutable internals — return `UnmodifiableListView`/a copy, not the
      private list.
- [ ] Illegal states made unrepresentable: `enum` / `sealed` over contradictory boolean flags;
      `final class` for model types not meant to be subclassed outside their library.

## Layer separation (the core stays pure)

- [ ] No `import 'package:flutter/...'` **and** no `import 'package:flame/...'` anywhere under
      `lib/models/` or `lib/systems/` — grep the diff to confirm.
- [ ] Game rules / state machine are plain Dart, synchronous, and run under `dart test` on the VM
      (no widget pump, no device).
- [ ] State machine modelled as a `sealed` type with an **exhaustive** `switch` expression and **no**
      `default` — adding a state must fail to compile until handled.
- [ ] Randomness comes from an injected seeded `Random` (`assets/seeded_random.dart`); no bare
      `Random()` or `DateTime.now()` inside game logic.
- [ ] I/O lives at the edge (`systems/`) behind a plain interface; the model never reaches for files,
      prefs, or the network directly.

## Naming (Effective Dart)

- [ ] Types / enums / extensions / mixins `UpperCamelCase`; members / vars / params `lowerCamelCase`;
      files & dirs `snake_case.dart`; constants `lowerCamelCase` (not `SCREAMING_CAPS`).
- [ ] Booleans are positive assertions — `isMatched`, `hasWon`, `canAcceptInput` — no `get` prefix,
      no double negatives.
- [ ] Side-effecting methods are imperative verbs (`flip`, `reset`); value-returning members are
      nouns (`score`, `legalMoves`) — no `getScore()`.
- [ ] Library-private members carry a leading `_`; default to private, widen only when another file
      needs it.
- [ ] Acronyms ≥3 letters read as words (`HttpClient`, not `HTTPClient`); descriptive noun last
      (`pageCount`, not `numPages`).

## Error handling

- [ ] `Exception` (recoverable, often I/O — bad level file) is thrown and **caught**; `Error`
      (programmer bug — `StateError`, `RangeError`, failed `assert`) is **not** caught to limp along.
- [ ] Ordinary branch-y outcomes in hot logic (illegal move, out-of-bounds tap) return a `sealed`
      `Result`, not an exception.
- [ ] No sentinel signalling — failure/absence is a typed throw or a nullable return, never `-1`,
      `''`, or `Duration.zero`; no nullable `Future`/`Stream`/collection returns (use empty).
- [ ] Catches are narrowed with `on Type`; `catch (e, s)` only when the stack is used. No bare
      `catch (_)` that swallows everything.
- [ ] Propagate-after-acting uses `rethrow`, never `throw e` (which loses the original stack trace).
- [ ] No un-awaited `Future` that can fail; await it, or mark fire-and-forget with `unawaited(...)`.

## Dispose / lifecycle

- [ ] Every `AnimationController`, `Ticker`, `ValueNotifier`/`ChangeNotifier`, `StreamSubscription`,
      `FocusNode`, `TextEditingController`, `ScrollController` is torn down — `dispose()` /
      `cancel()` in `State.dispose` (with `super.dispose()` last), Flame components in `onRemove()`.
- [ ] Timers and subscriptions are cancelled; pooled objects reset stale fields on reuse.
- [ ] Static screens (menu/pause/win) `pauseEngine()` (Flame) / stop tickers rather than leaking a
      running loop.

## No `print` in the play path

- [ ] No `print(...)` in shipped code (`avoid_print` lint clean). Use the `logging` package
      (`Logger`) or `dart:developer log`, or guard behind `kDebugMode` / `bool.fromEnvironment`.
- [ ] No logging on the per-frame path (`build`, `update`, `render`, gesture callbacks) — it
      allocates and janks frames.
- [ ] Logging stays on-device: console / `debugPrint` sink only; **no** remote log listener
      (Crashlytics/Sentry) — kids-safety requires no off-device telemetry.

## Docs & final read

- [ ] `///` dartdoc on every public type/member/constructor states the **contract** (when it throws,
      what `null` means) — not a restatement of the code.
- [ ] One responsibility per type/file; files small and focused.
- [ ] No commented-out code, leftover `TODO`/`FIXME` without an owner, or debug scaffolding left in.
