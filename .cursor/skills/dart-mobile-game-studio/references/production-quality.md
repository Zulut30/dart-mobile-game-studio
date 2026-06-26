# Production quality: patterns from real high-quality Flutter apps

How to make a *commercial-grade* mobile game (iOS + iPadOS + Android), not a tech demo. The
earlier references cover the engine-independent core, the three render modes, testing, and
kids-safety. This file is the polish layer: project structure, layering, navigation, responsive
and adaptive layout, theming/design tokens, an animation budget, state management at scale,
asset/localization structure, error/empty/loading states, and the production-UX details
(haptics, transitions, onboarding) that separate a shippable game from a prototype.

It is a **reference, not a copy**. Each rule cites what a named source *demonstrates*; adopt the
pattern, not the code. Do not lift Wonderous/sample source verbatim — it is licensed for showcase
study, and a coloring book does not need an artifact-API service layer.

Grounded against these sources on 2026-06-26:

- **Wonderous** — [`github.com/gskinnerTeam/flutter-wonderous-app`](https://github.com/gskinnerTeam/flutter-wonderous-app)
  (gskinner × Flutter team): a production showcase app. Verified its real `lib/` layout, the
  `AppLogic.bootstrap()` startup pattern, the `$styles`/`AppStyle` design-token system, and the
  `go_router` redirect guard.
- **flutter/samples** — [`github.com/flutter/samples`](https://github.com/flutter/samples):
  `compass_app` (MVVM + UI/domain/data layering), `platform_design` (adaptive iOS/Android),
  `animations`, `form_app`, `navigation_and_routing` (go_router scenarios), `material_3_demo`.
- **flutter/demos** — [`github.com/flutter/demos`](https://github.com/flutter/demos): talk/blog
  experiments (shaders, motion, AI). **Explicitly unmaintained** ("may not work with newer
  releases") — mine it for *techniques*, never as a dependency or a copy-paste source.
- **Official Flutter app-architecture guide** —
  [`docs.flutter.dev/app-architecture`](https://docs.flutter.dev/app-architecture): the
  canonical UI-layer / (optional) domain-layer / data-layer split this file maps onto a game.
- **itsallwidgets.com** — a curated gallery of shipped Flutter apps/widgets; use it as a survey
  of what production polish looks like in the wild when picking transitions/layout patterns.

> Pins drift. Wonderous is a deep, multi-feature *content* app — heavier than a casual game.
> Treat its structure as a **ceiling** to scale down from, not a floor every game must reach. The
> doctrine still holds: a pure-Dart core (no `package:flutter`), three render modes, injected
> seeded `Random`, kids-safe by construction.

---

## 1. Feature-first project structure

Wonderous's real top-level `lib/` (verified) is **layer-first at the root, feature-first
inside**:

```
lib/
├─ main.dart            # entry; runApp + bootstrap
├─ router.dart          # go_router table + redirect guard
├─ assets.dart          # generated/typed asset paths (no raw string literals at call sites)
├─ common_libs.dart     # one barrel export of the imports every file needs
├─ logic/               # business logic + data
│  ├─ *_logic.dart      # AppLogic, SettingsLogic, WondersLogic, … (state holders)
│  ├─ *_service.dart    # ArtifactApiService, UnsplashService (wrap one external source)
│  ├─ common/           # shared helpers
│  └─ data/             # models / repositories
├─ ui/
│  ├─ app_scaffold.dart # root shell
│  ├─ common/           # reusable widgets
│  ├─ screens/          # one folder per screen/feature
│  └─ wonder_illustrations/
├─ styles/              # colors.dart, styles.dart ($styles tokens), extensions
└─ l10n/                # localization
```

The lesson for a game: **group by feature, not by widget type.** Don't scatter a feature across
`widgets/`, `controllers/`, `models/`. The official architecture guide says the same — every
feature is one View + one ViewModel (UI) over one or more repositories (data).

This skill's own layout (see `flutter-game-architecture.md`) already encodes a stricter version:
a **rendering-free core** under `lib/models/` + `lib/systems/` that imports neither
`package:flutter` nor `package:flame`. Map Wonderous's layers onto the game like this:

| Wonderous layer | Game equivalent (this skill) | Import rule |
|---|---|---|
| `logic/*_logic.dart` (state holders) | `lib/game/` state-mgmt adapters (`ChangeNotifier`/`ValueNotifier` over the pure controller) | Flutter OK; **no** game rules — those stay pure |
| `logic/data/` + `logic/*_service.dart` | `lib/systems/` (save, score, spawn) + `lib/models/` (rules, entities, level data) | **Pure Dart** — no Flutter, no Flame |
| `ui/screens/`, `ui/common/`, `app_scaffold.dart` | `lib/widgets/` (menu, HUD, settings, `CustomPainter`) and/or `lib/game/` (Flame components) | Flutter/Flame only here |
| `styles/` | `lib/style/` (`AppStyle` tokens) | Flutter OK |
| `l10n/` | `lib/l10n/` | generated |

Two structural conveniences from Wonderous worth copying:

- **A typed `assets.dart`.** Every image/audio path is a `static const` on a class, so a renamed
  file is a *compile* error, not a silent missing-asset at runtime. (Generate it with
  `flutter_gen` if you prefer; the principle is "no bare asset strings at call sites.")
- **A `common_libs.dart` barrel.** One `export` file for the handful of imports nearly every file
  needs (your style tokens, common widgets, the controller type). Reduces import churn. Keep it
  small and do **not** put `package:flutter` re-exports into pure-Dart core files — the barrel is
  for the UI layer only, or the no-Flutter rule leaks.

---

## 2. Clear UI / logic / data separation (the layer contract)

The official guide splits an app into a **UI layer** (Views + ViewModels) over a **data layer**
(Repositories + Services), with an **optional domain layer** (use-cases) only when complexity
demands it. Map it to a game without ceremony:

```
┌─────────────────────────── UI layer ───────────────────────────┐
│  Views: widgets / CustomPainter / Flame components (thin)       │
│  ViewModel: ChangeNotifier|ValueNotifier adapter over the core  │
└───────────────────────────── ↓ reads ─────────────────────────┘
┌──────────────── (optional) game-logic / domain ────────────────┐
│  GameController: the pure state machine + rule reducers         │
│  Systems: spawn / score / collision (pure Dart)                 │
└───────────────────────────── ↓ uses ──────────────────────────┘
┌────────────────────────── data layer ─────────────────────────┐
│  Repositories: LevelRepository, SaveRepository (sources of truth)│
│  Services: SharedPreferences/file I/O wrappers (one per source) │
└────────────────────────────────────────────────────────────────┘
```

Hard rules, in order of how often they're violated:

1. **A View holds no game rules.** Per the guide a View contains only "minimal logic": conditional
   rendering, animation, layout-from-device-info, and simple routing. The verdict — *was that a
   legal move? did the level end?* — lives in the pure controller. A `CustomPainter` or Flame
   component reads a snapshot and draws it; it never decides scoring.
2. **A ViewModel is an adapter, not a brain.** The `ChangeNotifier`/`ValueNotifier` wraps the pure
   `GameController` and calls `notifyListeners()` after a transition. It must not re-implement a
   rule the controller already owns (see `flutter-game-architecture.md` for the exact
   `GameNotifier` shape). Wonderous's `*_logic.dart` files are this role — state holders that
   coordinate, while `*_service.dart` files wrap exactly one external source and **hold no state**
   (the guide's definition of a service).
3. **The data layer is the source of truth for persisted data.** A `SaveRepository` owns the
   save model; a `LevelRepository` owns level JSON. They expose `Future`/`Stream`, do caching and
   error handling, and hand back domain models. Wonderous separates `*_service.dart` (raw
   external call) from `*_logic.dart` (transform + cache) for exactly this reason.
4. **Add a domain/use-case layer only when it pays for itself.** The guide is explicit: use-cases
   reduce duplication and improve testability *but* add boilerplate, so add them "only when
   needed, not preemptively." A casual game almost never needs them — the pure `GameController`
   *is* the domain logic. Don't manufacture interactors for a sliding puzzle.

The win is testability: because the rules sit below the UI in pure Dart, `dart test` exercises
them on the VM with no widget pump and no device — the same payoff the guide attributes to its
View/ViewModel split, but stricter (this skill bans Flutter imports from the core outright).

---

## 3. Navigation with go_router (typed routes, deep links, guards)

Wonderous and `flutter/samples` (`navigation_and_routing`, `compass_app`) both route with
**go_router**, and the official guide's case study injects ViewModels per route inside the
`GoRouter` config. Adopt the same spine.

### Centralize paths; never sprinkle string literals

Wonderous defines a `ScreenPaths` class of static getters (verified): `splash = '/'`,
`home = '/home'`, and parameterized builders like `wonderDetails(type, {tabIndex})` →
`'/wonder/${type.name}?t=$tabIndex'`. One place to change a path; the rest of the app calls the
getter.

```dart
// lib/routing/screen_paths.dart  — single source of route strings
abstract final class ScreenPaths {
  static const String menu = '/';
  static const String play = '/play';
  static String level(int id) => '/play/level/$id'; // typed builder, not a literal at call sites
  static const String settings = '/settings';
}
```

### Prefer typed routes (compile-checked params)

go_router's code-gen `TypedGoRoute<T>` + `GoRouteData` turns route params into typed fields, so a
missing/mistyped argument is a build error rather than a runtime null. Use it when you have more
than a couple of parameterized routes; for a 3-screen game, the `ScreenPaths`-getter approach
above is enough.

```dart
// Typed route (go_router_builder): params are fields, navigation is go() on a data object.
@TypedGoRoute<LevelRoute>(path: '/play/level/:id')
class LevelRoute extends GoRouteData {
  const LevelRoute({required this.id});
  final int id;                                  // typed — no `state.pathParameters['id']!`
  @override
  Widget build(BuildContext context, GoRouterState state) => PlayScreen(levelId: id);
}
// navigate: const LevelRoute(id: 3).go(context);
```

### A startup guard via `redirect` (the bootstrap gate)

Wonderous's redirect (verified) keeps the user on splash until init finishes:

```dart
redirect: (context, state) {
  // Block every route until app-level init completes (assets, settings, save load).
  if (!appLogic.isBootstrapComplete && state.matchedLocation != ScreenPaths.splash) {
    return ScreenPaths.splash;
  }
  return null; // no redirect
},
```

For a game, use the same gate for a "load save + warm asset cache" splash, and for kids-flow
guards (e.g. a parental gate before a settings/purchase screen — return the gate route until it's
passed). Pair `redirect` with `refreshListenable:` (the guide passes the auth repository) so the
guard re-runs when the gating state changes; for a game, point it at the bootstrap/`SettingsLogic`
notifier.

### Deep links come for free — keep them consistent

The guide's reason for recommending go_router over imperative `Navigator`: declarative routing
"always displays the same screen when a deep link is received." A path like `/play/level/3` must
resolve to the same place whether reached by tap or by external link. Caveats for a kids game:

- A deep link must **not** bypass a parental gate. If `/play/level/99` is premium-gated, the
  `redirect` guard catches it the same as in-app navigation — that's the point of putting the gate
  in `redirect`, not in a button handler.
- Validate path params (`int.tryParse`, enum-with-fallback, like Wonderous's `_parseWonderType`)
  and redirect unknown values to a safe screen — a hand-typed deep link is untrusted input.
- Don't add custom URL schemes a kid could be socially-engineered through; keep external entry
  points minimal (offline-first means there's rarely a reason for them at all).

---

## 4. Responsive + adaptive layout

Two different problems, both required for "works on phone *and* iPad/tablet":

- **Responsive** = same design, fits any size. Driven by available space.
- **Adaptive** = right idiom per platform/input (touch vs pointer, Material vs Cupertino,
  phone single-pane vs tablet two-pane). `flutter/samples` `platform_design` demonstrates
  "maximizing code reuse while adhering to different design patterns on Android and iOS," and
  `compass_app` / `desktop_photo_search` show layout adapting across form factors.

### Drive size off a scale factor, not magic numbers

Wonderous derives a single `scale` from `screenSize.shortestSide` (verified breakpoints:
≤400 → 0.85, ≤600 → 0.9, ≤800 → 1.0, >800 → 1.15, >1000 → 1.25) and multiplies **all** insets and
font sizes by it. One factor → the whole UI grows coherently on an iPad without per-widget tweaks.
Fold it into the design tokens (§5) so call sites read `$styles.insets.md`, not a raw pixel value.

```dart
// One source of "how big is this device", read by the token system.
double scaleFromShortestSide(double shortestSide) {
  if (shortestSide > 1000) return 1.25;
  if (shortestSide > 800) return 1.15;
  if (shortestSide > 600) return 1.0;   // small tablet baseline
  if (shortestSide > 400) return 0.9;
  return 0.85;                          // small phone
}
```

### Layout primitives, in preference order

1. `LayoutBuilder` — branch on the **parent's** constraints (the correct signal for "do I have
   room for a two-pane board + side HUD?"). Prefer this over `MediaQuery.size` for component-level
   decisions.
2. `MediaQuery` (via `.sizeOf`, `.paddingOf`, `.viewInsetsOf`) — for screen-level facts: safe-area
   insets (notch, home indicator), the on-screen keyboard, and accessibility (`textScalerOf`,
   `disableAnimations`). Use the `.xOf(context)` accessors so a change to one field doesn't rebuild
   everything that reads `MediaQuery`.
3. `SafeArea` + `OrientationBuilder` — never paint the HUD under the notch; re-flow on rotation.
   Wonderous's `AppLogic` restricts orientation per device (phones portrait-locked, tablets
   free) — decide your game's allowed orientations once at bootstrap, not ad hoc.
4. `Flexible`/`Expanded`/`AspectRatio`/`FittedBox` — keep a fixed-aspect game board centered and
   uniformly scaled inside any window instead of stretching.

> A Flame game canvas is its own coordinate space — size it with the engine's camera/viewport
> (e.g. a fixed-resolution viewport letterboxed to the device), then let the surrounding Flutter
> chrome (menus, HUD overlays) be responsive in widget space. Don't conflate the two.

### Adaptive idioms

- **Material vs Cupertino** where it matters (dialogs, switches, the back gesture). `platform_design`
  shows the reuse-vs-divergence line. For a kids game, lean to one consistent, high-contrast visual
  language rather than chasing per-OS chrome — but still honor platform back/scroll physics.
- **Single-pane phone → two-pane tablet** (e.g. level grid + preview) via a `LayoutBuilder`
  breakpoint, the pattern `compass_app` uses. Don't ship a phone UI stretched across an iPad.
- **Input adaptivity**: support pointer hover/focus and a keyboard/`Shortcuts`/`Actions` map if the
  game can plausibly run on iPad-with-keyboard or desktop; don't assume touch-only.

---

## 5. Theming & design tokens

Wonderous's strongest, most copyable idea is `AppStyle` (exposed app-wide as `$styles`): a single
object holding sub-systems for **colors, corners, shadows, insets, text, and times** (verified),
all scaled by the responsive factor from §4. Every widget reads tokens — `$styles.insets.md`,
`$styles.text.h2`, `$styles.times.med` — and never hardcodes a number. This is what makes a global
restyle a one-file change and keeps spacing/typography consistent across screens.

```dart
// lib/style/app_style.dart  — design tokens; the ONE place numbers live.
@immutable
class AppStyle {
  AppStyle({Size screenSize = Size.zero}) : scale = scaleFromShortestSide(screenSize.shortestSide);
  final double scale;

  late final AppColors colors = AppColors();
  late final _Insets insets = _Insets(scale);
  late final _Corners corners = _Corners();
  late final _Times times = _Times();
  late final _Text text = _Text(scale, colors);
}

// A spacing scale (multiplied by the device scale) — the Wonderous insets shape.
class _Insets {
  _Insets(this._s);
  final double _s;
  late final double xs = 8 * _s;
  late final double sm = 16 * _s;
  late final double md = 24 * _s;
  late final double lg = 32 * _s;
  late final double xl = 48 * _s;
}

// Named animation durations (Wonderous groups fast/med/slow + a faster pageTransition).
class _Times {
  final Duration fast = const Duration(milliseconds: 300);
  final Duration med = const Duration(milliseconds: 600);
  final Duration slow = const Duration(milliseconds: 900);
  final Duration pageTransition = const Duration(milliseconds: 200);
}
```

Token rules:

- **A spacing scale, not free numbers.** `xs/sm/md/lg/xl` (Wonderous: `xxs=4 … offset=80`). A
  `SizedBox(height: 17)` anywhere is a smell — round it to a token.
- **Named durations.** Animation times come from `$styles.times`, so motion feels consistent and a
  "slow everything down" tweak is one edit. This is also where Reduce Motion hooks in (§7): when
  `disableAnimations` is set, collapse these to `Duration.zero` (or near it) in one place.
- **Provide the tokens via `MaterialApp.theme` *and* a `$styles` accessor.** Map colors/text onto a
  `ThemeData`/`ColorScheme` (so framework widgets inherit them and `material_3_demo`-style M3
  theming works), but keep the richer game-specific tokens (insets, times, custom corners) on the
  `AppStyle` object. Rebuild `AppStyle` when `screenSize` changes so the scale stays correct on
  rotation/resize.
- **Light/dark + high-contrast.** Define a `ColorScheme` per brightness; for a kids game prioritize
  a high-contrast, large-touch palette and verify contrast ratios (accessibility, not just taste).

---

## 6. Animation polish budget

`flutter/samples` `animations` and `flutter/demos` (shader/motion experiments) show how far Flutter
motion can go — but a *game's* animation budget is finite, and the wrong tool tanks the frame
rate. Spend it deliberately.

| Job | Reach for | Notes |
|---|---|---|
| Entrance/exit of a widget (menu items, dialog) | **Implicit** (`AnimatedOpacity`, `AnimatedPositioned`, `AnimatedSwitcher`) or **`flutter_animate`** | Declarative; no controller to dispose. Cheapest correct option. |
| Staggered list/grid reveal | `flutter_animate` `AnimateList` / `.animate(interval:)` | One chained call vs hand-rolled controllers. |
| Coordinated multi-property choreography | An explicit `AnimationController` + `Tween`/`Interval` | Use when timing relationships matter; **dispose it**. |
| Per-frame game simulation (motion, gravity, particles) | The **game loop** — Flame `update(dt)` or a `Ticker` | This is simulation, not "animation." Clamp `dt`; it's not a `flutter_animate` job. |
| Page/route motion | go_router `CustomTransitionPage` driven by `$styles.times.pageTransition` | Keep transitions short (~200 ms) and consistent. |

`flutter_animate` (verified API) chains effects fluently and removes controller boilerplate —
`MyWidget().animate().fadeIn(duration: 300.ms).slideY(begin: .1)` — and supports a `target:` value
that smoothly animates on state change without a `StatefulWidget`. Use it for UI flourish (menus,
HUD, win/lose banners). Do **not** use it for the core gameplay loop — that belongs to
`update(dt)` / a `Ticker`, where you control the clock and clamp for dropped frames.

Budget rules:

- **60 fps (or the device's refresh rate) is the budget; jank is a bug.** Profile in profile mode;
  watch the raster + UI threads. An animation that drops frames is worse than no animation.
- **Animate transforms/opacity, not layout, in hot paths.** Prefer `Transform`/`Opacity`/`RepaintBoundary`
  over animating widget *size* every frame (which re-lays-out the subtree).
- **`const` everything you can; isolate repaints with `RepaintBoundary`** around the animated
  region so a spinning coin doesn't repaint the whole HUD.
- **Dispose every controller/ticker** (the Dart quality bar, rule 7). A leaked
  `AnimationController` keeps ticking off-screen.
- **Every animation has a Reduce-Motion fallback** (§7). Decorative motion must degrade to an
  instant state change, never to a broken UI.

---

## 7. State management at scale (and when `ValueNotifier` is enough)

The architecture guide deliberately **does not prescribe** a state-management package — it's the
developer's choice over a clean layer split. Wonderous itself uses lightweight tools (`provider` +
`get_it` service locator), not Riverpod/Bloc. `flutter/samples` `provider_shopper` shows
`ChangeNotifier` + `provider`; other samples use plain `ValueNotifier`. The lesson: **structure
first, then the lightest notification wire that fits.**

This skill's escalation ladder (consistent with `flutter-game-architecture.md`):

| Reach for | When | Why not heavier |
|---|---|---|
| `setState` | State lives in one screen; tiny game | No sharing needed; the model can still be pure and held as a field |
| **`ValueNotifier` + `ValueListenableBuilder`** | One/few observable values (score, status); single screen or one play surface | **Default.** No package, granular rebuilds, trivially disposed and unit-tested |
| `ChangeNotifier` + `provider` | Several screens read the same controller (menu + HUD + settings) | One small, ubiquitous dep; the Wonderous/`provider_shopper`/toolkit choice |
| Riverpod | Many independent slices, no-`BuildContext` reads, compile-safe providers, large team | More concepts than a casual game needs — **justify it** |
| Bloc / `flutter_bloc` | You genuinely want an event log / strict unidirectional event→state streams | Most ceremony; rarely warranted for a simple game — **justify it** |

Decision rule: **`ValueNotifier` is enough until two or more screens must observe the same
mutable state.** At that boundary, lift to `ChangeNotifier` + `provider` (or a `get_it` singleton,
Wonderous-style). Reach past `provider` only when you have concrete slices that hurt without
Riverpod/Bloc — and write the one-line justification, per `package-policy` (official → mature
community → none). Whatever you pick, it stays a **thin notification wire over the pure
`GameController`**; the rules never move into the state-management object.

```dart
// The default: a ValueNotifier of the pure status drives the HUD. No package, one dispose.
final ValueNotifier<GameStatus> status = ValueNotifier(GameStatus.menu);
// ...
ValueListenableBuilder<GameStatus>(
  valueListenable: status,
  builder: (_, value, __) => HudBanner(status: value),
);
// remember: status.dispose() in State.dispose / onRemove.
```

---

## 8. Asset & localization structure

### Assets

- **Typed paths, no literals.** Wonderous's `assets.dart` exposes every asset as a `static const`
  (or use `flutter_gen`). A renamed/missing file becomes a compile error.
- **Resolution variants** (`2.0x/`, `3.0x/`) for raster art; declare the base path in `pubspec.yaml`
  and let Flutter pick. Prefer **vector / `CustomPainter` shapes** for simple game art — they scale
  cleanly across the §4 device range and keep the bundle tiny (and dodge copyright: placeholder
  vectors / user-owned assets only, per the skill's asset rule).
- **Group by feature** (`assets/levels/`, `assets/images/<feature>/`, `assets/audio/`); keep
  **levels as JSON data**, not Dart, loaded through a `LevelRepository`.
- **Fonts**: declare in `pubspec.yaml`; bundle the glyph ranges your locales need.

### Localization

Wonderous ships an `l10n/` directory; the framework path is `flutter_localizations` +
`gen_l10n` (ARB files → a generated `AppLocalizations`).

```yaml
# pubspec.yaml
flutter:
  generate: true        # turns on gen_l10n
```

```yaml
# l10n.yaml
arb-dir: lib/l10n
template-arb-file: app_en.arb
output-localization-file: app_localizations.dart
```

- **No user-facing string literal in a widget.** Route every label through
  `AppLocalizations.of(context)`. The pure model exposes *data* (e.g. `matched: 3, total: 12`); the
  UI formats it into a localized, pluralized string (`intl` plurals) — keeping the core
  Flutter-free *and* translatable.
- **Locale persistence** lives in settings (Wonderous has a dedicated `locale_logic.dart`), on
  device, like everything else.
- **Localize for the kids context**: keep copy short, age-appropriate, and verified after layout —
  some languages run 30–40% longer and must not overflow buttons at the largest text scale.

---

## 9. Error, empty, and loading states

A prototype shows the happy path; a shippable game handles the other three. Every screen that can
be empty, loading, or failing must render a deliberate state — never a blank screen, a raw
exception, or an infinite spinner.

- **Loading** — show progress only past a perceptible threshold (don't flash a spinner for a 50 ms
  load). Wonderous's bootstrap-gated splash (§3) is the app-level version: hold on splash until
  assets/save are ready, then route. For in-game loads, a determinate bar beats an indeterminate
  spinner when you know the size.
- **Empty** — "no saved games yet," "no levels unlocked," "no high scores" get a designed empty
  state with a clear next action (a Start button), not a bare `Container`.
- **Error** — wrap async repository calls; on failure show a friendly, kid-appropriate message
  ("Couldn't load that level — try again") with a retry, and **fall back to a safe state** (return
  to menu) rather than a stuck screen. For a kids/offline game most "errors" are local
  (corrupt/missing save, malformed level JSON): tolerate them (defaulted `fromJson`, per the Dart
  quality bar — never `!` external data) instead of crashing.

A compact way to make this non-optional is a sealed result the UI must exhaust:

```dart
// Pure-Dart load result — the UI switch is exhaustive, so "forgot the error case" won't compile.
sealed class LoadState<T> {
  const LoadState();
}
final class Loading<T> extends LoadState<T> { const Loading(); }
final class Loaded<T> extends LoadState<T> { const Loaded(this.value); final T value; }
final class Empty<T> extends LoadState<T> { const Empty(); }
final class Failed<T> extends LoadState<T> { const Failed(this.message); final String message; }

Widget build(BuildContext context) => switch (state) {
      Loading() => const _Spinner(),
      Empty() => const _EmptyState(),
      Loaded(:final value) => _Content(value),
      Failed(:final message) => _ErrorRetry(message),  // analyzer fails the build if a case is missing
    };
```

Crash reporting note: a kids/offline build does **not** ship a remote crash/analytics sink
(`monetization-policy`/kids-safety). Handle errors locally and log to console only.

---

## 10. Production UX: haptics, transitions, onboarding

The details that make a game feel finished — and where `itsallwidgets.com`-grade apps separate
from prototypes.

### Haptics

- Fire `HapticFeedback` (`lightImpact` / `mediumImpact` / `selectionClick`) on meaningful events:
  a correct match, a piece snapping into place, a button press, a win. Keep it *light and
  purposeful* — constant buzzing is noise.
- **Respect the platform & the user.** Gate it behind a settings toggle (persisted on device with
  the other settings) and don't rely on haptics as the *only* feedback channel (accessibility:
  pair with sound + a visible state change). On web/desktop it's a no-op — guard for it.

### Transitions

- Use go_router `CustomTransitionPage` and drive duration from `$styles.times.pageTransition`
  (~200 ms, Wonderous's value) so every route change feels the same.
- Match the transition to the action: a shared-element/`Hero` for "tap a level to open it," a
  fade/slide for menu ↔ play. Keep them short — a slow transition between every screen makes a
  game feel sluggish.
- Pause the simulation across a transition (Flame `pauseEngine()` / overlay swap; see
  `flutter-game-architecture.md` §Mode 3) so nothing advances under the menu.

### Onboarding

- Wonderous gates first-run on `settingsLogic.hasCompletedOnboarding` (verified) and routes intro
  vs home accordingly. Do the same: a persisted `hasOnboarded` flag, checked in the `redirect`
  guard, so onboarding shows **once**.
- For a kids game keep it **wordless or near-wordless** — a short interactive "try the mechanic"
  beats a text wall (and dodges localization for the most-seen screen). Make it skippable, and never
  put a sign-up/account/marketing step in it (kids-safety: no accounts, no external links).
- A parental gate (a task a young child can't do — arithmetic/date challenge, per
  `flutter-games-toolkit.md` §4.5) belongs *before* any sensitive action, surfaced through the same
  `redirect` mechanism — not as ad-hoc dialog logic.

### The small stuff that reads as "polished"

- A real app icon + adaptive icon + splash (`flutter_native_splash`/`flutter_launcher_icons`),
  set once after renaming the package.
- Consistent system chrome (status-bar style, locked orientation set at bootstrap, immersive mode
  for full-screen play) — Wonderous configures these in `AppLogic`.
- Tactile button states (pressed/disabled), focus rings for pointer/keyboard, and a back/escape
  affordance on every non-root screen.

---

## 11. Production-quality handoff checklist

- [ ] **Structure** feature-first; rendering-free core under `models/`+`systems/` imports neither
      `package:flutter` nor `package:flame`; UI/logic/data roles are distinct (§1–2).
- [ ] **Navigation** via go_router with centralized paths (typed routes where >2 params), a
      `redirect` startup/parental-gate guard, and deep links that can't bypass gates and validate
      params (§3).
- [ ] **Responsive**: one scale factor off `shortestSide` feeds the token system; `LayoutBuilder`
      for component layout; `SafeArea` honored; orientation decided once at bootstrap (§4).
- [ ] **Adaptive**: phone single-pane vs tablet/iPad multi-pane handled; platform back/scroll
      physics respected; pointer/keyboard supported where plausible (§4).
- [ ] **Design tokens**: an `AppStyle`/`$styles` object owns colors, a spacing scale, named
      durations; no magic numbers or bare durations at call sites; light/dark + high-contrast (§5).
- [ ] **Animation budget**: implicit/`flutter_animate` for UI, controllers (disposed) for
      choreography, the game loop for simulation; 60 fps held in profile mode; `RepaintBoundary`
      around hot regions; Reduce-Motion fallback for every animation (§6).
- [ ] **State management** is the lightest wire that fits (`ValueNotifier` default → `provider`
      when ≥2 screens share → Riverpod/Bloc only with a written justification); always a thin
      adapter over the pure controller (§7).
- [ ] **Assets** are typed (no literal paths), grouped by feature, vector-first; **levels are
      JSON**; placeholder/user-owned art only (§8).
- [ ] **Localization** via `gen_l10n`/ARB; no user-facing string literal in a widget; copy verified
      at the largest text scale; locale persisted on device (§8).
- [ ] **Every screen** renders deliberate loading / empty / error states (sealed `LoadState`
      exhausted by the UI); external data parsed null-safely; no remote crash sink (§9).
- [ ] **Production UX**: purposeful, toggleable haptics (not the only feedback); short consistent
      transitions with the simulation paused; once-only, near-wordless, account-free onboarding;
      icon/splash/system-chrome set (§10).
- [ ] **Quality bar still green**: `dart format`, `dart analyze --fatal-infos --fatal-warnings`,
      `dart test` (pure core, VM) all pass; everything disposed; seeded `Random` injected.

> No store-approval or quality guarantees — this is a checklist plus a risk list. Wonderous,
> `flutter/samples`, `flutter/demos`, and the official architecture guide demonstrate the
> *patterns*; the shipped binary is what Apple/Google review. Treat `flutter/demos` as
> technique-only (unmaintained), and scale Wonderous's depth **down** to what a casual game needs.
