# Flutter UI quality checklist

A tick-list a reviewer/agent runs over the **renderer layer** (`lib/widgets/`, `lib/game/`
overlays, `lib/style/`). It enforces the policies in `references/dart/flutter-widgets-mastery.md`,
`references/flutter-game-architecture.md`, and `references/performance-checklist.md`; it does not
re-explain them. Check each box or note why it doesn't apply. Verify in **profile mode on a real
device** where a box says "no jank" — debug-mode numbers don't count.

## const & rebuild boundaries
- [ ] Analyzer is clean for `prefer_const_constructors`, `prefer_const_literals_to_create_immutables`, and `prefer_const_constructors_in_immutables` (no `const` left on the table).
- [ ] Every constructor whose fields are all `final` is declared `const` so callers can `const` it.
- [ ] Static chrome (background, frame, title, decorative art) is `const` and is **not** rebuilt inside any animation/per-frame listener.
- [ ] Reusable sub-trees are extracted into named `StatelessWidget` classes, not `Widget _buildFoo()` helper methods (a class is a real rebuild boundary and can be `const`; a method re-runs with its parent).
- [ ] No framework widget is subclassed (`Container`/`Text`/`Padding`/etc.) — composition only.
- [ ] No `build()` is longer than it needs to be — deep nesting is factored into child widgets, each with its own rebuild boundary.

## State ownership & scoped rebuilds (no setState-the-world)
- [ ] Game/data state lives in the pure-Dart core (`models/`+`systems/`); no game rules or mutable game data sit in a `State` field or a `build` method.
- [ ] `StatefulWidget` is used **only** to own a disposable (controller/notifier/focus/subscription/ticker), never to hold data that changes.
- [ ] UI reads the model through the **smallest** listenable slice: `ValueListenableBuilder<T>` for one value, `Selector` for one derived slice — not a top-level `ListenableBuilder`/`Consumer` that rebuilds the whole screen.
- [ ] No `setState()` that rebuilds a whole screen/subtree for a single changed field (score, lives, timer); each is its own `ValueNotifier` + builder.
- [ ] `AnimatedBuilder`/`ListenableBuilder` pass the static part via the `child:` argument so it is built once, not every tick.
- [ ] The listenable seam lives in the pure core or a thin Flutter adapter — `package:flutter` does not leak into `models/`/`systems/`.

## Keys & identity
- [ ] Reorderable/shuffleable lists of stateful or animating children give each item a `ValueKey(domainId)` (e.g. `card.id`), never the list index.
- [ ] A level restart / board reset that must discard old `State` changes a parent `key` (or rebuilds from a fresh root), rather than mutating in place.
- [ ] `GlobalKey` is used only where a `State`/`RenderObject` must be reached across the tree (rare); `ValueKey`/`ObjectKey` is used for list identity.
- [ ] No key collides — keys are unique among siblings.

## RepaintBoundary & paint isolation
- [ ] A `RepaintBoundary` wraps the frequently-animating playfield/sprite so its repaints don't dirty the static background — and is **not** sprinkled on everything (each boundary costs a layer).
- [ ] `CustomPainter.shouldRepaint(old)` returns `true` only on a real input change (lean on model value-equality, e.g. `old.board != board`), never an unconditional `true`.
- [ ] No `Paint`/`Path`/`Gradient`/`TextPainter`/parsed-level allocation happens inside `paint()` or `build()` in a hot path — those are hoisted to fields/`const`.
- [ ] Static and animated paint are split (`painter` vs `foregroundPainter`, or two layers) so only the moving layer repaints.
- [ ] A `CustomPaint` that repaints on a notifier uses `super(repaint: notifier)` rather than rebuilding the widget each frame.

## Responsive layout (phones + tablets)
- [ ] The game surface is wrapped in `SafeArea` so the board/HUD clear notches, status bar, and home indicator.
- [ ] Layout is derived from constraints (`LayoutBuilder` / `MediaQuery`), never fixed pixels; the play area is sized off `min(maxWidth, maxHeight)` to stay square/proportional.
- [ ] HUD/layout adapts between tall phone (top/bottom bar) and wide tablet/landscape (side panel) off an aspect-ratio or width threshold, verified on both a small phone and a large tablet.
- [ ] Portrait/landscape swaps use `OrientationBuilder`; no layout overflows ("yellow-and-black stripes") at any supported size or orientation.
- [ ] `MediaQuery` is subscribed via the targeted `*Of` accessors (`MediaQuery.sizeOf`/`.orientationOf`/`.textScalerOf`) so unrelated MediaQuery changes don't rebuild.
- [ ] `CustomPainter` geometry scales off the passed `Size` (and `devicePixelRatio` when caching), never hard-coded pixels.

## Material / Cupertino correctness
- [ ] The app is rooted in exactly one `MaterialApp` (or `CupertinoApp`); material widgets are under a `Material`/`Scaffold` ancestor (no "No Material widget found" at runtime).
- [ ] Platform-specific widgets aren't mixed incorrectly (a `CupertinoButton` inside a Material flow, or vice-versa, only when intentional); adaptive constructors (`Switch.adaptive`, `Slider.adaptive`, `showAdaptiveDialog`, `CircularProgressIndicator.adaptive`) are used where one codebase should feel native on both iOS and Android.
- [ ] Navigation uses real routes (`Navigator`/router), not `setState`-toggled screens, so back gesture/button, transitions, and the system back work.
- [ ] Tap targets are ≥ 48×48 logical px (larger for kids), enforced with `SizedBox`/`ConstrainedBox`/`MaterialTapTargetSize`; no overlapping gesture detectors fight over one gesture.
- [ ] Built-in interactive widgets (`IconButton`/`FilledButton`/`Slider`) are preferred over hand-rolled painted buttons where a standard control fits (they ship correct semantics + ink/tap states).

## Theming
- [ ] Colors, text styles, and shapes come from `Theme.of(context)` / a central `style/` module — no magic `Color(0x…)` / hard-coded `TextStyle` scattered through widgets.
- [ ] One `ThemeData` (and `darkTheme` if shipped) is defined once at the app root; `ColorScheme.fromSeed` (Material 3) or an explicit scheme is the single source of palette truth.
- [ ] Light/dark are both exercised and legible; nothing is hard-coded to one brightness.
- [ ] Text respects `MediaQuery.textScalerOf` (the non-deprecated `textScaler`, not `textScaleFactor`); no font size is locked such that the largest Dynamic Type clips or overflows.
- [ ] Custom transition style, if any, is set via `ThemeData.pageTransitionsTheme` (`PageTransitionsTheme` with platform `PageTransitionsBuilder`s, e.g. `CupertinoPageTransitionsBuilder` / `ZoomPageTransitionsBuilder`) rather than ad-hoc per-route animations.

## Loading / empty / error states
- [ ] Every async surface (level load, asset/`precacheImage` warmup, save read) renders an explicit **loading** state — not a blank frame or a janky first paint.
- [ ] `FutureBuilder`/`StreamBuilder` (or the state-management equivalent) handle all three of `connectionState`/data, `hasError`, and the empty/`null` case — no unhandled snapshot path.
- [ ] An **error** state is shown with a retry path (e.g. corrupt save, missing level JSON), and the failure is recoverable without a crash; nothing throws into the widget tree unguarded.
- [ ] **Empty** states (no saved progress, empty level list, zero score history) have a designed placeholder, not an accidental zero-height/invisible widget.
- [ ] Async callbacks that touch widget state are guarded with `if (!mounted) return;` so a late `Future`/stream event after dispose can't `setState`.

## No jank in transitions & motion
- [ ] Reduce Motion is honored: `MediaQuery.disableAnimations` / `WidgetsBinding.instance.disableAnimations` is read and durations collapse to `Duration.zero` (motion snaps, never overrides the OS choice).
- [ ] No red bars on the UI **or** raster graph during screen transitions, route pushes, overlay add/remove, and list scroll in normal play (performance overlay / DevTools, profile mode, oldest device).
- [ ] No `saveLayer` triggers in animated/hot paths: avoid the `Opacity` widget (use `AnimatedOpacity`/`Image.opacity`/a semitransparent color), avoid `ClipRRect`/`ClipPath`/`ShaderMask`/`BackdropFilter`/`ColorFilter` mid-animation (prefer `borderRadius` on a decoration).
- [ ] On-screen lists/grids are lazy (`ListView.builder`/`GridView.builder`), never a literal `children:` of off-screen cells.
- [ ] Implicit animations (`AnimatedContainer`/`AnimatedScale`/`TweenAnimationBuilder`) are used for one-shot polish; explicit `AnimationController`s exist only for looping/reversible motion and are gated on Reduce Motion before `.repeat()`.
- [ ] No free-running ticker/animation drives a static menu/paused/win screen; widget-mode UI advances only on real state change (Flame engine paused per `performance-checklist.md`).

## Lifecycle & dispose (renderer hygiene)
- [ ] Every `AnimationController`, `Ticker`, self-created `ValueNotifier`/`ChangeNotifier`, `StreamSubscription`, `FocusNode`, `TextEditingController`, `ScrollController`, `OverlayEntry`, and `Timer` is disposed in `dispose()` (and any `addListener` has a matching `removeListener`).
- [ ] A notifier/controller that was **passed in** (not created here) is not disposed by this widget — the owner disposes it.
- [ ] Disposables are created in `initState`/`didChangeDependencies` and torn down in reverse order in `dispose`.

## Semantics (custom surfaces)
- [ ] Every painted/`GestureDetector`-only control is wrapped in `Semantics` with at least `label` (and `value` for stateful controls, `button: true`, `enabled:`); no silent painted button.
- [ ] Composite controls (icon + text) use `MergeSemantics`; purely decorative art uses `ExcludeSemantics` so the reader isn't spammed with dozens of unlabeled nodes.
- [ ] Key dynamic changes (win/lose, score milestone) are announced once via `liveRegion: true`.

## Format & analyzer gate
- [ ] `dart format` clean (2-space indent, trailing commas for vertical layout) — diff shows no formatting churn.
- [ ] Zero analyzer issues under the project lints (`very_good_analysis`/`flutter_lints`); no `// ignore:` added without a one-line justification.
