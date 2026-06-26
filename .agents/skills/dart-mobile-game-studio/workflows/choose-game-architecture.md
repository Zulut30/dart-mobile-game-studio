# Workflow: Choose Game Architecture

**Goal:** Given a game prompt, pick the smallest correct architecture (pure Flutter UI → CustomPainter → Flame → +backend / +BaaS / offline-first) and lock the pure-Dart-core seam *before* writing UI code.

## When to use
- First decision on **every** new game, before scaffolding (`workflows/scaffold-new-game.md`).
- Re-run when a prompt adds a new axis: real-time motion, online/multiplayer, leaderboards, accounts, or server-authoritative scoring.
- Implements §18.2 (architecture decision tree).

## Prerequisites
- Read `references/flutter-game-architecture.md` (the layering doctrine) and `quality-policy.md`.
- One-line problem statement: genre + the three inputs below answered.
- For any dependency you'll add: `package-policy.md`. For anything online: `monetization-policy.md` + `accessibility-child-safety.md` (kids = Apple Kids + Google Play Families).

## The three inputs (answer before deciding)
1. **Motion/physics?** Does the screen animate every frame from a simulation (gravity, velocity, collisions, particles, a scrolling world, a continuous timer the player reacts to)? — vs. discrete state that only changes on tap/drag.
2. **Online?** Does correctness or the experience need another device/server *now* (realtime multiplayer, server-authoritative score, remote content, cross-device sync)? — vs. fully local.
3. **Data?** What must outlive the session and how much: nothing / a few key-values (settings, best score, progress) / structured rows queried & sorted (level packs, large save, history)?

> Default posture: **offline-first, widgets-only.** Escalate one rung at a time and only when an input forces it. Every rung still keeps the same pure-Dart core seam — you are choosing a *renderer and an edge*, not a new core.

---

## STEPS

### STEP 1 — Decide the RENDERER from the Motion/physics input

```
Motion/physics every frame?
├─ NO  → discrete, event-driven state
│        ├─ Layout is standard widgets (lists, grids, cards, buttons)?
│        │        → (A) Pure Flutter widgets        ← DEFAULT
│        └─ Need free-form 2D drawing each state (board lines, coloring
│           canvas, hand-drawn shapes, simple tween animations)?
│                 → (B) Flutter + CustomPainter
└─ YES → continuous game loop with dt
         ├─ Light/occasional motion, few moving things, no real physics
         │  (one falling tile, a tween, a progress sweep)?
         │        → (B) CustomPainter driven by Ticker  (stay in widgets)
         └─ Many entities, a game world, collisions, particles, sprites,
            or you'd hand-roll a component tree / collision system?
                  → (C) Flutter + Flame (FlameGame + GameWidget)
```

- **(A) Pure Flutter widgets** — turn-based & static: memory/match, quiz, word, board (tic-tac-toe, 2048-style grids), sliding-tile, sudoku, settings-driven puzzles. Animate with `AnimatedFoo`/`ImplicitlyAnimatedWidget`/`AnimationController`. Cheapest to build, test, and make accessible. See `references/ui-and-animations.md`.
- **(B) Flutter + CustomPainter** — discrete state but bespoke pixels: coloring book, drawing/tracing, connect-the-dots, simple maze, jigsaw outlines, a custom game board. A `CustomPainter` reads model state and paints; for light motion drive `repaint` from an `AnimationController`/`Ticker`. Still "widgets-only" for deps. See `references/ui-and-animations.md` (CustomPainter section).
- **(C) Flutter + Flame** — real loop & many entities: endless runner, platformer, top-down, shooter, physics toys, anything spritey or collidey. `GameWidget` is the bridge that places a `FlameGame` (or low-level `Game`) into the Flutter tree, so you keep real Flutter menus/HUD around it (hybrid `GameWidget`). `FlameGame` gives you `update(double dt)` / `render(Canvas)`, the component tree (FCS), and collision detection. See `references/flutter-flame-patterns.md` and `assets/flame_game_template.dart`. *(Flame `GameWidget`/`FlameGame`/`update(dt)`/`render(canvas)`, collision system, and `pauseWhenBackgrounded` are documented Flame APIs — flame-engine/flame docs.)*

> **Do not reach for Flame for a static game.** A grid/board with tap handlers is widgets-only. Flame buys you a loop and a component/collision system; if you have no loop, it's pure cost.

### STEP 2 — Decide DATA persistence from the Data input
Pick the **smallest** store that fits; this is orthogonal to the renderer.

| Need | Use | Notes |
|---|---|---|
| Nothing persists | in-memory only | core holds it; nothing to add |
| A few primitives (settings, best score, last level, mute) | `shared_preferences` | key/value; justify per `package-policy.md` |
| Structured/queried local data (level packs, large save, run history, inventory) | local DB (`sqflite` or `drift`/`isar`) | justify the dep; keep DB code behind a `repository` interface so the core never imports it |
| Bundled, read-only content (levels, words, puzzles) | JSON/asset files via `rootBundle` | ship as assets, parse into pure-Dart models; see `references/asset-pipeline.md` |

Keep persistence behind a **`Repository` port** the core depends on by interface only (see STEP 5). Default to offline-first regardless of the Online answer.

### STEP 3 — Decide the ONLINE edge from the Online input
Default is **no edge** (offline-first). Escalate only if input #2 is YES.

```
Online needed?
├─ NO  → OFFLINE-FIRST (default). All state local. No network code.       ← DEFAULT
└─ YES → what kind?
         ├─ Read-only remote content / occasional config / simple
         │  submit-score where you control nothing else
         │        → Flutter + your own backend over HTTPS (`http`/`dio`)
         │          behind a RemoteSource port. App still runs offline;
         │          network is an enhancement, never the source of truth
         │          for local play.
         ├─ Auth + sync + leaderboards + realtime, you don't want to run
         │  a server
         │        → Flutter + BaaS (Firebase or Supabase) behind a port.
         │          Pick ONE; justify in package-policy. Heavy dep — only
         │          if multiplayer/cross-device/leaderboards are core.
         └─ Server-authoritative realtime multiplayer
                  → Flutter + backend you run (websockets/state on server).
                    Client is a thin view of server state. Rarely needed
                    for "simple 2D mobile games" — push back / descope to
                    async leaderboards first.
```

**Online guardrails (do all):**
- Game must remain **fully playable offline**; network failures degrade gracefully (queue, cache, retry), never block local play.
- Put every remote call behind a `RemoteSource`/`SyncService` **port**; mock it in tests so the core stays `dart test`-only.
- **Kids apps** (Apple Kids Category / Google Play Families): NO third-party analytics/ads SDKs, no account-required gating of core play, no personal data, parental gate for any external link/purchase. A BaaS/backend here is a compliance surface — review against `accessibility-child-safety.md` and `monetization-policy.md` *before* adding the dep.
- Adding Firebase/Supabase/a backend is an architecture change → re-run `package-policy.md` and note the justification in the handoff.

### STEP 4 — Compose the verdict
State it as a tuple: **Renderer (A/B/C) + Data store + Edge (offline-first | own-backend | BaaS | server-authoritative)**, each with one sentence of *why*, tied back to the three inputs.

Worked examples:
- *Memory match, best score saved, no online* → **A (widgets) + shared_preferences + offline-first.** No loop, trivial KV, no network.
- *Coloring book, save artwork, no online* → **B (CustomPainter) + local files/JSON + offline-first.** Bespoke canvas, blob save, local.
- *Endless runner, local high scores* → **C (Flame, hybrid GameWidget) + shared_preferences/sqflite + offline-first.** Real loop + entities; scores local.
- *Endless runner + global leaderboard* → **C (Flame) + local DB + BaaS-behind-a-port.** Loop needs Flame; leaderboard is the only online piece, isolated behind a port; still playable offline.

### STEP 5 — Lock the pure-Dart-core SEAM (do this for EVERY verdict)
The architecture choice must not leak into the core. Enforce the layering before scaffolding:

- **Core = pure Dart.** All rules, state machine, scoring, level logic in `lib/game/` (or `lib/src/core/`) with **no `package:flutter` import** and **no Flame/`dart:ui` import** in the rule code. Verify: `grep -rEn "import 'package:flutter|import 'package:flame|import 'dart:ui'" lib/<core_dir>/` returns nothing. Tested with `dart test` (no widget/Flame harness).
- **Determinism:** inject a seeded `Random` (`Random(seed)`) — never call global `Random()` / `DateTime.now()` inside rules. See `assets/seeded_random.dart` and `references/algorithms-for-games.md`.
- **Own your dt:** the renderer (Ticker for B, `FlameGame.update(dt)` for C) **clamps `dt`** before handing it to the core (e.g. `dt = dt.clamp(0, 1/30)`), and the core advances logic deterministically. This matters because a large `dt` after a background/resume causes physics tunnelling and missed collisions (documented Flame behaviour); also handle the lifecycle (`pauseEngine`/`resumeEngine`, or `pauseWhenBackgrounded`). See `references/performance-checklist.md`.
- **Ports for every edge:** persistence (`Repository`), remote (`RemoteSource`/`SyncService`), platform (audio/haptics) are **abstract interfaces in/near the core; concrete impls live in outer layers** and are dependency-injected. The core depends on interfaces only, so swapping shared_preferences↔sqflite, or offline↔BaaS, never touches rules or tests.
- **Three layers stay separate** (per doctrine): **UI** (widgets/screens) · **business/state** (controllers, view-models, repositories) · **game-logic** (pure core). Data flows UI→business→core; core returns plain Dart.

Result: the same core powers (A), (B), or (C) and offline or online — you only swap the outer renderer and edge adapters.

---

## Cross-links
- Layering & doctrine: `references/flutter-game-architecture.md`
- Renderer specifics: `references/flutter-flame-patterns.md` (C), `references/ui-and-animations.md` (A/B)
- Per-genre briefs (pick after the verdict): `references/game-templates.md`
- Determinism & loop math: `references/algorithms-for-games.md`, `assets/seeded_random.dart`
- Loop/lifecycle/perf: `references/performance-checklist.md`
- Templates to copy: `assets/flame_game_template.dart` (C), `assets/flutter_game_widget_template.dart` (hybrid)
- Data/assets: `references/asset-pipeline.md`
- Deps & policy: `package-policy.md`, `quality-policy.md`, `monetization-policy.md`, `release-policy.md`
- Kids safety (any online/BaaS edge): `references/accessibility-child-safety.md`, `checklists/` (child-safety, release)
- Tests for each layer: `references/testing-and-release.md`, `references/testing-e2e-patrol.md`
- Next step: `workflows/scaffold-new-game.md`

## Done when
- The three inputs (motion/physics, online, data) are explicitly answered in one line each.
- A verdict tuple is recorded: **Renderer + Data store + Edge**, each with a one-sentence justification tracing to an input.
- The default (offline-first, widgets-only) was the starting point and every escalation is justified by an input — not by habit.
- Every escalation past pure-widgets/offline-first names the dep and is checked against `package-policy.md` (+ child-safety if kids/online).
- The pure-Dart-core seam is specified: core dir with **no flutter/flame/dart:ui imports**, seeded `Random`, clamped `dt`, and abstract ports for persistence/remote/platform — ready for `dart test`.

## Common pitfalls
- **Reaching for Flame because "it's a game."** No frame loop ⇒ no Flame. Static/turn-based = pure widgets.
- **Choosing online/BaaS up front.** Start offline-first; add an edge only when an input demands it, always behind a port, always still-playable-offline.
- **Leaking the renderer into the core** — `import 'package:flutter'`/`package:flame`/`dart:ui` in rule code. The core must compile and test with plain `dart test`.
- **Unclamped `dt`.** Passing the raw frame delta after a resume/stall breaks physics (tunnelling) and determinism; clamp in the renderer before the core sees it.
- **Non-deterministic core** — global `Random()`/`DateTime.now()` in rules makes tests flaky; inject a seeded `Random`.
- **No persistence port.** Calling `shared_preferences`/sqflite/Firebase directly from widgets or core couples you to that store and blocks `dart test`; hide it behind a `Repository`.
- **Over-engineering the data tier** — reaching for a DB for two settings (use `shared_preferences`) or hardcoding bundled levels in Dart instead of JSON assets.
- **Kids-safety afterthought.** Deciding the online edge without checking Apple Kids / Google Play Families rules first; an analytics/ads SDK or account-gate can sink the release.
