# Dart API design

Distilled from Effective Dart (Style + Design), mapped to Dart 3 / Flutter with game examples.
Good names make game code read like prose and cut comments. Apply these to every class, member,
and constructor you add to the pure-Dart core. Everything here is `dart format`-clean (2-space
indent) and passes `very_good_analysis` / flutter lints.

## Clarity at the point of use is the goal
Code is read far more than written. Optimize the **call site**, not the declaration.

```dart
board.flip(3);                 // reads as a sentence
level.entitiesOfKind(Kind.coin);
player.moveBy(const Vector2(1, 0));
```

## Naming
- **Types, enums, extensions, typedefs, mixins:** `UpperCamelCase` (`Board`, `GameStatus`,
  `CardState`, `Collidable`).
- **Members, variables, parameters, named constructors:** `lowerCamelCase` (`flip`, `legalMoves`,
  `tileSize`).
- **Constants:** also `lowerCamelCase`, not `SCREAMING_CAPS` (`const maxLives = 3;`).
- **Libraries / files / directories:** `lowercase_with_underscores` (`game_status.dart`).
- **Acronyms ≥ 3 letters read as words:** `HttpClient`, `idfaBlocked`, `jsonScore` — not `HTTPClient`.
- **Most descriptive noun last:** `pageCount`, `coinValue` — not `numPages`, `valueCoin`.
- **Avoid abbreviations** unless more common than the full word (`id`, `ok` are fine).
- **Leading `_` = library-private.** Use it for everything not part of the public surface.

```dart
// don't
class card { final bool MATCHED; }
// do
class Card { final bool isMatched; const Card({required this.isMatched}); }
```

## Boolean members read as assertions
Non-imperative verb phrase, positive form, no `get` prefix — reads in an `if`.

```dart
bool get isMatched => state == CardState.matched;   // do
bool get hasWon => remaining == 0;                  // do
bool get canAcceptInput => !isLocked;               // do
```

```dart
bool get matched => ...;          // don't: not an assertion
bool get isNotDisconnected => ...; // don't: double negative; use isConnected
```

Exception: for a **named boolean parameter**, omit the verb — it reads better at the call site.

```dart
Tile({required this.kind, this.revealed = false});   // tile(revealed: true)
```

## Methods: verb for side effects, noun for results
- **Side-effecting command → imperative verb:** `flip()`, `spawn()`, `reset()`, `advance()`.
- **Returns a value → noun / non-imperative phrase:** `legalMoves`, `entityAt(p)`, `firstMatch`.
- **Never start a name with `get`** — use a getter or a noun. `score`, not `getScore()`.
- **Copy vs view:** `toList()`/`toJson()` returns a new object; `asMap()` returns a view backed by
  the original.

```dart
// don't
int getScore() => _score;
// do
int get score => _score;
```

## Constructors

Dart has no method overloading; its constructor toolkit replaces overloads and sentinel factories.
Prefer it over static `create…` helpers.

- **Initializing formals** assign fields directly: `Board(this.width, this.height);` — no body needed.
- **Named constructors** for alternate ways to build the *same* type: `Board.empty()`, `Vector2.zero()`,
  `LevelData.fromJson(json)`. Subclasses do not inherit them, so each type names its own.
- **Named vs factory:** a named *generative* constructor always returns a fresh instance of exactly
  this class; reach for a **`factory`** only when you need to *not* do that — return a cached/canonical
  instance, a subtype, or the result of validation that can't be a field initializer.
- **`required` named params** make call sites self-documenting and stop positional-arg bugs. `required`
  applies only to **named** params (`{...}`); a non-defaulted positional param is already mandatory.

  ```dart
  Card({required this.kind, required this.state});
  // Card(kind: Kind.fox, state: CardState.faceDown)
  ```

- **`const` constructors** when all fields are `final` — enables compile-time constants, canonical
  instances, and cheaper widget rebuilds. Default to const for value/model types.

  ```dart
  class Vector2 {
    const Vector2(this.x, this.y);
    final double x, y;
    static const zero = Vector2(0, 0);
  }
  ```

- **`factory` constructors** to return a cached/canonical instance or a subtype — cannot use `this`.
  Use for parsing, pooling, or dispatching:

  ```dart
  factory Tile.fromCode(int code) =>
      code == 0 ? const Tile.empty() : Tile._solid(code);
  ```

- **Redirecting constructors** (`Foo.alt() : this(...)`) to funnel through one canonical initializer
  instead of duplicating field setup.

## Make illegal states unrepresentable
Encode invariants in the type system so bad states can't compile. Reach for `enum` and Dart 3
`sealed` classes instead of contradictory boolean flags.

```dart
// don't: isFaceUp + isMatched can contradict
class Card { bool isFaceUp; bool isMatched; }
// do
enum CardState { faceDown, faceUp, matched }
```

`enum` for a fixed set of plain cases; **`sealed`** for a closed set of *variants that carry data*.
A sealed class is implicitly abstract (cannot be constructed) and its subtypes must live in the same
library, so the compiler makes `switch` **exhaustive** — add a variant and every unhandled `switch`
fails to compile. No `default`, no "unreachable" fallthrough.

```dart
sealed class MoveResult {
  const MoveResult();
}
class Accepted extends MoveResult { const Accepted(this.scored); final int scored; }
class Rejected extends MoveResult { const Rejected(this.reason); final String reason; }

// Exhaustive switch expression — compiler errors if a new variant is added.
String describe(MoveResult r) => switch (r) {
  Accepted(:final scored) => 'ok +$scored',
  Rejected(:final reason) => 'no: $reason',
};
```

Use `final class` for model types you do not intend to be subclassed/implemented outside their
library — it closes the hierarchy and documents intent in code, not a comment.

## No sentinels — throw or return nullable
Never signal failure (or "no argument") with `-1`, `''`, `Duration.zero`, or a magic value the caller
must remember to check. This cuts both ways — outputs *and* inputs.

- **Don't accept a sentinel parameter.** Replace a "pass `-1` to mean no limit" param with an optional
  named param whose absence *is* the signal: `entitiesOfKind(Kind.coin, {int? limit})`, `limit == null`
  means unlimited. The type tells the caller, no magic number to memorize.

- **Recoverable / expected absence → nullable** and let the caller pattern-match or `??`.

  ```dart
  Card? cardAt(int i) => (i >= 0 && i < _cards.length) ? _cards[i] : null;
  ```

- **Programmer error / broken invariant → throw** a typed error named for the failure.

  ```dart
  Level loadLevel(int id) {
    final level = _levels[id];
    if (level == null) throw LevelNotFoundException(id);
    return level;
  }
  ```

- **Don't return nullable `Future`/`Stream`/collections** — return an empty list/`Future.value`
  instead of `null`.

  ```dart
  List<Move> get legalMoves => _moves;     // do: empty list, never null
  // List<Move>? get legalMoves => ...;    // don't
  ```

## Immutable-by-default public surface
- Prefer `final` fields and top-level variables; expose reads, mutate through intent methods so
  callers can't corrupt invariants.
- Don't hand out your private mutable list — return an `UnmodifiableListView` or a copy.

```dart
final List<Card> _cards;
List<Card> get cards => UnmodifiableListView(_cards);   // do
// List<Card> get cards => _cards;                       // don't: caller can mutate state
```

- Model updates as new values (`copyWith`) rather than in-place mutation where practical; pair with
  `==`/`hashCode` so they compare by value.

## Getters and setters
- A getter is for a conceptual property: idempotent, no arguments, no visible side effects.
- Don't define a setter without a matching getter (a write-only "dropbox" breaks `+=` and confuses
  readers). For an action with side effects, use a verb method, not a setter.

## Documentation comments
- Use `///` dartdoc on every public type, member, and constructor. First sentence is a terse summary
  ending in a period; document the *contract* (when it throws, what `null` means), not what the code
  obviously does.
- Reference identifiers in `[square brackets]`; start methods with a third-person verb ("Flips…",
  "Returns…").

```dart
/// Flips the card at [index], applying the two-up matching rule.
///
/// Returns the resulting [MoveResult]; a flip on a locked board or an
/// already-matched card yields [Rejected].
MoveResult flip(int index) { ... }
```

## Quick review checklist for any new symbol
- [ ] Does the call site read as a clear phrase?
- [ ] Boolean is a positive, non-imperative assertion (`isX`/`hasX`/`canX`); no `get` prefix on members?
- [ ] Side-effect method is an imperative verb; value-returning member is a noun?
- [ ] Right constructor used (named/factory/`const`/`required` named) instead of overloads or sentinels?
- [ ] Could an illegal state be made unrepresentable with an `enum` or `sealed` class?
- [ ] Failures throw a typed error or return nullable — no `-1`/empty sentinels?
- [ ] Public surface is `final`/immutable; no leaked mutable internals?
- [ ] `///` doc states the contract; `dart format` + analyzer clean?