# UI and animations

Building polished **game UI** and **motion** in Flutter — the screens around the core loop and the
transitions between them. This is the *menu/HUD/chrome* layer: main menu, start, victory/defeat,
settings, shop, inventory, level selection, onboarding, and the pause overlay, plus the animated
buttons and route transitions that stitch them together. Everything here is the **thin renderer**
over the pure-Dart core (`lib/models/`, `lib/systems/`) — screens read an immutable model and emit
intents; no game rules live in a `build` method or an animation callback. Format with
`dart format` (2-space indent, trailing commas for vertical layout); keep zero analyzer issues.

It pairs with `dart/flutter-widgets-mastery.md` (stateless/`const`/keys/`dispose`/`Semantics`
fundamentals — assumed here, not repeated), `flutter-game-architecture.md` (the model⇄render seam
and state-management table), and `performance-checklist.md` (the frame-budget rules these patterns
must obey). The non-negotiable thread running through all of it: **gate non-essential motion on
`MediaQuery.disableAnimations`**, and keep every screen `const`-dense with a `RepaintBoundary`
around anything that animates.

Verified against docs.flutter.dev/ui/widgets/{material,cupertino,animation}, /ui/animations
(the implicit-vs-explicit decision tree), and the cookbook galleries (page-route-animation,
hero-animations, staggered-menu-animation). API names below are quoted from those sources.

## The screen map — a state machine of routes and overlays

A simple game is a small, fixed set of screens driven by the same `GameStatus` the core already
owns (`menu → playing → paused → won/lost → menu`; see `flutter-game-architecture.md`). Two
mechanisms move between them, and choosing right is the first design decision:

- **Routes** (`Navigator` / a router) — for screens that *replace* what's on top and have their own
  back affordance: main menu → level selection → settings → shop → inventory → onboarding. These
  get **route transitions** (below).
- **Overlays** — for things that sit *on top of* live gameplay without tearing it down: the **pause
  overlay**, a victory/defeat card, a hint toast. In Flutter-widgets mode use a `Stack` (or
  `showDialog` / `OverlayEntry`); in Flame/hybrid mode use the game's `overlayBuilderMap` +
  `overlays.add/remove` so the loop can keep its components mounted while paused
  (`pauseEngine()`/`resumeEngine()` — see `flutter-game-architecture.md`).

| Screen | Mechanism | Notes |
|---|---|---|
| Main menu | Root route | Entry; Play / Continue / Settings / Shop. |
| Start / level selection | Route (often `Hero` from the menu's Play button) | Grid of levels; locked/unlocked from save model. |
| Onboarding | Route, shown once | First-run only; gate on a `seenOnboarding` flag in the save model — never re-show. |
| Playing | Route (hosts the board / `GameWidget`) | The only screen that runs a loop. |
| Pause | **Overlay** over Playing | Loop paused; Resume / Restart / Quit. Never a separate route. |
| Victory / Defeat | **Overlay** over Playing | Result card; Next / Retry / Menu. Animate in, but keep the board visible behind. |
| Settings | Route | Toggles (sound, music, reduce-motion override, haptics); writes the save model. |
| Shop / Inventory | Route | Cosmetic-only for kids titles — see `monetization-policy.md`; no rules live here. |

> The screen the player is on is a **function of `GameStatus`**, not an independent variable. Drive
> route/overlay changes from status transitions in one place (a `ValueListenableBuilder<GameStatus>`
> or a router redirect), so back-button, win, and quit can't desync the UI from the model.

## Animated buttons — the smallest motion, done right

Every tap target in a game should give tactile feedback. The cheapest correct version is an
**implicit** scale-on-press; you do not need an `AnimationController` for a button.

```dart
// A reusable, const-friendly, Reduce-Motion-aware game button. Owns one bool of *visual* state
// (pressed) — that is a disposable-free StatefulWidget, allowed by the widget-layer rules.
class GameButton extends StatefulWidget {
  const GameButton({required this.label, required this.onPressed, super.key});
  final String label;
  final VoidCallback onPressed;

  @override
  State<GameButton> createState() => _GameButtonState();
}

class _GameButtonState extends State<GameButton> {
  bool _pressed = false;

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.of(context).disableAnimations;
    return Semantics(
      button: true,
      label: widget.label,
      child: GestureDetector(
        onTapDown: (_) => setState(() => _pressed = true),
        onTapCancel: () => setState(() => _pressed = false),
        onTapUp: (_) => setState(() => _pressed = false),
        onTap: widget.onPressed, // the intent; rules live in the core
        child: AnimatedScale(
          scale: _pressed ? 0.94 : 1.0,
          duration: reduceMotion ? Duration.zero : const Duration(milliseconds: 90),
          curve: Curves.easeOut,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minWidth: 88, minHeight: 48), // kids/a11y target
            child: const _ButtonChrome(), // const: built once, never per-frame
          ),
        ),
      ),
    );
  }
}
```

- **DO** prefer built-in buttons (`FilledButton`, `ElevatedButton`, `OutlinedButton`, `TextButton`,
  `IconButton`, `FloatingActionButton`) when their look fits — they ship correct ink/press
  feedback, focus, and `Semantics` for free, and Material 3 (the Flutter default since 3.16) styles
  them from your `ColorScheme`. Reach for a custom `GameButton` only when the visual identity
  demands it.
- **DO** keep the moving wrapper (`AnimatedScale`) shallow and the chrome inside it `const`, so the
  per-press rebuild touches only a `Transform`.
- **DON'T** drive a press scale with an `AnimationController` you have to `dispose` — that's the
  explicit toolkit for *looping/continuous* motion, not a one-shot toggle.
- **DON'T** put game logic in the tap callback; emit a single intent (covered in
  `dart/flutter-widgets-mastery.md`).

For a looping attention pulse on a primary CTA ("Play"), use the explicit `AnimationController` +
`AnimatedBuilder` pattern from `flutter-widgets-mastery.md`, and **only `repeat()` when
`!disableAnimations`** — a pulsing button is exactly the kind of motion Reduce Motion turns off.

## Route transitions — Hero, PageRouteBuilder, AnimatedSwitcher

Three tools, by intent:

### Hero — a shared element that flies between screens

A `Hero` animates a single widget across a route push/pop by matching `tag`s on the two screens.
Use it for continuity: the level thumbnail on the selection grid that grows into the playing
screen's header, or a coin icon that flies from the HUD to the shop.

```dart
// On the level-select grid:
Hero(tag: 'level-${level.id}', child: LevelThumbnail(level: level)),

// On the destination (playing) screen — SAME tag, and only one widget per tag per screen:
Hero(tag: 'level-${level.id}', child: LevelHeader(level: level)),
```

- **DO** make tags unique and stable (`'level-$id'`), and place exactly one `Hero` per tag on each
  screen — duplicate tags throw.
- **DO** supply a `flightShuttleBuilder` if the two widgets differ enough that the default
  cross-fade looks wrong.
- **DON'T** wrap large/complex subtrees in a `Hero`; it lifts the widget into an overlay for the
  flight. Hero a small image/icon, not a whole panel.

### PageRouteBuilder — a custom transition for a route

When you push a route and want a specific motion (slide a settings sheet up, fade the menu in),
build the route yourself and compose a transition widget — `SlideTransition`, `FadeTransition`,
`ScaleTransition` — driven by the route's `animation`. This is the cookbook pattern, verbatim
shape:

```dart
Route<void> _slideUpRoute(Widget page) {
  return PageRouteBuilder<void>(
    pageBuilder: (context, animation, secondaryAnimation) => page,
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      // Reduce Motion: skip the slide, hand back the child unmoved.
      if (MediaQuery.of(context).disableAnimations) return child;
      final tween = Tween(begin: const Offset(0, 1), end: Offset.zero)
          .chain(CurveTween(curve: Curves.easeOut));
      return SlideTransition(position: animation.drive(tween), child: child);
    },
    transitionDuration: const Duration(milliseconds: 250),
  );
}
```

- **DO** gate inside `transitionsBuilder`: when `disableAnimations` is true, `return child` so the
  push is instant. (`transitionDuration` still elapses but nothing moves — for a hard snap you can
  also push a `PageRouteBuilder` with zero duration when reduced.)
- **DO** drive transitions from the supplied `animation` (forward push) and use `secondaryAnimation`
  to animate the *outgoing* screen when a new route covers it.
- **DON'T** hand-roll an `AnimationController` for route motion — the `Navigator` already provides
  the `Animation`; reuse it.

### AnimatedSwitcher — cross-fade in place, no route

For swapping content *within* one screen — a HUD digit rolling over, a level card replacing the
previous, "Tap to start" giving way to the running board — `AnimatedSwitcher` tweens between an old
and new child whenever the child's **key** changes.

```dart
AnimatedSwitcher(
  duration: MediaQuery.of(context).disableAnimations
      ? Duration.zero
      : const Duration(milliseconds: 200),
  transitionBuilder: (child, anim) => FadeTransition(opacity: anim, child: child),
  child: KeyedSubtree(key: ValueKey(status), child: _screenFor(status)), // key drives the swap
);
```

- **DO** give each distinct child a unique `Key` (`ValueKey(status)` / `ValueKey(card.id)`); without
  a changed key `AnimatedSwitcher` sees "the same child" and won't transition. (Key identity rules:
  `dart/flutter-widgets-mastery.md`.)
- **DON'T** use it for list reordering — that's `AnimatedList`/`ReorderableListView` territory.

## Implicit vs explicit vs staggered — the decision tree

Flutter's own animation docs put this as a tree; follow it top-down and stop at the first match.

| You have… | Use | Why |
|---|---|---|
| A start and end value, fire-and-forget (button press, panel resize, fade a hint in) | **Implicit** — `AnimatedContainer`, `AnimatedOpacity`, `AnimatedAlign`, `AnimatedScale`, `AnimatedPositioned`, `TweenAnimationBuilder` | Zero controller, nothing to `dispose`; just swap the property. |
| Looping, reversible, or continuously-driven motion (pulse, shake-on-wrong, coin spin, progress) | **Explicit** — `AnimationController` + `Tween` + `CurvedAnimation`, rendered via `AnimatedBuilder` | You need `vsync`, `repeat`/`reverse`, status listeners, exact control. |
| Several sub-animations with offset timing off **one** clock (menu items cascading in, victory stars popping in sequence) | **Staggered** — one `AnimationController` + per-element `Interval` curves | One ticker, deterministic ordering, no controller-herding. |

### Implicit — the default

```dart
final reduceMotion = MediaQuery.of(context).disableAnimations;
AnimatedOpacity(
  opacity: hintVisible ? 1 : 0,
  duration: reduceMotion ? Duration.zero : const Duration(milliseconds: 250),
  child: const HintBadge(),
);
```

No `State` resource, no leak. Most menu/HUD polish is implicit.

### Explicit — when you own the clock

You hold an `AnimationController` in a `State` with `SingleTickerProviderStateMixin` (the `vsync`
that pauses offscreen animations), shape it with a `Tween` + `CurvedAnimation` (`Curves.easeInOut`,
`Curves.elasticOut`, `Curves.bounceOut`, …), wrap **only the moving subtree** in `AnimatedBuilder`,
pass the static part as its `const child`, and **`dispose` the controller**. Full canonical example
in `dart/flutter-widgets-mastery.md`. The Reduce-Motion gate for explicit motion is: *don't start
it* —

```dart
@override
void initState() {
  super.initState();
  _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 600));
  // Read disableAnimations from the binding in initState (no MediaQuery context yet).
  if (!WidgetsBinding.instance.disableAnimations) _c.repeat(reverse: true);
}
```

### Staggered — one controller, many intervals

A victory screen that pops stars 1, 2, 3 in sequence, or a menu whose buttons slide in one after
another, is the **staggered** pattern: a single `AnimationController` and a per-item `Interval`
slicing its `[0,1]` timeline, read inside one `AnimatedBuilder`. This is the cookbook
staggered-menu shape:

```dart
class StaggeredStars extends StatefulWidget {
  const StaggeredStars({required this.count, super.key});
  final int count;
  @override
  State<StaggeredStars> createState() => _StaggeredStarsState();
}

class _StaggeredStarsState extends State<StaggeredStars> with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 900));
    // Reduce Motion: jump straight to the final frame instead of playing the sequence.
    if (MediaQuery.maybeOf(context)?.disableAnimations ?? false) {
      _c.value = 1.0;
    } else {
      _c.forward();
    }
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
        animation: _c,
        builder: (context, _) => Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            for (var i = 0; i < widget.count; i++)
              Builder(builder: (context) {
                // Each star animates over its own slice of the shared timeline.
                final t = Interval(i * 0.2, i * 0.2 + 0.4, curve: Curves.easeOutBack)
                    .transform(_c.value);
                return Opacity(
                  opacity: t.clamp(0.0, 1.0),
                  child: Transform.scale(scale: t.clamp(0.0, 1.0), child: const StarIcon()),
                );
              }),
          ],
        ),
      );
}
```

- **DO** use **one** controller and many `Interval`s, not N controllers — it's deterministic and
  cheaper to dispose.
- **DO** for Reduce Motion set `_c.value = 1.0` (final state shown instantly) rather than playing.
- **DON'T** allocate the `Interval`s inside `build` if the list is large/hot; precompute them as
  fields (the cookbook builds them once in `initState`).

## Responsive layout — one UI for iPhone, iPad, Android phones and tablets

Game UI runs on a 5-inch phone and a 13-inch tablet, portrait and landscape. Lay out from
**constraints**, never constants. (Canvas/board responsiveness lives in
`dart/flutter-widgets-mastery.md`; here it's the *chrome*.)

- **`MediaQuery`** — `sizeOf`, `orientationOf`, `paddingOf`, `textScalerOf`, `disableAnimations`.
  Use the targeted `*Of(context)` accessors so a screen subscribes to *only* the field it reads and
  doesn't rebuild on unrelated MediaQuery changes.
- **`LayoutBuilder`** — gives the parent's `BoxConstraints`; branch layout off a width threshold
  (e.g. `> 600` ⇒ tablet) to swap a bottom `NavigationBar` for a side `NavigationRail`, or a single
  column for a two-pane menu.
- **`FractionallySizedBox`** — size a panel as a fraction of the parent (a settings card at 80% width
  on phone, capped on tablet) without hard pixels.
- **`Flexible` / `Expanded`** — distribute space in `Row`/`Column`; `Flexible(flex:)` for ratios,
  `Spacer` to push apart.
- **`SafeArea`** — wrap top-level screens so menus/HUD dodge notches, the status bar, and the home
  indicator. Non-negotiable on modern phones.
- **`OrientationBuilder`** / `AspectRatio` / `FittedBox` — portrait↔landscape swaps and keeping a
  proportional play area.

```dart
SafeArea(
  child: LayoutBuilder(
    builder: (context, constraints) {
      final wide = constraints.maxWidth > 600; // tablet / landscape
      final menu = FractionallySizedBox(
        widthFactor: wide ? 0.5 : 0.86,
        child: const MainMenuColumn(),
      );
      return wide
          ? Row(children: [const Expanded(flex: 2, child: HeroArt()), Expanded(flex: 3, child: Center(child: menu))])
          : Column(children: [const Flexible(child: HeroArt()), Center(child: menu)]);
    },
  ),
);
```

- **DON'T** hard-code widths/heights for panels (`SizedBox(width: 400)`); they overflow a small
  phone and strand a tablet. Drive size from constraints/fractions.
- **DON'T** lock font sizes — honor `MediaQuery.textScalerOf(context)` so large Dynamic Type doesn't
  clip a "Victory!" banner.

## Material vs Cupertino — and adaptive widgets

Flutter ships two design languages. A cross-platform game can pick one look and use it everywhere
(simplest, most games), or **adapt** per platform.

- **Material** (default, Material 3) — `MaterialApp`, `Scaffold`, `AppBar`, `NavigationBar`,
  `NavigationRail`, `Drawer`, `FilledButton`/`ElevatedButton`/`TextButton`, `AlertDialog`
  (`showDialog`), `BottomSheet` (`showModalBottomSheet`), `SnackBar`. Themed from `ThemeData` +
  `ColorScheme`.
- **Cupertino** (iOS look) — `CupertinoApp`, `CupertinoPageScaffold`, `CupertinoNavigationBar`,
  `CupertinoTabScaffold`/`CupertinoTabBar`, `CupertinoButton`, `CupertinoAlertDialog`
  (`showCupertinoDialog`), `CupertinoActionSheet`, `CupertinoSwitch`, `CupertinoSlider`,
  `CupertinoPicker`, `CupertinoActivityIndicator`, `CupertinoPageRoute`. Themed from
  `CupertinoThemeData`.

**Adaptive widgets** are the middle path — one widget that renders the platform's native control:

```dart
Switch.adaptive(value: soundOn, onChanged: setSound);   // CupertinoSwitch on iOS, Material elsewhere
Slider.adaptive(value: volume, onChanged: setVolume);
showAdaptiveDialog(context: context, builder: ...);     // adaptive AlertDialog
const CircularProgressIndicator.adaptive();
// Theme.of(context).platform / defaultTargetPlatform to branch manually when needed.
```

Doctrine for this skill: **a stylized game usually wants one consistent custom look** (themed
Material is the pragmatic base on both stores), so don't reach for full Cupertino mirroring by
default. *Do* use `*.adaptive` for the handful of **system-feel controls** in settings (switches,
sliders, the activity spinner, confirm dialogs) so they feel native, and use a platform-correct
**page transition** (Material's shared-axis-ish default vs `CupertinoPageRoute`'s edge-swipe-back)
where it matters. Justify any decision to maintain two full UI trees — it rarely pays off for a
simple game.

## Theming — define it once, read it everywhere

Centralize color, type, and shape so screens stay consistent and a dark/high-contrast variant is a
one-line swap.

```dart
final theme = ThemeData(
  useMaterial3: true,
  colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF3366CC)),
  // Component themes keep every button/dialog on-brand without per-call styling:
  filledButtonTheme: FilledButtonThemeData(style: FilledButton.styleFrom(/* shape, padding */)),
);
MaterialApp(theme: theme, darkTheme: ThemeData(/* … dark ColorScheme … */), home: const MainMenu());
```

- **DO** read tokens via `Theme.of(context)` / `Theme.of(context).colorScheme` /
  `Theme.of(context).textTheme` rather than hard-coding `Color`s and `TextStyle`s in screens — that
  is how Reduce-Motion's sibling settings (high contrast, dark mode, bold text) propagate for free.
- **DO** keep game-specific palettes (tile colors, team colors) in a small `style/` constants file
  the painter/components read, separate from the Material `ThemeData` for chrome.
- **DON'T** scatter literal hex colors and magic font sizes across screens; centralize, then theme
  the dark/high-contrast variants once.

## Keep the UI thin over the model — the same seam, restated

Screens, transitions, and animations are **renderer concerns**. They read the immutable model and
emit intents; they never hold authoritative rules.

- A victory overlay shows because `status == GameStatus.won`, computed in the **core**; the overlay
  just renders the result and offers Next/Retry intents.
- A shop screen lists items from the **save/economy model**; tapping "buy" calls one controller
  intent; the model validates affordability and returns a result. No price/affordability logic in
  the widget. (See `monetization-policy.md` for kids-title constraints — cosmetic, no rules in UI.)
- Onboarding "seen" is a **model flag**, persisted; the widget only reads it to decide whether to
  route there.

> Litmus test: if deleting a screen file would lose a *game rule* (a price, a win condition, a level
> unlock), the rule was in the wrong layer. Move it to `lib/models/` or `lib/systems/` and have the
> screen call an intent.

## Performance discipline for UI and motion

These are the frame-budget rules from `performance-checklist.md`, applied to the UI layer — non-
optional for 60 fps on the oldest device:

- **`const` everything that compiles** — static chrome (background, title, frame) should be `const`
  so a per-frame builder skips rebuilding it.
- **`RepaintBoundary` around the animating subtree** (a pulsing button, a sliding panel, the moving
  playfield) so its repaints don't dirty and re-raster the static background. Not around
  *everything* — each boundary has a layer cost.
- **`AnimatedBuilder`/`ListenableBuilder`: pass static subtrees via `child:`** so they build once,
  not every tick.
- **Avoid `Opacity` and clipping in hot paths** — both trigger `saveLayer`. For fades use
  `AnimatedOpacity`/`FadeTransition`; for rounded corners use a `borderRadius` on the decoration, not
  `ClipRRect`.
- **Rebuild the smallest slice** — drive HUD/menus from `ValueListenableBuilder`/`Selector`, never a
  whole-screen `setState` for one field.
- **Dispose every `AnimationController`/`Ticker`/notifier you create**, and guard async callbacks
  with `if (!mounted) return;` — a route's exit animation can outlive the widget.

## The UI-and-animations bar in miniature

1. **Screens are a function of `GameStatus`;** routes replace, overlays sit over live gameplay
   (pause/victory never become separate routes).
2. **Buttons feel tactile** via implicit `AnimatedScale`; prefer built-in buttons; ≥48 px targets.
3. **Transitions by intent** — `Hero` (shared element), `PageRouteBuilder` + `Slide/FadeTransition`
   (custom route), `AnimatedSwitcher` (in-place swap, key-driven).
4. **Pick motion by the tree** — implicit (start/end), explicit (looping/continuous, `dispose` it),
   staggered (one controller + `Interval`s).
5. **Always gate non-essential motion** on `MediaQuery.disableAnimations` (and respect
   `accessibleNavigation`): collapse durations to `Duration.zero`, don't `repeat()`, jump staggered
   controllers to `value = 1.0`. Never override the user's OS choice.
6. **Layout from constraints** — `MediaQuery.*Of` / `LayoutBuilder` / `FractionallySizedBox` /
   `Flexible` / `SafeArea`; tablet vs phone off a width threshold; honor `textScaler`.
7. **One design language by default;** use `*.adaptive` for system-feel controls and a
   platform-correct page transition; justify maintaining two full UI trees.
8. **Theme once** (`ThemeData`/`ColorScheme`/`textTheme`), read via `Theme.of`; no scattered hex.
9. **`const` + `RepaintBoundary`** on animating subtrees; static parts via `AnimatedBuilder`'s
   `child:`; no `Opacity`/clipping in hot paths.
10. **UI stays thin** — read the model, emit intents, `dispose` resources; zero game rules in a
    `build` method or animation callback, zero Flutter imports leaked into the core.
