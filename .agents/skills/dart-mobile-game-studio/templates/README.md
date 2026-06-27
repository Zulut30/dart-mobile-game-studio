# Genre templates

Per-genre **design starting points**: a filled-in Mini-GDD + an architecture skeleton you copy and
adapt. They answer *"what am I building and how is it shaped"* — distinct from
[`references/game-templates.md`](../references/game-templates.md), which is the *implementation recipe*
(how to code it), and [`workflows/create-new-game.md`](../workflows/create-new-game.md), which is the
*process*. Pick a template, fill the brackets, then build against the recipe and the workflow.

| Template | Genre | Mode | Implementation recipe |
|---|---|---|---|
| [`casual.md`](casual.md) | tap/swipe, no-fail toy | widgets | `tap-reaction` |
| [`coloring.md`](coloring.md) | tap-to-fill regions | widgets | `coloring-shapes` |
| [`card.md`](card.md) | memory / matching / sorting | widgets | `memory-cards` (+ `examples/memory_match`) |
| [`puzzle.md`](puzzle.md) | sliding / jigsaw / logic | widgets | `drag-and-drop-puzzle`, `shape-matching` |
| [`platformer-flame.md`](platformer-flame.md) | run & jump | Flame (hybrid) | `simple-platformer` |
| [`endless-runner.md`](endless-runner.md) | auto-run, tap-to-jump | Flame (hybrid) | `endless-runner-lite` |
| [`quiz.md`](quiz.md) | question → answer | widgets | — (self-contained) |
| [`educational-kids.md`](educational-kids.md) | letters/numbers/shapes | widgets | — (kids bar binding) |
| [`ui-heavy.md`](ui-heavy.md) | menus/economy/progression | widgets + go_router | — (production-quality) |

## How to use

1. **Pick the closest template** to the request (the coordinator/`game-designer` does this at step 1).
2. **Fill its Mini-GDD brackets** with the actual game — that *is* the skill's step 2 GDD, specialized.
3. **Build to its architecture skeleton** — the pure-Dart core types + folders are the starting layout.
4. **Follow its recipe + workflow** links to implement, test, and review.

Every template enforces the same non-negotiables: pure-Dart core (no `package:flutter` in
`models/`/`systems/`), injected seeded `Random`, `Semantics`, kids-safety, and `dart test` coverage.
They are starting points, not finished games — adapt scope to the request.
