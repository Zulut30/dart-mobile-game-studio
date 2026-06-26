# E2E testing with Patrol

The top of the test pyramid: end-to-end suites that drive the **real app on a real
device/emulator**, including the **native OS UI** that `integration_test` alone cannot
touch — permission dialogs, the notification shade, system alerts, app lifecycle, and
WebViews. This module complements [`references/testing-and-release.md`](testing-and-release.md),
which owns the lower layers (pure-Dart `dart test`, `flutter_test` widget tests, Flame
`flame_test`, goldens, and the plain `integration_test` setup). **Read that first** — this
file does not repeat the basics; it cross-links them and picks up where `integration_test`'s
sandbox ends.

Verified against [`github.com/leancodepl/patrol`](https://github.com/leancodepl/patrol),
the docs at [patrol.leancode.co](https://patrol.leancode.co/documentation), and the Flutter
[`integration_test`](https://docs.flutter.dev/testing/integration-tests) package on
2026-06-26. Patrol moves fast and has breaking renames between majors (see the API-drift
note in §3) — **re-check `pubspec.yaml` pins and the current API reference before quoting
versions or method names.**

---

## 1. The pyramid for a game (where each layer lives)

Fast and cheap at the bottom; slow, device-bound, and few at the top. Most of your value
is in the bottom two layers — keep the top deliberately thin.

| Layer | Tool | Runs on | What it covers | Module |
| --- | --- | --- | --- | --- |
| **Unit** | `dart test` | Dart VM (headless, ms) | Pure model: rules, scoring, win/lose, state machine, level decode, seeded-RNG determinism. **No `package:flutter` import.** | testing-and-release §Layer 1 |
| **Widget** | `flutter_test` | VM + flutter test harness | Thin renderer: a tap routes to the right model call, HUD reflects model score, gestures. | testing-and-release §Layer 2 |
| **Component** | `flame_test` | VM | Flame components against a real game loop (`game.update(dt)`). | testing-and-release §Layer 3 |
| **Golden** | `flutter_test` / `flame_test` | VM | Visual regression on stable, **text-free** visuals. | testing-and-release §Golden |
| **Integration** | `integration_test` | **device/emulator** | Full app, real frames, in-Flutter flows — but stuck inside the Flutter view. | testing-and-release §Integration |
| **E2E (native)** | **Patrol** | **device/emulator** | Everything `integration_test` can do **plus native OS UI**: permission dialogs, notifications, system alerts, lifecycle, WebViews, settings. | **this file** |

Rule of thumb for a small 2D game: dozens of unit tests, a handful of widget/Flame tests,
1–2 goldens, and **a small set of E2E smoke/regression flows** (§5). Do not try to assert
gameplay correctness through the slow E2E layer — assert it in pure Dart and use E2E only to
prove the wiring and the native touchpoints work on real hardware.

> **Honesty rule (carries over from testing-and-release):** every layer at "Integration" and
> above **requires an attached device, emulator, or simulator** — there is no headless path.
> Only claim an E2E run passed if you launched it and saw the native runner's pass/fail
> output. With no device/toolchain here, say "not run in this environment" and hand over the
> exact commands.

---

## 2. Why Patrol — the gap `integration_test` cannot cross

Flutter's `integration_test` reuses the `flutter_test` finders and `WidgetTester`, so it can
only see and drive widgets **inside your Flutter view**. The moment the OS draws something —
an iOS "Allow notifications?" alert, the Android runtime-permission dialog, the pull-down
notification shade, a Google/WebView sign-in page, the app switcher — `integration_test` is
blind and the test wedges. From the Patrol README:

> Flutter's default integration_test package can't interact with the OS your Flutter app is
> running on. This makes it impossible to test critical business features like granting
> runtime permissions, signing into apps through WebView or Google Services, tapping on
> notifications, and more. Patrol's native automation feature solves these problems.

Patrol wraps `integration_test` and adds a **native automation server** driven over the
platform's own UI-automation stack (UIAutomator on Android, XCUITest on iOS). Your Dart test
calls into it through `$.platform.mobile.*`, so a single test can tap a Flutter button, then
grant a system permission, then read a notification — crossing the Flutter/native boundary in
one flow. It builds and runs the test **as a native instrumentation test** (`./gradlew`
connected-Android test on Android, `xcodebuild` UI test on iOS), which is also what makes it
run on device farms (Firebase Test Lab, etc.).

What this unlocks for a game specifically:
- **Permission dialogs** — notifications (reminders/streaks), camera/photos (avatar capture),
  location, ATT/IDFA prompt. A kids build should request **none** of these; an E2E test is
  how you *prove* no native permission prompt appears (a negative assertion — see §5.10).
- **Notifications** — a "come back and play" local notification: open the shade, find it, tap
  it, assert deep-link into the game.
- **App lifecycle** — home/recents/back, then foreground: assert state preserved and no `dt`
  spike on resume (the lifecycle clamp from flutter-game-architecture / performance-checklist).
- **WebViews / system alerts** — a parental-gate web page, an external link confirmation, or a
  store/consent sheet rendered natively.

---

## 3. Setup (`patrol` + `patrol_cli`)

Two pieces: the **`patrol` package** (the Dart API your tests import) and the **`patrol_cli`**
(the runner that builds the native instrumentation harness and orchestrates the run). Plain
`flutter test integration_test/...` will **not** drive the native side — you must run through
`patrol test` / `patrol develop`.

> **Justify the dependency.** Per [`references/package-policy.md`](package-policy.md), Patrol
> is a **mature community** package, not official Apple/Google/Flutter — add it **`dev`-only**
> (it must never ship in the release binary) and only when you actually have native
> touchpoints to test. For a fully offline game with zero permissions, the negative-assertion
> smoke test (§5.10) may be the *only* thing Patrol buys you; weigh that before adopting it.

**1. Add the dev dependency** (`dev_dependencies`, never `dependencies`):

```bash
dart pub add patrol --dev
```

```yaml
# pubspec.yaml
dev_dependencies:
  flutter_test:
    sdk: flutter
  integration_test:
    sdk: flutter
  patrol: ^3.0.0          # re-check the current major before pinning
```

**2. Configure the native identifiers** in a top-level `patrol:` section of `pubspec.yaml`.
Patrol needs your real package name / bundle id to build the native test host:

```yaml
# pubspec.yaml
patrol:
  app_name: My Game
  android:
    package_name: com.example.mygame      # == applicationId
  ios:
    bundle_id: com.example.MyGame         # == PRODUCT_BUNDLE_IDENTIFIER
```

**3. Install the CLI** (separate from the package; manages the native runner):

```bash
dart pub global activate patrol_cli
patrol --version
patrol doctor            # verifies Android SDK / Xcode wiring before you waste a build
```

**4. Bootstrap the native test harness.** Patrol tests live in a dedicated test directory —
historically **`integration_test/`** (same place as plain integration tests), but the default has
moved across Patrol majors (newer `patrol_cli` versions scaffold/expect **`patrol_test/`**).
**Confirm your version's convention** with `patrol test --help` / the current `patrol_cli` docs and
use that directory consistently in `--target` below; the examples here use `integration_test/`. The
CLI generates/uses a native test entry on each platform that loads the Dart tests:

- **Android** — an instrumented test (a `*Test.kt`/`*Test.java` under
  `android/app/src/androidTest/...`) that runs your Dart suite as a connected-Android test via
  Gradle. `patrol test` invokes Gradle for you.
- **iOS** — a UI-testing target (`RunnerUITests`) in the Xcode project that `patrol test`
  drives via `xcodebuild`. You add the UITest target once in Xcode.

Follow the current [native setup guide](https://patrol.leancode.co/documentation) step by step
the first time — the exact generated files differ by Patrol major and are not worth memorizing.
After the one-time native setup, day-to-day work is **all in Dart** under `integration_test/`.

> **API drift — read before copying old snippets.** Patrol renamed core symbols across majors:
> - **v3**: the `nativeAutomation` and `bindingType` params were **removed** from
>   `patrolTest()`. `patrolTest()` now **implies** native automation; use **`patrolWidgetTest()`**
>   for a no-native widget test. `PatrolTester` was split — `PatrolIntegrationTester` is the `$`
>   type inside `patrolTest()`; `PatrolTester` is the `$` inside `patrolWidgetTest()`.
> - **v4**: the old `$.native` / `native2` API is **deprecated** in favor of the
>   **Platform Automation API `$.platform.mobile.*`** (e.g. `$.native.tap(...)` →
>   `$.platform.mobile.tap(...)`). The examples in §4–§5 use the current `$.platform.mobile`
>   form; if you're on an older Patrol, translate to `$.native`.

---

## 4. The Patrol test API

A Patrol test is a `patrolTest(...)` whose body receives a `PatrolIntegrationTester` — by
convention named **`$`**. It is a superset of `WidgetTester` plus a concise finder and the
native automator.

```dart
// integration_test/smoke_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:patrol/patrol.dart';
import 'package:my_game/main.dart' as app;

void main() {
  patrolTest('app launches to the menu', (PatrolIntegrationTester $) async {
    app.main();                 // start the real app
    await $.pumpAndSettle();    // drain startup animations

    expect($('Play'), findsOneWidget);
    await $('Play').tap();      // finder + tap in one expression
    expect($('Score: 0'), findsOneWidget);
  });
}
```

**Custom finders (`$`)** — terser than `find.*`, and chainable by descendant:

```dart
await $(#emailInput).enterText('user@leancode.co'); // by Key(ValueKey) / Symbol
await $('Log in').tap();                            // by visible text
await $(FloatingActionButton).tap();                // by widget type

// "first 'Log in' inside #box1 inside a Scaffold"
await $(Scaffold).$(#box1).$('Log in').tap();

// structural finders
$(Scrollable).containing(Text);
$(Scrollable).containing($(ElevatedButton).containing(Text));

// read state
expect($(#counterText).text, '1');
```

`$` also exposes the `WidgetTester` surface you already know from
[`testing-and-release.md`](testing-and-release.md) §Layer 2: `$.pumpWidgetAndSettle(widget)`,
`$.pump([Duration])`, `$.pumpAndSettle()`, `expect(find..., findsOneWidget)`. Patrol adds
**auto-scrolling**: tapping/entering text on a finder scrolls it into view first, and waits
(no manual `pumpAndSettle` between every step) — handy for a long settings or level list.

> Same `pumpAndSettle` caveat as widget tests: it **times out on a perpetual animation** (a
> live game loop / endless runner). Inside an active scene, advance with explicit
> `$.pump(const Duration(milliseconds: 16))` steps instead of `pumpAndSettle`.

**Native automation (`$.platform.mobile`)** — the whole point of Patrol. Selected methods
(verify the current set against the [API reference](https://pub.dev/documentation/patrol/latest/);
not all exist on both OSes):

| Area | Methods |
| --- | --- |
| Permissions | `isPermissionDialogVisible()`, `grantPermissionWhenInUse()`, `grantPermissionOnlyThisTime()`, `denyPermission()`, `selectFineLocation()` / `selectCoarseLocation()` |
| Notifications | `openNotifications()`, `closeNotifications()`, `tapOnNotificationByIndex(int)`, `tapOnNotificationBySelector(Selector(...))`, `getNotifications()` |
| Lifecycle | `pressHome()`, `pressBack()`, `pressDoubleRecentApps()`, `openApp(appId: ...)` |
| Generic native UI | `tap(Selector(text: 'Allow'))`, `enterTextByIndex(...)`, `getNativeViews(Selector(...))` |
| Device settings | `enableWifi()` / `disableWifi()`, `enableCellular()`, `enableDarkMode()` / `disableDarkMode()` |

`Selector` targets native views by text/index/etc.: `Selector(text: 'Allow')`,
`Selector(textContains: 'Patrol says hello!')`.

```dart
// canonical native flow, current ($.platform.mobile) API:
await $.platform.mobile.enableCellular();
await $.platform.mobile.disableWifi();
await $.platform.mobile.enableDarkMode();

await $.platform.mobile.selectFineLocation();        // native location dialog
await $.platform.mobile.grantPermissionWhenInUse();

await $.platform.mobile.openNotifications();
await $.platform.mobile.tapOnNotificationByIndex(0);
```

**No native needed?** Use `patrolWidgetTest((PatrolTester $) async {...})` to get the same
finder ergonomics without spinning up the native automator — faster, and can run as a
`flutter_test` widget test.

---

## 5. E2E suites to design

Organize `integration_test/` by flow, one file per suite, plus a tag so CI can select subsets
(`patrol test --tags smoke`). Each suite below lists what to assert and, where it crosses the
native boundary, the `$.platform.mobile` calls involved. **Drive the game's truth through the
pure model in unit tests; here, assert only that the flow wires up and the native touchpoints
behave.** For a privacy-first kids build, several of these are **negative** suites (prove the
prompt/flow is *absent*).

### 5.1 Onboarding (first launch)
Fresh install → tutorial/first-run screens → reach the menu. Assert each onboarding page
advances and that a "skip"/"done" lands on `Play`. Use a clean app state (uninstall between
runs, or reset persisted `shared_preferences`) so first-run logic actually fires.

### 5.2 Login (only if the game has accounts — kids builds do not)
Per [`references/accessibility-child-safety.md`](accessibility-child-safety.md), a kids/Families
game has **no accounts**. If a non-kids title does: fill `$(#emailInput)`/`$(#passwordInput)`,
tap sign-in, and if it uses a WebView or Google sign-in, handle the **native** auth surface —
this is exactly what `integration_test` can't do. The negative version for a kids build asserts
**no** sign-in UI exists at all.

### 5.3 Purchase flow (IAP)
Governed by [`references/monetization-policy.md`](monetization-policy.md) — **not allowed in a
kids build.** For a non-kids title, the store payment sheet is **native** (StoreKit / Google
Play Billing): tap "Buy", then drive the native sheet via `$.platform.mobile.tap(Selector(...))`,
using each platform's **sandbox/test** purchase account. Assert the entitlement unlocks in the
app afterward. The kids-build version is a **negative** suite: no purchasable UI, no price
strings, no store sheet reachable.

### 5.4 Rewarded-ads flow
Governed by [`references/monetization-policy.md`](monetization-policy.md) — **no ads in a kids
build.** Non-kids: tap "Watch to earn", let the (test-ad-unit) ad render — often a native/WebView
overlay — dismiss it via `$.platform.mobile`, and assert the reward is granted. Always use the
provider's **test ad unit ids**, never live ones. Kids-build version: **negative** — assert no
ad SDK init, no ad surface, no rewarded entry point.

### 5.5 Game start
`Play` → first scene loads → first interaction registers. Assert the HUD shows `Score: 0` (from
the model), the first tap/drag produces the expected model change reflected in the HUD, and the
scene is interactive. Keep it to "the loop starts and responds," not full play-through.

### 5.6 Level completion
Drive minimal, **deterministic** input (inject the seeded `Random` from
[`assets/seeded_random.dart`](../assets/seeded_random.dart) via a test entry point or a
`--dart-define`) to reach a win, then assert the win screen and that progress persists. Reaching
the exact win is the model's job to guarantee in unit tests; here you assert the *screen
transition and persistence*. Avoid frame-perfect timing — prefer scripted, seeded states.

### 5.7 Pause / resume
In-game `Pause` → assert paused HUD and that the loop is halted (model time not advancing) →
`Resume` → assert it continues. Then the **native** variant: `$.platform.mobile.pressHome()` →
`pressDoubleRecentApps()` / `openApp(appId:)` to foreground → assert **state preserved and no
`dt` spike on resume** (the clamp from flutter-game-architecture). This native backgrounding is
the part `integration_test` cannot do.

### 5.8 Settings
Open settings; toggle sound/music/reduce-motion; assert each toggle persists across a relaunch
(`shared_preferences`) and visibly changes behavior (mute really mutes; reduce-motion drops the
animation). Patrol auto-scroll handles a long settings list.

### 5.9 Permissions (native dialogs)
If the game legitimately requests one (e.g. notifications for reminders in a **non-kids** title):
trigger it, then
```dart
if (await $.platform.mobile.isPermissionDialogVisible()) {
  await $.platform.mobile.grantPermissionWhenInUse();   // or denyPermission()
}
```
Test **both** branches — granted and denied — and assert the app behaves gracefully when denied.

### 5.10 Native dialogs & the kids-safety negative suite ⚑
The single most valuable E2E test for a privacy-first build: **prove the absence** of native
prompts and external exits required by
[`references/accessibility-child-safety.md`](accessibility-child-safety.md) and
[`references/release-policy.md`](release-policy.md). Launch, play the full loop, and assert
**no permission dialog ever appears** and no purchase/ad/external surface is reachable:
```dart
patrolTest('kids build raises no native permission prompt', (PatrolIntegrationTester $) async {
  app.main();
  await $.pumpAndSettle();
  await $('Play').tap();
  // ... drive the whole loop ...
  expect(await $.platform.mobile.isPermissionDialogVisible(), isFalse);
});
```
Pair with a static check: the Advertising-ID permission must be **absent** from the merged
`AndroidManifest.xml` and no IDFA/ATT call on iOS (see testing-and-release §Kids/Families).

### 5.11 Notifications
Schedule a local "come back" notification, background the app, then:
```dart
await $.platform.mobile.openNotifications();
await $.platform.mobile.tapOnNotificationBySelector(
  Selector(textContains: 'Ready to play?'),
);
```
Assert the tap deep-links back into the right screen. (Kids builds that send no notifications:
negative suite — `getNotifications()` returns none.)

### 5.12 iOS / Android platform interactions
Some flows only exist or only break on one OS: Android hardware **back** button
(`$.platform.mobile.pressBack()` — does it pause vs. exit?), iOS swipe-back, the iOS ATT prompt
(must be **absent** in kids builds), safe-area/notch layout, dark mode
(`enableDarkMode()`/`disableDarkMode()`). Tag these per-platform and run on **both** an iOS
simulator and an Android emulator — behavior genuinely differs.

---

## 6. Golden, smoke, regression (how the labels map here)

These are **roles**, not separate tools — a given test is "a smoke test" by virtue of what it
covers and which tag/CI gate it sits behind.

- **Smoke** — the minimal "does it boot and play one round" set (essentially §5.5 + a slice of
  §5.6 + the §5.10 negative). Tag `smoke`; run on **every** PR as the fast gate:
  `patrol test --tags smoke`. If smoke is red, stop.
- **Regression** — broader suites pinned to bugs you've already fixed (a resume-state-loss bug,
  a denied-permission crash). Add one E2E (or, better, one **unit**) test per fixed bug so it
  can't silently come back. Tag `regression`; run nightly / pre-release, not on every PR
  (device E2E is slow).
- **Golden (visual regression)** — pixel snapshots of stable, **text-free** visuals. These live
  at the **widget/Flame layer**, not in Patrol — see
  [`testing-and-release.md`](testing-and-release.md) §Golden (`matchesGoldenFile`,
  `flutter test --update-goldens`, `flame_test`'s `testGolden`). Don't golden a live scene or
  anything with rasterized text — it flakes across machines. Patrol E2E asserts *behavior and
  native flow*; goldens assert *appearance*. Keep them in their own layers.

---

## 7. Running E2E (needs a device/emulator — no headless path)

```bash
flutter devices                 # confirm a real target exists FIRST
patrol doctor                   # verify native (Android SDK / Xcode) wiring

# run the whole integration_test/ suite as native instrumentation tests
patrol test

# one suite / by tag / on a chosen device
patrol test --target integration_test/smoke_test.dart
patrol test --tags smoke
patrol test --device <id>       # from `flutter devices`
patrol test --flavor dev        # if you use flavors
patrol test --dart-define=SEED=42   # inject the seeded RNG / test config

# iterative authoring: hot-restart a single test on the device (like flutter run for tests)
patrol develop --target integration_test/smoke_test.dart
```

`patrol test` **builds the app and a native instrumentation host**, installs both, and runs the
tests natively — calling **Gradle** on Android and **`xcodebuild`** on iOS — then reports in the
native format (and works on device farms like Firebase Test Lab). It is **not** `flutter test`;
running `flutter test integration_test/...` skips the native automator and your
`$.platform.mobile` calls will fail.

Before any E2E run, the lower gates from [`references/quality-policy.md`](quality-policy.md) and
testing-and-release must already be green — there's no point burning a device build on code that
isn't `dart format`/`dart analyze` clean:

```bash
dart format --output=none --set-exit-if-changed .
dart analyze
dart test            # pure-model layer — fast, headless
flutter test         # widget/Flame/golden layer
```

> **Report honestly.** E2E/integration/Patrol all need an attached device, emulator, or
> simulator and the matching native toolchain (Android SDK, or macOS + Xcode for iOS). If none
> is available here, state "E2E not run in this environment" and hand over the exact `patrol
> test` commands above plus the device requirement — do **not** claim a pass you didn't observe.
> Quote the native runner's real pass/fail summary in the handoff.

---

## 8. CI notes (high level)

- E2E needs an emulator/simulator in CI — a `macos` runner with an iOS simulator and/or an
  Android emulator action (e.g. `reactivecircus/android-emulator-runner`), or a managed device
  farm. It is **far** slower and flakier than the VM layers, so gate **only the `smoke` tag** on
  every PR and push the rest (`regression`, per-platform) to nightly/pre-release.
- Keep determinism: inject the seeded `Random` via `--dart-define` and use stable test data so a
  run can't depend on wall-clock or device entropy.
- The bulk of correctness still belongs to `dart test` (milliseconds, no device). Treat E2E as
  *integration evidence and native-touchpoint coverage*, not as where you prove the rules — that
  keeps the slow, flaky layer small, which is the whole pyramid.
