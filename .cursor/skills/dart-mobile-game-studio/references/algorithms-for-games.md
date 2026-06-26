# Algorithms for games

Reusable game algorithms as **pure Dart** — **no `package:flutter`, no `package:flame` imports**.
They live in `lib/systems/` (with the value types they operate on in `lib/models/`), so every one
is verified with `dart test` on the VM, no device or render loop required. Anything random takes an
injected `Random` — pass the `SeededRandom` from `assets/seeded_random.dart` — so a fixed seed
gives a fixed sequence and tests can assert exact outcomes.

These are the classic algorithms, grounded in [TheAlgorithms/Dart](https://github.com/TheAlgorithms/Dart)
(BFS, DFS, flood fill via `area_of_island`, Fisher–Yates, binary search) and modernised to this
skill's bar: null-safe, analyzer-clean, `const` where possible, `dart format` (2-space indent,
trailing commas), no `new`, no global mutable `Random`. Where a priority queue is needed (Dijkstra,
A\*) we use `HeapPriorityQueue` from the official `package:collection` (publisher **dart.dev**) per
`references/package-policy.md` — a binary heap beats the upstream `List`-scan queue
(`data_structures/Queue/Priority_Queue.dart`, O(n) insert).

**Complexity notation:** `V` = vertices/cells, `E` = edges, `n` = element count. Grid pathfinding on
a `W×H` tile map has `V = W·H` and `E ≤ 4·V` (4-neighbour) or `8·V` (8-neighbour).

**Determinism rule:** the *only* source of randomness is the injected `Random`. No `DateTime.now()`,
no unseeded `Random()`, no hash-order iteration feeding game state. Iterate `List`s (ordered), not
`Set`/`Map` literals, when the order affects results.

---

## 1. Grid pathfinding (BFS, Dijkstra, A\*)

A shared tile-grid model. `+y` is down, matching screen/Flame conventions. The grid is the graph;
neighbours are computed on demand, so there is no adjacency list to build or keep in sync.

```dart
// lib/models/tile_grid.dart — pure Dart.

/// An integer cell coordinate on a tile grid. Value type: usable as a Map/Set key.
class Cell {
  const Cell(this.x, this.y);
  final int x;
  final int y;

  @override
  bool operator ==(Object other) => other is Cell && other.x == x && other.y == y;

  @override
  int get hashCode => x * 73856093 ^ y * 19349663; // two large primes, cheap + well-spread

  @override
  String toString() => '($x, $y)';
}

/// A rectangular grid of passable/blocked cells. Rows are `y`, columns are `x`.
class TileGrid {
  TileGrid(this.width, this.height, {Set<Cell>? blocked})
      : _blocked = blocked ?? <Cell>{};

  final int width;
  final int height;
  final Set<Cell> _blocked;

  bool inBounds(Cell c) => c.x >= 0 && c.x < width && c.y >= 0 && c.y < height;
  bool isPassable(Cell c) => inBounds(c) && !_blocked.contains(c);

  /// 4-neighbour (von Neumann) successors, in a fixed order so paths are deterministic.
  /// Order matters: it is the tie-break when several cells have equal cost.
  static const List<Cell> _dirs4 = [
    Cell(1, 0), // right
    Cell(0, 1), // down
    Cell(-1, 0), // left
    Cell(0, -1), // up
  ];

  Iterable<Cell> neighbors4(Cell c) sync* {
    for (final d in _dirs4) {
      final n = Cell(c.x + d.x, c.y + d.y);
      if (isPassable(n)) yield n;
    }
  }
}
```

`Cell` and `TileGrid` are imported by every pathfinder below. Reconstructing the path is shared too:

```dart
// lib/systems/path_reconstruct.dart
List<Cell> reconstructPath(Map<Cell, Cell> cameFrom, Cell goal) {
  final path = <Cell>[goal];
  var current = goal;
  while (cameFrom.containsKey(current)) {
    current = cameFrom[current]!;
    path.add(current);
  }
  return path.reversed.toList(growable: false);
}
```

### 1a. BFS — shortest path on an unweighted grid

Every step costs the same (one tile), so the first time BFS reaches a cell it has reached it by a
shortest path. Grounded in `graphs/breadth_first_search.dart`; that version only enumerates reachable
nodes — here we also record predecessors so we can return the path, and we mark *on enqueue* (not on
dequeue) so a cell is never queued twice.

```dart
// lib/systems/bfs_path.dart
import 'dart:collection';

/// Shortest path on an unweighted grid, or `null` if `goal` is unreachable.
/// O(V + E) time, O(V) space.
List<Cell>? bfsPath(TileGrid grid, Cell start, Cell goal) {
  if (!grid.isPassable(start) || !grid.isPassable(goal)) return null;
  if (start == goal) return [start];

  final frontier = Queue<Cell>()..add(start);
  final cameFrom = <Cell, Cell>{};
  final seen = <Cell>{start};

  while (frontier.isNotEmpty) {
    final current = frontier.removeFirst();
    for (final next in grid.neighbors4(current)) {
      if (seen.add(next)) {
        // add() returns false if already present — dedupe + visit in one step
        cameFrom[next] = current;
        if (next == goal) return reconstructPath(cameFrom, goal);
        frontier.add(next);
      }
    }
  }
  return null;
}
```

**When to use:** uniform tile cost and you only need *a* shortest path — maze solving, "can the enemy
reach the player", flood-style reachability. Simplest correct option; reach for Dijkstra/A\* only when
costs vary or the grid is large.

### 1b. Dijkstra — shortest path with per-tile cost

When tiles cost different amounts to enter (mud = 3, road = 1), BFS no longer gives the cheapest path.
Dijkstra always expands the cheapest-so-far frontier cell, using a min-priority queue keyed by
accumulated cost `g`.

```dart
// lib/systems/dijkstra_path.dart
import 'package:collection/collection.dart'; // HeapPriorityQueue — dart.dev

/// "Infinity" for an unset score — far above any realistic mobile-grid path cost, and still an
/// exact VM int. (A plain `1 << 30` can be reached by accumulated tile costs and break comparisons.)
const int _inf = 1 << 52;

/// Cheapest path where `costOf(cell)` is the cost to ENTER that cell (must be >= 1).
/// O(E log V) with a binary heap. The heap is ordered by a priority stored IN each queued record —
/// never by a mutable map — so the heap invariant always holds. State (`gScore`/`cameFrom`) lives
/// outside the queue: a cell may be enqueued more than once (a "lazy" decrease-key) and a stale pop
/// (one whose cost has since improved) is skipped.
List<Cell>? dijkstraPath(
  TileGrid grid,
  Cell start,
  Cell goal,
  int Function(Cell) costOf,
) {
  final gScore = <Cell, int>{start: 0};
  final cameFrom = <Cell, Cell>{};
  // Each entry is (priorityWhenQueued, cell); the comparator reads only the immutable priority.
  final open = HeapPriorityQueue<(int, Cell)>((a, b) => a.$1.compareTo(b.$1))..add((0, start));

  while (open.isNotEmpty) {
    final (priority, current) = open.removeFirst();
    if (priority > (gScore[current] ?? _inf)) continue; // stale duplicate — already improved
    if (current == goal) return reconstructPath(cameFrom, goal);
    final baseCost = gScore[current]!;
    for (final next in grid.neighbors4(current)) {
      final tentative = baseCost + costOf(next); // costOf(next) must be >= 1
      if (tentative < (gScore[next] ?? _inf)) {
        gScore[next] = tentative;
        cameFrom[next] = current;
        open.add((tentative, next)); // enqueue with its priority; the old copy is skipped on pop
      }
    }
  }
  return null;
}
```

Each entry carries the priority it was queued at, so the heap never reorders behind your back. When a
cell is popped with a priority worse than its current `gScore`, it's a stale duplicate and is skipped
— correct, and cheaper than a real decrease-key. Costs **must be `>= 1`**; a `0`/negative tile cost
breaks the shortest-path guarantee.

**When to use:** weighted tiles (terrain, hazards) and no good distance estimate to the goal. If you
*do* have an admissible estimate, A\* explores far fewer cells for the same answer.

### 1c. A\* — Dijkstra guided by a heuristic

A\* orders the frontier by `f = g + h`, where `g` is cost-so-far and `h` is an *admissible* estimate of
the remaining cost (never an overestimate). With an admissible `h`, A\* returns an optimal path while
expanding only cells that look promising. On a 4-neighbour grid the **Manhattan distance** is the
correct admissible heuristic; for 8-neighbour movement use **octile** or Chebyshev distance instead
(Manhattan would overestimate diagonals and break optimality).

```dart
// lib/systems/astar_path.dart
import 'package:collection/collection.dart';

/// "Infinity" for an unset score (see dijkstra_path.dart for the rationale).
const int _inf = 1 << 52;

/// Manhattan distance — admissible & consistent for 4-neighbour grids with min step cost 1.
int manhattan(Cell a, Cell b) => (a.x - b.x).abs() + (a.y - b.y).abs();

/// A* shortest path. O(E log V) worst case; in practice expands far fewer cells than Dijkstra.
/// Pass `costOf` for weighted tiles (default: every tile costs 1, which must be >= 1). The heap is
/// ordered by the f-score stored in each queued record, so the heap invariant always holds; stale
/// pops are skipped.
List<Cell>? aStarPath(
  TileGrid grid,
  Cell start,
  Cell goal, {
  int Function(Cell a, Cell b) heuristic = manhattan,
  int Function(Cell)? costOf,
}) {
  final int Function(Cell) stepCost = costOf ?? (Cell _) => 1;
  final gScore = <Cell, int>{start: 0};
  final fScore = <Cell, int>{start: heuristic(start, goal)};
  final cameFrom = <Cell, Cell>{};
  // (fWhenQueued, cell): the comparator reads only the immutable priority.
  final open = HeapPriorityQueue<(int, Cell)>((a, b) => a.$1.compareTo(b.$1))
    ..add((fScore[start]!, start));

  while (open.isNotEmpty) {
    final (f, current) = open.removeFirst();
    if (f > (fScore[current] ?? _inf)) continue; // stale duplicate
    if (current == goal) return reconstructPath(cameFrom, goal);
    final baseCost = gScore[current]!;
    for (final next in grid.neighbors4(current)) {
      final tentative = baseCost + stepCost(next);
      if (tentative < (gScore[next] ?? _inf)) {
        cameFrom[next] = current;
        gScore[next] = tentative;
        final fNext = tentative + heuristic(next, goal);
        fScore[next] = fNext;
        open.add((fNext, next));
      }
    }
  }
  return null;
}
```

**When to use:** the default for enemy/unit pathfinding on any grid bigger than trivial. Set `h` to
`(_, __) => 0` and A\* degrades exactly to Dijkstra — handy for testing that both agree. Keep `h`
admissible (and ideally consistent) or the path may be sub-optimal.

**Tests (`dart test`):** on a grid with no obstacles, `bfsPath` length equals `manhattan(start, goal)
+ 1`; a wall that fully separates start and goal yields `null` from all three; with `h = 0`, A\* and
Dijkstra return paths of equal cost; A\* on a weighted grid returns a cost no greater than BFS's
hop-count path. Use fixed grids so assertions are exact.

---

## 2. Sorting & searching — leaderboards

A leaderboard is a sorted list of score entries. Dart's `List.sort` is a tuned hybrid (introsort-like,
~O(n log n)); **prefer it** over hand-rolling — the value here is the *comparator*, which encodes the
ranking rule and its tie-breaks. Define a stable, total order so equal scores rank deterministically
(e.g. earlier timestamp wins), otherwise two runs can disagree.

```dart
// lib/models/score_entry.dart
class ScoreEntry implements Comparable<ScoreEntry> {
  const ScoreEntry(this.name, this.score, this.epochMs);
  final String name;
  final int score;
  final int epochMs; // tie-break: lower (earlier) ranks higher

  /// Higher score first; ties broken by earlier time, then name — a TOTAL order.
  @override
  int compareTo(ScoreEntry other) {
    final byScore = other.score.compareTo(score); // descending
    if (byScore != 0) return byScore;
    final byTime = epochMs.compareTo(other.epochMs); // ascending
    if (byTime != 0) return byTime;
    return name.compareTo(other.name);
  }
}

// lib/systems/leaderboard.dart
/// Top-[limit] entries, highest first. O(n log n) sort.
List<ScoreEntry> topScores(List<ScoreEntry> entries, {int limit = 10}) {
  final sorted = [...entries]..sort(); // copy first: never mutate the caller's list
  return sorted.take(limit).toList(growable: false);
}

/// Rank a new score WITHOUT re-sorting: count strictly-better entries. O(n).
int rankOf(ScoreEntry candidate, List<ScoreEntry> sortedDescending) {
  var rank = 0;
  for (final e in sortedDescending) {
    if (e.compareTo(candidate) < 0) rank++; // e ranks ahead of candidate
  }
  return rank; // 0-based: 0 means new best
}
```

**Binary search** (grounded in `search/binary_Search.dart`, modernised to non-recursive, generic,
null-safe) finds an insertion point in an already-sorted list in O(log n) — the right tool for "where
does this score slot in" without a full re-sort:

```dart
// lib/systems/binary_search.dart
/// Leftmost index where `value` could be inserted to keep `sorted` ordered by
/// [compare]. O(log n). `sorted` must already be ordered by the same comparator.
int lowerBound<T>(List<T> sorted, T value, int Function(T, T) compare) {
  var lo = 0;
  var hi = sorted.length;
  while (lo < hi) {
    final mid = lo + ((hi - lo) >> 1); // no overflow; >> 1 is integer halve
    if (compare(sorted[mid], value) < 0) {
      lo = mid + 1;
    } else {
      hi = mid;
    }
  }
  return lo;
}
```

**When to use:** `List.sort` for building/refreshing the board; `lowerBound` to insert one new score
into a kept-sorted board (insert at the returned index) or to compute a rank in O(log n) instead of
O(n). Don't re-sort the whole board on every new score.

**Tests:** sorting is idempotent (`sort` of a sorted list is unchanged); ties resolve by the
documented rule; `lowerBound` of an existing value returns the index of its first occurrence; inserting
at `lowerBound` keeps the list sorted.

---

## 3. Graph basics — adjacency & flood fill

For non-grid graphs (level node maps, dialogue trees, region connectivity) use an explicit adjacency
list. This modernises `graphs/breadth_first_search.dart`'s `Graph` (which used `HashMap` + `new` +
untyped lists) into a typed, null-safe form.

```dart
// lib/models/graph.dart
/// Directed graph by adjacency list. Add edges both ways for an undirected graph.
class Graph<T> {
  final Map<T, List<T>> _adj = {};

  void addNode(T node) => _adj.putIfAbsent(node, () => <T>[]);

  void addEdge(T from, T to) {
    addNode(from);
    addNode(to);
    _adj[from]!.add(to);
  }

  Iterable<T> neighbors(T node) => _adj[node] ?? const [];
  Iterable<T> get nodes => _adj.keys;
}
```

**Flood fill** — the coloring-book "paint bucket" and the connectivity check behind match-3 clears and
"how big is this blob". Grounded in `graphs/area_of_island.dart` (4-direction deltas, visited matrix,
explicit stack instead of recursion to avoid stack overflow on large regions).

```dart
// lib/systems/flood_fill.dart
/// All cells reachable from [start] whose value equals start's value (4-connected).
/// Iterative (explicit stack) so a large region can't overflow the call stack.
/// O(V) over the filled region; visits each cell once.
Set<Cell> floodRegion(List<List<int>> grid, Cell start) {
  final h = grid.length;
  if (h == 0) return {};
  final w = grid[0].length;
  bool inBounds(Cell c) => c.x >= 0 && c.x < w && c.y >= 0 && c.y < h;

  final target = grid[start.y][start.x];
  final region = <Cell>{};
  final stack = <Cell>[start];
  const deltas = [Cell(1, 0), Cell(-1, 0), Cell(0, 1), Cell(0, -1)];

  while (stack.isNotEmpty) {
    final c = stack.removeLast();
    if (!inBounds(c) || region.contains(c)) continue;
    if (grid[c.y][c.x] != target) continue;
    region.add(c);
    for (final d in deltas) {
      stack.add(Cell(c.x + d.x, c.y + d.y));
    }
  }
  return region;
}

/// Paint-bucket: recolour the connected region under [start] to [newColor].
/// No-op if it's already that color (prevents a pointless full-grid walk).
void floodFill(List<List<int>> grid, Cell start, int newColor) {
  if (grid[start.y][start.x] == newColor) return;
  for (final c in floodRegion(grid, start)) {
    grid[c.y][c.x] = newColor;
  }
}
```

**When to use:** coloring/paint tools, counting connected blobs, board-region reachability. For purely
*counting* connected area without keeping the cells, the `area_of_island` accumulate-and-discard form
is lighter on memory.

**Tests:** filling a uniform grid touches every cell; a single-cell region returns size 1; `floodFill`
to the same color is a no-op; two regions separated by a different color don't bleed into each other.

---

## 4. Randomization via the injected RNG

All randomness goes through the injected `Random` (`SeededRandom` in tests). Never call the global
`Random()` from `other/fisher_yates_shuffle.dart`, and note that upstream's loop (`i > 1`,
`nextInt(i - 1)`) is *biased* and skips index 0/1 — the version below is unbiased and seedable.

```dart
// lib/systems/randomization.dart
import 'dart:math';

/// Unbiased Fisher–Yates shuffle in place, driven by an injected [rng].
/// O(n). Deterministic for a fixed seed + input. (SeededRandom already
/// provides .shuffle(); this is the standalone form when you only have a Random.)
void shuffleInPlace<T>(List<T> items, Random rng) {
  for (var i = items.length - 1; i > 0; i--) {
    final j = rng.nextInt(i + 1); // 0..i inclusive — the correct range
    final tmp = items[i];
    items[i] = items[j];
    items[j] = tmp;
  }
}

/// Weighted pick: choose an index with probability proportional to weights[i].
/// O(n). Weights must be non-negative with a positive sum (e.g. loot/spawn tables).
int weightedPickIndex(List<num> weights, Random rng) {
  var total = 0.0;
  for (final w in weights) {
    if (w < 0) throw ArgumentError('weights must be non-negative');
    total += w;
  }
  if (total <= 0) throw ArgumentError('weights must sum to a positive value');
  var roll = rng.nextDouble() * total; // [0, total)
  for (var i = 0; i < weights.length; i++) {
    roll -= weights[i];
    if (roll < 0) return i;
  }
  return weights.length - 1; // float-rounding guard; effectively unreachable
}
```

**When to use:** `shuffleInPlace` for decks/tiles/turn order; `weightedPickIndex` for loot tables,
biased spawns, weighted enemy selection. For repeated draws from the *same* table, precompute a
cumulative array and binary-search it (`lowerBound`, §2) for O(log n) per pick.

**Tests:** with `SeededRandom(42)`, a shuffle produces a fixed permutation (assert it exactly); the
same seed reproduces it across runs; over many `weightedPickIndex` draws the empirical counts track the
weight ratios within tolerance; a zero-weight entry is never picked.

---

## 5. Procedural generation

### 5a. Maze generation — recursive backtracker

Carves a perfect maze (exactly one path between any two cells, no loops) on a `(2w+1)×(2h+1)` grid
where odd cells are rooms and even cells are walls between them. Uses an explicit stack (no recursion
limit) and the injected RNG, so a seed reproduces the maze exactly. This is the backtracking pattern
from `backtracking/` applied to grid carving.

```dart
// lib/systems/maze.dart
import 'dart:math';

/// Generates a perfect maze. Returns a grid where 0 = passage, 1 = wall.
/// Dimensions are (2*cols+1) wide by (2*rows+1) tall. O(rows*cols).
List<List<int>> generateMaze(int rows, int cols, Random rng) {
  final h = 2 * rows + 1;
  final w = 2 * cols + 1;
  final grid = List.generate(h, (_) => List.filled(w, 1)); // all walls

  final visited = List.generate(rows, (_) => List.filled(cols, false));
  final stack = <Cell>[const Cell(0, 0)];
  visited[0][0] = true;
  grid[1][1] = 0; // open the start room

  // Room cell (cx,cy) maps to grid cell (2*cx+1, 2*cy+1).
  const dirs = [Cell(1, 0), Cell(-1, 0), Cell(0, 1), Cell(0, -1)];

  while (stack.isNotEmpty) {
    final cur = stack.last;
    final unvisited = <Cell>[];
    for (final d in dirs) {
      final n = Cell(cur.x + d.x, cur.y + d.y);
      if (n.x >= 0 && n.x < cols && n.y >= 0 && n.y < rows && !visited[n.y][n.x]) {
        unvisited.add(n);
      }
    }
    if (unvisited.isEmpty) {
      stack.removeLast(); // dead end — backtrack
      continue;
    }
    final next = unvisited[rng.nextInt(unvisited.length)]; // injected RNG
    visited[next.y][next.x] = true;
    // Knock out the wall between cur and next in the doubled grid.
    grid[next.y * 2 + 1][next.x * 2 + 1] = 0;
    grid[cur.y + next.y + 1][cur.x + next.x + 1] = 0;
    stack.add(next);
  }
  return grid;
}
```

### 5b. Room placement — simple dungeon

Drop non-overlapping rooms, then connect their centres with L-shaped corridors. Reject-on-overlap is
fine for the dozens-of-rooms scale of a mobile level; the injected RNG makes the whole layout
reproducible.

```dart
// lib/models/room.dart
class Room {
  const Room(this.x, this.y, this.w, this.h);
  final int x, y, w, h;
  Cell get center => Cell(x + w ~/ 2, y + h ~/ 2);
  bool overlaps(Room o) =>
      x < o.x + o.w && x + w > o.x && y < o.y + o.h && y + h > o.y;
}

// lib/systems/dungeon.dart
import 'dart:math';

/// Places up to [attempts] rooms without overlap. O(attempts * rooms placed).
List<Room> placeRooms(
  int mapW,
  int mapH,
  Random rng, {
  int attempts = 30,
  int minSize = 3,
  int maxSize = 7,
}) {
  final rooms = <Room>[];
  for (var i = 0; i < attempts; i++) {
    final w = minSize + rng.nextInt(maxSize - minSize + 1);
    final h = minSize + rng.nextInt(maxSize - minSize + 1);
    final x = rng.nextInt(mapW - w); // fits inside the map
    final y = rng.nextInt(mapH - h);
    final candidate = Room(x, y, w, h);
    if (rooms.every((r) => !candidate.overlaps(r))) rooms.add(candidate);
  }
  return rooms;
}
```

### 5c. Value-noise table — smooth pseudo-random fields

A cheap, deterministic alternative to Perlin for backgrounds, terrain height, or difficulty curves:
seed a lattice of random values, then bilinearly interpolate. Fully reproducible from the injected RNG.

```dart
// lib/systems/value_noise.dart
import 'dart:math';

/// A 2D value-noise sampler over a [size]×[size] lattice of random values in [0,1).
class ValueNoise {
  ValueNoise(int size, Random rng)
      : _size = size,
        _lattice = List.generate(
          size,
          (_) => List.generate(size, (_) => rng.nextDouble()),
          growable: false,
        );

  final int _size;
  final List<List<double>> _lattice;

  static double _smooth(double t) => t * t * (3 - 2 * t); // smoothstep ease

  /// Samples noise at continuous (x, y); coordinates wrap around the lattice.
  /// O(1) per sample.
  double sample(double x, double y) {
    final x0 = x.floor(), y0 = y.floor();
    final tx = _smooth(x - x0), ty = _smooth(y - y0);
    final i0 = x0 % _size, i1 = (x0 + 1) % _size;
    final j0 = y0 % _size, j1 = (y0 + 1) % _size;
    final top = _lerp(_lattice[j0][i0], _lattice[j0][i1], tx);
    final bot = _lerp(_lattice[j1][i0], _lattice[j1][i1], tx);
    return _lerp(top, bot, ty);
  }

  static double _lerp(double a, double b, double t) => a + (b - a) * t;
}
```

**When to use:** recursive backtracker for puzzle/maze levels (perfect mazes, guaranteed solvable);
room placement for dungeon-ish layouts; value noise for organic-looking but seeded fields. Generate
**off the main isolate** if a map is large (`references/dart/dart-async-isolates.md`) and ship the seed,
not the baked grid, so levels stay tiny and reproducible.

**Tests:** the same seed yields an identical maze/room set/noise field (deep-equality assert); a
generated maze is fully connected (run `bfsPath` between any two passages and expect non-null); placed
rooms never overlap; `sample` is continuous (adjacent samples differ by a bounded amount) and in
`[0, 1)`.

---

## 6. Scoring & combo systems

Keep scoring as a pure reducer over events — no timers, no widgets — so the full rule set is
unit-tested. A combo multiplies the value of consecutive successes and resets on a miss or timeout. Time
is *passed in* (never read from the clock) so the reducer stays deterministic.

```dart
// lib/systems/score_state.dart
class ScoreState {
  const ScoreState({this.score = 0, this.combo = 0, this.lastHitMs = -1});
  final int score;
  final int combo; // consecutive hits
  final int lastHitMs; // timestamp of the last hit, or -1

  ScoreState copyWith({int? score, int? combo, int? lastHitMs}) => ScoreState(
        score: score ?? this.score,
        combo: combo ?? this.combo,
        lastHitMs: lastHitMs ?? this.lastHitMs,
      );
}

/// Applies a successful hit worth [base] points at time [nowMs]. The combo
/// continues if the hit lands within [comboWindowMs] of the previous one,
/// otherwise it restarts at 1. Multiplier is capped to keep scores sane. O(1).
ScoreState applyHit(
  ScoreState s,
  int base,
  int nowMs, {
  int comboWindowMs = 1500,
  int maxMultiplier = 8,
}) {
  final continues = s.lastHitMs >= 0 && (nowMs - s.lastHitMs) <= comboWindowMs;
  final combo = continues ? s.combo + 1 : 1;
  final multiplier = combo.clamp(1, maxMultiplier);
  return s.copyWith(
    score: s.score + base * multiplier,
    combo: combo,
    lastHitMs: nowMs,
  );
}

/// A miss (or an expired window) breaks the combo without touching the score. O(1).
ScoreState applyMiss(ScoreState s) => s.copyWith(combo: 0, lastHitMs: -1);
```

**When to use:** any game with chained scoring — match-3 cascades, rhythm taps, runner pickups. Drive
it from the game loop by feeding the loop's accumulated game-time as `nowMs` (clamp `dt` first, per the
doctrine), not wall-clock time, so it replays identically.

**Tests:** hits inside the window grow the multiplier and score; a hit after the window resets the
combo to 1; the multiplier never exceeds `maxMultiplier`; `applyMiss` zeroes the combo but preserves
the score; identical event sequences produce identical end states.

---

## 7. Board / grid logic — neighbours, match-3, line clears

### 7a. Neighbours

```dart
// lib/systems/board.dart
/// 4-connected neighbours of (x, y) inside a [w]×[h] board, in fixed order.
Iterable<Cell> neighbors4(int x, int y, int w, int h) sync* {
  const deltas = [Cell(1, 0), Cell(-1, 0), Cell(0, 1), Cell(0, -1)];
  for (final d in deltas) {
    final nx = x + d.x, ny = y + d.y;
    if (nx >= 0 && nx < w && ny >= 0 && ny < h) yield Cell(nx, ny);
  }
}
```

### 7b. Match-3 detection

Scan rows then columns for runs of ≥3 equal non-empty tiles. Collecting into a `Set<Cell>` naturally
dedupes the cell shared by an intersecting horizontal+vertical match (a "T"/"L"). `-1` marks an empty
cell and never matches.

```dart
// lib/systems/match3.dart
/// All cells belonging to a horizontal or vertical run of >= 3 equal tiles.
/// `board[y][x]`; -1 = empty. O(w*h).
Set<Cell> findMatches(List<List<int>> board) {
  final h = board.length;
  if (h == 0) return {};
  final w = board[0].length;
  final matched = <Cell>{};

  void scanRun(List<Cell> run, int color) {
    if (color != -1 && run.length >= 3) matched.addAll(run);
  }

  // Horizontal runs.
  for (var y = 0; y < h; y++) {
    var run = <Cell>[];
    var color = -2; // sentinel distinct from -1 (empty)
    for (var x = 0; x < w; x++) {
      final c = board[y][x];
      if (c == color) {
        run.add(Cell(x, y));
      } else {
        scanRun(run, color);
        color = c;
        run = [Cell(x, y)];
      }
    }
    scanRun(run, color);
  }
  // Vertical runs.
  for (var x = 0; x < w; x++) {
    var run = <Cell>[];
    var color = -2;
    for (var y = 0; y < h; y++) {
      final c = board[y][x];
      if (c == color) {
        run.add(Cell(x, y));
      } else {
        scanRun(run, color);
        color = c;
        run = [Cell(x, y)];
      }
    }
    scanRun(run, color);
  }
  return matched;
}
```

### 7c. Line clears & gravity

Clearing matched tiles, then collapsing columns downward (Tetris-style gravity / match-3 refill).

```dart
// lib/systems/gravity.dart
/// Sets every matched cell to empty (-1). O(matches).
void clearCells(List<List<int>> board, Set<Cell> cells) {
  for (final c in cells) {
    board[c.y][c.x] = -1;
  }
}

/// Collapses each column so non-empty tiles fall to the bottom; tops become -1.
/// O(w*h). Pure column compaction — refilling new tiles is a separate step that
/// uses the injected RNG (so it stays deterministic).
void applyGravity(List<List<int>> board) {
  final h = board.length;
  if (h == 0) return;
  final w = board[0].length;
  for (var x = 0; x < w; x++) {
    var write = h - 1; // next slot to fill, from the bottom up
    for (var y = h - 1; y >= 0; y--) {
      if (board[y][x] != -1) {
        board[write][x] = board[y][x];
        if (write != y) board[y][x] = -1;
        write--;
      }
    }
    for (var y = write; y >= 0; y--) {
      board[y][x] = -1; // empties at the top
    }
  }
}
```

**When to use:** match-3, drop/merge, and Tetris-style boards. Keep the cycle as
`findMatches → clearCells → applyGravity → refill(rng) → findMatches …` until no matches remain, so
cascades resolve in one deterministic pass.

**Tests:** a 3-in-a-row is detected; a 2-in-a-row is not; intersecting matches dedupe the shared cell;
`applyGravity` packs tiles to the bottom with empties on top and is idempotent on a settled board; the
full cascade terminates.

---

## 8. Puzzle mechanics — sliding-puzzle

### 8a. Solvability

A randomly shuffled 15-puzzle (or any N-puzzle) is solvable for **only half** of permutations — so you
must *check* a generated board, not just shuffle and hope. The rule combines the permutation's
**inversion count** with the blank's row:

- **Odd width** (e.g. 3×3): solvable ⇔ inversions is even.
- **Even width** (e.g. 4×4): solvable ⇔ (inversions + row-of-blank-from-bottom) is odd.

```dart
// lib/systems/sliding_puzzle.dart
/// `tiles` is the board in row-major order; 0 is the blank. `width` is the side.
/// Returns whether this arrangement can reach the solved state. O(n^2).
bool isSolvable(List<int> tiles, int width) {
  var inversions = 0;
  for (var i = 0; i < tiles.length; i++) {
    if (tiles[i] == 0) continue;
    for (var j = i + 1; j < tiles.length; j++) {
      if (tiles[j] != 0 && tiles[i] > tiles[j]) inversions++;
    }
  }
  if (width.isOdd) return inversions.isEven;
  final blankIndex = tiles.indexOf(0);
  final rowFromBottom = width - (blankIndex ~/ width);
  return (inversions + rowFromBottom).isOdd;
}

/// Produces a SOLVABLE shuffle using the injected RNG: reshuffle until solvable
/// and non-trivial. Each reshuffle has ~50% success, so this halts fast. O(n^2) expected.
List<int> shuffledSolvable(int width, Random rng) {
  final n = width * width;
  final tiles = List<int>.generate(n, (i) => i); // 0..n-1, 0 = blank
  do {
    shuffleInPlace(tiles, rng); // from §4 — deterministic for a fixed seed
  } while (!isSolvable(tiles, width) || _isSolved(tiles));
  return tiles;
}

bool _isSolved(List<int> tiles) {
  for (var i = 0; i < tiles.length - 1; i++) {
    if (tiles[i] != i + 1) return false;
  }
  return tiles.last == 0;
}
```

### 8b. Move validation

A tile may move only if it is orthogonally adjacent to the blank. Validate, then swap.

```dart
/// Whether the tile at [index] can slide (is 4-adjacent to the blank). O(1).
bool canMove(List<int> tiles, int width, int index) {
  final blank = tiles.indexOf(0);
  final br = blank ~/ width, bc = blank % width;
  final tr = index ~/ width, tc = index % width;
  return (br == tr && (bc - tc).abs() == 1) ||
      (bc == tc && (br - tr).abs() == 1);
}

/// Slides the tile at [index] into the blank, returning a NEW list (pure).
/// Throws if the move is illegal — callers should gate on [canMove].
List<int> move(List<int> tiles, int width, int index) {
  if (!canMove(tiles, width, index)) {
    throw ArgumentError('illegal move: tile $index is not adjacent to the blank');
  }
  final next = [...tiles];
  final blank = next.indexOf(0);
  next[blank] = next[index];
  next[index] = 0;
  return next;
}
```

**When to use:** sliding/15-puzzles and any "swap adjacent" board. Always generate via
`shuffledSolvable` — never raw `shuffle`, or roughly half your levels are impossible. `move` is pure
(returns a new board) to fit the immutable-model + undo-stack convention; mutate in place only inside a
hot loop if profiling demands it.

**Tests:** the solved board is solvable and `_isSolved`; a single legal swap from solved is solvable; an
arrangement made by swapping two non-blank tiles in the solved board is *un*solvable on an odd width;
`canMove` is true only for the up-to-four neighbours of the blank; `move` rejects illegal moves and
leaves the input unmutated; `shuffledSolvable(seed)` is reproducible and always passes `isSolvable`.

---

## Where this lives & how it's tested

- **Location:** algorithms in `lib/systems/`, the value types they use (`Cell`, `Graph`, `Room`,
  `ScoreEntry`, `ScoreState`) in `lib/models/`. Pure Dart only — no `package:flutter`/`package:flame`.
- **RNG:** every randomized function takes a `Random`; pass `SeededRandom` (`assets/seeded_random.dart`)
  in tests for exact, reproducible assertions. No clock reads, no global RNG.
- **Verify:** `dart test` on the VM — no device, no render loop. See `references/testing-and-release.md`.
  Quality bar in `references/dart/` and `references/quality-policy.md` (`dart format`, analyzer-clean,
  null-safe, `const`).
- **Performance:** the complexity bounds above are the budget; `references/performance-checklist.md`
  covers keeping per-frame work allocation-free. Run heavy generation off the main isolate
  (`references/dart/dart-async-isolates.md`).
- **Packages:** only `package:collection` (publisher **dart.dev**) is pulled in, for
  `HeapPriorityQueue` (§1) — justified under `references/package-policy.md` (official first). Everything
  else is `dart:core` / `dart:collection` / `dart:math`.

**Grounding:** algorithms verified against
[TheAlgorithms/Dart](https://github.com/TheAlgorithms/Dart) — `graphs/breadth_first_search.dart`,
`graphs/depth_first_search.dart`, `graphs/area_of_island.dart` (flood fill), `other/fisher_yates_shuffle.dart`,
`search/binary_Search.dart`, `backtracking/` — and modernised to this skill's bar. `HeapPriorityQueue`
signature per the official `package:collection` API docs (pub.dev, publisher dart.dev).
