# Dart patterns & idioms (for game logic)

The recurring shapes a game's **pure-Dart core** is built from — `copyWith`, factory constructors,
`Comparable`, versioned JSON, extension methods, the `reduce(state, event)` state machine, an injected
seeded `Random`, and a value-typed `Vec2`. Everything here is framework-free: **no `package:flutter`,
no `package:flame`**, so it runs under `dart test` on the VM. This file assumes the basics in
[dart-language-essentials.md](dart-language-essentials.md) (sealed classes, null-safety, records,
enhanced enums, error handling) and the naming rules in [dart-api-design.md](dart-api-design.md); it
covers the *idioms layered on top*.

---

## 1. `copyWith` — derive a changed copy (and the `?? this.field` trap)

Immutable value types edit by producing a changed copy, not by mutation. The naive form has a bug: you
**cannot set a nullable field back to `null`**, because `?? this.field` reads "not passed" and "passed
`null`" identically.

```dart
class PlayerState {
  const PlayerState({required this.hp, required this.shieldUntil});
  final int hp;
  final Duration? shieldUntil;            // nullable: a shield that can be cleared

  // bad — can never clear shieldUntil: copyWith(shieldUntil: null) is a no-op.
  PlayerState copyWith({int? hp, Duration? shieldUntil}) =>
      PlayerState(hp: hp ?? this.hp, shieldUntil: shieldUntil ?? this.shieldUntil);
}
```

Use a sentinel to distinguish "absent" from "explicitly null":

```dart
const _unset = Object();

class PlayerState {
  const PlayerState({required this.hp, required this.shieldUntil});
  final int hp;
  final Duration? shieldUntil;

  PlayerState copyWith({int? hp, Object? shieldUntil = _unset}) => PlayerState(
        hp: hp ?? this.hp,
        shieldUntil:
            identical(shieldUntil, _unset) ? this.shieldUntil : shieldUntil as Duration?,
      );
}

// clear it explicitly, keep it implicitly:
state.copyWith(shieldUntil: null);   // shield removed
state.copyWith(hp: 8);               // shield untouched
```

For models with many fields, prefer code-gen (`freezed`) over hand-written `copyWith` — see
[../codegen-and-boilerplate.md](../codegen-and-boilerplate.md) for when that trade is worth it.

---

## 2. Factory & named constructors — validate, pick a subtype, cache

A `factory` runs code before returning an instance: validate, return a cached canonical value, or pick
a subtype. Named constructors give intent-revealing call sites.

```dart
class EnemyConfig {
  const EnemyConfig._(this.hp, this.speed, this.kind);   // private primitive ctor
  final int hp;
  final double speed;
  final EnemyKind kind;

  // Named constructors read as intent at the call site.
  const EnemyConfig.slime() : this._(10, 40, EnemyKind.slime);
  const EnemyConfig.bat() : this._(6, 90, EnemyKind.bat);

  // Factory validates, then delegates — illegal configs cannot be constructed.
  factory EnemyConfig.custom({required int hp, required double speed, required EnemyKind kind}) {
    if (hp <= 0) throw ArgumentError.value(hp, 'hp', 'must be > 0');
    if (speed < 0) throw ArgumentError.value(speed, 'speed', 'must be >= 0');
    return EnemyConfig._(hp, speed, kind);
  }
}
```

**Factory for subtype selection** — the caller asks for the abstraction, the factory picks the impl:

```dart
sealed class PowerUp {
  const PowerUp();
  factory PowerUp.fromKind(String kind) => switch (kind) {
        'heal' => const HealPowerUp(),
        'shield' => const ShieldPowerUp(),
        _ => throw ArgumentError.value(kind, 'kind', 'unknown power-up'),
      };
}
```

**`const`-cached canonical instances** — hand back the same object for a key instead of reallocating:

```dart
class Tile {
  const Tile._(this.id);
  final int id;
  static const empty = Tile._(0);
  static const wall = Tile._(1);
  static final _cache = <int, Tile>{};
  factory Tile.of(int id) => switch (id) {
        0 => empty,
        1 => wall,
        _ => _cache[id] ??= Tile._(id),   // memoised; equal ids share one instance
      };
}
```

---

## 3. `Comparable` — multi-key ordering done right

A leaderboard sorts by several keys with tie-breaks. Implement `compareTo` by **comparing**, never by
**subtracting** (subtracting `double`s loses precision and can overflow `int`s).

```dart
class Score implements Comparable<Score> {
  const Score({required this.points, required this.time, required this.name});
  final int points;
  final Duration time;
  final String name;

  @override
  int compareTo(Score other) {
    final byPoints = other.points.compareTo(points);     // points DESC (other vs this)
    if (byPoints != 0) return byPoints;
    final byTime = time.compareTo(other.time);           // faster time first
    if (byTime != 0) return byTime;
    return name.compareTo(other.name);                   // stable alphabetical tie-break
  }
  // bad: `=> other.points - points;` — fine for small ints, wrong for doubles/large values.
}
```

Keep `compareTo` **consistent with `==`**: if `a.compareTo(b) == 0`, then `a == b` should hold (and
their `hashCode`s match), or `SplayTreeSet`/sorted-map keys behave surprisingly. When you don't want
to bake one ordering into the type, sort externally instead:

```dart
import 'package:collection/collection.dart';
final ranked = scores.sortedByCompare((s) => s.points, (a, b) => b.compareTo(a)); // no Comparable needed
```

---

## 4. JSON `fromJson`/`toJson` — versioned, validated, tagged

Level/save data is the #1 source of runtime crashes: a missing key, a wrong type, or an old schema.
Three idioms harden it.

**Validate the shape with an `if-case`** instead of `!`/blind `as`:

```dart
factory LevelHeader.fromJson(Map<String, Object?> json) {
  if (json case {'rows': final int rows, 'cols': final int cols, 'par': final int par}) {
    return LevelHeader(rows: rows, cols: cols, par: par);
  }
  throw FormatException('bad level header: $json');   // one typed failure at the boundary
}
```

**Carry a `schemaVersion` and migrate forward** so old saves keep loading:

```dart
class SaveData {
  const SaveData({required this.coins, required this.unlocked});
  final int coins;
  final Set<String> unlocked;

  static const currentVersion = 3;

  factory SaveData.fromJson(Map<String, Object?> raw) {
    final migrated = _migrate(raw);   // raw → current shape, step by step
    return SaveData(
      coins: migrated['coins']! as int,
      unlocked: {...(migrated['unlocked']! as List).cast<String>()},
    );
  }

  // v1 had `gold` and no `unlocked`; v2 renamed gold→coins; v3 added `unlocked`.
  static Map<String, Object?> _migrate(Map<String, Object?> j) {
    var v = (j['schemaVersion'] as int?) ?? 1;
    final out = {...j};
    if (v == 1) { out['coins'] = out.remove('gold') ?? 0; v = 2; }
    if (v == 2) { out['unlocked'] ??= <String>[]; v = 3; }
    out['schemaVersion'] = v;
    return out;
  }

  Map<String, Object?> toJson() =>
      {'schemaVersion': currentVersion, 'coins': coins, 'unlocked': unlocked.toList()};
}
```

**Destructure entries with `MapEntry(:key, :value)`** when transforming maps:

```dart
final byId = {
  for (final MapEntry(:key, :value) in rawScores.entries) key: Score.fromJson(value as Map<String, Object?>),
};
```

**Tagged sealed `fromJson`** — one factory dispatches to the right variant by a `type` tag:

```dart
sealed class Entity {
  const Entity();
  factory Entity.fromJson(Map<String, Object?> j) => switch (j['type']) {
        'player' => PlayerEntity.fromJson(j),
        'enemy' => EnemyEntity.fromJson(j),
        final other => throw FormatException('unknown entity type: $other'),
      };
}
```

When the model has many fields, generate this with `json_serializable` rather than hand-rolling — see
[../codegen-and-boilerplate.md](../codegen-and-boilerplate.md).

---

## 5. Extension methods — ergonomic helpers (with their limits)

Extensions add call-site sugar to existing types without subclassing. They dispatch **statically** (on
the *declared* type, not the runtime type) and **cannot add state** — no fields, just methods/getters.

```dart
extension SafeList<T> on List<T> {
  T? at(int i) => (i >= 0 && i < length) ? this[i] : null;   // bounds-safe index
}

extension DoubleLerp on double {
  double lerpTo(double b, double t) => this + (b - this) * t; // easing without a helper class
}

extension DurationClock on Duration {
  String get clock {                                          // 75s → "1:15"
    final m = inMinutes, s = inSeconds % 60;
    return '$m:${s.toString().padLeft(2, '0')}';
  }
}

final cell = grid.at(idx);     // null instead of a RangeError (Dart has no Kotlin-style .let)
0.0.lerpTo(1.0, progress);     // reads as a phrase
elapsed.clock;                 // HUD string, pure-Dart-testable
```

Because dispatch is static, an extension on `List<T>` won't fire through a variable typed `Iterable<T>`
— extend the type you actually call it on. For polymorphism, use a method on the type or a `sealed`
hierarchy instead.

---

## 6. State machine as a pure `reduce(state, event)`

Model the whole game lifecycle as a pure function `(State, Event) → State`. Both are `sealed`, the
`switch` is over the **pair**, side effects live *outside* the reducer, and the result is trivially
testable by folding a list of events.

```dart
sealed class GameState { const GameState(); }
final class Menu extends GameState { const Menu(); }
final class Playing extends GameState {
  const Playing({required this.score, required this.lives});
  final int score; final int lives;
  Playing copyWith({int? score, int? lives}) =>
      Playing(score: score ?? this.score, lives: lives ?? this.lives);
}
final class Paused extends GameState { const Paused(this.resume); final Playing resume; }
final class Won extends GameState { const Won(this.score); final int score; }
final class Lost extends GameState { const Lost(this.score); final int score; }

sealed class GameEvent { const GameEvent(); }
final class Started extends GameEvent { const Started(); }
final class Scored extends GameEvent { const Scored(this.points); final int points; }
final class HitHazard extends GameEvent { const HitHazard(); }
final class PauseToggled extends GameEvent { const PauseToggled(); }

// Pure: no I/O, no Random, no clock, no Flutter. Same input → same output.
GameState reduce(GameState state, GameEvent event) => switch ((state, event)) {
      (Menu(), Started()) => const Playing(score: 0, lives: 3),
      (Playing p, Scored(:final points)) => p.copyWith(score: p.score + points),
      (Playing p, HitHazard()) when p.lives > 1 => p.copyWith(lives: p.lives - 1),
      (Playing p, HitHazard()) => Lost(p.score),
      (Playing p, PauseToggled()) => Paused(p),
      (Paused(:final resume), PauseToggled()) => resume,
      (_, _) => state,                       // ignore events that don't apply in this state
    };
```

The reducer never saves, plays audio, or spawns — callers do that **after** observing the new state
(audio on `Scored`, persistence on `Won`/`Lost`). That keeps the rules deterministic and the test a
one-liner:

```dart
final result = events.fold<GameState>(const Menu(), reduce);
expect(result, const Lost(40));     // a fixed event list always lands on the same state
```

---

## 7. Seeded deterministic `Random` — inject it, never reach for a global

Every shuffle, spawn, and procedural choice must be reproducible: same seed → same run, so tests pin a
golden sequence and a bug reproduces. The skill ships the full implementation in
[`assets/seeded_random.dart`](../../assets/seeded_random.dart) (a SplitMix64 `SeededRandom implements
Random`, bias-free `nextInt` via rejection sampling, with `intInRange`/`pick`/`shuffle` helpers). The
idiom is to **inject** it through the logic, not to call `Random()` inside it.

```dart
// bad — non-deterministic, untestable
class Deck { void deal() => cards.shuffle(); }   // hidden global Random + in-place mutation

// good — Random threads in; the method is pure given (deck, rng)
class Deck {
  const Deck(this.cards);
  final List<int> cards;
  Deck shuffled(Random rng) => Deck([...cards]..shuffle(rng));
  int draw(Random rng) => cards[rng.nextInt(cards.length)];
}

// inject one seeded instance at the composition root; pass it down:
final rng = SeededRandom(424242);
var deck = startingDeck.shuffled(rng);
```

```dart
// golden test — the sequence is locked, so a regression in any spawn/shuffle is caught
test('seed 7 → stable deal', () {
  final rng = SeededRandom(7);
  expect(Deck(const [1, 2, 3, 4, 5]).shuffled(rng).cards, [3, 1, 5, 2, 4]); // pinned
});
```

Same rule for time: inject a clock (`DateTime Function()` or `Duration`-based tick) rather than calling
`DateTime.now()` in logic, so timed mechanics are testable.

---

## 8. A value-typed `Vec2` for the model (convert only at the edge)

The pure core must not import `dart:ui` `Offset` or Flame `Vector2` (one is Flutter, the other is
mutable and engine-bound). Carry geometry on a small **immutable, value-equal** `Vec2`, and convert at
the renderer boundary.

```dart
class Vec2 {
  const Vec2(this.x, this.y);
  final double x, y;
  static const zero = Vec2(0, 0);

  Vec2 operator +(Vec2 o) => Vec2(x + o.x, y + o.y);
  Vec2 operator *(double s) => Vec2(x * s, y * s);
  double get length => math.sqrt(x * x + y * y);

  @override
  bool operator ==(Object o) => o is Vec2 && o.x == x && o.y == y;   // value equality →
  @override
  int get hashCode => Object.hash(x, y);                              // safe as a map key / in ==
}
```

```dart
// at the renderer edge only (in lib/game/ or lib/widgets/, never in the model):
Offset toOffset(Vec2 v) => Offset(v.x, v.y);          // Flutter widgets / CustomPainter
Vector2 toVector2(Vec2 v) => Vector2(v.x, v.y);       // Flame
```

Now `Board { Vec2 origin; }` compares by value, is `dart test`-able with no device, and never drags a
rendering type into the rules. (See [../../checklists/dart-code-quality.md](../../checklists/dart-code-quality.md),
"Layer separation".)

---

## Avoid these

- **`?? this.field` in `copyWith` for a nullable field** — use the `_unset` sentinel (§1), or you can
  never clear it.
- **`a - b` in `compareTo`** — compare, don't subtract (precision/overflow); keep `compareTo`
  consistent with `==`/`hashCode` (§3).
- **`!`/blind `as` on JSON** — validate with an `if-case` and migrate by `schemaVersion` (§4).
- **Side effects inside the reducer** — no save/audio/spawn/`Random`/`DateTime.now()` in
  `reduce`; act on the *result* (§6).
- **Bare `Random()` / `DateTime.now()` in game logic** — inject a seeded `Random`/clock (§7).
- **`Offset`/`Rect`/`Color`/Flame `Vector2` in the model** — use a value `Vec2`, convert at the edge
  (§8). A leaked rendering import breaks VM tests and the layer seam.
- **Hand-rolling `copyWith`/`fromJson` for big models** — reach for `freezed`/`json_serializable`
  ([../codegen-and-boilerplate.md](../codegen-and-boilerplate.md)) once the boilerplate outweighs the
  control.
