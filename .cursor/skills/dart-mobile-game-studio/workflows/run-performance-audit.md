# Workflow: Run a Performance Audit (steady 60/120 fps)

**Goal:** Confirm — or restore — a steady frame budget (60 fps everywhere; 120 fps on ProMotion) on
the **oldest target device**, and kill jank, per-frame allocation, and leaks before release.

**When to use:** the pre-release perf gate, or when a player/tester reports stutter, slow scrolling,
heat, or battery drain.

**When NOT to use:** an outright build/runtime error (use [`debug-common-errors`](debug-common-errors.md));
correctness bugs (those are tests, not profiling).

**Prerequisites**
- [`references/performance-checklist`](../references/performance-checklist.md) and
  [`checklists/performance`](../checklists/performance.md) — the full item list this operationalizes.
- [`scripts/dart-doctor.py`](../scripts/dart-doctor.py) for the static first pass; the catalog codes
  `FLAME_HOT_PATH_ALLOCATION`, `FLUTTER_BUILD_PERFORMANCE`, `FLUTTER_RENDER_COST`, `FLUTTER_MEMORY_LEAK`
  in [`references/common-pitfalls`](../references/common-pitfalls.md).

> **Doctrine:** "it runs" is not the bar — the bar is the loop running 60/120× a second with no
> garbage, jank, or leaks. **Measure in profile mode on a real device**; debug-mode and simulator
> numbers lie (assertions, no AOT, no real GPU).

---

## STEP 1 — Static pass first (free, no device)

```bash
scripts/dart-doctor.py . --only performance --no-color
```

It flags the analyzer-invisible perf classes by `file:line`: allocation inside `update()`/`render()`
(`FLAME_HOT_PATH_ALLOCATION`), an `update(double dt)` with no visible `dt` clamp (`FLAME_DT_IGNORED`),
and `setState()` inside `build()` (`FLUTTER_LIFECYCLE_SETSTATE`). Fix what it finds before you profile
— no point measuring a known hot-path allocation.

**Done when:** dart-doctor's performance dimension is clean (or each WARN is triaged with a reason).

---

## STEP 2 — Profile on the oldest real device

```bash
flutter run --profile
```

Debug mode is meaningless for perf (assertions, JIT, debug paint). Use **profile** on the **oldest**
device you target — a flagship hides the jank your players will see. Open DevTools (the URL printed by
`flutter run`).

**Done when:** the game is running in profile mode on real hardware with DevTools attached.

---

## STEP 3 — Read the timeline (UI vs raster)

In DevTools → **Performance**: play the core loop and watch the frame chart. Two lanes matter:

- **UI thread** (Dart `build`/`update`) over budget → too much work per frame (Step 5/6).
- **Raster thread** over budget → expensive painting: `saveLayer`, clips, big textures (Step 7).

Budget = **16.6 ms** @60 fps, **8.3 ms** @120 fps. Jank = sustained bars over budget, not a one-off.
Toggle the **performance overlay** (`P` in the console) for a quick on-device read.

**Done when:** you know whether the bottleneck is UI or raster, and on which interaction.

---

## STEP 4 — Kill per-frame allocation (the #1 Flame perf bug)

In every `update(dt)`/`render(canvas)` (and any hot `build`): no `Vector2`/`Paint`/`Rect`/`Path`/
`TextPaint`/list churn. 100 components @60 fps each `new`-ing two objects = 12 000 allocations/sec →
GC stutter.

```dart
// hoist to fields, mutate in place:
final Paint _paint = Paint()..color = color;
void update(double dt) => position.addScaled(_velocity, dt);   // no temp Vector2
```

Pool frequent spawns (bullets/particles) with `ComponentPool` (`FLAME_POOLING`). Confirm in DevTools →
**Memory** that the per-frame allocation rate is flat during play.

**Done when:** no allocation in hot methods; memory allocation rate is flat in steady play.

---

## STEP 5 — Frame-rate independence (`dt`)

Movement, timers, and cooldowns scale by `dt`, and **`dt` is clamped** (`final d = math.min(dt, 1/30);`)
before stepping — Flame does not clamp it, so a GC/load/backgrounding hitch must not teleport entities.
A constant `position.y += 5` runs twice as fast at 120 Hz: a correctness *and* feel bug.

**Done when:** the game plays identically at 60 and 120 Hz; a forced hitch doesn't tunnel entities.

---

## STEP 6 — Scope rebuilds (widget/UI side)

- No rebuild-the-world `setState` for a one-field change — drive the smallest subtree via
  `ValueListenableBuilder`/`Selector` (`FLUTTER_BUILD_PERFORMANCE`).
- No computation in `build` (sort/parse/generate); hoist to `initState`/a memoized selector.
- `const` every static subtree; wrap a frequently-repainting playfield in a `RepaintBoundary` so it
  doesn't dirty the static background — but not on everything (each boundary is a layer).
- `CustomPainter.shouldRepaint` returns `true` only on a real change.

**Done when:** only the changing subtree rebuilds/repaints; the static chrome doesn't.

---

## STEP 7 — Cut render cost (raster side)

Avoid `saveLayer` triggers on hot/animated paths: the `Opacity` widget (use `AnimatedOpacity`/
`Image.opacity`/a semitransparent color), `ClipPath`/`ClipRRect`/`ShaderMask`/`BackdropFilter` mid-
animation (prefer a decoration `borderRadius`). Right-size textures (an oversized PNG blows the GPU
budget); prefer vector/`CustomPainter` placeholders. `FLUTTER_RENDER_COST`.

**Done when:** the raster lane is within budget during transitions, motion, and scroll.

---

## STEP 8 — Leaks, battery, thermals

- DevTools → **Memory**: play a long session; the component/object count must not grow monotonically.
  Every `AnimationController`/`Ticker`/`StreamSubscription`/`Timer` disposed; Flame components freed in
  `onRemove`; pooled, not leaked (`FLUTTER_MEMORY_LEAK`).
- No loop runs on a static screen: `pauseEngine()` on menu/pause/win; widget-mode UI advances only on
  real state change. Audio is preloaded, not loaded mid-loop.

**Done when:** memory is flat over a long session; no engine loop runs on a paused/static screen.

---

## Master "done when"
1. dart-doctor `performance` is clean (Step 1).
2. Profile-mode run on the oldest device shows a steady budget for the core loop (Steps 2–3).
3. No per-frame allocation; `dt` clamped & frame-rate independent (Steps 4–5).
4. Rebuilds/repaints scoped; no needless `saveLayer` (Steps 6–7).
5. Memory flat over a long session; no loop on static screens (Step 8).

## Handoff
Report: device + OS profiled on, the before/after frame times (UI and raster), what was fixed
(by catalog code), and the DevTools evidence. **Verified, not assumed** — if you couldn't profile on
hardware here, say so and give the exact `flutter run --profile` steps and the checklist to walk.

## Common pitfalls
- **Profiling in debug mode / on a simulator** — numbers are meaningless; use profile + real hardware.
- **Profiling only on a flagship** — it hides the jank your oldest-device players hit.
- **Sprinkling `RepaintBoundary` everywhere** — each is a layer; place them deliberately.
- **Unclamped `dt`** — a single long frame tunnels the player; clamp every loop.
- **"Looks smooth to me"** — read the timeline; perceptual checks miss sub-second jank and slow leaks.

## See also
- [`references/performance-checklist`](../references/performance-checklist.md), [`checklists/performance`](../checklists/performance.md) — the full gate.
- [`references/common-pitfalls`](../references/common-pitfalls.md) — `FLAME_HOT_PATH_ALLOCATION`, `FLUTTER_BUILD_PERFORMANCE`, `FLUTTER_RENDER_COST`.
- [`references/flutter-flame-patterns`](../references/flutter-flame-patterns.md) — pooling, `dt`, component lifecycle.
