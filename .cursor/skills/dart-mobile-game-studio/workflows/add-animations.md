# Workflow: Add Animations

**Goal:** Add UI/game animation (implicit, explicit, staggered, transitions) that respects reduce-motion and stays in the view layer — never in the pure-Dart model.

## When to use
- Adding motion to a Flutter-widget game (menus, HUD, score pops, card flips, page/route transitions, list reorders).
- Adding motion to a Flame component (tween a sprite's position/scale/opacity, juice on collect/hit, spawn/despawn).
- Polishing an existing screen with entrance/exit transitions or staggered reveals.

Do **not** use this to drive game *state*. Animation is presentation only — see "Doctrine" below.

## Prerequisites
- A working game with the model/view split already in place (pure Dart core under `lib/src/game/` or similar, no `package:flutter` import).
- For Flame motion: components already on screen and updating via `update(dt)`.
- Familiarity with `references/ui-and-animations.md` (the canonical reference this workflow operationalizes) and `references/performance-checklist.md`.

## Doctrine (read first — non-negotiable)
1. **Animation lives in the view, never in the model.** The pure-Dart model holds discrete truth (a tile's logical position, a score, a `GameStatus`). Animation interpolates *between* model states for the eye only. The model must produce identical results whether or not anything is animating, and `dart test` must never touch an `AnimationController`, `Ticker`, or Flame `Effect`.
2. **Reduce motion is a hard gate, not a nice-to-have.** Every non-essential animation must collapse to its end state (or a crossfade) when the OS requests reduced motion. Kids-safety (Apple Kids + Google Play Families) and accessibility both depend on this. See Step 5.
3. **Pick the cheapest tool that works.** Implicit < explicit < hand-driven `AnimatedBuilder`. Reach for an `AnimationController` only when implicit widgets can't express it (see decision table).
4. **Pay the const + RepaintBoundary tax.** An animating subtree repaints every frame; isolate it so it doesn't drag static siblings with it (Step 6).

## Decision table — which animation kind?

| Need | Use | Notes |
|---|---|---|
| One property eases to a new value when state changes (size, color, padding, alignment, opacity) | **Implicit** — `AnimatedContainer`, `AnimatedOpacity`, `AnimatedAlign`, `AnimatedPadding`, `AnimatedPositioned`, `TweenAnimationBuilder` | No controller, no `dispose`. Cheapest. Default choice. |
| Swap one widget for another (win banner ↔ board, icon A ↔ icon B) | **Transition** — `AnimatedSwitcher` | Give children distinct `Key`s so it detects the swap. |
| Repeating, reversing, or precisely-timed motion driven by you (pulse, bounce, progress, custom curve) | **Explicit** — `AnimationController` + `*Transition`/`AnimatedBuilder` | Needs `vsync`, `dispose`. |
| Several elements animate on the same timeline with offset starts (menu items cascading in, board tiles revealing) | **Staggered** — one `AnimationController` + per-child `Interval` | One controller, many `CurvedAnimation(curve: Interval(...))`. |
| Element flies between two screens/positions on navigation | **Hero** — `Hero(tag: ...)` on both routes | Tags must match and be unique per pair. |
| Motion of a Flame component (sprite move/scale/opacity/rotate, juice, spawn/despawn) | **Flame `Effect`** — `MoveEffect`, `ScaleEffect`, `OpacityEffect`, `RotateEffect`, `SequenceEffect` | Driven by Flame's own clock; no Flutter controller. |

---

## STEPS

### 1. Classify the request, then locate the seam
Map the request to a row in the decision table. Confirm the value being animated already comes from the model (or from a controller/notifier reading the model) — you animate *toward* model state, you do not store animation progress in the model. If the value isn't exposed to the view yet, expose it first; only then animate.

### 2. Implicit animation — the default (Flutter-widget mode)
Prefer this whenever a single property eases to a new value. No controller, nothing to dispose.

```dart
// Rebuilds with a new color/size → the widget eases there over `duration`.
AnimatedContainer(
  duration: const Duration(milliseconds: 250),
  curve: Curves.easeOut,
  width: selected ? 96 : 72,
  decoration: BoxDecoration(
    color: selected ? Colors.amber : Colors.blueGrey,
    borderRadius: BorderRadius.circular(12),
  ),
);
```

For a one-shot tween on first build (e.g. a score number counting up) without a controller, use `TweenAnimationBuilder`:

```dart
TweenAnimationBuilder<double>(
  tween: Tween(begin: 0, end: score.toDouble()),
  duration: const Duration(milliseconds: 400),
  builder: (context, value, _) => Text(value.round().toString()),
);
```

### 3. Transition between two widgets — `AnimatedSwitcher`
Use for state swaps (board → win banner, paused → playing). Distinct `Key`s are required, or it treats them as the same widget and skips the transition.

```dart
AnimatedSwitcher(
  duration: const Duration(milliseconds: 300),
  child: status == GameStatus.won
      ? const WinBanner(key: ValueKey('win'))
      : GameBoard(key: const ValueKey('board'), state: state),
);
```

### 4. Explicit animation — `AnimationController` (only when implicit can't)
Use for repeating/reversing/precisely-curved motion. Driven by a `Ticker`, so it needs a `vsync` and **must** be disposed.

```dart
class _PulseState extends State<Pulse> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 600),
  )..repeat(reverse: true); // gate this in Step 5

  @override
  void dispose() {
    _c.dispose(); // MANDATORY — leaking a controller leaks a Ticker.
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => ScaleTransition(
        scale: Tween(begin: 1.0, end: 1.15).animate(
          CurvedAnimation(parent: _c, curve: Curves.easeInOut),
        ),
        child: widget.child,
      );
}
```

- `SingleTickerProviderStateMixin` for one controller; `TickerProviderStateMixin` for several.
- Prefer a built-in `*Transition` (`FadeTransition`, `ScaleTransition`, `SlideTransition`, `RotationTransition`) over a raw `AnimatedBuilder`; reach for `AnimatedBuilder` only when no transition widget fits.

### 5. Reduce-motion gate (do this for EVERY animation you add)
Read the OS preference once and branch. This is the gate, not an afterthought.

```dart
final reduceMotion = MediaQuery.of(context).disableAnimations;
```

Apply it per animation kind:
- **Implicit / transition:** set `duration: reduceMotion ? Duration.zero : const Duration(milliseconds: 250)`. The widget jumps to its end state — correct and non-disorienting.
- **Explicit (controller):** do **not** call `repeat()`/`forward()` when `reduceMotion` is true; jump the controller to its end (`_c.value = 1.0`) so the view shows the final frame. For decorative loops (pulse, idle bob), skip the animation entirely and render the resting state.
- **Hero / route transitions:** prefer a plain crossfade or no transition over large transl/scale moves.
- **Flame effects (Step 8):** when `reduceMotion`, apply the end state immediately — e.g. set `position`/`scale`/`opacity` to the target instead of adding the `Effect` (use a 0-duration controller or skip the effect and call the mutation directly).

Centralize it so you set the policy once:

```dart
Duration motion(BuildContext context, Duration d) =>
    MediaQuery.of(context).disableAnimations ? Duration.zero : d;
```

Essential, information-bearing motion (e.g. a progress bar that *is* the feedback) may stay, but minimize amplitude. When in doubt, collapse it.

### 6. Pay the const + RepaintBoundary tax
An animating subtree repaints every frame. Two cheap, mandatory habits:
- **`const` every static widget** in and around the animated subtree so Flutter skips rebuilding them. (The analyzer's `prefer_const_constructors` enforces this — keep it analyzer-clean.)
- **Wrap the animated subtree in `RepaintBoundary`** so its per-frame repaints don't invalidate static siblings.

```dart
RepaintBoundary(
  child: ScaleTransition(scale: _scale, child: const _Coin()),
);
```

Verify with DevTools' "Highlight repaints" — only the animated box should flash. See `references/performance-checklist.md`.

### 7. Staggered reveal — one controller, per-child `Interval`
For a cascade (menu items, board tiles), drive **one** controller and give each child a `CurvedAnimation` whose curve is an `Interval` covering a slice of `[0,1]`.

```dart
class _MenuState extends State<Menu> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 600),
  );

  Animation<double> _slot(int i, int n) {
    final start = (i / n) * 0.5;        // last item starts at 50% of the timeline
    return CurvedAnimation(
      parent: _c,
      curve: Interval(start, (start + 0.5).clamp(0.0, 1.0), curve: Curves.easeOut),
    );
  }

  @override
  void initState() {
    super.initState();
    if (!WidgetsBinding.instance.platformDispatcher.accessibilityFeatures.disableAnimations) {
      _c.forward();        // gate per Step 5
    } else {
      _c.value = 1.0;      // reduced motion: show final state, no cascade
    }
  }

  @override
  void dispose() { _c.dispose(); super.dispose(); }
  // build: for each item i, FadeTransition+SlideTransition driven by _slot(i, items.length).
}
```

One controller for N children keeps it cheap and the timeline coherent.

### 8. Flame component motion — use `Effect`s, not the model
For Flame (or hybrid `GameWidget`) mode, animate components with built-in effects driven by Flame's own clock. Do **not** hand-roll easing in `update(dt)` for these. The component's *logical* state still lives in the pure-Dart model; the effect just moves the visual.

```dart
import 'package:flame/effects.dart';

// Move + scale juice on collect, then remove:
component.add(
  SequenceEffect([
    ScaleEffect.by(Vector2.all(1.3), EffectController(duration: 0.15, alternate: true)),
    MoveEffect.to(targetPos, EffectController(duration: 0.25, curve: Curves.easeIn)),
    OpacityEffect.to(0, EffectController(duration: 0.2)), // component must implement OpacityProvider
    RemoveEffect(),
  ]),
);
```

- `EffectController` takes `duration`, `curve`, `alternate`, `reverseDuration`, `infinite`, `startDelay` — compose loops/ping-pong there, not in your own counters.
- `OpacityEffect` requires the target to provide opacity (e.g. a `SpriteComponent`/`HasPaint` mixin).
- Reduce-motion: when `disableAnimations`, skip the effect and apply the final mutation directly (set `position`/`opacity`, or `add(RemoveEffect())` alone) so the outcome is identical without the motion.
- Effects auto-remove when finished; `RemoveEffect()` despawns the component. Don't leak effects on components you keep — they clean themselves up on completion.

### 9. Route/page transitions
Use `PageRouteBuilder` with a `transitionsBuilder` (or `MaterialPageRoute` defaults) and a `Hero` for shared elements between screens. Gate large transitions to a crossfade under reduced motion (Step 5). Keep transition durations short (200–300 ms) for a game's snappy feel.

---

## Done when
- Each animation maps to the cheapest tool from the decision table (implicit unless it genuinely can't express the motion).
- **Every** animation has a reduce-motion branch that collapses to the end state / crossfade; toggled "Reduce Motion" in the OS simulator and confirmed no large or looping motion remains.
- Every `AnimationController` (and any manual `Ticker`) is `dispose`d; no controller created in `build`.
- The animated subtree is wrapped in `RepaintBoundary` and surrounded by `const` widgets; DevTools "Highlight repaints" shows only the animated box flashing.
- `dart analyze` is clean; `dart format` (2-space) applied; no `package:flutter` import crept into the model.
- `dart test` on the pure-Dart core still passes unchanged — proving animation added zero logic to the model.

## Common pitfalls
- **Animation state in the model.** Storing controller `.value`, "is animating", or interpolated positions in the pure-Dart core. Truth is discrete; the view interpolates. This breaks `dart test` determinism — keep it out.
- **Forgetting `dispose`.** A leaked `AnimationController` leaks a `Ticker` that keeps ticking off-screen; the analyzer won't always catch it.
- **Creating a controller in `build`.** Re-creates it every rebuild. Create in `initState` (or a `late final` field), dispose in `dispose`.
- **No reduce-motion gate.** The single most common omission; it's a kids-safety/accessibility failure, not cosmetic. Gate every animation.
- **`AnimatedSwitcher` children without distinct `Key`s.** It sees them as the same widget and skips the transition.
- **No `RepaintBoundary`.** The whole screen repaints every frame; janks on low-end Android. Isolate the animated subtree.
- **Hand-rolling easing in Flame `update(dt)`** when a built-in `Effect` exists — more code, more bugs, and you still owe a `dt` clamp. Use effects.
- **Long durations.** Games feel sluggish above ~300 ms for UI feedback; reserve longer durations for deliberate, essential motion.

## Cross-links
- `references/ui-and-animations.md` — canonical reference for this workflow (curves catalog, transition widgets, juice patterns).
- `references/performance-checklist.md` — `const`/`RepaintBoundary`/repaint-profiling detail.
- `references/accessibility-child-safety.md` — reduce-motion, Apple Kids + Google Play Families expectations.
- `references/flutter-flame-patterns.md` — Flame `Effect`/`EffectController` patterns and the component/model split.
