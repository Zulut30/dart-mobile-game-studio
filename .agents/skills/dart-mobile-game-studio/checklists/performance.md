# Performance checklist

A tick-list a reviewer/agent runs over a Flutter/Flame mobile game to prove it holds **60 fps with
no jank**. It enforces `references/performance-checklist.md` and `references/dart/dart-memory-performance.md`;
it does not re-explain them — read those for the *why*. Check each box or note why it doesn't apply.

**Profile, don't guess.** Every "no jank / no red bars / fps" box means **profile mode on the oldest
real device** (`flutter run --profile`) — debug builds are deliberately slow and emulators/simulators
hide GPU and GC cost. A box verified only in debug or on a simulator does not count.

## Frame budget (60 fps, no jank)
- [ ] Holds the target frame rate on the **oldest supported device** with low battery: no red bars on
      the **UI** graph **or** the **raster** graph in normal play (performance overlay / DevTools).
- [ ] Budget is met on **both** Flutter threads — UI (`build`/layout/paint + Flame `update`) and raster
      (GPU rasterize) — each under ~16.6 ms (under ~8.3 ms on 120 Hz ProMotion / high-refresh).
- [ ] All motion is **frame-rate independent**: advanced by `dt`, never by a per-frame constant.
- [ ] `dt` is **clamped** (e.g. `dt = min(dt, 1/30)`) so a GC pause or load hitch can't teleport
      objects — Flame does **not** clamp for you.
- [ ] Physics/determinism-sensitive logic runs on a **fixed timestep** (`fixedUpdate` / a fixed-step
      loop), independent of render rate; seeded `Random` stays injected so it's reproducible.

## No work in `build()` / `paint()` (widget mode)
- [ ] No `Paint`/`Path`/`Gradient`/`TextPainter`/parsed-level allocation inside `build()` or
      `CustomPainter.paint()` — all hoisted to fields or `const` (they run every frame during animation).
- [ ] No per-frame closures (`() => …` built in `build`/`update`) or interpolated debug strings
      (`'score: $s'`) on the hot path; HUD labels update only when the value actually changes.
- [ ] `const` is applied wherever it compiles (lints `prefer_const_*` clean) so unchanged subtrees
      short-circuit the rebuild.
- [ ] Lists/grids of cells are lazy (`ListView.builder`/`GridView.builder`), never a literal
      `children:` of off-screen widgets.

## No rebuild-the-world (scoped rebuilds)
- [ ] No `setState()` rebuilds a whole screen/subtree for one changed field (score, lives, timer);
      each is its own `ValueNotifier` read via `ValueListenableBuilder` / `Selector`.
- [ ] `AnimatedBuilder`/`ListenableBuilder` pass the static subtree via the **`child:`** argument so it
      is built once, not every tick.
- [ ] A `RepaintBoundary` isolates the frequently-animating playfield/sprite from the static background
      — present on the moving layer, **not** sprinkled on everything (each boundary costs a layer).
- [ ] `CustomPainter.shouldRepaint(old)` returns `false` when inputs are unchanged (leans on model
      value-equality), never an unconditional `true`; static vs animated paint split across
      `painter`/`foregroundPainter`.
- [ ] DevTools **Rebuild Stats** / **Track widget builds** shows no widget rebuilding far more often
      than its data changes.

## No `saveLayer` / overdraw in hot paths
- [ ] No `Opacity` **widget** in animated paths — use `AnimatedOpacity`, an `Image`'s `opacity`, or a
      semitransparent color instead.
- [ ] No `ClipRRect`/`ClipPath` mid-animation — prefer `borderRadius` on the decoration.
- [ ] No other `saveLayer` sources on the hot path (`ShaderMask`, `ColorFilter`, `BackdropFilter`);
      `checkerboardOffscreenLayers` shows no unexpected offscreen layers during play.

## Image & asset sizing
- [ ] Raster assets are **decoded at display size** (`cacheWidth`/`cacheHeight` on `Image.asset`, or
      `ResizeImage`) — never a 4K/2048px PNG decoded for a 64px sprite.
- [ ] Images are **loaded once up front** (`precacheImage`, `Flame.images.load`/`loadAll` in
      `onLoad`) — never `Image.asset` / `Flame.images.load` inside `update` or a spawn path.
- [ ] Vector/`CustomPainter` placeholder art is used where it can be, keeping texture memory near zero.
- [ ] `imageCache` / `Flame.images` is **evicted on level exit** (`imageCache.clear()`/`evict` /
      `Flame.images.clearCache()`) so the previous level's atlas isn't resident; `maximumSizeBytes`
      lowered if a memory-constrained device is a target.

## Flame component lifecycle
- [ ] **Component count is bounded:** anything off-screen or finished calls `removeFromParent()`; draw
      order set via `priority`, not add-order.
- [ ] **No allocation in `update`/`render`:** reusable `Vector2`/`Paint`/`Rect` are fields, mutated in
      place (`setFrom`/`add`/`addScaled`/`setValues`) — not `position = position + Vector2(...)`.
- [ ] High-churn spawners (bullets/coins/particles/obstacles) use a **pool** (`ComponentPool<T>` or a
      `List` free-list); `removeFromParent()` returns the component to the pool, no manual release.
- [ ] **Pooled state is reset on reuse** (`onMount` / a reset) so stale fields don't leak across lives;
      caller-set fields (position/velocity, set between `acquire()` and `add()`) are *not* clobbered.
- [ ] Sprites are **batched**: packed into an atlas and drawn via `SpriteBatch`/`SpriteSheet`/
      `SpriteAnimation` so many sprites are one draw call, not one each.
- [ ] Collision is cheap: hitboxes only where needed, non-reactive ones marked
      `CollisionType.passive`, simple shapes (`Rectangle`/`Circle` hitbox) over polygons.

## Shader / animation perf
- [ ] First-run **shader-compilation jank** is mitigated (warm up first-frame shaders / Impeller in use)
      so the first animation or transition doesn't hitch.
- [ ] Explicit `AnimationController`s exist only for looping/reversible motion; one-shot polish uses
      implicit animations (`AnimatedContainer`/`TweenAnimationBuilder`).
- [ ] **Reduce Motion is honored** — `MediaQuery.disableAnimations` collapses durations before any
      `.repeat()`; no free-running animation overrides the OS choice.
- [ ] No animation/ticker runs on a **static** menu/paused/win screen.

## Memory leaks (dispose)
- [ ] Every `AnimationController`, `Ticker`, self-created `ValueNotifier`/`ChangeNotifier`,
      `StreamSubscription`, `FocusNode`, `TextEditingController`, `ScrollController`, `Timer` is disposed
      in `State.dispose` (`super.dispose()` last) / Flame `Component.onRemove`; every `addListener` has a
      matching `removeListener`.
- [ ] A passed-in (not self-created) notifier/controller is **not** disposed here — the owner disposes it.
- [ ] DevTools **Memory view** over a long session shows a flat/sawtooth heap that returns to baseline —
      **not** a climbing staircase. Enter-level → exit-level snapshot **diff** shows no level-specific
      object still retained.
- [ ] Engine is **paused on static screens** (`pauseEngine()` / `paused = true`, resumed with
      `resumeEngine()`); widget-mode UI advances only on real state change, no free-running ticker.
- [ ] Audio players stop when silent; no busy-wait polling timers — the engine loop drives frames.

## Package usage (perf cost)
- [ ] No package pulled in for something a few lines of Dart or an Apple/Flutter framework already do
      (`package-policy`: official → mature community → none); each dependency justified.
- [ ] No heavy/native plugin added solely for a cosmetic effect that `CustomPainter`/built-in animation
      could do without the binary-size and startup cost.

## Profile to verify (don't guess)
- [ ] Verified in **`flutter run --profile` on the oldest real device**, not debug, not a simulator/emulator.
- [ ] **DevTools → Performance:** Flutter frames chart has no over-budget frames in normal play; the
      **Frame Analysis** Build/Layout/Paint/Raster breakdown shows no single phase blowing the budget.
- [ ] **DevTools → CPU profiler:** no fat `update`/`build`/`paint`/`render` self-time and no heavy time
      in list/allocation growth (`_GrowableList`) pointing at per-frame churn to hoist or pool.
- [ ] **DevTools → Memory:** "track allocations" identifies the churning class for any hotspot;
      re-profiled **after** each fix to confirm it (then stop — no speculative micro-tuning).
