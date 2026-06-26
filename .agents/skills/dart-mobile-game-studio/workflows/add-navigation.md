# Workflow: Add Navigation (go_router + Flame overlays)

**Goal:** Wire screen-to-screen navigation with `go_router` (routes, named/typed, redirects/guards, deep links) while keeping in-game transient UI (pause, result, settings) as **Flame overlays — not routes**.

## When to use
- The game has more than one full screen: splash/menu → game → level-select → settings → about, etc.
- You need deep links (universal/app links) into a screen, or a guard (e.g. "age gate not passed → redirect to gate").
- You are converting an ad-hoc `Navigator.push` app to a single, declarative router.

**Do NOT use this** for pause/resume, win/lose result cards, or a HUD settings popover that sit *on top of the running game* — those are Flame overlays (see Step 6). Routes unmount the game; overlays do not.

## Prerequisites
- App scaffolded per `references/flutter-game-architecture.md` (UI / business-logic / game-logic separated; pure-Dart core has **no** `package:flutter` import).
- `flutter` SDK on PATH; run `flutter --version` to confirm.
- Decide the route table on paper first: every full screen = one route; every in-game popup = one overlay. Write the list down before coding.

---

## STEPS

### 1. Add the dependency (justify it per package-policy)
`go_router` is the package the Flutter team itself recommends over raw `Navigator` 2.0 and named routes; it is allowed under `references/package-policy.md` as a routing primitive (declarative routes, deep links, guards) you would otherwise hand-roll. Pin it.

```bash
flutter pub add go_router
flutter pub get
```

Confirm it resolved:
```bash
flutter pub deps --no-dev | grep go_router
```

### 2. Define route *names* as constants (avoid stringly-typed nav)
Create `lib/routing/routes.dart`. Centralizing names is the cheap version of "typed routes" and keeps `goNamed` call sites refactor-safe.

```dart
// lib/routing/routes.dart — pure Dart, no flutter import.
abstract final class AppRoute {
  static const menu = 'menu';
  static const levelSelect = 'levelSelect';
  static const game = 'game';
  static const settings = 'settings';
  static const ageGate = 'ageGate';
}
```

### 3. Build the `GoRouter` in one place
Create `lib/routing/app_router.dart`. Use `name:` on every route, `builder:` for default platform transitions, and read params from `GoRouterState`.

```dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'routes.dart';

GoRouter createRouter({required bool ageGatePassed}) {
  return GoRouter(
    initialLocation: '/',
    debugLogDiagnostics: true, // dev only; strip for release builds
    routes: [
      GoRoute(
        path: '/',
        name: AppRoute.menu,
        builder: (context, state) => const MenuScreen(),
        routes: [
          GoRoute(
            path: 'levels',
            name: AppRoute.levelSelect,
            builder: (context, state) => const LevelSelectScreen(),
          ),
          GoRoute(
            // path param: /play/3
            path: 'play/:levelId',
            name: AppRoute.game,
            builder: (context, state) {
              final levelId =
                  int.tryParse(state.pathParameters['levelId'] ?? '') ?? 1;
              return GameScreen(levelId: levelId);
            },
          ),
          GoRoute(
            path: 'settings',
            name: AppRoute.settings,
            builder: (context, state) => const SettingsScreen(),
          ),
        ],
      ),
      GoRoute(
        path: '/age-gate',
        name: AppRoute.ageGate,
        builder: (context, state) => const AgeGateScreen(),
      ),
    ],
    redirect: (context, state) => _guard(state, ageGatePassed),
    errorBuilder: (context, state) =>
        ErrorScreen(message: state.error?.toString() ?? 'Not found'),
  );
}
```

`GoRouterState` fields you will use: `state.uri`, `state.pathParameters['levelId']`, `state.uri.queryParameters['from']`, `state.extra` (arbitrary object passed in-process; **not** available across a cold deep link, so never depend on it for restorable state).

### 4. Mount the router on `MaterialApp.router`
In `lib/app.dart` (the UI layer):

```dart
class MyGameApp extends StatelessWidget {
  const MyGameApp({super.key, required this.router});
  final GoRouter router;

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      routerConfig: router,
      title: 'My Game',
    );
  }
}
```

Build the router once (e.g. in `main()` or an `InheritedWidget`/provider) and pass it down — recreating `GoRouter` on every rebuild throws away navigation state.

### 5. Navigate: `go` vs `push` vs `goNamed`
Pick by intent — this is the most common source of "back button does the wrong thing" bugs.

| Call | Effect | Use for |
|---|---|---|
| `context.goNamed(AppRoute.game, pathParameters: {'levelId': '3'})` | **Replaces** the stack to that location | menu → level (forward flow you don't want to "pop back" through screen-by-screen) |
| `context.go('/play/3')` | Same as above, by raw path | deep-link-style jumps |
| `context.pushNamed(AppRoute.settings)` | **Pushes** onto the stack | modal-ish screens you expect the user to pop back from |
| `context.pop()` | Pops one entry | a pushed screen's back affordance |

Prefer `goNamed`/`pushNamed` with constants over raw paths so a path change is one edit. Example with a query param and `extra`:

```dart
context.goNamed(
  AppRoute.game,
  pathParameters: {'levelId': '3'},
  queryParameters: {'from': 'levelSelect'},
  extra: SessionSeed(seed: 42), // in-process only
);
```

### 6. Keep pause / result / settings-popover as **Flame overlays, not routes**
A route swaps the whole screen and **disposes the `FlameGame`**, losing in-flight game state and forcing a re-init. For anything that floats over the *running* game, use the overlay system instead (see `references/flutter-flame-patterns.md`).

```dart
// In your FlameGame: register overlay builders on the GameWidget.
GameWidget<MyGame>(
  game: game,
  overlayBuilderMap: {
    'pause': (context, MyGame g) => PauseMenu(game: g),
    'result': (context, MyGame g) => ResultCard(game: g),
  },
);

// Toggle from gameplay/business logic — NOT context.go():
game.overlays.add('pause');     // show pause; game.pauseEngine() alongside
game.overlays.remove('pause');  // resume; game.resumeEngine()
```

Decision rule:
- **New full screen, own back stack, deep-linkable** → `GoRoute`.
- **Floats over the live game, keeps game state, no URL** → `overlays.add(...)`.

A "Quit to menu" button *inside* the pause overlay is the bridge: it removes the overlay **and** does `context.goNamed(AppRoute.menu)` (route change is correct there because you intend to tear the game down).

### 7. Redirects / guards (age gate, kids-safety)
Centralize guards in the top-level `redirect`. Return a path `String` to redirect, or `null` to allow. Keep it pure and synchronous; never `await` here.

```dart
String? _guard(GoRouterState state, bool ageGatePassed) {
  final goingToGate = state.matchedLocation == '/age-gate';
  // Block sensitive areas until the parental/age gate passes.
  if (!ageGatePassed && !goingToGate) return '/age-gate';
  // Don't strand the user on the gate once passed.
  if (ageGatePassed && goingToGate) return '/';
  return null; // allow
}
```

Always guard against redirect loops (the two early-returns above). For kids titles, the gate itself must follow `references/accessibility-child-safety.md` (parental gate before external/sensitive actions, no data collection).

### 8. Wire deep links (platform config)
go_router consumes the platform deep link automatically once the OS hands it over. Enable OS-level delivery:

**iOS** — `ios/Runner/Info.plist`:
```xml
<key>FlutterDeepLinkingEnabled</key>
<true/>
```
For universal links add the Associated Domains entitlement in `ios/Runner/Runner.entitlements`:
```xml
<key>com.apple.developer.associated-domains</key>
<array><string>applinks:example.com</string></array>
```

**Android** — add to the `<activity>` in `android/app/src/main/AndroidManifest.xml`:
```xml
<meta-data android:name="flutter_deeplinking_enabled" android:value="true" />
<intent-filter android:autoVerify="true">
  <action android:name="android.intent.action.VIEW" />
  <category android:name="android.intent.category.DEFAULT" />
  <category android:name="android.intent.category.BROWSABLE" />
  <data android:scheme="https" android:host="example.com" />
</intent-filter>
```
Host `https://example.com/.well-known/assetlinks.json` with your release signing SHA-256 for `autoVerify` to succeed.

A deep link to `https://example.com/play/3` lands directly on the `game` route because the path table matches `/play/:levelId`. Because `extra` is unavailable on a cold deep link, any state the screen needs (here, `levelId`) **must** come from path/query params.

### 9. Back / system-back handling
- `MaterialApp.router` + go_router already route the Android hardware back and the predictive-back gesture through the router; a pushed route pops correctly with no extra code.
- For a screen that must **confirm before leaving** (e.g. discard progress), wrap its body in `PopScope`:
```dart
PopScope(
  canPop: false,
  onPopInvokedWithResult: (didPop, result) {
    if (didPop) return;
    showQuitConfirmDialog(context); // then context.pop() on confirm
  },
  child: gameBody,
);
```
- Inside the running game, hardware-back should typically **open the pause overlay**, not pop the route. Handle it at the game screen with `PopScope(canPop: false, ...)` that calls `game.overlays.add('pause')`.

### 10. Transitions
- Default `builder:` gives the platform-correct push animation (Cupertino slide on iOS, fade-up on Android). Keep it unless asked otherwise.
- For a custom transition use `pageBuilder:` with `CustomTransitionPage`:
```dart
pageBuilder: (context, state) => CustomTransitionPage(
  key: state.pageKey,
  child: const MenuScreen(),
  transitionsBuilder: (context, animation, _, child) =>
      FadeTransition(opacity: animation, child: child),
);
```
- **Honor Reduce Motion.** If `MediaQuery.of(context).disableAnimations` (or platform reduce-motion) is true, fall back to no/instant transition. Required by `references/accessibility-child-safety.md`.

### 11. Verify
```bash
dart format --set-exit-if-changed lib/routing/
flutter analyze
flutter test
```
Manual deep-link smoke test (app installed/running on a device or simulator):
```bash
# Android
adb shell am start -W -a android.intent.action.VIEW \
  -d "https://example.com/play/3" com.example.mygame
# iOS Simulator
xcrun simctl openurl booted "https://example.com/play/3"
```
Confirm: cold launch lands on `/play/3`, the back button returns to menu, and the age gate redirect fires when `ageGatePassed == false`.

---

## Done when
- One `GoRouter` owns all full-screen navigation; no stray `Navigator.push` for screens.
- Pause / result / in-game settings are Flame overlays toggled via `overlays.add/remove`, and they preserve game state (verified: pausing then resuming keeps the same session).
- Named routes + constants used at all call sites; path/query params parsed from `GoRouterState`.
- Guard redirects (age gate) work and cannot loop.
- Deep link opens the correct screen on cold start on both platforms (manual smoke test passed).
- `flutter analyze` clean, `dart format` clean, `flutter test` green.

## Common pitfalls
- **Using a route for pause/result.** It disposes the `FlameGame` and wipes game state. Use overlays. (Step 6.)
- **Depending on `state.extra` for deep-link / restorable state.** `extra` is in-process only and is `null` on cold deep links and app restart. Put restorable data in path/query params. (Steps 3, 8.)
- **Recreating `GoRouter` on every build** (e.g. inside `build()`), which resets navigation. Build it once. (Step 4.)
- **`go` vs `push` confusion** producing a broken back stack — `go` *replaces* the location, `push` *adds* to it. (Step 5.)
- **Redirect loops** from a guard that redirects toward a location the guard also blocks. Always allow the target itself. (Step 7.)
- **Async work in `redirect`.** It must be synchronous and pure; do auth/age checks against already-loaded state, not an `await`.
- **Forgetting `FlutterDeepLinkingEnabled` / `flutter_deeplinking_enabled`**, so the OS never forwards the link to go_router. (Step 8.)
- **Animated transitions ignoring Reduce Motion**, failing accessibility. (Step 10.)
- **Quit-to-menu from an overlay** that removes the overlay but forgets `context.goNamed(menu)` (or vice-versa), leaving a zombie game running under the menu. Do both. (Step 6.)

## Cross-links
- `references/production-quality.md` — analyzer-clean, `const`, `dispose`, null-safety, 2-space format gates this navigation code must pass.
- `references/flutter-flame-patterns.md` — overlay system, `pauseEngine`/`resumeEngine`, GameWidget setup.
- `references/flutter-game-architecture.md` — UI / business-logic / game-logic separation (routing lives in the UI layer; never import `go_router` into the pure-Dart core).
- `references/accessibility-child-safety.md` — parental/age gate, Reduce Motion, kids-safety requirements driving the guard and transitions.
- `references/package-policy.md` — justification for adding `go_router`.
