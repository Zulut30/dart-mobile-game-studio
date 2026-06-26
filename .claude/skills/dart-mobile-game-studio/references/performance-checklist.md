# Performance checklist

Simple 2D mobile games (iOS + Android) should hold a steady frame rate on the oldest supported
device with low battery and thermal impact. Budget first; optimize only what a profiler proves.
Never guess — Flutter's debug build is intentionally slow, so all numbers below mean **profile
mode** (`flutter run --profile`) on a real device.

## Frame budget

- Target 60 fps → **~16.6 ms/frame**. 120 Hz (ProMotion / Android high-refresh) → **~8.3 ms**.
  Stay well under, both for headroom and for battery/thermals.
- Flutter splits each frame across **two threads**, and **either** can miss the budget:
  - **UI thread** — all your Dart runs here: `build`, layout, paint into a *layer tree*, plus the
    Flame game loop (`update`/`render`). "Don't block this thread."
  - **Raster thread** — takes the layer tree and rasterizes it via the GPU (Skia/Impeller). A
    red bar here means the *scene is too expensive to draw* (overdraw, `saveLayer`, clipping).
- The overlay draws **two graphs** with white 16 ms gridlines: top = raster thread, bottom = UI
  thread. A bar crossing a line drops below 60 Hz; a **red bar** marks a janked frame. If both
  are red, diagnose the UI thread first.
- Make all motion **frame-rate independent**: advance by `dt`, never by per-frame constants.
- **Clamp `dt`** (e.g. `dt = min(dt, 1 / 30)`) so a GC pause or load hitch doesn't teleport
  objects across the screen.

## Flutter-widgets / CustomPainter mode (static & turn-based)

The cost lives in `build()` and in paint. Rebuilds cascade to descendants, so keep them small and
rare.

- **`const` everywhere it compiles.** A `const` widget short-circuits the rebuild: Flutter stops
  re-traversing a subtree when it re-encounters the same instance as last frame.
- **Never do work in `build()`.** Hoist `Paint`, `Path`, gradients, `TextPainter`, and parsed
  level data out of `build()` and out of `CustomPainter.paint()` — build/paint run on every frame
  during animation. Cache them as fields.
- **Rebuild the smallest possible subtree.** Drive UI from a pure-Dart model exposed as a
  `ValueNotifier` / `ChangeNotifier`, and listen *granularly* with `ValueListenableBuilder` (or a
  `Selector` if using provider) so a score tick repaints the score, not the whole HUD. Keep
  `setState()` on the smallest `StatefulWidget`.
- **`AnimatedBuilder`/`ListenableBuilder`: pass static subtrees via the `child:` argument** so they
  are built once, not rebuilt every animation tick.
- **`RepaintBoundary`** around a frequently-animating widget isolates its repaints into a separate
  layer, so its motion doesn't dirty (and re-raster) the static background. Use it for the moving
  playfield, not for everything — each boundary has its own layer cost.
- **Avoid the `Opacity` widget** (it triggers `saveLayer`). For a fading sprite use
  `AnimatedOpacity`/`FadeInImage`, an `Image`'s own `opacity`, or just a semitransparent color.
- **Avoid clipping** in hot paths (`ClipRRect`/`ClipPath` cost a `saveLayer` / GPU work). Prefer a
  `borderRadius` on the decoration. Other `saveLayer` sources to watch: `ShaderMask`, `ColorFilter`,
  `BackdropFilter`.
- **`CustomPaint`:** implement `shouldRepaint` to return `false` when inputs are unchanged; split a
  static layer (`painter`) from an animated layer (`foregroundPainter`) so only one repaints.
- **Lists/grids:** use `ListView.builder` / `GridView.builder` (lazy) — never a literal `children:`
  list of off-screen cells.

## Flame mode (FlameGame + components)

- **Bound the component count.** The game loop walks every component each frame, so cap what is
  alive and `removeFromParent()` anything off-screen or finished. Set `priority` for draw order
  rather than relying on add-order.
- **No allocation in `update`/`render`.** At 60 fps, 100 components each allocating one object is
  6000 garbage objects per second → GC hitches. Store reusable `Vector2`/`Paint`/`Rect` as fields
  and mutate in place (`position.setFrom(...)`, `..setValues(...)`), e.g.:
  ```dart
  class Bullet extends PositionComponent {
    final Vector2 _velocity = Vector2(0, -300); // reused, not re-created
    final Paint _paint = Paint()..color = const Color(0xFFFFC107);

    @override
    void update(double dt) {
      position.addScaled(_velocity, dt); // frame-rate independent, no new Vector2
    }

    @override
    void render(Canvas canvas) => canvas.drawRect(size.toRect(), _paint);
  }
  ```
- **Object pooling for spawners** (bullets, coins, particles, obstacles). Recycle instead of
  create/destroy churn. Flame ships `ComponentPool<T>`:
  ```dart
  final bulletPool = ComponentPool<Bullet>(
    factory: Bullet.new,
    maxSize: 50,
    initialSize: 10,
  );

  void spawnBullet(Vector2 at, Vector2 vel) {
    final bullet = bulletPool.acquire(); // reuses or lazily creates
    bullet.position.setFrom(at);
    world.add(bullet);
  }
  // removeFromParent() returns the component to its pool automatically.
  ```
- **Batch draws with one texture.** Pack sprites into an atlas (one `ui.Image`) and draw the frame
  with a **`SpriteBatch`** (or `SpriteBatchComponent`) so many sprites become one draw call;
  `SpriteSheet`/`SpriteAnimation` cut from the same sheet keep the raster thread cheap. Load images
  once through the global **`Flame.images`** cache (`Flame.images.load` / `loadAll`) — don't decode
  per spawn.
- **Collision:** add hitboxes only where needed and mark non-reactive ones
  `collisionType = CollisionType.passive` — Flame skips passive↔passive pairs entirely. Use simple
  shapes (`RectangleHitbox`/`CircleHitbox`), not polygons, where they'll do.
- **Fixed timestep for physics/determinism:** override `fixedUpdate` / use a fixed-step loop so
  simulation is stable and reproducible regardless of render rate; keep your seeded `Random`
  injected so logic stays deterministic and unit-testable on the Dart VM.

## Memory & images

- Vector/placeholder art (`CustomPainter`, simple shapes) keeps texture memory tiny. For raster
  assets, **decode at display size** — pass `cacheWidth`/`cacheHeight` to `Image.asset`, or
  `ResizeImage` — never decode a 4K PNG for a 64 px sprite.
- Flutter holds decoded frames in the **`ImageCache`**; `precacheImage` warms it before a level so
  the first draw doesn't hitch. Don't keep every level's atlas resident — evict on level exit.
- **Dispose what you create:** `AnimationController`, `Ticker`, `ValueNotifier`/`ChangeNotifier`,
  `StreamSubscription`, `FocusNode`, `TextEditingController` all leak (and keep timers/listeners
  firing) if not disposed in `State.dispose` / `Component.onRemove`.

## Battery & thermals

- **Don't run a loop on a static screen.** Pause the Flame engine on menu/pause/win
  (`game.pauseEngine()` or `game.paused = true`; resume with `resumeEngine()`). A `CustomPainter`
  game should advance only on real state changes, not on a free-running ticker.
- Stop/lower work when nothing moves; stop audio players when silent. Avoid busy-wait timers — let
  the engine's loop drive frames, not tight polling.

## How to verify (don't guess)

- **Profile mode on the oldest real device** — `flutter run --profile`. Debug-mode numbers are
  meaningless; the simulator/emulator hides GPU cost.
- **DevTools → Performance view:** find frames over 16 ms, read the UI-vs-raster split, enable
  **Track widget builds** / **Track layouts** to catch over-rebuilding and intrinsic passes.
- **Performance overlay** (`MaterialApp(showPerformanceOverlay: true)` or `--show-performance-overlay`):
  watch both 16 ms graphs live; red bars = jank. `checkerboardOffscreenLayers` flags `saveLayer`
  overdraw; `checkerboardRasterCacheImages` flags re-rastered images.
- **CPU profiler / memory view** in DevTools for hot Dart and for leak/allocation growth over a
  long session.

## Quick checklist

- [ ] Profiled in **profile mode on the oldest real device**, not debug/simulator.
- [ ] Steady target fps; no red bars on the UI **or** raster graph in normal play.
- [ ] Motion uses `dt`; `dt` is clamped; physics on a fixed timestep where determinism matters.
- [ ] Widgets: `const` used, `build()` does no work, rebuilds are granular
      (`ValueListenableBuilder`/`Selector`), `RepaintBoundary` on the moving layer.
- [ ] No `Opacity` widget / clipping / `saveLayer` in hot paths.
- [ ] Flame: component count bounded, off-screen removed, **no allocations** in `update`/`render`,
      spawners pooled.
- [ ] Sprites atlased + batched (`SpriteBatch`); images loaded once via `Flame.images`; decoded at
      display size (`cacheWidth`/`cacheHeight`).
- [ ] All controllers/notifiers/subscriptions disposed; image cache evicted between levels.
- [ ] Engine paused on static/menu screens; audio stops when idle.
- [ ] Memory stable over a long session (DevTools memory view).