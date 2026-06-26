# Dart async & isolates (event loop, Futures, Streams, Isolates)

Games are mostly synchronous on a single thread, but loading, decoding, and any I/O must be
async so the UI never stalls. Dart has **one UI event loop per isolate** and **no shared-memory
threads** — concurrency is cooperative (async on the loop) or message-passing (isolates). The
analog of Swift's "keep game state on `@MainActor`, offload heavy work" is: keep rules on the
event loop, push CPU-heavy work to an isolate.

## Mental model
- **Event loop** — one isolate has a single thread that drains a microtask queue then an event
  queue, forever. `async`/`await` does **not** add threads; it interleaves work on this one loop.
- **`Future<T>`** — a value that arrives later. `await` suspends the current function and yields
  the loop to other events until the future completes; it does **not** block the thread.
- **`Stream<T>`** — zero-or-more async values over time (taps, ticks, file chunks). Consume with
  `await for` or `listen`.
- **Isolate** — a separate worker with its **own** event loop and memory. Isolates share nothing;
  they communicate by copying messages. This is where true parallel CPU work happens.
- **`Isolate.run` / `compute`** — run one function on a throwaway isolate and get a `Future` back.
- **Determinism stays synchronous.** Game rules live in plain, synchronous pure-Dart methods. Async
  is only the *delivery* mechanism (load, then apply); it never decides outcomes.

## The main rule for games
**Never block the event loop.** A frame is ~16 ms at 60 fps; any synchronous call longer than that
janks the frame. Two offenders: tight CPU loops (level generation, big `jsonDecode`, pathfinding)
and accidental sync I/O. Fix CPU work by moving it to an isolate (`Isolate.run`/`compute`); fix I/O
by `await`ing the async API. `await` alone does **not** make CPU work non-blocking — an `await`ed
function that runs a 200 ms loop *still* freezes the frame. Only an isolate runs it elsewhere.

```dart
// DON'T — heavy decode on the loop; the frame that calls this drops.
Level loadLevelSync(String json) => Level.fromMap(jsonDecode(json) as Map); // blocks UI

// DO — run the parse on a throwaway isolate; the loop stays free for rendering.
Future<Level> loadLevel(String json) =>
    Isolate.run(() => Level.fromMap(jsonDecode(json) as Map<String, dynamic>));
```

## Futures & async/await basics
```dart
Future<GameSave> loadSave() async {
  final raw = await file.readAsString();      // suspends, frees the loop; no thread blocked
  return GameSave.fromJson(jsonDecode(raw));  // small + sync — fine on the loop
}

// Run independent awaits concurrently, then join (Dart's analog of `async let`):
Future<void> preload() async {
  final (level, prefs) = await (loadLevel(id), loadPrefs()).wait; // both in flight
  apply(level, prefs);
}
```
- `await` returns control to the loop until the `Future` completes — other events keep running.
- `Future.wait([...])` / record `.wait` join multiple futures concurrently; don't `await` them
  one-by-one in a loop if they're independent.
- A `Future` is **not** a thread. `Future(() => heavyLoop())` still runs `heavyLoop` on *this*
  isolate's loop — use `Isolate.run` for parallelism, not `Future(...)`.

```dart
// DON'T — wrapping CPU work in a Future does NOT move it off the loop.
final result = await Future(() => generateMaze(10000)); // still blocks the UI isolate
// DO
final result = await Isolate.run(() => generateMaze(10000));
```

## Streams & StreamController
A `Stream` is the async sequence. Consume with `await for` (in an `async` function) or `listen`
(for a handle you can pause/cancel). Create one with a `StreamController` when you bridge a
callback/event source into a stream.

```dart
// Consume:
await for (final tick in ticks) { /* ... */ }        // loops until the stream closes
final sub = scores.listen(_onScore);                  // returns a StreamSubscription

// Produce: a broadcast controller for game events many widgets can observe.
final _events = StreamController<GameEvent>.broadcast();
Stream<GameEvent> get events => _events.stream;
void emit(GameEvent e) => _events.add(e);
```
- **Single-subscription** (default) = one listener, for a finite sequence (a file's chunks).
  **`.broadcast()`** = many listeners, for ongoing events (score changes, achievements).
- **Always close**: `await controller.close()` in `dispose`, and `sub.cancel()` for every
  `listen`. A leaked subscription keeps the source — and its captured state — alive.
- `StreamSubscription` supports `pause()` / `resume()` / `cancel()`; pause a non-essential stream
  while a menu is up instead of fighting events you'll ignore.
- For UI, prefer Flutter's `ValueNotifier`/`ChangeNotifier` (see architecture ref) for simple
  state; reach for `Stream` when you genuinely have an async *sequence* of events.

```dart
// DON'T — listen without ever cancelling; leaks on every screen rebuild.
inputStream.listen(handle); // no handle kept → cannot cancel
// DO
_sub = inputStream.listen(handle);
@override
void dispose() { _sub.cancel(); _events.close(); super.dispose(); }
```

## Isolates for CPU-heavy work
Use an isolate for anything that would blow the frame budget: procedural level generation, large
JSON/asset decode, solver/pathfinding, image processing. Two ergonomic entry points; both copy the
input in and the result out.

```dart
// Isolate.run (Dart 2.19+, standard in Dart 3): one closure, one result. Simplest for one-off
// heavy work; on native it spins up a throwaway isolate and tears it down when the future completes.
final level = await Isolate.run(() => generateLevel(seed: 42, size: 64));

// compute (Flutter foundation): a callback + a single message argument. On native it is
// equivalent to `await Isolate.run(() => callback(message))`; on web there are no isolates,
// so it runs on the current event loop. Use a top-level or static callback to keep the
// implicitly-captured state minimal and sendable.
final level = await compute(generateLevelFor, GenParams(seed: 42, size: 64));
Level generateLevelFor(GenParams p) => generateLevel(seed: p.seed, size: p.size); // top-level
```
- **Pass data as explicit arguments**, not captured closure state. Captured variables get copied
  too and can silently bloat the message — or fail at runtime if they hold something unsendable
  (open files, sockets, `SendPort`-less handles, most platform objects).
- **Message in / result out must be sendable** (copyable): primitives, `String`, `List`/`Map`/`Set`
  of sendables, `TransferableTypedData` for big byte buffers, and your own plain-data classes.
- **Keep the isolate function pure and synchronous-deterministic**: pass the seed in, build a
  `Random(seed)` *inside* (the skill ships `assets/seeded_random.dart`), and the same input yields
  the same level — even though delivery was async.
- Spawning an isolate costs a few ms and copies the payload; it's a win for hundreds-of-ms jobs,
  a loss for tiny ones. Don't isolate a 0.2 ms function.
- A `Flame` game can use the `flame_isolate` package's `FlameIsolate` mixin and its `isolate(fn,
  input)` helper to run work off-loop from inside the game; plain `Isolate.run`/`compute` work too.

```dart
// DON'T — capture a big board by closure; it's copied implicitly and may not be sendable.
final solved = await Isolate.run(() => solve(board)); // `board` captured from outer scope
// DO — pass it in as the explicit, sendable argument.
final solved = await compute(solveBoard, board.toData());
```

## The game loop is a Ticker / Flame update — NOT a Future loop
Per-frame stepping must be **frame-synced**, driven by the engine's vsync, not scheduled on the
async queue. Never build the loop out of `await`/`Future.delayed`/`Timer` — that desyncs from the
display and accumulates drift.

```dart
// DON'T — an async "loop" is not frame-synced and drifts.
Future<void> gameLoop() async {
  while (running) {
    controller.advance(0.016);
    await Future.delayed(const Duration(milliseconds: 16)); // wrong: scheduler, not vsync
  }
}

// DO (Flame) — the engine calls update(dt) every frame on the loop.
@override
void update(double dt) {
  super.update(dt);
  controller.advance(min(dt, 1 / 30)); // clamp dt; advance the PURE, synchronous model
}

// DO (Flutter-only) — a Ticker gives vsync-aligned callbacks.
late final Ticker _ticker = createTicker((elapsed) {
  controller.advanceTo(elapsed.inMicroseconds / 1e6); // sync model step; no await
})..start();
```
- The per-frame `update`/`Ticker` callback must stay **synchronous and allocation-light** — no
  `await`, no per-frame `Isolate.run`, no object churn (reuse `Vector2`/`Paint`). Offloaded work is
  kicked off *outside* the loop and its result applied on a later frame.
- Time advances the model via `dt` (seconds). Clamp `dt` (e.g. `min(dt, 1/30)`) so one slow frame
  can't teleport entities. The simulation step itself is plain synchronous Dart — and therefore
  unit-testable with `dart test` by feeding fixed `dt` values, no engine, no device.

## Cancellation
Dart `Future`s have no built-in cancel, and `Isolate.run` can't be interrupted mid-run — design
around it:
- **Streams**: cancel the `StreamSubscription` (`sub.cancel()`); for `await for`, `break` out or
  wrap the source so closing it ends the loop.
- **Stale async results**: guard with a token/`mounted` check before applying — when a load
  finishes after the player left the level, drop it instead of mutating dead state.
- **Long isolate jobs**: if you must abort, spawn a manual `Isolate` with a `ReceivePort` and kill
  it (`isolate.kill`), or chunk the work and check a "cancelled" flag between chunks. For a simple
  game, prefer making jobs short enough that just ignoring a stale result is sufficient.

```dart
// Guard against applying a result the player no longer wants.
final token = ++_loadToken;
final level = await Isolate.run(() => generateLevel(seed: seed));
if (token != _loadToken) return; // a newer load superseded this one — discard
_apply(level);
```

## What NOT to do
- Don't run CPU-heavy work on the event loop, even behind `await` — `await` frees the loop only at
  suspension points, not during a synchronous burst. Move the burst to an isolate.
- Don't build the game loop from `Timer` / `Future.delayed` / async `while` — use Flame `update` or
  a `Ticker`.
- Don't `await` inside a per-frame `update`/`Ticker` callback, or allocate per frame.
- Don't capture large/unsendable state into an `Isolate.run`/`compute` closure — pass plain-data
  arguments.
- Don't `listen` to a stream without keeping the subscription and cancelling it; don't forget
  `controller.close()`.
- Don't put rules/RNG decisions in async code — keep determinism in the synchronous model and seed
  it explicitly.

(API names verified against Dart/Flutter docs: `Isolate.run<R>(FutureOr<R> computation(),
{String? debugName})` [Dart 2.19+]; `compute<M, R>(ComputeCallback<M, R> callback, M message,
{String? debugLabel})` — on native equivalent to `await Isolate.run(() => callback(message))`,
runs on the current event loop on web; `Stream`, `StreamController` + `.broadcast()`,
`StreamSubscription.pause/resume/cancel`, `await for`, `Future.wait`; Flame `update(double dt)`;
Flutter `Ticker`/`createTicker`; `flame_isolate`'s `FlameIsolate` mixin and `isolate(fn, input)`.)
