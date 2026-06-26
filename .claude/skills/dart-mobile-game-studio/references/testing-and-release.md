# Testing & release

How to test a Flutter/Dart mobile game and prepare an honest dual-store release
checklist. Same doctrine as the Swift skill: test the **pure Dart core** first and
hardest, keep the renderer thin, and never claim a build or a store outcome you
didn't actually produce.

## What to test (priority order)

1. **Pure model rules** — highest value, cheapest to run. Legal moves, scoring,
   win/lose, state-machine transitions (`menu → playing → paused → win/lose →
   menu`), level loading/decoding. Pure Dart, no `package:flutter` import, runs on
   the Dart VM in milliseconds with `dart test` — no device or emulator.
2. **Systems** — spawn logic, collision verdicts, save/load round-trips, difficulty
   ramps. Still pure Dart where you kept it pure.
3. **Determinism** — the injected seeded `Random` (ships as `assets/seeded_random.dart`)
   produces reproducible shuffles/spawns: same seed ⇒ same sequence.
4. **Widget / Flame layer (light)** — only the load-bearing bits: a tap routes to the
   right model call, the HUD shows the model's score, a Flame component reacts to a
   collision. Avoid brittle full-screen snapshots for an MVP; prefer one or two
   goldens of stable, text-free visuals.

The split is the whole point: because the core has **no `package:flutter` import**, it
runs under `dart test` on the VM (fast, headless). Only the thin renderer needs
`flutter_test`.

## Layer 1 — pure model with `dart test` (VM, fast)

`package:test` is the engine; `dart test` is the runner for non-Flutter code. Test
files live in `test/`, end in `_test.dart`.

```dart
// test/board_test.dart
import 'package:test/test.dart';
import 'package:my_game/model/board.dart';
import 'package:my_game/model/seeded_random.dart';

void main() {
  group('Board rules', () {
    test('matched pair stays face up', () {
      final board = Board(random: SeededRandom(42));
      board.flip(0);
      board.flip(board.indexOfMatch(0));
      expect(
        board.cards.every((c) => !c.isFaceUp || c.isMatched),
        isTrue,
      );
    });

    test('win when all matched', () {
      final board = Board(random: SeededRandom(1))..matchAllForTesting();
      expect(board.isWin, isTrue);
    });
  });

  test('seeded RNG is deterministic', () {
    int rolls(int seed) =>
        List.generate(5, (_) => SeededRandom(seed).nextInt(100)).first;
    expect(rolls(7), equals(rolls(7))); // same seed ⇒ same sequence
  });
}
```

Run:

```bash
dart test                          # all VM tests
dart test test/board_test.dart     # one file
dart test -n 'win when all matched'  # by name (substring/regex)
dart test --coverage=coverage      # emit coverage data
```

> If the core unavoidably depends on Flutter (rare — usually it shouldn't), run those
> files with `flutter test` instead; `dart test` can't resolve `package:flutter`.

## Layer 2 — widget tests with `flutter_test` (`testWidgets`)

For Flutter-widget UI (menus, HUD, `CustomPainter` views, gesture handling). `flutter_test`
ships with the SDK. Same `test/` directory.

```dart
// test/hud_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:my_game/ui/game_hud.dart';

void main() {
  testWidgets('HUD shows score and Pause control', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: GameHud(score: 3, isPaused: false)),
    );

    expect(find.text('Score: 3'), findsOneWidget);
    expect(find.byTooltip('Pause'), findsOneWidget);

    await tester.tap(find.byIcon(Icons.pause));
    await tester.pumpAndSettle(); // drain animations/transitions

    expect(find.byIcon(Icons.play_arrow), findsOneWidget);
  });
}
```

Key APIs:
- `testWidgets(name, (tester) async {...})` — gives you a `WidgetTester`.
- `tester.pumpWidget(widget)` — mount; `tester.pump([Duration])` — render one frame /
  advance the clock; `tester.pumpAndSettle()` — pump until no frame is scheduled
  (animations done). `pumpAndSettle` **times out** on an infinite animation (e.g. a
  perpetual game loop) — use explicit `pump(Duration(...))` steps there instead.
- Finders: `find.text`, `find.byType`, `find.byKey`, `find.byIcon`, `find.byTooltip`,
  `find.bySemanticsLabel` (verifies your `Semantics` accessibility labels).
- Matchers: `findsOneWidget`, `findsNothing`, `findsNWidgets(n)`, `findsWidgets`.
- Interactions: `tester.tap`, `tester.enterText`, `tester.drag`, `tester.fling`.

Run:

```bash
flutter test                       # all flutter_test + VM tests under test/
flutter test test/hud_test.dart
flutter test --plain-name 'HUD shows score'
```

## Layer 3 — Flame component & game tests (`flame_test`)

For mode-2 (Flame) and mode-3 (hybrid) games, the `flame_test` package wraps a fully
initialized `FlameGame` so you can test components against a real game loop. Add as a
dev dependency:

```yaml
dev_dependencies:
  flutter_test:
    sdk: flutter
  flame_test: ^1.0.0   # pin to the version matching your `flame`
```

```dart
// test/player_test.dart
import 'package:flame/components.dart';
import 'package:flame_test/flame_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:my_game/game/player.dart';

void main() {
  // testWithFlameGame spins up a plain FlameGame for you.
  testWithFlameGame('player is added and falls under gravity', (game) async {
    final player = Player(position: Vector2(0, 0));
    await game.ensureAdd(player);          // add + await onLoad
    await game.ready();                     // process the add queue

    game.update(0.5);                       // advance the loop 0.5s
    expect(player.position.y, greaterThan(0));
    expect(player.position, closeToVector(Vector2(0, 1.225), 0.01));
  });
}
```

Use `testWithGame<MyGame>('...', MyGame.new, (game) async {...})` when you need your own
`FlameGame` subclass. `flame_test` provides Vector2 matchers like `closeToVector`. Drive
time with `game.update(dt)` (seconds), not wall-clock.

To test a Flame game mounted in the widget tree (hybrid mode), use `testWidgets` with a
`GameWidget` and pump frames — `pump()` is roughly one `update(0)`, and `pump(Duration)`
advances in-game time:

```dart
testWidgets('GameWidget mounts the game', (tester) async {
  final game = MyGame();
  await tester.pumpWidget(GameWidget(game: game));
  await tester.pump();                       // initialize
  await tester.pump(const Duration(milliseconds: 16)); // ~1 frame
  expect(game.isLoaded, isTrue);
});
```

## Golden tests (visual regression)

Goldens snapshot a widget's rendered pixels to a reference PNG. Good for a stable
sprite/board layout; **avoid text** (font rasterization differs across machines and
causes false diffs). For Flame, `flame_test` offers `testGolden`:

```dart
testGolden(
  'board renders in start position',
  (game) async {
    await game.ensureAdd(BoardComponent());
  },
  size: Vector2(300, 200),
  goldenFile: 'goldens/board_start.png',
);
```

For plain Flutter widgets, use `matchesGoldenFile`:

```dart
await expectLater(
  find.byType(BoardView),
  matchesGoldenFile('goldens/board_view.png'),
);
```

Generate/refresh references (review the diffs before committing them):

```bash
flutter test --update-goldens
```

CI tip: pin a font and disable shadows where you can, or keep goldens text-free, so they
don't flake across environments. Commit the reference PNGs.

## Integration tests (`integration_test`, on a device/emulator)

End-to-end on a real device or emulator — the full app, real frames. Add the SDK package
and put tests in a top-level `integration_test/` directory.

```yaml
dev_dependencies:
  integration_test:
    sdk: flutter
```

```dart
// integration_test/app_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:my_game/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('play one round to a win', (tester) async {
    app.main();
    await tester.pumpAndSettle();

    await tester.tap(find.text('Play'));
    await tester.pumpAndSettle();
    // ...drive the core loop...
    expect(find.text('You win!'), findsOneWidget);
  });
}
```

Run (needs an attached device or running emulator/simulator):

```bash
flutter test integration_test/app_test.dart
flutter devices                    # confirm a target exists first
```

`integration_test` reuses `flutter_test` APIs but **cannot** drive native OS UI
(permission dialogs, the share sheet). If you must, the third-party `patrol` package
extends it — note this is an extra dependency to justify under the skill's minimal-deps
rule.

## Static analysis & formatting (run before any test claim)

```bash
dart format .                      # 2-space indent; --set-exit-if-changed in CI
dart analyze                       # analyzer-clean against your lint set
flutter analyze                    # same, with Flutter-aware rules
```

Configure lints in `analysis_options.yaml` (e.g. `include: package:very_good_analysis/analysis_options.yaml`
or `package:flutter_lints/flutter.yaml`). The bar: `dart format` produces no diff and
`dart analyze` reports zero issues before you call anything done.

## Honesty rule

**Only claim a build, a test run, or analysis passed if you actually ran it and saw the
output.** If there's no Flutter toolchain, no device, or no project here, say "not
built/tested in this environment" and hand over the exact commands above. Quote the real
command output in the handoff — pass/fail counts, analyzer summary, build artifact paths.

## Building release artifacts

Versioning is one line in `pubspec.yaml`: `version: 1.0.0+1` → name `1.0.0`, build `1`.
Maps to Android `versionName`/`versionCode` and iOS `CFBundleShortVersionString`/build.
Override per build with `--build-name=` / `--build-number=`. **Bump the build number on
every upload to either store** — both reject a re-used build for the same version.

```bash
# Android
flutter build apk --release              # fat APK (sideload/test)
flutter build apk --split-per-abi        # smaller per-ABI APKs
flutter build appbundle                  # .aab — required for Play upload
#   → build/app/outputs/bundle/release/app-release.aab

# iOS (needs macOS + Xcode + Apple Developer account)
flutter build ipa                        # archive + .ipa for App Store
#   → build/ios/ipa/*.ipa
flutter build ipa --export-options-plist=ExportOptions.plist
```

- **App IDs:** Android `applicationId` in `android/app/build.gradle(.kts)`; iOS Bundle
  Identifier in Xcode (`ios/Runner.xcworkspace`). Set both away from `com.example.*`.
- **Signing:** Android needs an upload keystore referenced via `android/key.properties`
  (`keytool -genkey -v -keystore ... -alias upload`); iOS uses Xcode automatic signing
  with your Team. Keep keystores/keys out of git.
- **Icons & splash:** the `flutter_launcher_icons` and `flutter_native_splash` dev
  packages generate per-platform assets from a single source image; or set them by hand
  (`mipmap-*` + `AndroidManifest.xml` on Android, `Assets.xcassets` on iOS). Provide a
  1024×1024 master icon with **no alpha** for App Store.
- **Upload:** Play → upload the `.aab` in Play Console (internal testing track first).
  App Store → Transporter app or `xcrun altool --upload-app --type ios -f build/ios/ipa/*.ipa
  --apiKey <id> --apiIssuer <id>`, then TestFlight before review.

## Dual-store privacy & compliance forms

You must complete **both** privacy declarations, and they must match what the app
actually does. For a privacy-first kids game the truthful answer is almost always
"no data collected."

- **Apple — Privacy Nutrition Label** (App Store Connect → App Privacy): declare data
  collection per category. An offline game with no tracking/analytics/accounts should be
  **"Data Not Collected."** Also ship an accurate `ios/Runner/PrivacyInfo.xcprivacy`
  privacy manifest (and declare reasons for any required-reason APIs you use).
- **Google Play — Data safety form** (Play Console → App content): independently declare
  data collected/shared and security practices. Must agree with the Apple label and the
  actual code — Play audits this.
- **Age rating:** Apple sets it from a questionnaire in App Store Connect. Google Play
  uses the **IARC** questionnaire to issue regional ratings. Answer honestly; a kids
  game lands in the lowest brackets only if it really has no objectionable content.

## Kids / Families program checklist

Privacy-first kids safety spans **both** Apple's Kids Category and Google Play's
**Designed for Families** / Families policies. If you opt in, the bar is strict and the
code must back up every declaration:

- [ ] **No tracking, ads, or analytics.** No third-party SDKs that collect data.
- [ ] **No advertising identifiers** — do not read IDFA (`ATTrackingManager`) or GAID
      (`AdvertisingIdClient`). For Families on Play, the Advertising ID permission must
      be **absent** from the merged `AndroidManifest.xml`.
- [ ] **No accounts, sign-in, or personal data** collected. Offline-first.
- [ ] **No external links** out of the app (web, store, social) without a verified
      parental gate; no dark patterns or manipulative purchase nudges.
- [ ] iOS **Kids Category** band (5 & under / 6–8 / 9–11) selected; no third-party
      analytics/ads per Apple's Kids rules; parental gate on any sensitive action.
- [ ] Play **target audience = children**; complete the Families policy declarations;
      use a Families-approved ads/SDK posture (ideally none).
- [ ] Accessibility: `Semantics(label:/value:/...)` on every interactive control;
      respects large text and reduced-motion settings.

## Manual QA pass (before calling it done)

- Launch; play the core loop start → finish; reach **win** and (if any) **lose**.
- Rotate the device; check phone and tablet sizes and safe-area insets (notch / cutout /
  gesture bar).
- Background then foreground mid-game: state preserved, no `dt` spike on resume, audio
  pauses/resumes.
- Screen reader on (VoiceOver / TalkBack): can you navigate and play? Reduced-motion on:
  no jarring animation.
- Restart/replay works; any persistence survives a cold relaunch.
- Run on **both** an iOS device/simulator and an Android device/emulator — layout, fonts,
  and back-button behavior differ.

## Release checklist (honest, not a guarantee)

- [ ] `dart format` clean, `dart analyze`/`flutter analyze` zero issues.
- [ ] All `dart test` and `flutter test` green; build numbers bumped.
- [ ] Adaptive launcher icon + splash for both platforms; 1024² App Store icon, no alpha.
- [ ] App IDs set off `com.example.*`; Android signing + iOS signing configured.
- [ ] Supported orientations/devices set; min SDK / deployment target set.
- [ ] Apple Privacy Nutrition Label **and** Play Data safety form completed and
      consistent; `PrivacyInfo.xcprivacy` accurate.
- [ ] Age rating questionnaires (Apple + IARC) answered honestly.
- [ ] Kids/Families checklist above satisfied if targeting children.
- [ ] No debug logging, placeholder text, or copyrighted assets shipped.
- [ ] `flutter build appbundle` and `flutter build ipa` succeed and run on real devices.
- [ ] Store screenshots prepared for required device sizes.

**Never assert guaranteed App Store / Google Play / COPPA / Kids approval.** Provide this
checklist plus a risk list and recommend verifying against the current App Store Review
Guidelines, Google Play Families policies, and each store's data-disclosure requirements.
