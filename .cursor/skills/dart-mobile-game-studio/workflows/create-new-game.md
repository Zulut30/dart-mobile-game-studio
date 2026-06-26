# Workflow: Create a New Game (end-to-end scaffold)

**Goal:** Take a user game prompt to a running, analyzer-clean Flutter project with a pure-Dart core, a base state machine, screens, an asset pipeline, tests, and a passing performance pass.

**When to use:** Any new mobile game build from a prompt. This is the §18.1 master flow; it **orchestrates** the other workflows — run it first, then branch into the linked ones.

**When NOT to use:** Editing an existing game (use the relevant feature workflow directly), or non-game Flutter apps.

**Prerequisites**
- `flutter --version` ≥ 3.x stable, `dart --version` present. Run `flutter doctor` and resolve iOS/Android toolchain blockers before scaffolding.
- Read these references before deciding architecture: [`references/flutter-game-architecture`](../references/flutter-game-architecture.md), [`references/game-templates`](../references/game-templates.md), [`references/package-policy`](../references/package-policy.md), [`references/quality-policy`](../references/quality-policy.md).
- Confirm target audience. If kids/families, [`references/accessibility-child-safety`](../references/accessibility-child-safety.md) is **binding** from step 0, not an afterthought.

> **Doctrine recap (non-negotiable):** pure-Dart core with **no `package:flutter` import**, tested by `dart test`; clamp `dt` yourself; inject a seeded `Random`; UI / business / game-logic separated; analyzer-clean; `dart format` (2-space); `const` everywhere; `dispose` everything; null-safe. No store-approval guarantees are ever made.

---

## STEP 1 — Determine the game type

Classify the prompt into a genre so you can pick the matching template brief in [`references/game-templates`](../references/game-templates.md):

| Signal in prompt | Likely genre | Template |
| --- | --- | --- |
| "color", "paint", "fill regions" | Coloring book | `game-templates#coloring` |
| "jigsaw", "sliding", "15-puzzle", "rearrange" | Puzzle (static board) | `game-templates#sliding-puzzle` |
| "match pairs", "memory", "flip cards" | Memory/matching | `game-templates#memory-match` |
| "drag X onto Y", "sort", "sorting" | Drag-and-drop | `game-templates#drag-drop` |
| "jump", "platform", "side-scroll" | Light platformer | `game-templates#platformer` |
| "runner", "endless", "dodge", "auto-run" | Lite endless runner | `game-templates#endless-runner` |
| "tap when", "reflex", "whack", "fast tap" | Tap-reaction | `game-templates#tap-reaction` |
| "quiz", "learn letters/numbers", "spelling" | Educational mini-game | `game-templates#edu-mini` |

**Output of this step:** one sentence — *"This is a `<genre>` game; core loop is `<one line>`."* If the prompt spans two genres, pick the dominant interaction and note the secondary as a stretch goal. Ambiguous prompt → ask one clarifying question, do not guess silently.

**Done when:** genre + one-line core loop are written down and a template brief is selected.

---

## STEP 2 — Decide Flame vs Flutter-widgets vs hybrid (decision rule)

Apply this rule top-to-bottom; **stop at the first match.**

1. **Continuous per-frame motion or physics?** (gravity, velocity, collisions, scrolling world, particles, anything needing a 60 fps `update(dt)`) → **Flame** (`FlameGame` + `GameWidget`). Endless runner, platformer, most tap-reaction-with-movement.
2. **Discrete, turn/tap-based state with NO frame loop?** (a move changes a model, UI rebuilds, then waits for input) → **Flutter widgets only.** Sliding puzzle, memory match, quiz, static coloring, drag-and-drop sorting. Cheaper, fully accessible via the widget tree, easiest to test.
3. **Discrete logic but a few animated/physical flourishes** (confetti, a bouncing tile, a timed reflex meter on an otherwise static board) → **Hybrid:** Flutter widget shell hosting a `GameWidget` for the animated surface, native widgets for menu/HUD/result. Use Flame `overlays` for the in-game HUD.

> Tie-breaker: if you can implement it with `AnimatedBuilder`/`AnimationController` and an occasional `Ticker` and it stays smooth, prefer **Flutter widgets** — fewer deps, better a11y out of the box. Reach for Flame only when you'd otherwise hand-roll a game loop. See [`references/flutter-flame-patterns`](../references/flutter-flame-patterns.md) for the Flame side and [`references/ui-and-animations`](../references/ui-and-animations.md) for the widget side.

**Mode-specific entry points (grounded):**
- *Flame:* `class MyGame extends FlameGame { ... }` then `runApp(GameWidget(game: MyGame()));`. Use a `World` + `CameraComponent.withFixedResolution(width: W, height: H)` for resolution independence.
- *Flutter widgets:* a `StatefulWidget` (or a state-management primitive per [`references/flutter-games-toolkit`](../references/flutter-games-toolkit.md)) owning an immutable model from the pure-Dart core.

**Done when:** mode is chosen with a one-line justification tied to rule 1/2/3.

---

## STEP 3 — Propose architecture (before any code)

Write a short architecture note (5–10 lines), grounded in [`references/flutter-game-architecture`](../references/flutter-game-architecture.md):

- **Core model types** — the pure-Dart state machine and entities (e.g. `GameState`, `Phase`, `Board`, `Tile`). No Flutter import. List the key types and the `Phase` enum values.
- **Systems** — pure functions/services operating on the model (scoring, win-check, level loading, RNG-driven spawning). All take an injected `Random`.
- **Rendering layer** — Flame components *or* widgets that read the model and render; hold zero rules.
- **Boundaries** — UI → calls intents → business/systems → mutate/return new model → UI rebuilds. One-directional.

**Done when:** the note names every core type, the `Phase` enum, and which layer owns each responsibility. Cross-check against the chosen template brief in [`references/game-templates`](../references/game-templates.md).

---

## STEP 4 — Create the project structure

Run `flutter create` with explicit org and the three mobile-first platforms. `--empty` avoids the counter-app boilerplate so `lib/main.dart` is a clean starting point.

```bash
flutter create \
  --org com.example \
  --project-name my_game \
  --platforms ios,android \
  --empty \
  my_game
cd my_game
```

> Notes: `--platforms` accepts `ios,android,web,linux,macos,windows`; keep it to the targets you actually ship. Project name must be `lowercase_with_underscores`. Add `web` only if a browser build is in scope. Verify with `flutter analyze` (should be clean on a fresh project).

Then create the standard game layout under `lib/` (and a top-level `test/`):

```bash
mkdir -p lib/models lib/systems lib/game lib/widgets lib/data \
         assets/images assets/audio assets/levels test/models test/systems
```

Layer responsibilities:

| Folder | Holds | Flutter import allowed? |
| --- | --- | --- |
| `lib/models/` | pure-Dart state machine, entities, immutable value types | **No** |
| `lib/systems/` | pure-Dart rules: scoring, win/lose, spawn, level parsing | **No** |
| `lib/game/` | Flame `FlameGame`/components (Flame mode/hybrid only) | yes |
| `lib/widgets/` | screens, HUD, buttons, overlays | yes |
| `lib/data/` | level/asset loading glue (rootBundle, JSON decode) | yes |
| `assets/` | images, audio, level JSON | n/a |
| `test/` | `dart test` units mirror `models/` + `systems/` | no (test core w/o Flutter) |

**Pitfall:** keep the pure-Dart core importable by `dart test` without a Flutter runtime — any stray `package:flutter` import in `models/`/`systems/` breaks that and the doctrine. Add a CI/lint guard (see [`references/codegen-and-boilerplate`](../references/codegen-and-boilerplate.md)).

**Done when:** `flutter analyze` is clean, the folders exist, and `lib/main.dart` is minimal.

---

## STEP 5 — Configure minimal dependencies

Default to **zero** non-Apple/Flutter-core packages. Add only what the mode demands, and justify each against [`references/package-policy`](../references/package-policy.md).

- **Flame mode:** add `flame` (the engine). That is usually the *only* runtime add.
- **Flutter-widgets mode:** typically **none** — `flutter` SDK covers it. A small state primitive (e.g. `provider`/`flutter_riverpod`) is allowed only if the architecture note justifies it.
- **Audio:** add an audio package (e.g. `flame_audio` for Flame, or a vetted SFX package) **only if** the prompt needs sound.
- **Dev deps:** keep `flutter_lints` (or `very_good_analysis`); add `flame_test` for Flame game-loop tests; `dart test` is built in for the pure core.

```bash
# Flame example:
flutter pub add flame
flutter pub add dev:flame_test
```

> Rule: every dependency line gets a one-clause justification in the handoff. No analytics, ads, tracking, or networking SDKs in kids titles (per [`references/monetization-policy`](../references/monetization-policy.md) and [`references/accessibility-child-safety`](../references/accessibility-child-safety.md)). Prefer Apple/Flutter frameworks; pin versions; run `flutter pub outdated` before release.

**Done when:** `pubspec.yaml` lists only justified deps and `flutter pub get` succeeds.

---

## STEP 6 — Add base screens (menu / play / pause / result)

Every game ships these four surfaces. Build them as widgets even in Flame mode (Flame surfaces only the play canvas; menu/pause/result are widgets or Flame `overlays`). Pattern from [`references/ui-and-animations`](../references/ui-and-animations.md):

- **MenuScreen** — title, Play, (Settings, How-to-play). Entry route.
- **PlayScreen** — the game surface. Widgets mode: hosts the board/canvas. Flame mode: hosts `GameWidget` with `overlayBuilderMap` for HUD.
- **PauseScreen / Pause overlay** — resume, restart, quit-to-menu. In Flame, drive with `pauseEngine()`/`resumeEngine()` and an overlay.
- **ResultScreen** — win/lose, score, replay, menu. Reads the final model; never recomputes rules.

**Flame HUD/overlay wiring (grounded):** register overlays in `GameWidget(overlayBuilderMap: {...})`, then from game logic call `overlays.add('PauseMenu')`, `overlays.remove('PauseMenu')`, `overlays.toggle(...)`, `overlays.isActive(...)`. Pair `overlays.add('PauseMenu')` with `pauseEngine()` (and `resumeEngine()` on remove) so the loop actually stops.

**Accessibility from the first screen:** every interactive control gets a `Semantics` label; respect Dynamic Type and Reduce Motion. See [`references/accessibility-child-safety`](../references/accessibility-child-safety.md).

**Done when:** you can navigate menu → play → pause → result → menu, even with placeholder content.

---

## STEP 7 — Add the game state machine

Implement the phase machine in the **pure-Dart core** (`lib/models/`), driven from [`references/flutter-game-architecture`](../references/flutter-game-architecture.md). Canonical phases:

```dart
enum GamePhase { menu, playing, paused, win, lose }
```

Transition table (adapt per genre):

| From | Event | To |
| --- | --- | --- |
| `menu` | startGame | `playing` |
| `playing` | pause | `paused` |
| `paused` | resume | `playing` |
| `playing` | winCondition | `win` |
| `playing` | loseCondition | `lose` |
| `win` / `lose` | replay | `playing` |
| any | quitToMenu | `menu` |

Rules:
- The model owns the current phase; UI/Flame read it and render. Transitions are pure functions returning a new state (or mutating a controller), never side-effecting the UI directly.
- **Frame loop (Flame mode):** in `update(dt)`, **clamp `dt` yourself** (e.g. `final step = dt.clamp(0.0, 1 / 30);`) before advancing physics, to survive frame hitches/backgrounding. Do not advance the model while `phase == paused`.
- **RNG:** inject a seeded `Random` into every system that needs randomness (spawn, shuffle, deal) — see [`assets/seeded_random.dart`](../assets/seeded_random.dart). Determinism makes tests reproducible.
- Map UI/engine pause to the phase: widget Pause button → `pause` event; Flame → also `pauseEngine()`.

**Done when:** every transition in the table is unit-tested in `dart test` against the pure model (no Flutter), and illegal transitions are rejected.

---

## STEP 8 — Add the assets pipeline

Follow [`references/asset-pipeline`](../references/asset-pipeline.md). No copyrighted material — placeholder vector shapes / generated art / user-owned assets only. Levels are **data (JSON)**, not code.

1. Drop files into `assets/images`, `assets/audio`, `assets/levels`.
2. Declare them in `pubspec.yaml`:
   ```yaml
   flutter:
     assets:
       - assets/images/
       - assets/audio/
       - assets/levels/
   ```
3. **Loading:**
   - *Flame:* `Flame.images.load('sprite.png')` / `Sprite.load('sprite.png')` (Flame resolves under `assets/images/` by convention).
   - *Widgets/levels:* `rootBundle.loadString('assets/levels/level_01.json')` then decode in `lib/data/` into pure-Dart level objects consumed by `lib/systems/`.
4. **Level schema:** define a versioned JSON shape; parse in a pure-Dart loader so level logic is unit-testable without Flutter. Validate on load (fail loudly on malformed data).

**Pitfall:** large/unoptimized PNGs blow the texture budget. Right-size art and prefer vector/`CustomPainter` placeholders where possible (also helps Reduce Motion / scaling).

**Done when:** at least one real level loads from JSON and renders, and asset declarations match the files on disk.

---

## STEP 9 — Add tests

Test the pure core hard; smoke-test the rendering layer. Detailed patterns in [`references/testing-and-release`](../references/testing-and-release.md); E2E in [`references/testing-e2e-patrol`](../references/testing-e2e-patrol.md).

- **Unit (`dart test`, no Flutter)** — the bulk. Cover: state-machine transitions (Step 7), win/lose detection, scoring/economy, level parsing/validation, and RNG-seeded systems (assert deterministic output for a fixed seed).
- **Widget (`flutter test`)** — screens render, buttons fire intents, navigation menu→play→pause→result works, `Semantics` labels present.
- **Flame (`flame_test`)** — game-loop behavior: components load, `update(dt)` advances state, collisions/spawns fire. Use the package's game-test harness to pump frames.
- **E2E (optional, Patrol)** — full playthrough on device/emulator for the headline flow; see [`references/testing-e2e-patrol`](../references/testing-e2e-patrol.md).

Run:
```bash
dart test          # pure core
flutter test       # widget + flame tests
flutter analyze    # must be clean
dart format --set-exit-if-changed .   # 2-space, enforced
```

**Done when:** all four commands pass and core logic has meaningful (not trivial) coverage. **Report honestly** — only claim a suite passed if you ran it and saw the output.

---

## STEP 10 — Run the performance checklist

Walk [`references/performance-checklist`](../references/performance-checklist.md) and the gate in [`checklists/`](../checklists/). Headline items:

- Profile in **profile mode** on a real device: `flutter run --profile`; check DevTools timeline for jank (target 60 fps; no frames > 16 ms sustained).
- `dt` is clamped; no work proportional to frame count leaks across pause/background.
- No per-frame allocations in `update()`/`build()` (no `new` Vector2/list churn in hot paths); reuse objects.
- Dispose every `AnimationController`, `Ticker`, stream, and Flame component; verify no leaks on screen exit.
- Asset/texture budget respected (Step 8); audio preloaded, not loaded mid-loop.
- `const` constructors everywhere they apply; `flutter analyze` clean confirms.

**Done when:** profile-mode run shows a steady frame budget for the core loop and the performance checklist items are all checked or explicitly waived with a reason.

---

## Master "done when" (whole workflow)
1. Genre + mode chosen with written justification (Steps 1–2).
2. Architecture note exists; pure-Dart core has **no** Flutter import (Steps 3–4).
3. Deps minimal and justified; `flutter pub get` clean (Step 5).
4. menu→play→pause→result navigation works (Step 6).
5. Phase machine implemented and fully unit-tested (Step 7).
6. ≥1 JSON level loads and renders; assets declared (Step 8).
7. `dart test`, `flutter test`, `flutter analyze`, `dart format` all pass — with real output captured (Step 9).
8. Profile-mode performance pass complete (Step 10).

## Handoff
Finish with: what was built, **mode chosen and why**, changed files, **commands run + real output** (or why none ran), dependencies + justifications, kids-safety status, assumptions, open risks/next steps. **No store-approval or compliance guarantees** — provide the [`checklists/`](../checklists/) results and a risk list instead. See [`references/release-policy`](../references/release-policy.md).

## Common pitfalls
- **Choosing Flame for a turn-based puzzle** — you inherit a game loop you don't need and worse a11y. Re-check Step 2 rule 2.
- **Leaking Flutter into the core** — `models/`/`systems/` must stay `dart test`-able; one `package:flutter` import breaks the doctrine.
- **Unclamped `dt`** — a single long frame (backgrounding) tunnels the player through walls or skips spawns. Clamp every loop.
- **Unseeded `Random`** — non-deterministic tests and unbalanceable difficulty. Always inject.
- **Levels as code** — hard to test and balance. Keep them JSON in `assets/levels/`, parsed by a pure loader.
- **Forgetting `dispose`** — controllers/tickers/components leak and tank performance; the perf checklist catches it only if you run it.
- **Copyrighted assets** — never. Placeholders, generated, or user-owned only.

## See also
- [`workflows/`](.) — the per-genre and per-system workflows this one orchestrates (build the model, add Flame loop, wire input, ship release).
- [`references/quality-policy`](../references/quality-policy.md), [`references/production-quality`](../references/production-quality.md) — the bar every step is held to.
