# Flame quality checklist

A tick-list a reviewer/agent runs over the **Flame layer** (`lib/game/`: `FlameGame`, `Component`s,
overlays) of a Mode-2/Mode-3 game. Enforces the policies in `references/flutter-game-architecture.md`
(§"Mode 2 — Flame", §"Mode 3 — Hybrid", §"Time and the loop"), `references/performance-checklist.md`
(§"Flame mode", §"Battery & thermals"), and `references/flutter-games-toolkit.md` (hybrid wiring); it
does not re-explain them. Each box is verifiable by reading code, `grep`, or a profile-mode run —
not by judgement. Fail any box → fix before handoff. APIs below are verified against the Flame docs
(`flame-engine/flame`): `HasGameReference`, `CollisionCallbacks` (`onCollisionStart`/`onCollision`/
`onCollisionEnd`), `ComponentPool`, `pauseEngine`/`resumeEngine`/`paused`, `overlays`, and the
`onLoad → onMount → update/render → onRemove` lifecycle.

## Structure: FlameGame / Component / PositionComponent
- [ ] The game class `extends FlameGame` (not a hand-rolled loop); it owns the loop and is the only root.
- [ ] On-screen entities are `Component`s — spatial ones subclass `PositionComponent` (so `position`/`size`/`anchor` exist), non-spatial logic ones subclass `Component`.
- [ ] No framework type is over-extended: a component does one job; rendering and spatial state stay on `PositionComponent`, not bolted onto `FlameGame`.
- [ ] `onLoad` (runs once) does async setup/asset load and the initial `add`s; per-add setup that must run on every mount is in `onMount`, not `onLoad`.
- [ ] Draw order is set with `priority` (constructor arg or field), not relied upon from add-order.
- [ ] Children are added via `add`/`addAll` (or `world.add` when a `World` is used), and `super.onLoad()`/`super.update(dt)` are called so the component tree is advanced.
- [ ] The Flame layer lives only under `lib/game/`; `grep -rlE "package:flame" lib/models lib/systems` is empty (rules core stays Flame-free).

## Game reference: HasGameReference<MyGame> (not legacy)
- [ ] Components reach the game via `with HasGameReference<MyGame>` and the `game` getter — typed to the concrete game class, not `dynamic`/`FlameGame`.
- [ ] The legacy `HasGameRef` mixin and the `gameRef` getter are NOT used: `grep -rE "HasGameRef\b|\.gameRef\b" lib/game` returns nothing.
- [ ] Components read the injected pure-Dart model through `game` (e.g. `game.model` / `game.controller`); they do not construct or own the controller themselves.
- [ ] No component stores its own copy of authoritative state that the model also owns — it mirrors, it does not duplicate.

## The loop & dt (clamp it yourself — Flame does NOT)
- [ ] `update(double dt)` clamps `dt` before advancing the simulation: `final clamped = math.min(dt, 1 / 30);` (or equivalent) — Flame does not clamp for you, so a GC/load hitch can't teleport entities.
- [ ] `super.update(clamped)` advances children, then the pure model is stepped (`game.model.advance(clamped)`); the clamped value (not the raw `dt`) is used for both.
- [ ] All motion is frame-rate independent — advance by `dt` (`position.addScaled(_velocity, dt)`), never by per-frame constants.
- [ ] No game rule, win/lose decision, scoring, or spawn policy lives in any component's `update` — the component forwards/mirrors; the verdict is decided in pure Dart (`grep` components for win/score logic returns none).
- [ ] Where determinism matters, physics runs on a fixed timestep (`fixedUpdate` / a fixed-step accumulator), and the injected seeded `Random` drives every spawn/shuffle (no bare `Random()`/`DateTime.now()` in the loop).

## Collisions via CollisionCallbacks
- [ ] The `FlameGame` mixes in `HasCollisionDetection`; colliding components mix in `CollisionCallbacks` and add a hitbox (`RectangleHitbox`/`CircleHitbox` — simple shapes, not polygons, where they'll do).
- [ ] Collision handling is in `onCollisionStart`/`onCollision`/`onCollisionEnd` (the `CollisionCallbacks` API) — not polled by manual bounds-checking in `update`.
- [ ] A collision callback forwards the *event* to the controller/model; the outcome (did the run end? points scored?) is decided in pure Dart, not inside the callback.
- [ ] Non-reactive/static hitboxes are marked `collisionType = CollisionType.passive` so Flame skips passive↔passive pairs; hitboxes exist only where a collision is actually consumed.

## Object pooling for spawners
- [ ] Every spawner of short-lived entities (bullets, coins, particles, obstacles) recycles via a pool (`ComponentPool<T>`) instead of `new`/destroy churn each frame.
- [ ] Spawn re-initializes a pooled instance in place (`acquire()` → reset `position`/velocity/state) rather than allocating; the pool has a bounded `maxSize`.
- [ ] Finished/off-screen pooled components are returned via `removeFromParent()` (which returns them to the pool automatically) — not dropped for GC.
- [ ] No allocation in `update`/`render`: `Vector2`/`Paint`/`Rect`/`Path` are stored as fields and mutated in place (`setFrom`/`setValues`/`addScaled`); `grep` of hot methods shows no `Vector2(`/`Paint()`/`Rect.` construction.
- [ ] Sprite images are loaded once via `Flame.images` (`load`/`loadAll`) and batched (`SpriteBatch`/atlas) — not decoded per spawn.

## Bounded component count
- [ ] The live component count is capped: anything off-screen, expired, or finished calls `removeFromParent()` each frame — the tree does not grow unbounded over a session.
- [ ] Spawn rate has an explicit ceiling (pool `maxSize` or a spawn cap) so a long run can't accumulate thousands of components.
- [ ] Memory is stable over a long play session (DevTools memory view shows no monotonic growth in component/object count).

## Pause/resume & overlays
- [ ] On menu/paused/win/lose the engine is stopped — `pauseEngine()` / `game.paused = true` — so `update`/`render` halt; `resumeEngine()` only on return to `playing` (no loop runs on a static screen, per battery/thermals policy).
- [ ] Pause/resume is driven by the pure state machine's status transitions, not toggled ad-hoc by a widget.
- [ ] Menus/HUD/pause/game-over are Flutter **overlays**: `GameWidget` registers an `overlayBuilderMap` (id → widget) and the game toggles them via `overlays.add/remove/toggle(id)`; the active overlay tracks `GameStatus`.
- [ ] Hybrid embeds use the right `GameWidget` form: `GameWidget(game: …)` when nested under the app router (menus stay Flutter screens), `GameWidget<T>.controlled(gameFactory: …)` only when the game is the app root.
- [ ] Accessibility is provided at the Flutter layer (the bare Flame canvas is invisible to screen readers): `GameWidget`/overlays carry `Semantics(label:/value:)` sourced from pure-model getters, and large labeled overlay buttons back the canvas tap; Reduce Motion (`MediaQuery.disableAnimations`) is honored.

## Dispose in onRemove (lifecycle hygiene)
- [ ] Anything a component creates that must be released (timers, stream subscriptions, self-owned notifiers/tickers, manual listeners) is torn down in `onRemove` — the Flame analog of widget `dispose`.
- [ ] `removeFromParent()` is called for finished/off-screen components so `onRemove` actually fires (pooled components are recycled, not leaked).
- [ ] Renderer-side disposables in the hosting widget (the `GameWidget` screen) — `AnimationController`, `FocusNode`, `StreamSubscription`, self-created `ValueNotifier`/`ChangeNotifier`, `Timer` — are disposed in `State.dispose`; a passed-in controller is disposed by its owner, not here.
- [ ] The image cache is evicted on level exit (`Flame.images`/`ImageCache`) so a finished level's atlas doesn't stay resident.

## Render layer is rules-free
- [ ] `render(Canvas)` only draws from already-computed state — no model mutation, no rule evaluation, no allocation inside `render`.
- [ ] `update` mirrors authoritative model state into component `position`/`size`/sprite (`position.setFrom`/`setValues`) and does nothing else rules-bearing; the simulation step is the model's, advanced once per frame by the game.
- [ ] Input handlers (`TapCallbacks`/`DragCallbacks`) translate the hit point to model coordinates and forward a model **intent**; the legality/score verdict lives in pure Dart, testable without a gesture.
- [ ] A full menu → playing → paused → win/lose → menu cycle, plus a deterministic play-through with a fixed seed, is covered by `dart test` against the pure core (no `GameWidget` pump needed).

## Format & analyzer gate
- [ ] `dart format --output=none --set-exit-if-changed .` is clean (2-space) and `dart analyze` reports zero issues under the project lints; no `// ignore:` added without a one-line justification.
