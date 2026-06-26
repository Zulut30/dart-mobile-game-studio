# Flutter Casual Games Toolkit (`flutter/games`)

How to start a kids-safe, privacy-first mobile game from the official
[`github.com/flutter/games`](https://github.com/flutter/games) repo, and how to keep its
optional ads / IAP / analytics hooks **out** of the build. This is the Flutter analog of the
Swift skill's "starter project" guidance: use the toolkit for app scaffolding (router, settings,
audio, lifecycle), keep the **pure-Dart game core** engine-independent, and treat every
monetization / telemetry integration as opt-in that a kids build never opts into.

> Doctrine reminder: the toolkit gives you the *shell* (menu → play → settings, navigation,
> audio, persisted progress). Your rules/state live in pure Dart (`lib/game_internals/`,
> no `package:flutter` import) and are unit-tested with `dart test`. Rendering is widgets-only
> (`CustomPainter`) or Flame, chosen per the three-mode rule.

Verified against the repo (`templates/basic`, `templates/card`, `templates/endless_runner`,
`samples/ads`) and the toolkit docs at flutter.dev/games on 2026-06-26. Versions are pins from
the repo and drift — re-check `pubspec.yaml` before quoting them.

---

## 1. What the repo provides

The repo is split into **templates** (starting points you copy and build on) and **samples**
(each shows one integration beyond the basics). Verified directories:

| Path | Engine | Use it for |
| --- | --- | --- |
| `templates/basic` | widgets only | The default shell — menu, navigation, settings, audio, progress. Start here for static/turn-based games. |
| `templates/card` | widgets only (+ drag/drop) | Card games; same shell, no Flame. |
| `templates/endless_runner` | **Flame** `^1.18.0` | Motion/physics game built on `FlameGame`; also pulls `flame_audio`, `nes_ui`, `google_fonts`. |
| `samples/ads` | widgets + `google_mobile_ads` | Reference only — shows AdMob wiring. **Do not copy into a kids build.** |
| `samples/multiplayer` | networked (Firestore) | Reference only — networking/accounts are out of scope for kids/offline-first. |

Fetch a single project without cloning the whole repo with the repo's recommended
[`sample_downloader`](https://pub.dev/packages/sample_downloader) tool:

```bash
dart pub global activate sample_downloader
sample_downloader            # interactive: pick templates/basic (or card, endless_runner)
```

Or `git clone --depth 1` and copy the one template directory (see §2).

### `templates/basic` layout (feature-first)

`lib/` is organized in a feature-first fashion — one directory per feature, each owning its
widgets, controller, and models:

- `app_lifecycle/` — foreground/background signal (`AppLifecycleStateNotifier`), used to pause
  audio when the app is backgrounded.
- `audio/` — `AudioController` over the `audioplayers` package; respects `SettingsController`
  mute flags.
- `game_internals/` — **core game mechanics and logic.** This is your pure-Dart home.
- `level_selection/` — level/stage picker + `LevelData`.
- `main_menu/` — title screen.
- `play_session/` — the gameplay screen; the docs tell you to "jump directly into building your
  game" here.
- `player_progress/` — progress/stats, persisted via `shared_preferences`.
- `settings/` — `SettingsController` backed by `shared_preferences`.
- `style/` — theming (`Palette`), page transitions, responsive helpers.
- `win_game/` — the win screen.
- `main.dart` — app entry; wires providers (see below).
- `router.dart` — `go_router` route table (menu / play / settings / win).

### `templates/basic` dependencies (verified)

```yaml
environment:
  sdk: ^3.8.0

dependencies:
  flutter:
    sdk: flutter
  audioplayers: ^6.0.0       # sound + music
  go_router: ^17.0.0         # navigation
  logging: ^1.2.0            # console logging (no remote sink)
  provider: ^6.1.2           # low-level state mgmt
  shared_preferences: ^2.2.3 # on-device settings + progress

dev_dependencies:
  flutter_lints: ^6.0.0
  flutter_test:
    sdk: flutter
  flutter_launcher_icons: ^0.14.0
  test: ^1.24.3
```

Note what is **absent by design**: no `google_mobile_ads`, no `in_app_purchase`, no
`games_services`, no `firebase_*`. The toolkit's stance is that integrations like ads, IAP, and
analytics are deliberately left out of the starter and added later via the recipes at
flutter.dev/games. For a kids build, "later" is "never" — see §4.

State management is intentionally low-level (`provider` + `ChangeNotifier`/`ValueNotifier`), so
you can lift the shell without learning a new paradigm and keep the core engine-free.

### `main.dart` provider wiring (verified)

`main()` does the standard setup, then `runApp` mounts a `MultiProvider` inside an
`AppLifecycleObserver`:

- `WidgetsFlutterBinding.ensureInitialized()`, configure `Logger.root.level` /
  `onRecord.listen(...)` (console only), set immersive UI mode and lock orientation via
  `SystemChrome`, then `runApp(...)`.
- Registered providers (the surface you'll extend):

  | Provider | Class | Note |
  | --- | --- | --- |
  | `Provider` | `SettingsController` | reads/writes `shared_preferences` |
  | `Provider` | `Palette` | theme colors for `MaterialApp` |
  | `ChangeNotifierProvider` | `PlayerProgress` | persisted progress |
  | `ProxyProvider2` | `AudioController` | depends on `AppLifecycleStateNotifier` + `SettingsController`; `lazy: false` so music starts immediately; `dispose:` releases players |

Add **your** game controllers (the pure-Dart state machine, exposed as a `ChangeNotifier`/
`ValueNotifier`) to this same `MultiProvider`, or scope them to `play_session/`. Do **not** add a
network/account/ads provider here in a kids build.

---

## 2. Starting from the template

```bash
# Grab just the basic template (shallow), then make it yours.
git clone --depth 1 https://github.com/flutter/games.git _games_src
cp -R _games_src/templates/basic my_game
rm -rf _games_src
cd my_game
```

Then, before any feature work, **rename the package** (the repo recommends the
[`rename`](https://pub.dev/packages/rename) tool; do it before deeper integrations so bundle
IDs are set once):

```bash
dart pub global activate rename
dart run rename setAppName --targets ios,android --value "My Game"
dart run rename setBundleId --targets ios,android --value com.example.mygame
```

Verify it builds and the pure-Dart side tests on the VM (no device needed):

```bash
flutter pub get
dart analyze            # analyzer-clean against flutter_lints / very_good_analysis
dart format --output=none --set-exit-if-changed .
dart test               # runs lib/game_internals/ unit tests on the Dart VM
flutter test            # widget tests
```

> Only claim a build/test passed if you ran it and saw the output. If no Flutter SDK is
> available here, say so and hand over the exact commands above.

### Pick a rendering mode (same three-mode rule as Swift)

1. **Widgets-only** (static / turn-based: coloring, matching, sliding puzzle, card) — stay on
   `templates/basic` or `templates/card`. Render with `CustomPainter`/`Canvas`, handle input
   with `GestureDetector`. No engine dependency.
2. **Flame** (motion / physics: runner, tap-reaction, light platformer) — start from
   `templates/endless_runner`, or add Flame to `basic`:
   ```yaml
   dependencies:
     flame: ^1.18.0       # FlameGame, Component/PositionComponent, CollisionCallbacks
     # flame_forge2d: ^…  # only if you genuinely need rigid-body physics (Forge2D/Box2D)
   ```
3. **Hybrid** — embed a `FlameGame` via `GameWidget` inside the template's Flutter screen so the
   `go_router` menus/settings stay native Flutter while the play surface is Flame.

> `endless_runner` pins `go_router: ^16.0.0` while `basic` pins `^17.0.0`. If you lift Flame code
> from the runner into a `basic`-derived project, align the `go_router` versions before
> `flutter pub get`.

### Hybrid wiring: Flame inside the template's `play_session/`

`GameWidget` is the bridge between Flutter and Flame — it places the `FlameGame` into the Flutter
widget tree. Use Flame's **overlays** for the HUD/pause/win so Flutter widgets render over the
game canvas and your game logic can toggle them:

```dart
// lib/play_session/play_session_screen.dart
import 'package:flame/game.dart';
import 'package:flutter/material.dart';

import 'my_flame_game.dart'; // class MyFlameGame extends FlameGame { ... }

class PlaySessionScreen extends StatefulWidget {
  const PlaySessionScreen({super.key});

  @override
  State<PlaySessionScreen> createState() => _PlaySessionScreenState();
}

class _PlaySessionScreenState extends State<PlaySessionScreen> {
  late final MyFlameGame _game = MyFlameGame();

  @override
  Widget build(BuildContext context) {
    return GameWidget<MyFlameGame>(
      game: _game,
      // Flutter widgets layered over the Flame canvas; game logic shows/hides them.
      overlayBuilderMap: {
        'PauseMenu': (context, game) => PauseMenu(game: game),
        'GameOver': (context, game) => GameOver(game: game),
      },
      initialActiveOverlays: const <String>[],
    );
  }
}
```

Toggle overlays from inside the game (verified `overlays` API):

```dart
class MyFlameGame extends FlameGame {
  @override
  void update(double dt) {
    super.update(dt);
    if (core.isGameOver && !overlays.isActive('GameOver')) {
      overlays.add('GameOver');     // also: overlays.remove(id), overlays.toggle(id)
    }
  }
}
```

The `GameWidget<T>.controlled(gameFactory: T.new, ...)` constructor is the variant used when the
game is the app root (as in `templates/endless_runner`); the plain `GameWidget(game: …)` form
above is what you want when embedding under the template's router so menus/settings remain
Flutter screens.

**Keep the core engine-free.** `MyFlameGame` is a thin renderer that reads/writes a pure-Dart
model. The rules, scoring, and the menu→playing→paused→win/lose state machine live in
`lib/game_internals/` with **no `package:flutter` and no `package:flame` import**, so `dart test`
exercises them headless. Inject a seeded `Random` (ship `assets/seeded_random.dart`) for
deterministic logic.

---

## 3. The optional integrations the toolkit documents

flutter.dev/games ships recipes/codelabs for deeper integrations. None of them are in
`templates/basic`; you add them yourself by following those recipes. For a **kids** build, the
decision is made for you — each one is either banned or load-bearing-risky:

| Integration | Typical package (from the recipes) | Kids-build verdict |
| --- | --- | --- |
| Ads | `google_mobile_ads` (see `samples/ads`) | **Banned.** Uses the advertising identifier (IDFA / GAID). |
| In-app purchase | `in_app_purchase` | **Avoid.** If unavoidable, gate behind a parental gate; no impulse/dark-pattern flows. |
| Achievements / leaderboards | `games_services` | **Avoid.** Requires Game Center / Play Games sign-in (an account + network). |
| Multiplayer | `cloud_firestore` (see `samples/multiplayer`) | **Avoid.** Network + accounts + off-device data. |
| Analytics | `firebase_analytics` | **Banned.** Tracking + data collection. |
| Crash reporting | `firebase_crashlytics` | **Avoid.** Collects device/usage data; treat as tracking. |

The recipes wrap each plugin in a controller (e.g. a `GamesServicesController` with
`initialize()` → `GamesServices.signIn()`, `awardAchievement()`, `submitLeaderboardScore()`,
`showAchievements()`, `showLeaderboard()`), instantiated before `runApp` and exposed via a
provider — the same wiring pattern as the audio/settings controllers. A kids build skips all of
it. `samples/ads` adds exactly `google_mobile_ads` on top of the basic dependency set, plus a
`lib/ads/` directory and an `AdsController` provider in `main.dart` — a useful illustration of
*how much surface area* one integration adds, and a clear signal of what your kids `pubspec.yaml`
and `main.dart` must **not** contain.

---

## 4. Keeping ads / IAP / analytics OUT of a kids build

Kids safety here spans **both** the Apple Kids Category **and** Google Play Families policy:
no tracking, no ads, no analytics, no advertising identifier (IDFA/GAID), no external links,
no accounts, no dark patterns; offline-first; no personal data. Because the toolkit ships none
of these by default, the job is mostly *keeping it that way* and proving it.

### 4.1 pubspec gate — the allowlist

Keep `dependencies` to the template set plus (optionally) Flame. If any of these appear, the
build is not kids-clean:

```text
# DISALLOWED in a kids build:
google_mobile_ads        # ads + advertising id
in_app_purchase          # store purchases (parental-gate at minimum)
games_services           # Game Center / Play Games account + network
cloud_firestore          # networked data / multiplayer
firebase_analytics       # tracking
firebase_crashlytics     # device/usage telemetry
firebase_core            # pulled in transitively by the above
facebook_*, appsflyer_*, segment_*, mixpanel_*, sentry_flutter  # any analytics/attribution SDK
```

Grep the dependency tree (transitive too) as a CI gate:

```bash
flutter pub deps --style=compact > /tmp/deps.txt
if grep -E 'google_mobile_ads|in_app_purchase|games_services|cloud_firestore|firebase_analytics|firebase_crashlytics|appsflyer|segment|mixpanel|sentry' /tmp/deps.txt; then
  echo 'FAIL: monetization/telemetry dependency present in kids build' && exit 1
fi
```

### 4.2 If you started from `samples/ads` or `endless_runner`, strip the extras

- Remove `google_mobile_ads` from `pubspec.yaml`; delete the `lib/ads/` directory and the
  `AdsController` provider/import in `main.dart` and any references in `router.dart`.
- Remove any `<meta-data android:name="com.google.android.gms.ads.APPLICATION_ID" …>` from
  `android/app/src/main/AndroidManifest.xml` and the `GADApplicationIdentifier` key from
  `ios/Runner/Info.plist`.
- Run `flutter pub get` and re-grep (§4.1).

### 4.3 The advertising identifier must not be present

The advertising id is the bright line for both stores. With ads removed there is no reason for
the AdSupport framework or the Play `AD_ID` permission to be present:

- **iOS** — do not link `AdSupport.framework`; do not call `ASIdentifierManager`; do not add
  `NSUserTrackingUsageDescription` (no App Tracking Transparency prompt should exist in a kids
  app). Ship a `PrivacyInfo.xcprivacy` that declares **no** tracking and no collected data
  types.
- **Android** — Play auto-adds the `com.google.android.gms.permission.AD_ID` permission when
  certain SDKs are present. In a kids build, explicitly **remove** it:
  ```xml
  <!-- android/app/src/main/AndroidManifest.xml -->
  <uses-permission android:name="com.google.android.gms.permission.AD_ID"
      tools:node="remove" />
  ```
  (Add `xmlns:tools="http://schemas.android.com/tools"` to the `<manifest>` tag.) Then declare
  in the Play Console Data Safety form that you collect no data and do not use an advertising id.

### 4.4 Logging stays local

The template's `logging` package writes to the console only — fine. **Never** attach a remote
listener that ships logs off-device (no Crashlytics/Sentry sink). Keep
`Logger.root.onRecord.listen(...)` pointed at `debugPrint`/console.

### 4.5 If IAP is truly required (prefer not to)

Kids policy does not flatly ban paid content, but it bans pressure and unsupervised spend. If a
purchase exists: put it behind a parental gate (a task a young child cannot complete, e.g. a
date or arithmetic challenge — not a "tap to buy"), never interrupt gameplay with a buy prompt,
and avoid timers/lives/loot mechanics that pressure spending. Most kids games should simply ship
no `in_app_purchase` at all and stay offline-first.

### 4.6 Settings and progress stay on-device

The shell already does the right thing: `settings/` and `player_progress/` persist via
`shared_preferences` (local key-value), and audio respects `SettingsController` mute flags.
There is **no** account, no cloud sync, no network call in the default shell — keep it that way.
This is your offline-first, no-personal-data baseline.

---

## 5. Handoff checklist for a toolkit-based kids build

- [ ] Started from `templates/basic` / `card` (widgets) or `endless_runner` (Flame); rendering
      mode justified by the three-mode rule.
- [ ] Package renamed before any integration work.
- [ ] `dependencies` match the template allowlist (+ Flame only if motion/physics); §4.1 grep is
      clean on the transitive tree.
- [ ] No `google_mobile_ads` / `in_app_purchase` / `games_services` / `cloud_firestore` /
      `firebase_*` / analytics-attribution SDK anywhere.
- [ ] No advertising identifier: iOS has no AdSupport/ATT prompt and a no-tracking
      `PrivacyInfo.xcprivacy`; Android removes the `AD_ID` permission.
- [ ] Logging is console-only; no remote crash/analytics sink.
- [ ] Settings + progress are `shared_preferences` (on-device); no account, no network in the
      default flow; offline-first verified by running in airplane mode.
- [ ] Game rules in `lib/game_internals/` import neither `package:flutter` nor `package:flame`;
      `dart test` passes headless with a seeded `Random`.
- [ ] `dart analyze` and `dart format --set-exit-if-changed` are clean.

> No store-approval guarantees. This is a checklist plus a risk list — Apple Kids Category and
> Google Play Families review the final binary and its declared data practices, not this doc.