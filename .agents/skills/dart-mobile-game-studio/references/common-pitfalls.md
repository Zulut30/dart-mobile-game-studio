# Common pitfalls — Dart · Flutter · Flame (review & generation catalog)

The fast index the reviewer/auditor opens **first**, and the rule-set the generator writes **by**.
It is an operational knowledge base of the mistakes that actually break mobile-game projects —
ordered by how they fail (compile, runtime, lifecycle, FPS, memory, architecture, game loop), not by
topic. Each entry carries a **classifier code**, a **severity**, a **tripwire** you can `grep`, a
tight **bad → good**, and a one-line **AI rule**. Deep explanations live in the linked references and
`checklists/` — this file is the map, not the territory.

> **On the frequencies.** There is no reliable public statistic of the form "X% of Flutter devs make
> mistake Y". The P0–P3 priorities below are an applied expert scale grounded in three proxies: the
> official Flutter *common errors* pages, the Dart/Flutter analyzer lint set, and the Flutter/Flame
> performance & lifecycle guides. Treat them as triage order, not measurement.

## How to use this file

- **Generating code** → write to the defaults in [§ Generation defaults](#generation-defaults-write-it-right-the-first-time);
  they encode the fixes pre-emptively so the bug never lands.
- **Reviewing a diff/PR** → scan the changed `.dart` for the [classifier](#error-classifier-codes)
  tripwires; phrase each finding `CODE · severity · file:line · what → consequence → fix`. Pairs with
  the `code-reviewer` agent (diff) and `code-auditor` agent (whole repo).
- **Debugging a crash/jank/leak** → jump to the [Symptom → cause → fix matrix](#symptom--cause--fix);
  match the console string or the observed behaviour, apply the fix.

---

## Priority ladder (catch these first)

| # | Priority | Zone | Mistake | Classifier |
|---|---|---|---|---|
| 1 | **P0** | Flutter layout | `RenderFlex overflowed`, unbounded constraints, `RenderBox was not laid out` | `FLUTTER_LAYOUT_CONSTRAINTS` |
| 2 | **P0** | Dart null-safety | abusing `!`, `late`, nullable fields → `Null check operator…`, `LateInitializationError` | `DART_NULL_SAFETY` |
| 3 | **P0** | Async/lifecycle | `BuildContext` across an `await`; `setState` after `dispose` | `DART_CONTEXT_ACROSS_ASYNC`, `FLUTTER_LIFECYCLE_SETSTATE` |
| 4 | **P0** | Flutter perf | heavy work inside `build()` | `FLUTTER_BUILD_PERFORMANCE` |
| 5 | **P1** | Flame perf | allocating `Vector2`/`Paint`/`Rect`/`TextPaint` in `update()`/`render()` | `FLAME_HOT_PATH_ALLOCATION` |
| 6 | **P1** | Flame lifecycle | not knowing `add`/`remove` are async; one-shot init in `onMount` | `FLAME_COMPONENT_LIFECYCLE` |
| 7 | **P1** | Flame assets | `images.fromCache()` before the asset is loaded | `FLAME_ASSET_LIFECYCLE` |
| 8 | **P1** | Flutter lifecycle | un-`dispose`d controller/subscription/timer | `FLUTTER_MEMORY_LEAK` |
| 9 | **P1** | Dart async | forgotten `await`; fire-and-forget without `unawaited()` | `DART_ASYNC_AWAIT` |
| 10 | **P1** | Flutter lists | `Column` + big list instead of a lazy `.builder` | `FLUTTER_BUILD_PERFORMANCE` |
| 11 | **P1** | Flame collision | no `HasCollisionDetection`/hitbox/`CollisionCallbacks`; every hitbox active | `FLAME_COLLISION_CONFIG` |
| 12 | **P2** | Architecture | game loop + Flutter UI + business/state logic mixed | `ARCHITECTURE_LAYERING` |
| 13 | **P2** | Flutter rendering | needless `Opacity`/clip/`saveLayer` | `FLUTTER_RENDER_COST` |
| 14 | **P2** | Flame camera/world | binding the world to screen size instead of `World`/`CameraComponent` | `FLAME_CAMERA_WORLD_COORDINATES` |
| 15 | **P2** | Dart typing | `dynamic`, raw types, loose JSON models | `DART_DYNAMIC_TYPING` |

**Priority = triage order**, severity = blast radius (next section). A P2 with a Critical instance
(e.g. an architecture tangle that loses save data) still gets fixed first on its merits.

---

## Error classifier (codes)

Tag every finding with a code so review output is groupable and scoreable. Each maps to a deep
reference and a checklist that own the full rationale.

| Code | Zone | Lands as | Deep ref / checklist |
|---|---|---|---|
| `DART_NULL_SAFETY` | `!`, `late`, nullable | runtime crash | [dart/dart-language-essentials.md](dart/dart-language-essentials.md) · [dart-code-quality](../checklists/dart-code-quality.md) |
| `DART_ASYNC_AWAIT` | unawaited / fire-and-forget | races, lost errors | [dart/dart-async-isolates.md](dart/dart-async-isolates.md) |
| `DART_CONTEXT_ACROSS_ASYNC` | `BuildContext` after `await` | crash on navigate/close | [dart/flutter-widgets-mastery.md](dart/flutter-widgets-mastery.md) |
| `DART_DYNAMIC_TYPING` | `dynamic`, raw `Map`/`List` | compile-time → runtime | [dart/dart-api-design.md](dart/dart-api-design.md) · [dart/dart-patterns-idioms.md](dart/dart-patterns-idioms.md) |
| `FLUTTER_LAYOUT_CONSTRAINTS` | overflow / unbounded / parent-data | broken UI | [flutter-game-architecture.md](flutter-game-architecture.md) · [flutter-ui-quality](../checklists/flutter-ui-quality.md) |
| `FLUTTER_LIFECYCLE_SETSTATE` | `setState` in `build`/after `dispose` | crash, jank | [dart/flutter-widgets-mastery.md](dart/flutter-widgets-mastery.md) |
| `FLUTTER_BUILD_PERFORMANCE` | heavy `build`, eager lists | jank | [performance-checklist.md](performance-checklist.md) |
| `FLUTTER_RENDER_COST` | `Opacity`/clip/`saveLayer` | GPU jank | [performance-checklist.md](performance-checklist.md) |
| `FLUTTER_MEMORY_LEAK` | missing `dispose`, stored `BuildContext` | leak, late callback | [flutter-ui-quality](../checklists/flutter-ui-quality.md) |
| `FLAME_HOT_PATH_ALLOCATION` | alloc in `update`/`render` | GC stutter, FPS drop | [flutter-flame-patterns.md](flutter-flame-patterns.md) · [flame-quality](../checklists/flame-quality.md) |
| `FLAME_DT_IGNORED` | movement without `dt` | wrong speed @120 Hz | [flutter-flame-patterns.md](flutter-flame-patterns.md) |
| `FLAME_COMPONENT_LIFECYCLE` | async add/remove, `onMount` misuse | "didn't appear", races | [flame-quality](../checklists/flame-quality.md) |
| `FLAME_ASSET_LIFECYCLE` | `fromCache` before `load` | exception, empty sprite | [flutter-flame-patterns.md](flutter-flame-patterns.md) |
| `FLAME_SPRITE_BATCHING` | many images vs atlas/batch | memory, draw calls | [asset-pipeline.md](asset-pipeline.md) |
| `FLAME_COLLISION_CONFIG` | detection/hitbox/type missing | no collisions / too slow | [flame-quality](../checklists/flame-quality.md) |
| `FLAME_POOLING` | spawn/destroy churn | GC, FPS decay | [performance-checklist.md](performance-checklist.md) |
| `FLAME_VISIBILITY` | add/remove vs `HasVisibility` | flicker, stale update | [flutter-flame-patterns.md](flutter-flame-patterns.md) |
| `FLAME_UI_OVERLAY_BOUNDARY` | Flutter UI inside the loop | untestable, janky | [flutter-games-toolkit.md](flutter-games-toolkit.md) |
| `FLAME_CAMERA_WORLD_COORDINATES` | screen vs world coords mixed | scaling bugs | [flutter-flame-patterns.md](flutter-flame-patterns.md) |
| `ARCHITECTURE_LAYERING` | loop/UI/domain/persistence mixed | untestable, fragile | [flutter-game-architecture.md](flutter-game-architecture.md) · [quality-policy.md](quality-policy.md) |

## Severity scoring

| Severity | Means | Examples |
|---|---|---|
| **Critical** | runtime crash, data loss, broken navigation, asset-load failure | `!` on a null, `setState` after dispose, `fromCache` before load, save lost by a missing `await` |
| **High** | jank, memory leak, broken collision, wrong game speed | alloc per frame, un-disposed controller, no `dt`, no hitbox |
| **Medium** | poor architecture, weak typing, over-rebuild | `dynamic` JSON, loop/UI tangle, rebuild-the-world `setState` |
| **Low** | style / lint / readability | `var`-over-`final`, naming drift, missing trailing comma |

Critical & High are **blocking**. Medium is should-fix. Low is a nit. A lint catches most Low and a
little Medium; **everything Critical/High in the Flame and layout zones passes the analyzer cleanly**
— that is exactly why this catalog exists.

---

## Dart pitfalls

### `DART_NULL_SAFETY` — `!`, `late`, nullable state · Critical · P0
**Tripwire:** `grep -nE '!\.|!\)|! ;|\blate \b'` in game logic. **Treat `!` and `late` as red flags**
unless a lifecycle invariant is documented. Symptoms: `Null check operator used on a null value`,
`LateInitializationError`.
```dart
// bad — ! relies on a runtime hope; late read before init throws
Player? player;
void onHit() => player!.takeDamage(10);
// good — promote then guard
void onHit() { final p = player; if (p == null) return; p.takeDamage(10); }
```
`late final` is acceptable **only** when set once in `onLoad`/`initState` and read strictly after.
**AI rule:** never `!`/`as` external data (JSON, prefs, sensors, map lookups); promote-and-guard, or
`(x as T?) ?? fallback`, or an `if (json case {'k': final int v})`. → [dart/dart-language-essentials.md](dart/dart-language-essentials.md)

### `DART_ASYNC_AWAIT` — forgotten await / fire-and-forget · High · P1
**Tripwire:** a call returning `Future` whose result is discarded in a non-`async` body; `analysis`
lint `unawaited_futures`/`discarded_futures`.
```dart
// bad — navigation may run before the save lands
void saveGame() { repository.save(progress); goToMenu(); }
// good
Future<void> saveGame() async { await repository.save(progress); goToMenu(); }
```
**AI rule:** every `Future` must be `await`-ed, `return`-ed, `Future.wait`-ed, or explicitly
`unawaited(...)` — there is no fifth, silent option. → [dart/dart-async-isolates.md](dart/dart-async-isolates.md)

### `DART_CONTEXT_ACROSS_ASYNC` — `BuildContext` after `await` · Critical · P0
**Tripwire:** `await` then `Navigator.of(context)` / `ScaffoldMessenger.of(context)` / `context.` with
no `mounted` guard between. Lint: `use_build_context_synchronously`.
```dart
// bad
await loader.load(); Navigator.of(context).pushNamed('/game');
// good
await loader.load(); if (!context.mounted) return; Navigator.of(context).pushNamed('/game');
```
Inside a `State`, guard with `if (!mounted) return;` before `setState`. **AI rule:** an async gap
invalidates `context` — re-check `mounted` after every `await` that precedes a context use. → [dart/flutter-widgets-mastery.md](dart/flutter-widgets-mastery.md)

### `DART_DYNAMIC_TYPING` — `dynamic` / raw types / loose JSON · Medium · P2
**Tripwire:** `grep -nE '\bdynamic\b|Map<String, dynamic>|jsonDecode\('` in domain code; lint
`avoid_dynamic_calls` (promoted to **error** in the shipped `analysis_options.yaml`).
```dart
// bad — runtime minefield as the game grows
final hp = jsonDecode(body)['player']['stats']['hp'];
// good — typed boundary model
final stats = PlayerStats.fromJson(json['stats'] as Map<String, Object?>);
```
**AI rule:** prefer `Map<String, Object?>` over `Map<String, dynamic>`; lift JSON into typed models at
the boundary; reach for Dart 3 `sealed` events, `enum`, `record`, and `extension type` IDs to keep
errors at compile time. → [dart/dart-patterns-idioms.md](dart/dart-patterns-idioms.md), [dart/dart-api-design.md](dart/dart-api-design.md)

### `DART_MUTABLE_STATE` — `var` where `final` belongs · Low · P3
**Tripwire:** `var`/mutable field never reassigned; lints `prefer_final_locals`, `prefer_final_fields`.
**AI rule:** generate `final` / `late final` / `const` by default; `var` and mutable fields only where
a real reassignment exists. Configs (levels, enemies, loot, waves) are immutable value types. →
[dart/dart-language-essentials.md](dart/dart-language-essentials.md)

---

## Flutter pitfalls

### `FLUTTER_LAYOUT_CONSTRAINTS` — overflow / unbounded / parent-data · Critical · P0
Flutter names `RenderFlex overflow` one of its most frequent framework errors. Three faces:

**(a) Overflow** — a `Row`/`Column` child wants more than the main axis offers.
```dart
// bad — Column inside Row gets loose width → overflow stripes
Row(children: [avatar, Column(children: [Text(name), Text(longDesc)])])
// good — Expanded bounds it; ellipsis the text
Row(children: [avatar, Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start,
  children: [Text(name), Text(longDesc, overflow: TextOverflow.ellipsis)]))])
```
**(b) Unbounded** — `Vertical viewport was given unbounded height`: a scrollable in a `Column`.
```dart
// bad
Column(children: [title, ListView.builder(itemCount: n, itemBuilder: ...)])
// good
Column(children: [title, Expanded(child: ListView.builder(itemCount: n, itemBuilder: ...))])
```
**(c) Parent-data mismatch** — `Incorrect use of ParentDataWidget`: `Expanded`/`Flexible` must be a
**direct** child of `Row`/`Column`/`Flex`; `Positioned` of `Stack`; `TableCell` of `Table`.
```dart
// bad → good: hoist the parent-data widget to the direct child slot
Padding(padding: p, child: Expanded(child: t))   →   Expanded(child: Padding(padding: p, child: t))
```
**AI rule:** a scrollable/flex child without a bound is a defect — reach for `Expanded`/`Flexible`/
`SizedBox`/`ConstrainedBox`/`LayoutBuilder`, and keep `Expanded`/`Positioned`/`TableCell` directly
under their required parent. → [flutter-ui-quality](../checklists/flutter-ui-quality.md) (responsive layout)

### `FLUTTER_LIFECYCLE_SETSTATE` — `setState` in `build` / after `dispose` · Critical · P0
**Tripwire:** `setState`/`showDialog`/`Navigator.push`/`ScaffoldMessenger.of` **inside** `build()`; a
`Timer`/`Future`/`Stream` callback calling `setState` with no `mounted` guard or no teardown.
```dart
// bad — setState during build; build can run every frame
Widget build(c) { if (over) setState(() => showOver = true); return ...; }
// good — derive, don't store; render the state directly
Widget build(c) => over ? const GameOverScreen() : const PlayingScreen();

// bad — timer fires setState after the widget is gone
timer = Timer.periodic(d, (_) => setState(() => seconds++));
// good — guard AND cancel in dispose
timer = Timer.periodic(d, (_) { if (!mounted) return; setState(() => seconds++); });
@override void dispose() { timer.cancel(); super.dispose(); }
```
**AI rule:** `build` is pure — no state mutation, no navigation, no dialogs. Prefer deriving UI from
state over storing derived state. Cancel the source in `dispose`, don't just check `mounted`. →
[dart/flutter-widgets-mastery.md](dart/flutter-widgets-mastery.md)

### `FLUTTER_BUILD_PERFORMANCE` — heavy `build` / eager lists · High · P0–P1
**Tripwire:** inside `build()` — `sort`, `jsonDecode`, file/network/db, asset load, pathfinding,
proc-gen, large loops, or **creating controllers**. Also a literal `Column(children: bigList.map…)`.
```dart
// bad — recomputed every rebuild (and build can be per-frame)
Widget build(c) { final sorted = items..sort(byRarity); return View(sorted); }
// good — compute once; lazy-build long lists
late final sorted = [...widget.items]..sort(byRarity);   // in initState/field
ListView.builder(itemCount: cards.length, itemBuilder: (c, i) => CardTile(cards[i]));
```
**AI rule:** `build` only *describes* UI from ready state. Move computation to `initState`/a memoised
selector/the pure model; long/grid lists use `.builder`. → [performance-checklist.md](performance-checklist.md)

### `FLUTTER_RENDER_COST` — needless `Opacity` / clip / `saveLayer` · Medium · P2
**Tripwire:** `Opacity(`, `ShaderMask`, `BackdropFilter`, `Clip.antiAliasWithSaveLayer`,
`ColorFilter`, `PhysicalModel` on a hot/animated path. `saveLayer` breaks the GPU pipeline → jank.
```dart
// bad — full saveLayer for a constant tint
Opacity(opacity: .5, child: Container(color: Colors.red, child: child))
// good — bake alpha into the color
Container(color: Colors.red.withValues(alpha: .5), child: child)
```
**AI rule:** prefer a semitransparent color / `AnimatedOpacity` / `Image.opacity` / decoration
`borderRadius` over the widget that triggers `saveLayer` mid-motion. → [performance-checklist.md](performance-checklist.md)

### `FLUTTER_MEMORY_LEAK` — missing `dispose` / stored `BuildContext` · High · P1
**Tripwire:** `AnimationController`/`Ticker`/`ValueNotifier`/`ChangeNotifier`/`StreamSubscription`/
`Timer`/`FocusNode`/`TextEditingController`/`ScrollController` created in a `State` with no matching
teardown; a `BuildContext` stored in a field. **AI rule:** every disposable created here is torn down
in `dispose()` (`cancel`/`close`/`removeListener`), reverse order, `super.dispose()` last; a passed-in
controller is disposed by its owner, not here; never cache `BuildContext` (a `State` can outlive its
widget). → [flutter-ui-quality](../checklists/flutter-ui-quality.md) (lifecycle & dispose)

---

## Flame pitfalls

> Flame owns the game loop and component tree; each tick calls `update(dt)` then `render(canvas)`.
> The failures cluster in three places: **hot-path allocation**, **lifecycle/assets**, and
> **collision config**. Full patterns: [flutter-flame-patterns.md](flutter-flame-patterns.md) +
> [flame-quality](../checklists/flame-quality.md).

### `FLAME_HOT_PATH_ALLOCATION` — allocating per frame · High · P1
The single most important Flame perf bug. 100 components @60 FPS each `new`-ing a `Vector2`+`Paint` =
**12 000 objects/sec** → constant GC → frame drops.
**Tripwire:** in `update`/`render` — `Vector2(`, `Paint()`, `TextPaint(`, `Sprite(`,
`SpriteAnimation(`, `Path()`, `Rect.fromLTWH(`, `List.generate(`, `.where(...).toList()`,
`.map(...).toList()`.
```dart
// bad
void render(Canvas c) { final p = Paint()..color = color; c.drawRect(size.toRect(), p); }
// good — Paint is a field; mutate vectors in place
final Paint _paint = Paint()..color = color;
void update(double dt) => position.y += speed * dt;          // no temp Vector2 at all
void render(Canvas c) => c.drawRect(size.toRect(), _paint);
```
**AI rule:** hoist `Paint`/`Vector2`/`Rect`/`Path` to fields; mutate with `setFrom`/`setValues`/
`addScaled`. Only knowingly short-lived, profiler-blessed allocations are allowed. → [flame-quality](../checklists/flame-quality.md)

### `FLAME_DT_IGNORED` — movement without `dt` · High · P1
**Tripwire:** `position`/timer/cooldown changed by a per-frame constant in `update`. **Flame supplies
`dt` in seconds but does NOT clamp it** — you must.
```dart
// bad — twice as fast on a 120 Hz screen
void update(double dt) => position.y += 5;
// good — frame-rate independent, and clamp dt against hitches
void update(double dt) { final d = math.min(dt, 1 / 30); position.y += speed * d; }
```
**AI rule:** all motion/timers scale by `dt`; clamp `dt` (`min(dt, 1/30)`) before stepping so a GC/load
spike can't teleport entities. → [flutter-flame-patterns.md](flutter-flame-patterns.md)

### `FLAME_COMPONENT_LIFECYCLE` — async add/remove, `onMount` misuse · High · P1
`onLoad` runs **once** (async init/assets); `onMount` runs on **every** mount; `add`/`remove` complete
on the next tick, not immediately.
```dart
// bad — one-shot init in onMount (runs again on re-mount); racey post-add mutation
late final Vector2 spawn; @override void onMount() { spawn = position.clone(); }
// good — construct configured; await the add when ordering matters
final enemy = Enemy(spawn: spawnPoint); await world.add(enemy);
```
**AI rule:** `onLoad` = one-time async setup; `onMount` = repeatable per-mount setup (pooled-object
reset goes here); `onRemove` = cleanup; `update` = simulation; `render` = drawing only. Never put
one-shot `late final` init in `onMount`. → [flame-quality](../checklists/flame-quality.md)

### `FLAME_ASSET_LIFECYCLE` — `fromCache` before `load` · Critical · P1
**Tripwire:** `images.fromCache(` / `Sprite(` with no awaited `images.load`/`loadAll` first.
`fromCache` throws if the image isn't loaded.
```dart
// good — load in onLoad, then build sprites
Future<void> onLoad() async {
  await images.loadAll(['player.png', 'enemy.png']);
  playerSprite = Sprite(images.fromCache('player.png'));
}
```
**AI rule:** every `fromCache(x)` must have a provable preceding `await images.load(x)`/`loadAll([…])`,
normally in the game's `onLoad` or a preloader. → [flutter-flame-patterns.md](flutter-flame-patterns.md)

### `FLAME_SPRITE_BATCHING` — many images vs atlas/batch · Medium · P2
**Tripwire:** dozens of individual `*.png` for one entity's frames; many `SpriteComponent`s sharing a
texture family drawn separately. **AI rule:** pack frames into a sprite sheet/atlas; for mass draws
use `SpriteBatch`/a shared `Sprite`/`Image`; pool the components. → [asset-pipeline.md](asset-pipeline.md)

### `FLAME_COLLISION_CONFIG` — detection/hitbox/type · High · P1
Three sub-faults: (1) collisions silently don't fire; (2) expecting physics resolution from the
detector; (3) every body active.
```dart
// good — game enables detection; component has a hitbox + callbacks
class MyGame extends FlameGame with HasCollisionDetection {}
class Bullet extends SpriteComponent with CollisionCallbacks {
  @override Future<void> onLoad() async => add(RectangleHitbox()..collisionType = CollisionType.passive);
}
```
**AI rule:** `FlameGame` mixes `HasCollisionDetection`; colliders mix `CollisionCallbacks` + a hitbox;
mark non-reactive bodies `CollisionType.passive`; the detector only *reports* — game logic decides
outcomes in pure Dart; add anti-tunneling for fast projectiles (it is **not** automatic). → [flame-quality](../checklists/flame-quality.md)

### `FLAME_POOLING` — spawn/destroy churn · High · P1–P2
**Tripwire:** `add(Bullet(...))`/`add(Particle(...))` in a frequent spawn path; entities created and
removed many times/sec. **AI rule:** pool hot entities (bullets, particles, damage numbers, enemy
projectiles, loot) via `ComponentPool` or a manual pool with bounded `maxSize`; `removeFromParent()`
recycles; reset reusable state in `onMount`. → [performance-checklist.md](performance-checklist.md)

### `FLAME_VISIBILITY` — add/remove vs `HasVisibility` · Medium · P2
**Tripwire:** `removeFromParent()` immediately followed by re-`add` of the same component (async — it
may not have detached yet). **AI rule:** to merely hide, use `HasVisibility` (but note it still
`update`s/collides/receives input); to truly detach-and-reattach, `await component.removed` before
re-adding. → [flutter-flame-patterns.md](flutter-flame-patterns.md)

### `FLAME_UI_OVERLAY_BOUNDARY` — Flutter UI inside the loop · Medium · P2
**Tripwire:** showing dialogs / building Flutter widgets from inside `update`, or storing widgets in
components. **AI rule:** gameplay/render/input = Flame components; menus/HUD/settings/dialogs = Flutter
**overlays** (`overlayBuilderMap` + `overlays.add/remove`); save/config/rules = pure Dart services.
Pause via `pauseEngine()` + an overlay. → [flutter-games-toolkit.md](flutter-games-toolkit.md)

### `FLAME_CAMERA_WORLD_COORDINATES` — screen vs world · Medium · P2
**Tripwire:** positioning gameplay off `screenWidth`/`screenHeight` instead of placing it in a `World`
observed by a `CameraComponent`. **AI rule:** gameplay lives in `World` (world coordinates); the
camera decides what's visible (`viewfinder`); HUD is a Flutter overlay or viewport component — never
size the world to the screen. → [flutter-flame-patterns.md](flutter-flame-patterns.md)

---

## Architecture pitfalls

### `ARCHITECTURE_LAYERING` — loop/UI/domain/persistence mixed · Medium · P2
**Tripwire:** business rules, saves, or network calls inside `update`/a component/`build`; Flutter or
Flame imports under `lib/models/`/`lib/systems/`. **AI rule — keep the seams:**

| Layer | Owns | Must not |
|---|---|---|
| `FlameGame` | loop, world/camera, orchestration | decide rules / score |
| `Component` | position, render, local behaviour | hold game rules |
| `System` | spawn, waves, collisions, AI, cleanup | touch Flutter |
| `Domain` (pure Dart) | rules: damage, loot, stats, state machine | import flutter/flame |
| `Repository` | save/load, config, persistence | run in the loop |
| Flutter UI | menus, HUD, overlays, navigation | hold simulation state |

Rules + state machine are pure Dart (`menu → playing → paused → won/lost`, `sealed` + exhaustive
`switch`), unit-tested on the VM. State management (`ValueNotifier`/Provider/Riverpod/Bloc) binds UI
to game state with UI-state and simulation-state kept apart. → [flutter-game-architecture.md](flutter-game-architecture.md), [quality-policy.md](quality-policy.md)

---

## Symptom → cause → fix

Match the console string or the observed behaviour; apply the fix.

| Symptom | Likely cause | Fix |
|---|---|---|
| `A RenderFlex overflowed by … pixels` | `Row`/`Column` child unbounded | `Expanded`/`Flexible`/`SizedBox`; ellipsis text |
| `RenderBox was not laid out` | an earlier constraints error cascaded | fix the **first** layout exception in the log |
| `Vertical viewport was given unbounded height` | `ListView` in a `Column` without height | `Expanded(child: ListView…)` |
| `Incorrect use of ParentDataWidget` | `Expanded`/`Positioned` under the wrong parent | put it directly under `Row`/`Column`/`Flex` / `Stack` |
| `setState() called after dispose()` | timer/listener/future fired post-teardown | `cancel`/`removeListener` in `dispose`; `mounted` guard |
| `setState()/markNeedsBuild() called during build` | state mutated inside `build` | derive state, or `addPostFrameCallback` |
| `Null check operator used on a null value` | `!` on a nullable | promote + guard; typed init |
| `LateInitializationError` | `late` read before init | init in `onLoad`/constructor; or nullable + fallback |
| Asset-not-found / `fromCache` throws | not in `pubspec` or not loaded | declare in `pubspec.yaml`; `await images.load` |
| Collisions never fire | no `HasCollisionDetection`/hitbox/callbacks | add the mixin + hitbox + `CollisionCallbacks` |
| FPS decays over a session | per-frame allocation, no pooling | hoist `Paint`/`Vector2`; `ComponentPool` |
| Entities move faster on a 120 Hz device | movement not scaled by `dt` | `position += velocity * dt` (clamped) |
| Pause menu corrupts game state | UI logic inside the game loop | `pauseEngine()` + a Flutter overlay |
| HUD scales/pans with the world | HUD placed in `World` | move HUD to a Flutter overlay / viewport component |
| Save sometimes doesn't persist | missing `await` on the write | `await repository.save(...)` before navigating |

---

## Generation defaults (write it right the first time)

The fixes above, encoded as what the agent emits **by default** so the bug never lands.

**Dart:** `const` constructors; `final` fields; typed models (no `dynamic` outside a boundary);
`sealed` events + exhaustive `switch`; every `Future` awaited/returned/`unawaited`; `!` only on a
documented invariant; injected seeded `Random` (`assets/seeded_random.dart`), never bare `Random()`.

**Flutter:** small `const` widgets (classes, not `_buildX()` helpers); `.builder` for long lists; no
computation in `build`; dispose every disposable; `mounted` after every `await` before a context use;
never store `BuildContext`; bound every flex/scroll child.

**Flame:** load assets in `onLoad`; movement scales by clamped `dt`; zero allocation in `update`/
`render`; correct `onLoad`/`onMount`/`onRemove` split; collisions configured explicitly; pool frequent
spawns; UI via overlays; gameplay in `World`, HUD in overlays.

**Worked, on-contract snippet** (typed, lifecycle-correct, dt-scaled, no hot alloc):
```dart
class Bullet extends SpriteComponent with HasGameReference<MyGame>, CollisionCallbacks {
  Bullet({required super.position, required Vector2 velocity, required super.sprite})
      : _velocity = velocity, super(size: Vector2.all(16), anchor: Anchor.center);
  final Vector2 _velocity;

  @override
  Future<void> onLoad() async => add(CircleHitbox()..collisionType = CollisionType.passive);

  @override
  void update(double dt) {
    super.update(dt);
    position.addScaled(_velocity, dt);            // dt-scaled, no temp Vector2
    if (position.y < -size.y) removeFromParent(); // recycle (pooled)
  }

  @override
  void onCollisionStart(Set<Vector2> points, PositionComponent other) {
    super.onCollisionStart(points, other);
    if (other is Enemy) { game.onBulletHit(other); removeFromParent(); } // verdict in pure Dart
  }
}
```

---

## Built-in review prompt

When asked to review Dart/Flutter/Flame code, the skill runs this internally:

> Review this Dart/Flutter/Flame code as a senior game engineer. Check: (1) Dart null-safety, async,
> typing, lints; (2) Flutter layout constraints, lifecycle, build performance, memory leaks; (3) Flame
> component & asset lifecycle, `update`/`render` hot path, collision setup, camera/world usage; (4)
> architecture boundaries between Game, Components, Domain, Repositories, and Flutter UI; (5) perf
> under 60/120 FPS. Return: Critical issues, High-impact issues, refactor recommendations, concrete
> code patches, and the analyzer rules or tests that would prevent regression. Tag each finding with
> its classifier code and severity.

**The one heuristic to remember:** in Flutter, *constraints and lifecycle* break most; in Flame,
*lifecycle, assets, and hot-path allocation* break most; in Dart, runtime pain comes from *null
safety, async, and `dynamic` typing*. Code that merely "works" is not the bar — the bar is code that
works **60/120 times a second, with no garbage, jank, or races**.
