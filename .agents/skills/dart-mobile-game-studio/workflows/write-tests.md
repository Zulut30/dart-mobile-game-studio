# Workflow: Write Tests

**Goal:** Build a layered test suite — pure-Dart model (`dart test`), widgets/golden (`flutter_test`), Flame components (`flame_test`), and Patrol E2E for native flows — all deterministic, analyzer-clean, formatted.

## When to use
- After the model + at least one screen exist (run alongside or right after `implement-game.md`).
- Any time you add a rule, scoring change, state transition, system, or screen — tests are not a one-shot phase; extend them with the feature.
- Before any release gate (see `checklists/testing.md`, `release-policy.md`).

## Prerequisites
- Pure-Dart core lives in `lib/game/` (or a `core` package) with **no `package:flutter` import** — verify before starting (a Flutter import forces every model test into the slow `flutter test` VM). Grep: `grep -rL "package:flutter" lib/game/`.
- All randomness flows through an injected `Random` (constructor param, defaulting to `Random()`), never a top-level `Random()` call. See `assets/seeded_random.dart`.
- `dev_dependencies` in `pubspec.yaml`: `test`, `flutter_test` (sdk), `flame_test` (match your `flame` major), and — only if doing E2E — `patrol` + `integration_test` (sdk). Justify `patrol` per `package-policy.md` (E2E of native permission/lifecycle flows; the only dep that earns its weight here).

## The test pyramid (write in this order, most tests at the bottom)
1. **Pure-Dart model** (`dart test`) — fast, the bulk of coverage: moves, scoring, win/lose, transitions, determinism.
2. **Flame component** (`flame_test`) — only if using Flame: component lifecycle, collisions, dt-driven behavior.
3. **Widget + golden** (`flutter_test`) — screens render, taps wire to logic, pixel snapshots.
4. **Patrol E2E** (`patrol test`) — a thin top: 1–3 native happy-path flows. Cross-link `testing-e2e-patrol.md`.

---

## STEP 1 — Layout & naming
- Mirror `lib/` under `test/`; suffix every file `_test.dart` (the runners only pick up `*_test.dart`).
  ```
  test/
    game/        # pure-Dart model tests -> dart test
    components/  # flame_test
    widgets/     # flutter_test
    goldens/     # golden tests + _goldens/*.png
  integration_test/   # Patrol E2E (NOT under test/)
  ```
- One `void main()` per file; group by unit with `group(...)`.

## STEP 2 — Pure-Dart model tests (`dart test`) — do these first, they are the core
Import `package:test/test.dart` only. If a test file here pulls in `flutter_test`, it can no longer run under `dart test` — keep them separate.

Cover, per `checklists/testing.md`:
- **Moves / rules:** every legal move mutates state correctly; every illegal move is rejected and leaves state unchanged.
- **Scoring:** points awarded/penalized exactly; boundaries (0, max, overflow clamp).
- **Win / lose:** the precise condition flips `status` to win and to lose — and does NOT flip one move early/late.
- **Transitions:** the state machine `menu → playing → paused → won/lost → menu` (see `references/flutter-game-architecture`); assert illegal transitions are no-ops/throw.
- **Determinism:** same seed ⇒ identical sequence; different seed ⇒ different (usually).

```dart
import 'package:test/test.dart';
import 'package:my_game/game/game_state.dart';
import 'dart:math';

void main() {
  group('GameState moves', () {
    late GameState state;
    setUp(() => state = GameState.initial(random: Random(42)));

    test('legal move updates board and score', () {
      final next = state.applyMove(const Move(row: 0, col: 1));
      expect(next.score, equals(10));
      expect(next.status, equals(GameStatus.playing));
    });

    test('illegal move leaves state unchanged', () {
      final next = state.applyMove(const Move(row: -1, col: 0));
      expect(next, equals(state)); // requires value equality (==/hashCode)
    });

    test('win condition flips status exactly once', () {
      final won = state.copyWith(score: 99).applyMove(scoringMove);
      expect(won.status, equals(GameStatus.won));
    });
  });

  group('determinism', () {
    test('same seed => identical spawn sequence', () {
      List<int> run(int seed) =>
          List.generate(20, (_) => GameState.initial(random: Random(seed)).spawn());
      expect(run(7), equals(run(7)));
      expect(run(7), isNot(equals(run(8))));
    });
  });
}
```
Matchers you'll lean on: `equals`, `isTrue`/`isFalse`, `isA<T>()`, `throwsA(isA<StateError>())`, `contains`, `closeTo(x, 1e-9)` for doubles (never `equals` on a `double`).

**dt clamping:** if the model has a `tick(double dt)`, test it directly — feed a huge `dt` (e.g. a frame drop) and assert it's clamped, plus `dt == 0` is a no-op. This is the cheapest place to prove dt safety; don't rely on the widget layer for it.

Run: `dart test` (sub-second; this is your inner loop).

## STEP 3 — Flame component tests (`flame_test`) — only if using Flame
Use `testWithGame` / `testWithFlameGame` from `flame_test` — they build and dispose the game for you. `game.ready()` waits for queued component mounts; advance time with `game.update(dt)`.
```dart
import 'package:flame_test/flame_test.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWithGame<MyGame>('player mounts and falls under gravity', MyGame.new,
      (game) async {
    final player = Player();
    game.add(player);
    await game.ready();            // wait for the add to mount
    final y0 = player.position.y;
    game.update(0.016);           // one ~60fps frame
    expect(player.position.y, greaterThan(y0));
  });
}
```
Use `testWithFlameGame('name', (game) async {...})` for a plain `FlameGame`. Keep these few — push gravity/collision math into the pure model and test it in STEP 2 where it's faster.

## STEP 4 — Widget tests (`flutter_test`)
Import `package:flutter_test/flutter_test.dart`; run with `flutter test`. `testWidgets` provides a `WidgetTester`.
- `pumpWidget(widget)` mounts; `pump([duration])` rebuilds/advances one frame; `pumpAndSettle()` runs until animations finish (never call it on an infinite animation — it times out).
- Finders: `find.text`, `find.byType`, `find.byKey(const ValueKey('start'))`, `find.byIcon`.
- Matchers: `findsOneWidget`, `findsNothing`, `findsNWidgets(n)`, `findsWidgets`.
- Actions: `tester.tap`, `tester.enterText`, `tester.drag`.
```dart
testWidgets('tapping Start moves menu -> playing', (tester) async {
  await tester.pumpWidget(const MaterialApp(home: MenuScreen()));
  expect(find.text('Start'), findsOneWidget);
  await tester.tap(find.byKey(const ValueKey('start')));
  await tester.pumpAndSettle();
  expect(find.byType(GameScreen), findsOneWidget);
});
```
For a Flame `GameWidget`, mount it and pump twice to finish init, then pump a `Duration` to advance in-game time:
```dart
testWidgets('game widget initializes', (tester) async {
  final game = MyGame(random: Random(1));
  await tester.pumpWidget(GameWidget(game: game));
  await tester.pump();                          // build
  await tester.pump();                          // init complete
  await tester.pump(const Duration(milliseconds: 20)); // advance 20ms
  expect(game.children.whereType<Player>(), isNotEmpty);
});
```
Test the **wiring** (tap → state change → UI updates), not the rules again — rules are already covered in STEP 2.

## STEP 5 — Golden tests
Two flavors — pick by layer:
- **Flame:** `testGolden` from `flame_test`, with a fixed `size:` and `goldenFile:`.
  ```dart
  testGolden('board renders', (game) async { game.add(Board()); },
      size: Vector2(300, 200), goldenFile: '_goldens/board.png');
  ```
- **Widget:** `flutter_test`'s `expectLater(find.byType(X), matchesGoldenFile('_goldens/x.png'))`.

Rules for stable goldens:
- **Avoid text in goldens** — font rendering differs across machines/CI and causes flaky diffs (Flame docs call this out explicitly). Snapshot shapes/sprites; assert text with finders instead.
- Inject a fixed seed so procedural layouts are reproducible.
- Generate/update baselines deliberately: `flutter test --update-goldens`, then **review the PNG diff** before committing. Never blind-update.
- Commit `_goldens/*.png`; treat unexpected diffs as failures, not noise.

## STEP 6 — Patrol E2E (native flows)
Thin top of the pyramid — 1–3 flows that genuinely need native UI: permission dialogs, app backgrounding/resume, launch-to-play. Everything else stays in widget tests (faster, no device). Full setup in `testing-e2e-patrol.md`.

- Tests live in `integration_test/` and use `patrolTest`; the `$` tester wraps `flutter_test`.
- Finders: `$(Type)`, `$(#key)`, chained `$(Scaffold).$('Play')`; `.tap()`, `.enterText()`.
- Native ops via `$.native` (current API: `$.native.tap(...)`, `$.native.grantPermissionWhenInUse()`, `$.native.pressHome()` / app-lifecycle). Confirm the exact method names against your installed `patrol` version's API docs before writing — the native surface changes between majors.
```dart
import 'package:patrol/patrol.dart';

void main() {
  patrolTest('launch to first move', ($) async {
    await $.pumpWidgetAndSettle(const MyApp());
    await $(#start).tap();
    expect($(GameScreen), findsOneWidget);
    await $.native.pressHome();   // background
    // resume + assert state persists ...
  });
}
```
Run on a booted simulator/emulator or device:
- `patrol test` — CI/headless run.
- `patrol develop` — hot-restart loop while authoring.
Requires `patrol_cli` (`dart pub global activate patrol_cli`) and the native bootstrap (`patrol bootstrap` / config block in `pubspec.yaml`). Do NOT run E2E on the dart-test fast loop — keep it a separate CI job.

## STEP 7 — Format, analyze, run all
```bash
dart format .                 # 2-space, enforce in CI with --set-exit-if-changed
dart analyze                  # must be clean — zero warnings/infos
dart test                     # pure model (fast, run constantly)
flutter test                  # widgets + goldens + flame_test
patrol test                   # E2E (separate CI job, on a device)
```
Wire these into CI per `testing-and-release` / `release-policy.md`. Gate merges on the first four; E2E can be a slower required check.

---

## Done when
- Model coverage: every move/score/win/lose/transition rule has a passing `dart test`, including illegal-input and boundary cases.
- A determinism test proves same-seed reproducibility.
- Each screen has a widget test asserting render + one interaction wiring to a state change.
- At least one golden per distinct visual state, baselines reviewed and committed, no text in goldens.
- 1–3 Patrol flows cover the native happy paths that matter.
- `dart format` is a no-op, `dart analyze` is clean, and every suite is green locally and in CI.
- `checklists/testing.md` fully ticked.

## Common pitfalls
- **Flutter import in the model** → model tests can't run under `dart test`; they get dragged into the slow Flutter VM. Keep `lib/game/` Flutter-free.
- **Un-injected `Random`** → flaky, unreproducible tests. Inject a seeded `Random` everywhere (`assets/seeded_random.dart`).
- **`equals` on doubles** → use `closeTo(value, epsilon)`.
- **Text in golden files** → cross-machine font diffs make them flaky; snapshot graphics only.
- **`pumpAndSettle` on a looping animation/game loop** → hangs until timeout; use timed `pump(Duration(...))` instead.
- **Too few `pump()`s after mounting a `GameWidget`** → assertions run before init; pump twice, then pump a `Duration` to advance game time.
- **Asserting on equality without `==`/`hashCode`** → "unchanged state" checks silently pass/fail by identity; give model types value equality.
- **Blind `--update-goldens`** → bakes a regression into the baseline. Always diff the PNG before committing.
- **Running E2E on every save** → slow and device-bound; keep Patrol in its own CI job, iterate the model with `dart test`.
