# Dart language essentials (Dart 3)

The core language toolkit for writing clean, correct game logic. Targets **Dart 3** with sound null
safety. Examples are game-flavored and belong in the **pure-Dart core** (`lib/models/` +
`lib/systems/`) — no `package:flutter` / `package:flame` imports, so every snippet here is testable
with `dart test` on the VM. This is the baseline every model/system file should meet. Format with
`dart format` (2-space indent); keep it analyzer-clean.

## Sound null safety — model "absence", never crash on it

Non-nullable is the default. `T?` is the only thing that can be null, and the analyzer forces you to
handle it. Express "maybe no value" with `?`; resolve it deliberately.

- **Do** narrow with `if (x != null)` (promotion), default with `??`, chain with `?.`, assign-if-null
  with `??=`.
- **Don't** use the null-assertion `!` on data you don't control (level JSON, user input, map
  lookups). `!` throws at runtime — exactly the crash null safety exists to prevent. Use `!` only on
  an invariant the surrounding code guarantees, and prefer a guard even then.

```dart
final level = levels[id];              // LevelData?  — lookups are nullable
if (level == null) return MoveResult.invalid; // early exit; `level` is now non-null below
final title = level.name ?? 'Untitled';
final firstCoin = entities.firstWhereOrNull((e) => e.kind == Kind.coin)?.position;
```

```dart
// DON'T: force-unwrap external data
final lvl = jsonMap['level']!;         // throws if key missing — brittle on real files
// DO: decode defensively (see "No force-unwrap on external data" below)
```

## `final` and `const` — immutability by default

- **`final`**: set once at runtime. Use it for nearly every variable and field; reach for `var` only
  on something you genuinely reassign.
- **`const`**: a compile-time constant (and a *deeply* immutable value). Use it for fixed config,
  literals, and constructors so instances are canonicalized (one shared object) and cheap.
- A `const` constructor makes a class instantiable as a compile-time constant — essential for value
  objects and (in the renderer) for `const` widgets that skip rebuilds.

```dart
const tileSize = 32.0;                       // compile-time constant
const startBoard = Board(rows: 4, cols: 4);  // const constructor → canonicalized
final rng = Random(seed);                    // runtime value, never reassigned → final
var score = 0;                               // genuinely mutated → var
```

```dart
// DON'T: var when you never reassign        // DO: final communicates intent and the analyzer agrees
var width = size.width;                       final width = size.width;
```

## Immutable data classes — `==` / `hashCode` / `copyWith`

Game entities are values: two cards with the same fields *are* the same card. Make them immutable
with `final` fields + a `const` constructor, override `==`/`hashCode` so they compare by value, and
expose `copyWith` to derive a changed copy instead of mutating.

```dart
class Card {
  const Card({
    required this.id,
    required this.symbol,
    this.isFaceUp = false,
    this.isMatched = false,
  });

  final int id;
  final String symbol;
  final bool isFaceUp;
  final bool isMatched;

  Card copyWith({bool? isFaceUp, bool? isMatched}) => Card(
        id: id,
        symbol: symbol,
        isFaceUp: isFaceUp ?? this.isFaceUp,
        isMatched: isMatched ?? this.isMatched,
      );

  @override
  bool operator ==(Object other) =>
      other is Card &&
      other.id == id &&
      other.symbol == symbol &&
      other.isFaceUp == isFaceUp &&
      other.isMatched == isMatched;

  @override
  int get hashCode => Object.hash(id, symbol, isFaceUp, isMatched);
}
```

- Use **`Object.hash(...)`** (or `Object.hashAll(list)` for collections) — never a hand-rolled
  prime-multiply. The two must agree: equal objects must have equal `hashCode`, or `Set`/`Map` break.
- This is exactly the boilerplate the optional `equatable` package (or a code-gen tool like
  `freezed`) removes; either is a justified small dep if hand-writing `==` gets heavy. Hand-writing is
  fine for a handful of value types.
- A widget rebuild can hinge on `==` (e.g. `CustomPainter.shouldRepaint`, `Selector`), so correct
  value equality is also a performance lever, not just a correctness one.

## Records — lightweight multiple values, no class needed

Records are anonymous, immutable, structurally-typed aggregates. Reach for them to return two or
three values, or to group a transient tuple, *without* declaring a class. They get `==`/`hashCode`
for free (structural). Promote to a real data class once the shape gains behavior or a name that
should travel.

```dart
// Return multiple values — name the fields for readable call sites.
({int row, int col}) tileAt(Offset p) =>
    (row: (p.dy / tileSize).floor(), col: (p.dx / tileSize).floor());

final hit = tileAt(localPos);
board.toggle(hit.row, hit.col);

// Positional fields are $1, $2…; destructure inline with a pattern.
(int, int) spawnCell(Random rng) => (rng.nextInt(cols), rng.nextInt(rows));
final (x, y) = spawnCell(rng);
```

```dart
// DON'T: a throwaway class for a 2-field return     // DO: a record
class _Cell { final int row, col; ... }              ({int row, int col}) tileAt(...) => (...);
```

## Sealed classes + exhaustive `switch` — model states & events

A `sealed` class can only be subtyped **in its own library**, so the compiler knows the full set of
subtypes and makes a `switch` over it **exhaustive**: omit a case and it's a *compile error*, not a
silent fall-through. This is the Dart analog of Swift's enums-with-associated-values — use it for game
states, moves, and events that carry data. Use a switch *expression* (`=>`, returns a value) with **no
`default`** so adding a new case forces you to handle it everywhere.

```dart
sealed class Move {
  const Move();
}

class Flip extends Move {
  const Flip(this.cardId);
  final int cardId;
}

class Restart extends Move {
  const Restart();
}

class Pause extends Move {
  const Pause();
}

MoveResult apply(GameState state, Move move) => switch (move) {
      Flip(:final cardId) => state.flip(cardId), // object pattern destructures the field
      Restart() => state.reset(),
      Pause() => state.pause(),
      // No `default`: add a new Move subclass and this switch fails to compile until handled.
    };
```

Pattern features that pay off in game logic:

- **Object/record destructuring** in a case: `Won(:final score)`, `(int dx, int dy)`.
- **Logical-or** to share a body: `case Restart() || Pause(): …`.
- **Guards** with `when`: `Flip(:final cardId) when board.isFaceDown(cardId) => …`.
- **Relational** patterns: `>= 100 => Rank.gold`.
- **`if-case`** for one-off matches without a full switch:

```dart
if (event case Won(:final score)) showConfetti(score); // binds `score` only when it matches
```

## Enums with members — small closed sets that carry data & behavior

Use a plain `enum` for a fixed, flat set of options (status, difficulty, direction). Dart 3 enums are
**enhanced**: they can have `final` fields, a `const` constructor, getters/methods, and implement
interfaces. Prefer this over scattering `const int` flags. (Reach for a `sealed` class instead when
cases must carry *per-instance* payloads like `Won(score)`.)

```dart
enum Difficulty {
  easy(gridSize: 3, moveLimit: 30),
  normal(gridSize: 4, moveLimit: 24),
  hard(gridSize: 5, moveLimit: 20);

  const Difficulty({required this.gridSize, required this.moveLimit});

  final int gridSize;
  final int moveLimit;

  int get tileCount => gridSize * gridSize;
}

// Exhaustive switch over a plain enum needs no `default` either:
String label(Difficulty d) => switch (d) {
      Difficulty.easy => 'Easy',
      Difficulty.normal => 'Normal',
      Difficulty.hard => 'Hard',
    };
```

- Built-ins: `Difficulty.values` (all cases), `.name` (`'easy'`), `.index`. Parse user/JSON input with
  `Difficulty.values.byName(s)` — but guard it (see below), since it throws on an unknown name.

## A pure-Dart state machine, end to end

Putting it together — sealed status, enum difficulty, immutable board, exhaustive transitions, all
VM-testable:

```dart
sealed class GameStatus {
  const GameStatus();
}

class Menu extends GameStatus { const Menu(); }
class Playing extends GameStatus { const Playing(); }
class Paused extends GameStatus { const Paused(); }
class Won extends GameStatus { const Won(this.score); final int score; }
class Lost extends GameStatus { const Lost(); }

GameStatus next(GameStatus status, Move move) => switch ((status, move)) {
      (Menu(), Restart()) => const Playing(),
      (Playing(), Pause()) => const Paused(),
      (Paused(), Restart()) => const Playing(),
      _ => status, // unmatched (status, move) pairs are a no-op — explicit, not accidental
    };
```

## Collections & functional transforms

Prefer declarative transforms over manual index loops for clarity in the model. Be mindful of
allocations only in per-frame *render* code — the pure model favors readability (see
`performance-checklist.md`).

```dart
final allMatched = cards.every((c) => c.isMatched);
final openIndices = [for (final (i, c) in cards.indexed) if (!c.isMatched) i]; // collection-for + .indexed
final symbols = {for (final c in cards) c.symbol};                            // Set literal, O(1) membership
final score = tiles.fold<int>(0, (sum, t) => sum + t.value);
final faceUp = cards.where((c) => c.isFaceUp).map((c) => c.id).toList();
```

- Use `Set`/`Map` for O(1) membership and lookup (matched ids, occupied cells) instead of repeated
  `list.contains`.
- `package:collection` adds the safe, null-returning helpers — `firstWhereOrNull`, `groupListsBy`,
  `mapEquals`/`listEquals` — that avoid `firstWhere`'s throw-on-miss. A justified small dep.
- **Don't** call `.first` / `.single` / `[index]` without proving non-empty / in-range first; they
  throw. Prefer `firstWhereOrNull`, `isNotEmpty` guards, or bounds checks.

## Error handling — `Exception` vs `Error`, no silent failure

Two hierarchies, two meanings:

- **`Exception`** = an *expected, recoverable* condition (a level file is missing or malformed). Throw
  a domain `Exception` and **catch** it. Define your own: `class LevelException implements Exception`.
- **`Error`** = a *programmer bug* (failed `assert`, `StateError`, `RangeError`, a broken invariant).
  Don't catch these to limp along — fix the code. Let them crash in debug so you see them.

```dart
class LevelException implements Exception {
  const LevelException(this.message);
  final String message;
  @override
  String toString() => 'LevelException: $message';
}

LevelData parseLevel(String jsonText) {
  final decoded = jsonDecode(jsonText); // dynamic — validate before trusting (next section)
  if (decoded is! Map<String, dynamic>) {
    throw const LevelException('root is not an object');
  }
  return LevelData.fromJson(decoded);
}

// Call site: recover from the expected failure, don't swallow the unexpected one.
LevelData loadOrFallback(String text) {
  try {
    return parseLevel(text);
  } on LevelException catch (e, stack) {
    log('level load failed: $e', stack);
    return LevelData.fallback;
  }
  // No bare `catch (_)`: a RangeError/StateError here is a bug — let it surface.
}
```

- Catch the **narrowest** type with `on` ; add `catch (e, stack)` only when you use the stack.
- **`rethrow`** to act on an exception (log) and still propagate it — never re-`throw e` (that loses
  the original stack trace).
- `finally` runs on every exit; use it for cleanup that must happen regardless.
- **Don't** write a bare `catch (_)` that hides all failure — it masks real bugs and turns a crash
  into corrupt state.

## Result-style returns — failures the type system makes you handle

For *expected, frequent* outcomes (an illegal move, an out-of-bounds tap), an exception is the wrong
tool — returning the outcome is clearer and cheaper, and the analyzer's exhaustive switch forces the
caller to handle every case. Model it as a `sealed` result (Dart has no built-in `Result`):

```dart
sealed class MoveResult {
  const MoveResult();
}

class Moved extends MoveResult {
  const Moved(this.board);
  final Board board;
}

class Illegal extends MoveResult {
  const Illegal(this.reason);
  final String reason;
}

// Caller must handle both arms — no forgotten error path.
final message = switch (board.applyMove(move)) {
      Moved(:final board) => 'ok: ${board.remaining} left',
      Illegal(:final reason) => 'nope: $reason',
    };
```

Rule of thumb: **`Exception`** for rare, exceptional, often-I/O failures you `try/catch`;
**sealed `Result`** for ordinary branch-y outcomes in hot game logic. Reserve `Error`/`assert` for
"this can't happen" invariants.

## No force-unwrap on external data

Anything from outside your code — `jsonDecode` output, `SharedPreferences`, asset bundles, gestures —
is `dynamic` or nullable and may be wrong. Validate the *shape* before trusting it; never `!` or blind-
cast your way through it. A pattern in an `if-case` validates and destructures in one step:

```dart
LevelData fromJson(Map<String, dynamic> json) {
  // Validate shape declaratively; bind names only if every check passes.
  if (json
      case {
        'id': final String id,
        'rows': final int rows,
        'cols': final int cols,
        'tiles': final List<dynamic> tiles,
      } when rows > 0 && cols > 0) {
    return LevelData(
      id: id,
      rows: rows,
      cols: cols,
      tiles: tiles.map((t) => Tile.fromJson(t as Map<String, dynamic>)).toList(),
    );
  }
  throw const LevelException('malformed level json');
}
```

```dart
// DON'T: trust external data with ! and blind casts
final rows = json['rows']! as int;          // throws on null AND on wrong type — two crashes in one line
// DO: type-checked pattern (above), or read with a default
final rows = (json['rows'] as int?) ?? 4;   // explicit fallback, no crash
```

- `as` casts *throw* on mismatch; `as?`-style safety is `(x as T?)` then `??`, or an `x is T` check
  that promotes. Validate seeds/levels at the boundary so the pure core only ever sees valid data —
  that keeps deterministic logic (seeded `Random`) reproducible in tests.

## Async essentials (for systems that touch I/O)

Most game *rules* are synchronous and that's good — keep them so they test instantly on the VM. Async
appears at the edges (loading a level file, reading a save). Keep it in `systems/` behind a plain
interface so the rules stay sync and pure.

```dart
Future<LevelData> loadLevel(String path) async {
  final text = await File(path).readAsString(); // I/O at the edge
  return parseLevel(text);                       // pure, sync, tested separately
}
```

- `async`/`await` over raw `.then`; a function returning a `Future` should be `async`.
- **Don't** swallow a `Future` you should await — an un-awaited failing `Future` becomes an
  unhandled async error. Await it, or explicitly `unawaited(...)` (from `dart:async`) when fire-and-
  forget is intended.

## Access control & style baseline

- **Privacy is library-level via `_`**: a leading underscore (`_board`, `_advance()`) makes a member
  private to its file/library. Default to private; widen only when another file needs it. (Dart has no
  `private`/`public` keyword.)
- Types & enums `UpperCamelCase`; members, variables, params `lowerCamelCase`; files & dirs
  `snake_case.dart`; constants `lowerCamelCase` (not `SCREAMING_CAPS`).
- Booleans read as assertions: `isMatched`, `canAcceptInput`, `hasWon`.
- One responsibility per type/file; small is good. Keep `models/` + `systems/` free of
  `package:flutter` and `package:flame` so the core tests on the VM.
- Run `dart format` and treat analyzer warnings as errors (the skill targets `very_good_analysis` /
  flutter lints). `final`-by-default, `const`-where-it-compiles, and exhaustive switches are all
  lint-enforceable — let the tooling hold the line.

---

*Verified against the official Dart 3 language docs (dart.dev): records (positional `$1`/named fields,
structural `==`/`hashCode`, multi-value returns), patterns (switch expressions, object/record
destructuring, logical-or `||`, relational, `when` guards, `if-case`, wildcard `_`), sealed classes &
switch exhaustiveness, enhanced enums (`final` fields + `const` constructor + methods, `.values` /
`.name` / `.index` / `.byName`), error handling (`Exception` vs `Error`, `on`/`catch (e, s)`/
`rethrow`/`finally`), and `Object.hash`/`Object.hashAll`.*
