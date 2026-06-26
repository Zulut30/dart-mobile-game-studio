# Workflow: Add the Game Loop

**Goal:** Wire a frame-rate-independent, deterministic game loop that clamps `dt`, advances a pure-Dart model, mirrors state to nodes/widgets, and supports pause/resume.

## When to use
- You have a pure-Dart model with an `advance(double dt)` (or `update(double dt)`) method and need to drive it every frame.
- The genre needs continuous motion/physics/timers (runner, platformer, tap-reaction with a countdown, animated puzzle feedback). Static turn-based games (jigsaw, memory, coloring) usually need **no** loop — skip this and drive state from input callbacks instead.
- You are deciding between **Flame** (`update`/`render`) and **widgets-only** (`Ticker` / `SchedulerBinding`).

## Prerequisites
- Pure-Dart core exists and is testable with `dart test` (NO `package:flutter` import in the model). See `references/flutter-game-architecture` and `references/dart/*`.
- A seeded `Random` is injected into the model (determinism). See `assets/seeded_random.dart`.
- Mode chosen per `references/flutter-game-architecture` (Flutter-widgets / Flame / hybrid `GameWidget`).

## Core doctrine (read before coding)
1. **Time is an input, not a side effect.** The model never reads a wall clock; the loop passes `dt` in. This is what makes the core unit-testable and deterministic.
2. **Clamp `dt` yourself.** A dropped frame, a backgrounded app, or a debugger pause produces a huge `dt` that tunnels objects through walls and explodes physics. Clamp every frame: `dt = dt.clamp(0.0, maxFrameTime)`.
3. **Separate advance from render.** `model.advance(dt)` mutates state; the render/build step only reads state. Never mutate the model inside `render`/`build`.
4. **Determinism = fixed step.** Variable `dt` makes floating-point results depend on frame timing → replays/tests diverge. For anything you must reproduce (level validation, replays, golden tests), accumulate real time and step the model in **fixed** increments.

---

## STEPS

### 1. Define the model's loop entry point (pure Dart, no Flutter)
Keep one method that takes a clamped `dt` and is total (handles `dt == 0`).

```dart
// lib/game/snake_model.dart — NO package:flutter import
class SnakeModel {
  SnakeModel({required this.rng});
  final Random rng;          // injected — never Random() inline
  GamePhase phase = GamePhase.playing;

  /// Advance simulation by [dt] seconds. Caller MUST pass a clamped dt.
  void advance(double dt) {
    if (phase != GamePhase.playing || dt <= 0) return;
    // integrate positions, timers, collisions, win/lose transitions…
  }
}
```
Cross-link: model shape per the relevant `references/game-templates` brief.

### 2. Pick the loop driver

| Mode | Driver | Use when |
|------|--------|----------|
| Flame / hybrid `GameWidget` | `FlameGame.update(double dt)` + `render(Canvas)` | motion, physics, many sprites, camera. `dt` is already in **seconds**. |
| Widgets-only, continuous | `Ticker` (via `SingleTickerProviderStateMixin`) | light animation/timers, you want Flutter's vsync-driven callback. |
| Widgets-only, manual control | `SchedulerBinding.instance.scheduleFrameCallback` | you want explicit start/stop and per-frame rescheduling without a `TickerProvider`. |

Prefer **Flame** for anything with real motion (see `references/flutter-flame-patterns`). Prefer **Ticker** for widgets-only — it auto-reschedules each frame and respects the provider's mute state.

---

### 3A. Flame path — `update`/`render`

`FlameGame` is the root of the component tree and owns the loop; `update(double dt)` receives seconds since the last frame (per Flame `game.md`). Mirror model → components in `update`, draw in component `render`.

```dart
import 'package:flame/game.dart';
import 'package:flame/components.dart';

class SnakeGame extends FlameGame {
  SnakeGame({required this.model});
  final SnakeModel model;
  static const double _maxFrameTime = 1 / 30; // clamp: never step more than ~33ms

  @override
  void update(double dt) {
    final clamped = dt.clamp(0.0, _maxFrameTime);
    model.advance(clamped);   // pure step
    super.update(clamped);    // advances child components/effects
    _syncComponents();        // mirror model state -> nodes
  }

  void _syncComponents() {
    // position PositionComponents from model coords; add/remove on spawn/despawn
  }
}
```

**Pause/resume (Flame):** use `pauseEngine()` / `resumeEngine()`, or set the `paused` attribute. When paused the `GameLoop` stops calling `update`/`render` until resumed. For debugging, `stepEngine()` advances exactly one frame while paused. (Flame `game.md`.)

**Slow-mo / fast-forward (optional):** add the `HasTimeScale` mixin to the game and set `timeScale` (default `1.0`; `>1` faster, `<1` slower). It also exposes convenience `pause`/`resume`. (Flame `util.md`.) Do **not** hand-multiply `dt` if you use this mixin — it scales for you.

**Resolution independence:** drive the camera with `CameraComponent.withFixedResolution(width:, height:, world:)` so world coordinates stay constant across devices and only black bars change. Keep model units = world units; never bake screen pixels into the model. (Flame `camera.md`.)

---

### 3B. Widgets-only path — `Ticker`

A `Ticker` "calls its callback once per animation frame, when enabled"; the callback receives `elapsed` as a **`Duration`** measured from `start()`. Because `elapsed` is cumulative, compute per-frame `dt` by differencing against the previous elapsed.

```dart
import 'package:flutter/scheduler.dart';

class _GameScreenState extends State<GameScreen>
    with SingleTickerProviderStateMixin {
  late final Ticker _ticker;
  Duration _last = Duration.zero;
  static const double _maxFrameTime = 1 / 30;

  @override
  void initState() {
    super.initState();
    _ticker = createTicker(_onTick)..start();
  }

  void _onTick(Duration elapsed) {
    final dt = (elapsed - _last).inMicroseconds / 1e6; // seconds
    _last = elapsed;
    final clamped = dt.clamp(0.0, _maxFrameTime);
    widget.model.advance(clamped);
    setState(() {}); // mirror model -> widgets (or notify a ValueNotifier/ChangeNotifier)
  }

  @override
  void dispose() {
    _ticker.dispose(); // REQUIRED — leaks a frame callback otherwise
    super.dispose();
  }
}
```

**Pause/resume (Ticker):** call `_ticker.stop()` to pause and `_ticker.start()` to resume. On resume, reset `_last = Duration.zero` is **not** needed because `elapsed` continues from the same clock — but you MUST guard the first post-resume tick (the gap produces a large `dt`); the clamp in step 4 handles this. Alternatively set `_ticker.muted = true`: time still elapses but no callbacks fire (per Ticker docs) — usually prefer `stop()` for a real pause so no simulated time is lost.

> Prefer pushing state through a `ValueNotifier`/`ChangeNotifier` and rebuilding only the affected subtree (`ValueListenableBuilder`) instead of a top-level `setState` — see `references/ui-and-animations` and `references/performance-checklist`.

---

### 3C. Widgets-only path — `SchedulerBinding` (manual)

`scheduleFrameCallback` fires its callback **once**, receiving `Duration timeStamp`; you must re-register every frame (`rescheduling: true`) to keep looping, and cancel by id to stop. Use when you need explicit lifecycle control without a `TickerProvider`.

```dart
import 'package:flutter/scheduler.dart';

int? _cbId;
Duration _last = Duration.zero;
const double _maxFrameTime = 1 / 30;

void _start() {
  _cbId = SchedulerBinding.instance.scheduleFrameCallback(_frame);
}

void _frame(Duration timeStamp) {
  final dt = (timeStamp - _last).inMicroseconds / 1e6;
  _last = timeStamp;
  model.advance(dt.clamp(0.0, _maxFrameTime));
  // mirror state -> widgets
  _cbId = SchedulerBinding.instance.scheduleFrameCallback(_frame, rescheduling: true);
}

void _stop() {
  final id = _cbId;
  if (id != null) SchedulerBinding.instance.cancelFrameCallbackWithId(id);
  _cbId = null;
}
```

---

### 4. Clamp `dt` (mandatory, all paths)
Apply **before** calling `advance`. Recommended cap: `1/30` s (≈33 ms). Floor at `0.0`.

```dart
final clamped = dt.clamp(0.0, 1 / 30);
```
- The cap bounds worst-case per-frame motion → no tunnelling after a hitch.
- The floor rejects a negative `dt` (clock skew on resume / first frame where `_last == 0`).
- First Ticker/Scheduler frame: `elapsed - 0` is the full elapsed time → clamp saves you, but ideally seed `_last` on the first tick (`if (_last == Duration.zero) { _last = elapsed; return; }`).

### 5. Make it deterministic — fixed-timestep accumulator (when reproducibility matters)
Variable `dt` is fine for visuals but NOT for replays/level-validation/golden tests. Accumulate real time and step the model in fixed slices. This decouples simulation rate from frame rate.

```dart
const double _fixed = 1 / 60; // simulation step (seconds)
double _accumulator = 0;

void pump(double rawDt) {
  _accumulator += rawDt.clamp(0.0, 0.25); // clamp accumulated, larger cap ok here
  while (_accumulator >= _fixed) {
    model.advance(_fixed);   // ALWAYS the same step -> deterministic
    _accumulator -= _fixed;
  }
  // optional: interpolate render using _accumulator / _fixed for smoothness
}
```
- Same seed + same input sequence + fixed step → bit-identical state. This is the contract your tests rely on. See `references/algorithms-for-games` and `references/testing-and-release`.
- Cap the accumulator (e.g. 0.25 s) to avoid a "spiral of death" where a slow frame queues more steps than the next frame can run.

### 6. Mirror model → presentation (one direction only)
- Flame: in `update`, position/add/remove components from model state. Input handlers mutate the model, never the components directly.
- Widgets: render from model fields each build. Keep build pure (no mutation).
- Never let the view hold authoritative state. The model is the single source of truth (`references/flutter-game-architecture`).

### 7. Lifecycle & app backgrounding
- Stop/pause the loop when the route is not visible and on `AppLifecycleState.paused`/`inactive` (Flame: `pauseEngine`; widgets: `_ticker.stop()` / cancel callback). Resume on `resumed`.
- Always `dispose()` the `Ticker` / cancel the scheduled callback in `dispose()` — a leaked frame callback runs forever and burns battery.
- On resume, the clamp prevents the giant catch-up `dt`. Do not "replay" lost wall-clock time for kids' games — just resume.

### 8. Write the tests (pure Dart, no widgets)
Cross-link: `references/testing-and-release`, `checklists/*`.
- **Frame-rate independence:** advancing 1.0 s as one `advance(1.0)` vs. sixty `advance(1/60)` lands the object within an epsilon of the same position.
- **Determinism:** two models with the same seed + same fixed-step input sequence produce identical state (deep-equal).
- **Clamp:** `advance` with a 5 s raw `dt` (pre-clamp) does not tunnel; post-clamp step is bounded.
- **Pause:** while `phase == paused` (or loop stopped), `advance` is a no-op / not called → state frozen.
- **dt == 0:** `advance(0)` is a no-op and never NaNs.

```dart
test('frame-rate independent within epsilon', () {
  final a = SnakeModel(rng: Random(1))..phase = GamePhase.playing;
  final b = SnakeModel(rng: Random(1))..phase = GamePhase.playing;
  a.advance(1.0);
  for (var i = 0; i < 60; i++) { b.advance(1 / 60); }
  expect((a.headX - b.headX).abs(), lessThan(1e-3));
});
```

---

## Done when
- [ ] `dt` is clamped (`clamp(0.0, maxFrameTime)`) on **every** path before `advance`.
- [ ] Model has no `package:flutter` import and no wall-clock reads; `Random` is injected.
- [ ] One driver chosen (Flame `update` / `Ticker` / `SchedulerBinding`) and wired; render only reads state.
- [ ] Pause/resume works (Flame `pauseEngine`/`resumeEngine`, or `Ticker.stop()`/`start()`), and loop pauses on app background.
- [ ] `Ticker`/scheduled callback is disposed/cancelled in `dispose()`.
- [ ] Frame-rate-independence + determinism tests pass under `dart test`.
- [ ] (If reproducibility required) fixed-timestep accumulator in place; replay/golden tests pass.

## Common pitfalls
- **Mutating the model in `render`/`build`.** Breaks determinism and causes "set state during build" errors. Mutate only in `update`/the tick handler.
- **Forgetting the clamp** → object tunnels through walls after a single dropped frame or a debugger pause; physics NaNs.
- **Using variable `dt` for replays/validation** → tests flake because float results depend on frame timing. Use the fixed step (step 5).
- **`Random()` inline in the model** → non-reproducible. Inject a seeded `Random` (`assets/seeded_random.dart`).
- **Not differencing `elapsed`/`timeStamp`.** Both are cumulative `Duration` from start, not per-frame deltas — subtract the previous value, then convert to seconds via `inMicroseconds / 1e6`.
- **Leaking the Ticker.** No `dispose()` → callback keeps firing off-screen, draining battery and mutating a dead model. Kids-app reviewers notice battery drain.
- **Hand-scaling `dt` while also using `HasTimeScale`** → double-applied time scale. Pick one.
- **Baking screen pixels into the model.** Keep model units device-independent; map to pixels only in the view / via `CameraComponent.withFixedResolution`.
- **No-loop genres running a loop anyway.** Jigsaw/memory/coloring should react to input events, not spin a 60 fps ticker — wasted battery for a kids' app (`references/performance-checklist`, `references/accessibility-child-safety`).
- **Ignoring Reduce Motion.** If the loop only drives decorative motion, honor the platform reduce-motion setting and idle the loop when nothing is animating (`references/accessibility-child-safety`).

## Cross-links
- `references/flutter-game-architecture` — mode choice, model/view separation.
- `references/flutter-flame-patterns` — `FlameGame`, components, camera.
- `references/algorithms-for-games` — fixed-step integration, interpolation.
- `references/testing-and-release` — `dart test`, golden/replay determinism.
- `references/performance-checklist` — minimize per-frame rebuilds, idle when static.
- `references/accessibility-child-safety` — Reduce Motion, battery, kids-safety.
- `assets/seeded_random.dart`, `assets/flame_game_template.dart`, `assets/flutter_game_widget_template.dart`.
- `checklists/*` — pre-handoff verification.
