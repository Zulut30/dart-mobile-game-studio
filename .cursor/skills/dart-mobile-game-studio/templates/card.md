# Template: Card (memory / matching / sorting)

A **design brief + architecture skeleton** for a card game (flip-and-match, pairs, sort-into-piles).
Fill the brackets, implement against the [`memory-cards` recipe](../references/game-templates.md), and
copy the **worked example** [`examples/memory_match/`](../../../../examples/memory_match) — it is this
template, built and tested.

**Mode:** Flutter-widgets-only (`GridView` + flip animation). No loop; fully testable.

---

## Mini-GDD (filled example — adapt)

- **One-liner:** `<flip two cards; matching pairs stay; clear the board>`.
- **Audience & age:** ages 4–9, kids/general; sessions 1–3 min.
- **Core loop:** flip a card → flip a second → match keeps both / mismatch flips back → repeat. Win = all matched.
- **Primary verb:** tap (flip).
- **Failure model:** **no-fail**; track moves and/or time as a self-competitive score.
- **Win / progression:** grid sizes (2×2 → 4×4 → 6×6); themed symbol sets; star rating by moves.
- **Art:** placeholder symbols by shape **and** color (color-blind safe); calm flip animation.
- **Scope (in):** one grid size, flip/match, moves counter, win, restart.
- **Cut-line (later):** sizes/themes, timer, star ratings, sort/solitaire variants.

## Architecture skeleton (pure Dart, no Flutter import)

```
lib/models/   game_phase.dart   # enum GamePhase { menu, playing, paused, won }
              memory_card.dart   # immutable: id (slot), faceId (pair), isFaceUp, isMatched; copyWith
              game_state.dart    # cards, phase, moves, firstFlipped?, pendingMismatch?; ==/hashCode
lib/systems/  board_factory.dart # deal 2*pairs from an injected Random; faceId twice each
              game_logic.dart    # flip / resolveMismatch reducer (lock input during mismatch); pure
lib/widgets/  game_screen.dart   # owns state + mismatch Timer (disposed); GridView; HUD; win
```

- **Two-up rule + input lock:** a mismatch reveals both, then *locks* input (`pendingMismatch`) until
  the view's short reveal Timer calls `resolveMismatch` — the model is truth, the view animates toward it.
- **Determinism:** deal from an injected seeded `Random`; same seed → identical board (golden test).
- **Identity keys:** give each card widget a `ValueKey(card.id)`, never the list index.

## Genre specifics (what matters here)

- **Symbols differ by shape, not just color** — never color-alone (a child or a color-blind player
  must tell pairs apart).
- **Lock taps during the mismatch reveal** — the #1 bug; the `pendingMismatch` lock is the fix.
- **No-fail, gentle** — moves/time are a personal score, never a loss condition.
- **Reduce Motion** collapses the flip to instant.

## Genre checklist

- [ ] Two-up match rule with an input lock during the mismatch reveal; `dart test` covers it.
- [ ] Deal from an injected seeded `Random`; same seed → identical board (golden test).
- [ ] Cards differ by shape (not color alone); `Semantics` value per card (face down / symbol).
- [ ] `ValueKey(card.id)` on tiles; mismatch Timer disposed; Reduce Motion honored.
- [ ] No `package:flutter` in `models/`/`systems/`; win only when all matched.

## See also
- [`examples/memory_match/`](../../../../examples/memory_match) — the built, tested reference (copy it).
- [`references/game-templates.md`](../references/game-templates.md) — `memory-cards` recipe.
- [`workflows/create-new-game.md`](../workflows/create-new-game.md) · [`workflows/write-tests.md`](../workflows/write-tests.md).
