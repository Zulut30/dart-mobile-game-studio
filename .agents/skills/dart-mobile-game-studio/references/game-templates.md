# Game templates

Per-template recipes for simple 2D mobile games (iOS + Android). Each gives: **mode**, **core
loop**, **model** (pure Dart, no `package:flutter` imports), **widget / Flame layer**, **data**,
**tests** (`dart test` on the VM, no device), and **pitfalls**. Pick the closest and adapt.

All art is **placeholder vector only** — `CustomPainter`/`Canvas` or Flame's
`RectangleComponent` / `CircleComponent` / `PolygonComponent` painted from a `Paint`. No
copyrighted or downloaded assets.

**Mode key** (see `references/flutter-game-architecture.md` for the full decision tree):
- **Flutter-widgets-only** — `CustomPainter` + `GestureDetector`/`Semantics`. Static or
  turn-based; no game loop. No Flame dependency.
- **Flame** — `FlameGame` + `Component`/`PositionComponent` with the `update(dt)`/`render(canvas)`
  loop, mounted by a `GameWidget`. Motion, spawning, per-frame physics.
- **Hybrid** — a Flame `GameWidget` embedded in the Flutter tree; menus/HUD/dialogs are Flutter
  widgets drawn over it via `GameWidget.overlayBuilderMap` and toggled with
  `game.overlays.add/remove`.

Across all templates the **pure-Dart core owns the rules and the state machine**
(`menu → playing → paused → won/lost → menu`); the renderer is thin and reads from the core.
Inject the seeded RNG from `assets/seeded_random.dart` anywhere shuffles/spawns must be
reproducible in tests.

---

## coloring-shapes  (Flutter-widgets-only)

**Loop:** pick a color → tap a region → that region fills. No fail state; optional "all filled"
celebration.

**Model:**
```dart
// pure Dart — no package:flutter import. Colors are plain ARGB ints, not dart:ui Color.
class Region {
  const Region({required this.id, required this.fill});
  final int id;
  final int? fill; // null = uncolored; ARGB int chosen from the palette
  Region copyWith({int? fill}) => Region(id: id, fill: fill ?? this.fill);
}

class Picture {
  Picture(this.regions);
  final List<Region> regions;
  bool get isComplete => regions.every((r) => r.fill != null);
}
```
`apply(int color, {required int regionId})` returns a new `Picture` with only that region
changed; keep an undo stack of prior `Picture` snapshots.

**Widget layer:** a `CustomPainter` draws each region's `Path` (built from the JSON points) with
its `Paint..color`. Hit-test taps with `Path.contains(offset)`, iterating **front-to-back** so
the topmost overlapping region wins. Palette is a `Row` of swatch buttons; provide undo/clear.
Wrap each region in `Semantics(label: 'Region 3, blue', button: true)`.

**Data:** regions as normalized (0..1) path points in JSON, scaled to the canvas at paint time so
art stays crisp at any DPI. Palette is a JSON list of ARGB ints. See `assets/level_schema.json`.

**Tests:** filling a region changes only that region; `apply` is pure (input `Picture`
unmutated); undo restores the previous snapshot; `isComplete` flips only when every region is
filled.

**Pitfalls:** hit-testing overlapping paths (resolve front-to-back, not by bounding box);
recompute scaled `Path`s only when canvas size changes, not every frame; don't store `dart:ui`
`Color`/`Path` in the model — keep it `flutter`-free so it stays VM-testable.

---

## simple-platformer  (Flame)

**Loop:** move left/right, jump gaps, reach the goal; fall off the bottom or touch a hazard =
retry the level.

**Model:** keep tunables and the win/lose rule in pure Dart so they unit-test without a world.
```dart
class PlatformerTuning {
  const PlatformerTuning({
    this.gravity = 900,      // px/s^2, +y is down
    this.moveSpeed = 160,    // px/s
    this.jumpSpeed = 380,    // px/s initial upward
  });
  final double gravity, moveSpeed, jumpSpeed;
}

/// Pure kinematic step — no Flame, no Forge2D. Deterministic, fully testable.
({double y, double vy, bool onGround}) stepVertical({
  required double y, required double vy, required bool jumpHeld,
  required bool onGround, required double groundY,
  required PlatformerTuning t, required double dt,
}) {
  var nvy = vy + t.gravity * dt;
  if (jumpHeld && onGround) nvy = -t.jumpSpeed; // gate jump on ground contact
  var ny = y + nvy * dt;
  var grounded = false;
  if (ny >= groundY) { ny = groundY; nvy = 0; grounded = true; }
  return (y: ny, vy: nvy, onGround: grounded);
}
```
For tile-platform games this kinematic core is enough and is preferred for kids titles (fully
deterministic). Reach for **Forge2D** (`Forge2DGame`, `BodyComponent`, `BodyType.dynamic` player
with `fixedRotation: true`, `BodyType.static` ground via `createFixtureFromShape`) only when you
need slopes, stacked bodies, or realistic restitution — and accept that physics is no longer
bit-reproducible across platforms, so don't assert exact body positions in tests.

**Flame layer:** `class PlatformerGame extends FlameGame with HasCollisionDetection`. The player
is a `PositionComponent with HasGameReference<PlatformerGame>` (placeholder `RectangleComponent`
child); its `update(dt)` reads the game's input flags via `game.jumpHeld` / `game.moveDir`, calls
`stepVertical(...)`, and writes `position`. Add a `RectangleHitbox` to the player and to the goal;
mix `CollisionCallbacks` into the player and detect the win in `onCollisionStart(intersectionPoints, other)`
when `other is Goal`. Lose when `position.y` passes the floor or a hazard hitbox is hit. Use a
`World` + `CameraComponent` (`FlameGame(world: ...)`) so the camera follows the player.

**Input:** in **hybrid** shell, on-screen Left/Right/Jump are Flutter buttons in a
`GameWidget.overlayBuilderMap` overlay that set intent flags on the game
(`game.moveDir`, `game.jumpHeld`); the player reads those flags in `update`. Keep input out of the
model — pass resolved intents into `stepVertical`.

**Data:** level JSON = platform rects, hazard rects, spawn point, goal rect (all in world units).
Load in `onLoad()` and spawn one component per rect.

**Tests:** `stepVertical` — gravity accelerates `vy`; jump fires only when `onGround`; landing
clamps to `groundY` and zeroes `vy`; a second jump mid-air is rejected. Win/lose **rule**
(reaching goal x/y, y past floor) tested as pure predicates.

**Pitfalls:** double-jump (gate strictly on `onGround`, set false the instant you leave ground);
tunneling at speed (cap per-frame displacement, or set `bullet: true` on a Forge2D body); never
multiply by a literal `1/60` — always use the real `dt` passed to `update`.

---

## drag-and-drop-puzzle  (Flutter-widgets-only, or Flame for many pieces)

**Loop:** drag a piece to its matching slot; correct → snaps & locks; wrong → springs back. Win =
every slot correctly filled.

**Model:**
```dart
class Piece { const Piece(this.id, this.correctSlot); final int id, correctSlot; }

class Board {
  Board(this.slots);                 // slotId -> placed pieceId (or null)
  final Map<int, int?> slots;
  /// Returns true and records placement iff this is the piece's home slot.
  bool place(Piece p, int slotId) {
    if (p.correctSlot != slotId || slots[slotId] != null) return false;
    slots[slotId] = p.id; return true;
  }
  bool get isSolved => slots.values.every((v) => v != null);
}
```

**Widget layer (default):** Flutter's first-party `Draggable` / `DragTarget` does the heavy
lifting — `DragTarget.onWillAcceptWithDetails` validates against `place`, `onAcceptWithDetails`
commits and locks the slot; on reject the `Draggable` animates home automatically. Raise the
active piece visually with `feedback`. Wrap pieces/slots in `Semantics` and offer a
non-drag fallback (tap-piece-then-tap-slot) for switch/VoiceOver users.

**Flame layer (only if dozens of pieces / animated board):** piece is a `PositionComponent` with
`DragCallbacks`; in `onDragUpdate` do `position += event.localDelta`; in `onDragEnd` use
`parent!.componentsAtPoint(position + size / 2).whereType<Slot>()` to find the drop target, call
`place`, then either snap to the slot or tween back.

**Data:** piece→slot mapping and slot layout (rects) in JSON.

**Tests:** correct placement locks the slot and counts toward the win; wrong slot or an occupied
slot is rejected; `isSolved` true only when all slots filled; placement order doesn't matter.

**Pitfalls:** z-order while dragging (lift the active piece above siblings —
`priority`/`feedback`); snap math (center the piece on the slot, account for piece size);
partial-overlap matching (match by slot containment, not nearest-pixel); don't trust the view —
the model's `place` is the single source of truth.

---

## memory-cards  (Flutter-widgets-only)

**Loop:** flip two cards; a match keeps them face-up; a mismatch flips both back after a short
delay. No fail; track moves/time. Win = all matched.

**Model:** classic two-up rule, deterministic shuffle via injected seed.
```dart
import '../assets/seeded_random.dart'; // SeededRandom wrapping dart:math Random(seed)

enum Phase { ready, oneUp, resolving } // resolving = brief lock during mismatch

class MemoryGame {
  MemoryGame(List<int> symbols, {required int seed})
      : cards = _deal(symbols, seed);
  final List<Card> cards;
  Phase phase = Phase.ready;
  int? _firstIndex;
  int moves = 0;

  static List<Card> _deal(List<int> symbols, int seed) {
    final deck = [...symbols, ...symbols] // each symbol twice
        .asMap().entries.map((e) => Card(e.key, e.value)).toList();
    SeededRandom(seed).shuffle(deck); // Fisher–Yates with seeded Random
    return deck;
  }

  /// Returns indices to flip back (empty on match / first flip). View animates the result.
  List<int> flip(int i) {
    if (phase == Phase.resolving) return const []; // input lock
    final c = cards[i];
    if (c.isFaceUp || c.isMatched) return const [];
    c.isFaceUp = true;
    if (phase == Phase.ready) { _firstIndex = i; phase = Phase.oneUp; return const []; }
    moves++;
    final first = cards[_firstIndex!];
    if (first.symbol == c.symbol) {
      first.isMatched = c.isMatched = true; phase = Phase.ready; return const [];
    }
    phase = Phase.resolving; // caller flips both back, then sets phase = ready
    return [_firstIndex!, i];
  }

  bool get isWon => cards.every((c) => c.isMatched);
}
```

**Widget layer:** a `GridView` of card widgets with a flip animation
(`AnimatedSwitcher`/`Transform`); a moves+timer HUD; restart button. After `flip` returns a
mismatch pair, show both, wait (~700 ms), flip back, then set `phase = ready`. One `Semantics`
label per card (`'Card, face down'` / `'Card, star'`).

**Data:** symbol set + grid dimensions in JSON; pass a fixed `seed` (e.g. from level id) for
reproducible boards; random seed for casual replay.

**Tests:** two matching symbols stay up and mark matched; two different return a flip-back pair
and lock input until cleared; `isWon` only when all matched; same seed ⇒ identical deal (assert
`cards.map((c)=>c.symbol)`); odd inputs handled (require even pairs).

**Pitfalls:** taps during the mismatch delay (the `Phase.resolving` lock is the fix); animating
state the model doesn't own (model is truth, view animates toward it); forgetting to reset
`_firstIndex` semantics between rounds.

---

## shape-matching  (Flutter-widgets-only)

**Loop:** a prompt item (shape/color/count) appears with 2–4 targets; tap the matching target.
Positive reinforcement on correct; advance to the next round. Round-based, no hard fail.

**Model:**
```dart
class Item { const Item(this.shape, this.color); final int shape, color; }

class Round {
  const Round(this.prompt, this.options, this.answerIndex);
  final Item prompt;
  final List<Item> options;       // includes the correct one
  final int answerIndex;
  bool isCorrect(int i) => i == answerIndex;
}

class MatchSession {
  MatchSession(this.rounds);
  final List<Round> rounds;
  int index = 0, score = 0;
  bool answer(int optionIndex) {
    final ok = rounds[index].isCorrect(optionIndex);
    if (ok) { score++; index++; }            // advance only on correct
    return ok;
  }
  bool get isDone => index >= rounds.length;
}
```
Generate rounds from a seeded RNG so distractors are reproducible and the answer slot varies.

**Widget layer:** show the prompt; render 2–4 target buttons; on tap call `answer`, play a short
success cue on `true`, no advance on `false`. `Semantics` on every option
(`'Triangle, red'`) — never convey the match by color alone.

**Data:** round bank or generator parameters (shape/color pools, options-per-round) in JSON.

**Tests:** correct option scores and advances `index`; wrong option neither scores nor advances;
every generated round contains exactly one correct option and a valid `answerIndex`; `isDone` at
the end.

**Pitfalls:** unfair distractors for the target age; color-only cues (pair color with shape/icon
for color-blind and pre-readers); answer always in the same slot (shuffle option order with the
seed).

---

## endless-runner-lite  (Flame)

**Loop:** auto-run; tap to jump obstacles; speed ramps; one hit ends the run; score = distance
(+ optional coins).

**Model:** keep spawning and scoring deterministic in pure Dart so a fixed seed reproduces an
entire run in tests.
```dart
import '../assets/seeded_random.dart';

class Spawner {
  Spawner(int seed) : _rng = SeededRandom(seed);
  final SeededRandom _rng;
  double _next = 0;
  /// Returns gap (px) to the next obstacle; ramps tighter as distance grows.
  double gapAfter(double distance) {
    final base = (260 - distance * 0.02).clamp(140.0, 260.0);
    return base + _rng.nextDouble() * 60; // jitter, still seed-reproducible
  }
}

double scoreFor(double distance, int coins) => distance.floor() / 10 + coins * 5;
```
Jump arc reuses the platformer's `stepVertical` against a fixed ground line.

**Flame layer:** `class RunnerGame extends FlameGame with HasCollisionDetection, TapCallbacks`.
World scrolls; the runner is a `PositionComponent` fixed in x, its y driven by `stepVertical`;
`onTapDown` sets `jumpHeld`. Obstacles are pooled `RectangleComponent`s — recycle off-screen
ones with `removeFromParent()` / re-add rather than allocating per spawn. `RectangleHitbox` +
`CollisionCallbacks`: `onCollisionStart` with an obstacle ⇒ set game-over and `pauseEngine()`.
Parallax background via Flame's `ParallaxComponent`.

**Input:** tap anywhere to jump — `TapCallbacks.onTapDown` on the game, or a full-screen overlay
button in the hybrid shell for a larger, accessible target.

**Data:** tuning JSON (initial speed, ramp rate, gap bounds, jump speed); a per-run `seed`.

**Tests:** collision ends the run (rule as a pure predicate over rects); `gapAfter` clamps within
bounds and tightens with distance; `scoreFor` monotonic in distance and coins; same seed ⇒
identical gap sequence (assert the first N gaps).

**Pitfalls:** node churn / GC stutter (object-pool obstacles, don't allocate per frame);
frame-independent motion (scroll by `speed * dt`, never a constant); fairness of the ramp (clamp
the minimum gap so it stays clearable); reset all run state on restart (score, spawner, pool).

---

## tap-reaction  (Flutter-widgets-only, or Flame)

**Loop:** targets appear at random valid positions; tap before each expires. Hit = score; expire
= miss (soft — lower score, no game-over for kids).

**Model:**
```dart
class Target {
  Target(this.id, this.x, this.y, this.bornAt, this.lifetime);
  final int id; final double x, y;     // normalized 0..1
  final double bornAt, lifetime;       // seconds
  bool tapped = false;
  bool isExpired(double now) => !tapped && (now - bornAt) >= lifetime;
}

class ReactionGame {
  ReactionGame(int seed) : _rng = SeededRandom(seed);
  final SeededRandom _rng;
  int score = 0, misses = 0;
  Target spawn(int id, double now, {double lifetime = 1.2}) =>
      Target(id, _rng.nextDouble(), _rng.nextDouble(), now, lifetime);
  void hit(Target t)  { if (!t.tapped) { t.tapped = true; score++; } }
  void expire(Target t) { misses++; }
}
```
Time-driven: advance a clock and ask each target `isExpired(now)`.

**Widget layer:** a `Stack` placing targets via `Positioned` from normalized coords ×
`MediaQuery` size; a shrink/fade `AnimatedContainer` shows the lifetime; `GestureDetector` per
target calls `hit`. Or **Flame**: targets are `CircleComponent`s with `TapCallbacks`, removed in
`update` once `isExpired`. HUD shows score/combo.

**Data:** difficulty curve (lifetime per age/level, max concurrent targets, spawn interval) in
JSON; a `seed` for reproducible position/lifetime sequences.

**Tests:** a tap within `lifetime` scores once and is idempotent (second tap no-ops);
`isExpired` true only after `lifetime` elapses and only if untapped; spawned positions stay in
0..1 (on-screen after scaling); same seed ⇒ same position/lifetime stream.

**Pitfalls:** spawn overlap (reject positions too close to live targets, or grid the field);
lifetime fairness by age (older kids = shorter); double-count on rapid taps (guard with
`tapped`); always derive timing from the real frame `dt`/clock, not a fixed step.

---

## Shared conventions

- **Pure-Dart core, thin renderer.** Rules, scoring, and the `menu → playing → paused →
  won/lost → menu` state machine live in `flutter`-free Dart and are tested with `dart test` on
  the VM. SwiftUI's analog here is Flutter/Flame: it only renders and forwards input.
- **Deterministic RNG.** Inject `SeededRandom` (`assets/seeded_random.dart`) for every shuffle
  and spawn so tests assert exact sequences; use a random seed for casual replay.
- **Frame-independent motion (Flame).** Multiply by the real `dt` in `update(dt)`; never hardcode
  `1/60`. Drive win/lose from the model, not from animation completion.
- **No-fail option.** For young audiences prefer soft feedback (lower score, gentle retry) over a
  hard game-over.
- **Celebrate success.** Short, skippable scale/particle flourish on win; nothing that blocks
  replay.
- **Accessibility.** Wrap every interactive element in `Semantics` (label + `button`/value);
  support Reduce Motion; never gate play on reading; pair color with shape/icon.
- **Kids-safe / privacy-first.** Offline-first; no analytics, ads, tracking, IDFA/GAID, accounts,
  or external links; persist only progress/settings (e.g. `shared_preferences`) — nothing
  personal, nothing over the network. (Covers both Apple Kids Category and Google Play Families.)
- **Placeholder vector art only.** `CustomPainter`/`Canvas` or Flame's
  `RectangleComponent`/`CircleComponent`/`PolygonComponent` from a `Paint`; levels as JSON data,
  not code.
- **Minimal dependencies.** Flutter SDK for widgets-only templates; add **Flame** (and **Forge2D**
  only if real physics is required) for motion templates. Justify anything beyond that.