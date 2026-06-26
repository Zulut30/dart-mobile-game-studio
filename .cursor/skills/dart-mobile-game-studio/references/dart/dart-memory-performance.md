# Dart & Flutter memory & performance (language level)

Memory and allocation discipline at the **Dart language** level — the habits that keep GC pauses out
of your frames before any engine-specific tuning. This is the *how the runtime behaves* companion to
the operational [`../performance-checklist.md`](../performance-checklist.md) (which covers the
frame budget, Flame/widget render tactics, and how to profile). Read that for the checklist; read
this to understand **why** `const`, reuse, pooling, and disposal matter, and where each pays off.

**The one rule that governs everything below:** the Dart GC is generational and fast at collecting
*short-lived* garbage, but every allocation still has a cost, and a collection pause can blow a 16 ms
frame. So the goal is **not zero allocation** — it's *no allocation on the hot path* (per-frame
`update`/`render`/`build`/`paint`). Allocate freely at load time and on rare events; allocate nothing
in the loop. And **profile before optimizing** — Dart's escape analysis and generational GC make most
one-off allocations free in practice. Don't contort readable model code chasing a cost a profiler
never showed.

## `const` canonicalization — free, shared, immutable

A `const` expression is evaluated at **compile time** and **canonicalized**: every structurally-equal
`const` value in the program is the *same* object in memory. `const Color(0xFF2196F3)` written in
fifty widgets is one allocation total, not fifty. There is no runtime construction cost and no GC
pressure — the instance lives for the life of the program.

```dart
// DO — const value objects + const constructors → canonicalized, zero per-use cost.
const tile = Size(32, 32);                 // same object everywhere it appears
const gap = SizedBox(height: 8);           // const widget: identical instance across rebuilds
class Coin {
  const Coin({required this.value});       // const constructor → instances can be canonicalized
  final int value;
}
const goldCoin = Coin(value: 100);
```

```dart
// DON'T — a runtime constructor allocates a fresh object on every evaluation.
final tile = Size(32, 32);                 // new object each call; not shared
final gap = SizedBox(height: 8);           // rebuilt every frame in a build() method
```

- In the **renderer**, a `const` widget is the single biggest free win: when Flutter re-encounters
  the *same* widget instance during a rebuild it short-circuits and stops re-traversing that subtree.
  Mark every static widget `const`. `prefer_const_constructors` / `prefer_const_literals_to_create_immutables`
  enforce it — let the lint do the bookkeeping.
- In the **pure-Dart core**, `const` config (`const Difficulty.normal`, fixed tables, `const [...]`
  literals) means lookup tables and default values cost nothing at runtime.
- `const` requires *every* input to be a compile-time constant. The moment a value depends on runtime
  data it must be `final`; that's fine — reserve `const` for genuinely fixed data.
- A `const` collection literal (`const [...]`, `const {...}`) is **deeply immutable** *and* shared —
  mutating it throws. Use it for fixed level palettes, symbol sets, lookup tables.

## Don't allocate in `build()` / `paint()` / per-frame `update`

`build()` and `CustomPainter.paint()` run on **every frame** during animation; a Flame component's
`update`/`render` run every frame, period. An object created there is born and dies inside one frame
— the textbook short-lived garbage that, multiplied by component count × 60 fps, becomes thousands of
objects per second and a steady drip of GC pauses.

```dart
// DON'T — fresh Paint + Vector2 every frame; 60 fps × N components = garbage storm.
class Star extends PositionComponent {
  @override
  void update(double dt) => position += Vector2(0, 40) * dt;   // new Vector2 each frame
  @override
  void render(Canvas canvas) =>
      canvas.drawCircle(Offset.zero, 4, Paint()..color = const Color(0xFFFFD54F)); // new Paint
}

// DO — hoist immutables to fields; mutate Vector2 in place, reuse Paint.
class Star extends PositionComponent {
  static final _fall = Vector2(0, 40);                          // shared, never mutated
  final _paint = Paint()..color = const Color(0xFFFFD54F);      // built once
  @override
  void update(double dt) => position.addScaled(_fall, dt);      // in-place, no allocation
  @override
  void render(Canvas canvas) => canvas.drawCircle(Offset.zero, 4, _paint);
}
```

- **Hoist out of the hot path:** `Paint`, `Path`, `Gradient`, `TextPainter`, parsed level data, and
  any `Vector2`/`Rect` used as scratch space → cache as fields, build once.
- **Mutate vector math in place:** `position.setFrom(v)`, `position.add(v)`, `position.addScaled(v, dt)`,
  `..setValues(x, y)` — not `position = position + Vector2(...)`, which allocates.
- **Closures allocate too.** A `() => …` created inside `build`/`update` is a new object each frame.
  Hoist callbacks to fields or top-level functions; pass static subtrees via the `child:` argument of
  `AnimatedBuilder`/`ListenableBuilder` so they aren't rebuilt per tick.
- **String interpolation allocates.** Don't build debug strings every frame (`'score: $s'`); update
  the HUD label only when the value actually changes, driven by a `ValueNotifier`.
- This is a **hot-path** rule, not a blanket ban. In the model and at load time, write the clear,
  allocating, declarative version (`.map`, `.where`, record returns) — readability wins there.

## Object pooling — recycle high-churn spawns

When you create *and destroy* many short-lived objects rapidly (bullets, coins, particles,
obstacles), the churn — not the live set — is what stresses the GC. A **pool** keeps a reservoir of
reusable instances: acquire one, use it, return it, repeat. No steady allocation, no steady
collection. Pool only proven-churn spawners; a pool for a handful of long-lived objects is just
complexity.

Flame ships `ComponentPool<T>` and wires return-on-removal automatically:

```dart
// Pool created once at load.
late final ComponentPool<Bullet> _bullets;
@override
Future<void> onLoad() async {
  _bullets = ComponentPool<Bullet>(
    factory: Bullet.new,   // how to make one when the pool is empty
    maxSize: 50,           // cap kept in reserve (excess is dropped, not retained)
    initialSize: 10,       // pre-warm so the first volley doesn't allocate
  );
}

void fire(Vector2 from, Vector2 dir) {
  final b = _bullets.acquire();   // reuses a free one, or lazily creates
  b.position.setFrom(from);       // caller sets state AFTER acquire, BEFORE add
  b.velocity.setFrom(dir);
  world.add(b);
}
```

```dart
class Bullet extends PositionComponent {
  final Vector2 velocity = Vector2.zero();
  @override
  void update(double dt) {
    super.update(dt);
    position.addScaled(velocity, dt);
    if (!_onScreen) removeFromParent();   // removeFromParent() returns it to the pool automatically
  }

  @override
  void onMount() {
    super.onMount();
    // Reset INTERNAL/visual state so a recycled instance is clean.
    // Do NOT reset caller-set fields (position/velocity) — those were set between acquire() and add().
    opacity = 1;
  }
}
```

- **`removeFromParent()` returns the component to its pool** — no manual `release`. The hard part is
  **state hygiene**: a pooled object is *reused*, so stale fields leak across lives. Reset internal
  state in `onMount` (or your own reset), and remember caller-configured state is set between
  `acquire()` and `add()`, so don't clobber it.
- `acquire()` lazily creates past `initialSize`; `maxSize` caps how many are *kept* — overflow on
  return is simply discarded, so the pool can't grow without bound.
- `pool.clear()` frees the reserve (e.g. on level exit) without touching in-flight components.
- A plain Dart pool (no Flame) is the same idea — a `List<T>` free-list with `acquire`/`release`:

```dart
class Pool<T> {
  Pool(this._create, {int prefill = 0}) {
    for (var i = 0; i < prefill; i++) _free.add(_create());
  }
  final T Function() _create;
  final _free = <T>[];                              // grows only when demand exceeds supply
  T acquire() => _free.isNotEmpty ? _free.removeLast() : _create();
  void release(T item) => _free.add(item);          // caller must reset item's state
}
```

## Lists: growable vs fixed, `const`, and avoiding rebuilds

`List` is the default workhorse but has three shapes with different costs:

- **Growable** (`[]`, `List.of`, `List.from`) — backed by an array that **reallocates and copies**
  when it outgrows capacity. Fine for build-up; avoid *repeated growth* in a hot loop.
- **Fixed-length** (`List.filled(n, v)`, `List.generate(n, f, growable: false)`) — one allocation, no
  resize cost. Use it for a board/grid whose size is known and stable.
- **`const` list** (`const [...]`) — compile-time, canonicalized, deeply immutable, zero runtime cost.

```dart
// DON'T — grow element-by-element in a hot path (repeated realloc + copy).
final cells = <Cell>[];
for (var i = 0; i < rows * cols; i++) cells.add(Cell.empty);

// DO — size known up front → one allocation.
final cells = List<Cell>.filled(rows * cols, Cell.empty);          // fixed grid
final tiles = List<Tile>.generate(count, buildTile, growable: false);
```

- **Pre-size when the count is known:** `List.filled`/`List.generate(growable: false)` beats `add`
  in a loop. If you must grow, build the whole thing once with a **collection-for**
  (`[for (final x in xs) f(x)]`) rather than `..add` in a manual loop.
- **`Iterable` is lazy; `List` is eager.** `.map`/`.where` return a lazy view that re-runs the
  transform on **each** iteration — calling `.toList()` once and reusing it is cheaper than iterating
  a lazy chain repeatedly (and avoids re-allocating per frame). Don't call `.toList()` *inside* a
  per-frame loop; do it once and cache.
- **Reuse the same list instance** for per-frame scratch (e.g. collision candidates): `list.clear()`
  and refill rather than `final hits = <X>[]` each frame.
- **`Set`/`Map` for membership/lookup** (matched ids, occupied cells) — O(1) vs `list.contains`'s
  O(n); fewer wasted comparisons each frame.

## Immutable value types — cheap to share, safe to alias

Immutable models (`final` fields + `const` constructor, value `==`/`hashCode`, `copyWith`) aren't
just a correctness pattern — they're a **memory** one. Because they can't change, they can be freely
**shared and aliased** without defensive copies, and `const` ones are canonicalized to a single
instance. `copyWith` allocates *one* new object for the *one* field that changed and structurally
shares the rest.

```dart
final flipped = card.copyWith(isFaceUp: true);   // one small allocation; other fields shared by ref
```

- Value equality is also a **performance lever**: `CustomPainter.shouldRepaint`, `ValueListenableBuilder`,
  and `Selector` skip work when the new value `==` the old. Correct `==`/`hashCode` (or a record's
  free structural equality) turns "nothing changed" into "no repaint."
- Don't over-rotate: a `copyWith` **per frame** for animated state is churn — for continuous motion,
  mutate a `Vector2`/controller in place (renderer side) and keep immutability for *discrete* state
  transitions (a move applied, a card flipped). Immutable model, mutable scratch.
- See [`dart-language-essentials.md`](dart-language-essentials.md) for the full value-type recipe.

## Dispose everything that holds a resource or a callback — leaks are forever

Dart's GC frees objects with no references. The classic Flutter/Flame leak is an object the GC
**can't** collect because something still references it: a `ValueNotifier` someone still listens to, a
`StreamSubscription` the source still holds, a `Ticker`/`AnimationController` the vsync still drives.
These keep firing callbacks and keep their captured state — and the whole object graph behind it —
alive. Always dispose in the matching teardown.

```dart
class _PlayState extends State<Play> {
  final _score = ValueNotifier<int>(0);
  late final AnimationController _anim = AnimationController(vsync: this, duration: _kFade);
  StreamSubscription<GameEvent>? _events;

  @override
  void initState() {
    super.initState();
    _events = widget.game.events.listen(_onEvent);
  }

  @override
  void dispose() {
    _events?.cancel();   // StreamSubscription — source keeps it alive otherwise
    _anim.dispose();     // AnimationController/Ticker — vsync keeps ticking otherwise
    _score.dispose();    // ValueNotifier/ChangeNotifier — listeners keep it alive otherwise
    super.dispose();     // last
  }
}
```

| Resource | Disposed by | Leak symptom if you forget |
|---|---|---|
| `AnimationController`, `Ticker` | `.dispose()` in `State.dispose` | keeps vsync-driving every frame; battery + retained graph |
| `ValueNotifier` / `ChangeNotifier` | `.dispose()` | listeners pinned; rebuilds fire on dead widgets |
| `StreamController` | `await .close()` | subscribers never get done; controller retained |
| `StreamSubscription` | `.cancel()` | source holds it; captured closure state retained |
| `FocusNode`, `TextEditingController`, `ScrollController` | `.dispose()` | retained + still notifying |
| Flame `Component` (timers, subs, listeners) | `onRemove()` | per-component leak × spawn count |

- **In Flame**, clean up in `onRemove()` — cancel timers/subscriptions, return things to pools. The
  game loop walking dead-but-retained components is both a memory and a CPU cost.
- **Pause, don't leak, on static screens.** A menu/pause/win screen should `pauseEngine()` (Flame) or
  stop its `Ticker` (widgets) — not leave a loop running. (Battery angle in the checklist; the memory
  angle is that a running loop keeps everything it touches hot and uncollectable.)

## Image & asset cache — load once, decode at display size, evict on exit

Decoded images are the **largest** memory consumers in a simple 2D game — a decoded bitmap is
`width × height × 4` bytes regardless of the PNG's compressed size. Two caches matter:

- **Flutter `ImageCache`** (`PaintingBinding.instance.imageCache`, or the top-level `imageCache`) —
  an LRU cache, by default up to **1000 entries / 100 MB**. `Image.asset`, `precacheImage`, etc. all
  route through it.
- **Flame `Images`** (`Flame.images`) — caches decoded `ui.Image`s by filename; `load`/`loadAll`
  are safe to call repeatedly (returns the cached instance), `fromCache` reads it synchronously,
  `clear(name)` / `clearCache()` evict.

```dart
// DON'T — decode a 2048px PNG to draw a 64px sprite (4 MB+ resident for a thumbnail).
Image.asset('assets/coin.png');

// DO — decode at the size you actually draw; the cache holds the small bitmap.
Image.asset('assets/coin.png', cacheWidth: 64, cacheHeight: 64);   // or ResizeImage(...)
await Flame.images.loadAll(['coin.png', 'star.png']);              // load once, up front
```

- **Decode at display size:** pass `cacheWidth`/`cacheHeight` (or wrap in `ResizeImage`) so the
  cached bitmap is the on-screen size, not the source size. This is the single biggest image-memory
  win.
- **Load once, not per spawn:** warm assets in `onLoad`/`precacheImage` before the level; never call
  `Image.asset`/`Flame.images.load` inside `update`/a spawn path.
- **Evict on level exit:** `Flame.images.clearCache()` or `imageCache.clear()` / `imageCache.evict(key)`
  so last level's atlas isn't resident during this one. Lower `imageCache.maximumSizeBytes` if a
  memory-constrained device is a target.
- **Prefer vector/`CustomPainter` placeholder art** where you can — it keeps texture memory near zero
  (and dodges the no-copyrighted-assets rule entirely).

## Weak references & `Expando` — rarely the answer

Dart has `WeakReference<T>` (a reference the GC may clear) and `Expando<T>` (attach data to an object
without keeping it alive), plus `Finalizer` for native cleanup. In a small 2D game you almost never
need them — **deterministic disposal (above) is the right tool**, because it frees *now* rather than
"whenever the GC runs," and it's testable.

- Reach for a weak reference **only** for a genuine cache/observer that must not keep its target
  alive (e.g. an optional back-pointer that shouldn't pin a parent). If a plain field plus a
  `dispose()` works, use that instead — it's clearer and immediate.
- `WeakReference.target` can be `null` at any time (the GC took it) — you must null-check every read.
- `Finalizer` is **not guaranteed to run** (and never on a clean exit); use it only as a backstop for
  native resources, never as your primary cleanup path.

```dart
// Rarely needed; shown for completeness — a back-reference that must not keep the parent alive.
final WeakReference<Board> _board;
void tick() {
  final board = _board.target;
  if (board == null) return;   // GC may have collected it — always null-check
  board.step();
}
```

## Profiling — measure before (and after) you change anything

Never optimize from a guess. Dart's generational GC makes most allocations cheap, and the analyzer
can't see runtime cost — only a profiler can. **Always profile in `--profile` mode on a real
device** (debug builds are deliberately slow; emulators hide GPU and GC behavior).

- **DevTools → Memory view:** watch the **allocation/heap graph over a long session**. A sawtooth
  that returns to baseline is healthy churn; a staircase that climbs and never falls is a **leak** —
  find the undisposed notifier/subscription/controller. Use **"track allocations"** / the allocation
  profiler to see *which class* is churning, and **snapshot diffing** to find what's retained between
  two points (e.g. enter level → exit level → diff: anything level-specific still alive is a leak).
- **DevTools → CPU profiler:** find hot Dart methods; a fat `update`/`build`/`paint` self-time, or
  lots of time in `_GrowableList`/allocation, points at per-frame churn to hoist or pool.
- **DevTools → Performance view & the performance overlay:** find frames over budget and read the
  UI-vs-raster split (covered operationally in [`../performance-checklist.md`](../performance-checklist.md)).
  GC pauses show up here as occasional spikes on the **UI** thread.
- **Workflow:** profile → find the *one* real hotspot → fix it (`const`, hoist, pool, dispose,
  pre-size) → **re-profile to confirm**. Then stop. Don't pre-pool, pre-`const`-everything-by-hand, or
  micro-tune the model on a hunch — let lints handle the free wins and the profiler pick the rest.

## Quick checklist

- [ ] `const` on every static widget and fixed value object (lints on); `final` otherwise.
- [ ] No allocation on the hot path — `build`/`paint`/`update`/`render` reuse hoisted
      `Paint`/`Path`/`Vector2` and mutate in place; no per-frame closures or interpolated strings.
- [ ] High-churn spawners pooled (`ComponentPool` or a `List` free-list); pooled state reset on reuse.
- [ ] Lists pre-sized when the count is known (`List.filled`/`generate(growable: false)`); membership
      via `Set`/`Map`; `.toList()` cached, not re-run per frame.
- [ ] Immutable value models shared freely; `copyWith` for discrete edits, in-place mutation for
      continuous motion.
- [ ] Every controller/notifier/subscription/focus-node disposed in `dispose`/`onRemove`; engine
      paused on static screens.
- [ ] Images decoded at display size (`cacheWidth`/`cacheHeight`), loaded once, evicted on level exit;
      `imageCache`/`Flame.images` bounded.
- [ ] Weak refs/`Finalizer` only where a deterministic `dispose` genuinely can't work.
- [ ] Verified in **DevTools, profile mode, real device** — heap flat over a long session, no frames
      over budget; re-profiled after each change.

---

*API names verified against official docs. Flame `ComponentPool<T>({required T Function() factory,
int? maxSize, int initialSize})` with `acquire()` / `clear()` and automatic return-to-pool on
`removeFromParent()`; `Flame.images` (`Images`) `load`/`loadAll`/`fromCache`/`clear`/`clearCache`;
in-place `Vector2` ops (`setFrom`/`add`/`addScaled`/`setValues`) — flame-engine docs (performance.md,
images.md). Flutter `ImageCache` via `PaintingBinding.instance.imageCache` / top-level `imageCache`
(`maximumSize` default 1000, `maximumSizeBytes` default 100 MB, `evict`/`clear`/`currentSizeBytes`),
`Image(cacheWidth:, cacheHeight:)` / `ResizeImage`, `precacheImage` — api.flutter.dev. Dart core
`List.filled`/`List.generate(growable:)`, `const` canonicalization, `WeakReference<T>`/`Expando`/
`Finalizer` — dart.dev.*