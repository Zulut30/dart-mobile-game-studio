# Template: Puzzle (sliding / jigsaw / logic board)

A **design brief + architecture skeleton** for a turn-based puzzle (15-puzzle, jigsaw, sort/logic).
Fill the brackets, implement against the [`drag-and-drop-puzzle`/`shape-matching` recipes](../references/game-templates.md),
and use the solvability/maze helpers in [`references/algorithms-for-games.md`](../references/algorithms-for-games.md).

**Mode:** Flutter-widgets-only (`GridView`/`Draggable` + `CustomPainter`). Discrete state, no loop —
the move changes a model, the UI rebuilds. Fully testable.

---

## Mini-GDD (filled example — adapt)

- **One-liner:** `<slide tiles to restore the picture / number order>`.
- **Audience & age:** ages 6+, general/kids; sessions 1–5 min.
- **Core loop:** see the scrambled board → make a legal move → board updates → repeat until solved.
- **Primary verb:** tap (slide) / drag (place).
- **Failure model:** **no-fail**; score by moves/time; offer hints/undo for kids.
- **Win / progression:** board sizes (3×3 → 5×5), picture sets, par/star by moves.
- **Art:** numbered tiles or a sliced picture; clear "correct slot" affordance.
- **Scope (in):** one size, legal-move logic, shuffle (solvable!), win-check, restart, undo.
- **Cut-line (later):** sizes, pictures, hints, timer, daily board.

## Architecture skeleton (pure Dart, no Flutter import)

```
lib/models/   board.dart        # immutable grid: List<int> tiles, blankIndex, dims; copyWith, ==
              game_state.dart    # board, moves, phase; ==/hashCode
lib/systems/  shuffler.dart     # generate a SOLVABLE scramble from an injected Random
              move_system.dart   # legalMoves(board); apply(board, tileIndex) -> new board; pure
              solver.dart?       # optional: BFS/A* hint = next best move (algorithms-for-games.md)
lib/widgets/  puzzle_screen.dart # renders the grid; tap/drag → move intent; HUD; win
```

- **Solvable shuffles only.** A random permutation is solvable just half the time — generate the
  scramble by applying N random *legal* moves from the solved state (always solvable), or check the
  inversion-count parity. See [`algorithms-for-games.md`](../references/algorithms-for-games.md) (sliding-puzzle solvability).
- **Legality in pure Dart.** `legalMoves`/`apply` are pure functions; the view only sends a tile index.
- **Win-check** is value equality against the solved board.

## Genre specifics (what matters here)

- **Never deal an unsolvable board** — the classic puzzle bug; generate by legal moves or verify parity.
- **Snap + legal-only feedback** — a tile that can't move shouldn't; show why (the blank is elsewhere).
- **Undo/hints for kids** — frustration kills casual puzzles; a bounded undo stack + an optional
  next-move hint (A*) keeps it gentle.
- **Determinism** — same seed → same solvable board (golden test).

## Genre checklist

- [ ] Shuffle is provably solvable (legal-move scramble or parity check); `dart test` asserts it.
- [ ] `legalMoves`/`apply`/win-check are pure and unit-tested; illegal moves are no-ops.
- [ ] Same seed → identical board (golden test); injected seeded `Random`.
- [ ] Undo (and optional A* hint); `Semantics` on tiles (position + value).
- [ ] No `package:flutter` in `models/`/`systems/`; no-fail, restart present.

## See also
- [`references/algorithms-for-games.md`](../references/algorithms-for-games.md) — solvability, BFS/A* hints, grid math.
- [`references/game-templates.md`](../references/game-templates.md) — `drag-and-drop-puzzle`, `shape-matching`.
- [`workflows/create-new-game.md`](../workflows/create-new-game.md) · [`workflows/add-level-system.md`](../workflows/add-level-system.md).
