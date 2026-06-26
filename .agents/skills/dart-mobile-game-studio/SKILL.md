---
name: dart-mobile-game-studio
description: Build simple 2D mobile games in Flutter/Dart for iOS and Android — coloring books, jigsaw/sliding puzzles, light platformers, drag-and-drop puzzles, memory/matching card games, lite endless runners, tap-reaction, and educational mini-games. Use when a request involves Dart, Flutter, Flame, Forge2D, the Flutter Casual Games Toolkit, a mobile game, a kids/children's game, game architecture, level design, an asset pipeline, child-safety/privacy review (Apple Kids + Google Play Families), game testing, or `flutter`/`dart` build & test. Produces a Mini-GDD, an MVP, tests, and a review checklist.
---

# Dart Mobile Game Studio

Operational guide for building simple, polished 2D games for **iOS and Android** in Flutter/Dart.
You are the implementer: produce a working MVP, keep core logic testable, and finish with a
child-safety / privacy / accessibility / performance review and an honest handoff.

## When to use
Trigger on any 2D mobile game task: coloring, puzzles, platformers, drag-and-drop, memory/matching,
lite arcades, tap-reaction, or educational mini-games. Trigger on mentions of Dart, Flutter, Flame,
Forge2D, the Casual Games Toolkit, `flutter`/`dart` CLI, or "kids app".

## Supported stack & official sources
Dart · Flutter · **Flame** (2D game engine) · Forge2D (Box2D physics, optional) ·
`games_services` (Game Center / Play Games, optional) · `dart test` / `flutter_test` /
`integration_test` · `flutter`/`dart` CLI. Target: a single Flutter codebase shipping to **iOS and
Android**, portrait + landscape, phone + tablet, privacy-first defaults.

Ground decisions in the official org (https://github.com/orgs/flutter):
- **flutter/games** — the *Casual Games Toolkit* and gaming templates (app scaffolding, state,
  audio, settings, achievements, ads/IAP hooks). The canonical first-party reference.
- **flame-engine/flame** — the de-facto 2D engine (`FlameGame`, components, game loop, collisions).
- **flutter/samples**, **flutter/packages** — official examples and first-party packages.

## Execution workflow
Run these in order. Skip a step only with a stated reason.

1. **Understand the game request.** Genre, target age, core verb (tap / drag / match / move),
   win/lose vs no-fail, session length, platforms (iOS + Android), orientation.
2. **Generate a Mini-GDD.** Use `assets/gdd-template.md`. One page.
3. **Select implementation mode:**
   - **Flutter-widgets-only** — static/turn-based boards, coloring, memory, matching, drag-and-drop,
     tap-reaction. `CustomPainter`/`Canvas`, `AnimatedBuilder`, gestures. Simplest, most testable.
   - **Flame** — continuous motion, physics, sprites, particles: platformer, runner. `FlameGame`
     + components + game loop (`update`/`render`); Forge2D for real physics.
   - **Hybrid** — Flame gameplay embedded in a Flutter widget tree via `GameWidget`, with Flutter
     widgets for menus/HUD/settings. Default for action games that need real UI.
   See `references/flutter-game-architecture.md` and `references/flutter-flame-patterns.md`.
4. **Define architecture.** Separate **pure Dart logic** (model + rules + state machine, *no Flutter
   imports*) from rendering. The core is unit-tested with `dart test` — no device. Choose state
   management for the shell (`ValueNotifier`/`ChangeNotifier`, Provider, or Riverpod/Bloc) and keep
   it thin over the model.
5. **Implement the MVP.** Start from `assets/flame_game_template.dart` and/or
   `assets/flutter_game_widget_template.dart`. Small files, modular folders
   (`lib/models/`, `lib/systems/`, `lib/game/`, `lib/widgets/`, `assets/`). Recipes in
   `references/game-templates.md`. **Write excellent Dart** — meet the quality bar in
   `references/dart/README.md` and generate to the defaults in `references/common-pitfalls.md`
   (so the common Dart/Flutter/Flame bugs never land). Mirror the worked example in `examples/`.
6. **Add tests.** Cover the pure model: legal moves, scoring, win/lose, level loading, transitions,
   deterministic (seeded) shuffles/spawns. `dart test` for the core; `flutter_test` for widgets.
7. **Run build/test when available.** Use `scripts/verify-flutter-project.sh` to detect a project
   and run `dart analyze` + `dart test` (+ `flutter test`). If you cannot (no toolchain), say so and
   give the exact commands — do not claim it passed.
8. **Review.** Run `scripts/dart-doctor.py <project>`, then sweep `references/common-pitfalls.md` (the
   analyzer-invisible classes: layout constraints, Flame hot-path/lifecycle/collision, layering —
   tag findings by code + severity) and walk `assets/review-checklist.md`: child safety, privacy,
   accessibility, performance. See `references/accessibility-child-safety.md`.
9. **Handoff.** Report: what you built, chosen mode and why, **changed files**, **commands run with
   real output** (or why none ran), assumptions, open risks, next steps.

## Game templates
Pick the closest and adapt (full recipes in `references/game-templates.md`):
- `coloring-shapes` — tap-to-fill vector regions. Flutter-widgets-only (`CustomPainter`).
- `simple-platformer` — run/jump on platforms, simple physics. Flame (hybrid shell).
- `drag-and-drop-puzzle` — drag pieces to slots / snap-to-grid. Flutter-widgets-only (`Draggable`).
- `memory-cards` — flip-and-match pairs, no-fail. Flutter-widgets-only.
- `shape-matching` — match shape/color to target slot. Flutter-widgets-only.
- `endless-runner-lite` — auto-run, tap to jump. Flame (hybrid).
- `tap-reaction` — tap targets before they vanish. Flutter-widgets or Flame.

## Strict rules
- **No copyrighted assets.** Generate placeholder vector shapes (`CustomPainter`/`flutter_svg`) or
  use only user-owned assets. No third-party characters/logos/fonts/music/sprites.
- **Minimal dependencies.** Prefer Flutter SDK + Flame. Justify any other pub.dev package.
- **Testable core.** Game logic runs and is tested with `dart test`, outside Flutter/Flame.
- **Small, modular files;** prefer `const` constructors; many focused files.
- **Accessibility.** Wrap interactive controls in `Semantics` (label/value/button); honor text
  scaling, `MediaQuery.disableAnimations` / Reduce Motion, screen readers (TalkBack/VoiceOver).
- **Children's apps:** no tracking, no third-party analytics, no ads, no AdvertisingId/IDFA/GAID,
  no external links, no accounts, no dark patterns; offline-first; no personal data. Must satisfy
  **both** Apple Kids Category **and** Google Play Families policy.
- **No compliance guarantees.** Produce a checklist and a risk list, never "store-approved".

## Fallback behavior (defaults when details are missing)
Build a small polished MVP and document assumptions: ages 4–8, no-fail; support both orientations,
phone-first; **Flutter-widgets-only** unless the genre needs motion/physics (then Flame); bright
high-contrast placeholder vector art; gentle optional SFX with a mute toggle (off if unsure);
lightweight local persistence (`shared_preferences` or a JSON file) for progress only; no networking,
accounts, or analytics. State these in the Mini-GDD and handoff.

## Reference map
- `references/game-development-pipeline.md` — end-to-end process & the Mini-GDD step.
- `references/flutter-game-architecture.md` — modes, pure-Dart core, state management, layout.
- `references/flutter-flame-patterns.md` — Flame game loop/components/collisions, `GameWidget`,
  `CustomPainter` for widget-only games, input, embedding Flame in Flutter.
- `references/game-templates.md` — per-template recipes and pitfalls.
- `references/asset-pipeline.md` — placeholder art, asset bundling, audio, level data (JSON).
- `references/accessibility-child-safety.md` — Flutter `Semantics` + Apple Kids & Google Play Families.
- `references/testing-and-release.md` — `dart test`/`flutter test`, build & both-store release.
- `references/performance-checklist.md` — frame budget, `const`/`RepaintBoundary`, Flame perf, jank.
- `references/flutter-games-toolkit.md` — using the official flutter/games Casual Games Toolkit.
- `references/algorithms-for-games.md` — pure-Dart, deterministic game algorithms (pathfinding
  BFS/Dijkstra/A*, match-3, line-clears, maze/proc-gen, scoring, sliding-puzzle solvability).
- `references/ui-and-animations.md` — game screens (menu/start/win/settings/shop/onboarding),
  animated buttons & transitions, implicit/explicit/staggered animation, responsive + Material/Cupertino,
  reduce-motion gating.
- `references/production-quality.md` — production patterns distilled from Wonderous/flutter samples:
  structure, go_router navigation, responsive/adaptive, theming, state-at-scale, UX polish.
- `references/codegen-and-boilerplate.md` — when (and when not) to use build_runner / freezed /
  json_serializable / auto_route; generated-file policy; boilerplate guidance.
- `references/testing-e2e-patrol.md` — the full test pyramid incl. Patrol E2E (native dialogs,
  permissions, lifecycle); complements testing-and-release.md.
- `references/common-pitfalls.md` — **the review-&-generation catalog**: the top mistakes that break
  Dart/Flutter/Flame games, ranked P0–P3, with an error classifier (codes + severity), per-class
  tripwire/bad→good/AI-rule, a symptom→cause→fix matrix, generation defaults, and a built-in review
  prompt. Open it first when reviewing or debugging; generate to its defaults. The `code-reviewer` and
  `code-auditor` agents tag findings with its codes.

### Policies (the rules agents enforce) — `references/`
- `references/package-policy.md` — dependency decision order (SDK → official → Flame → mature → DIY) + justification.
- `references/quality-policy.md` — the production quality bar (layer separation, null-safety, dispose, tests).
- `references/monetization-policy.md` — ads/IAP/subscriptions with the kids-vs-13+ audience gate.
- `references/release-policy.md` — App Store + Google Play submission rules and rejection traps.

### Checklists (tick-lists a reviewer/agent runs) — `checklists/`
`dart-code-quality`, `flutter-ui-quality`, `game-architecture`, `flame-quality`, `performance`,
`accessibility`, `localization`, `monetization`, `app-store-release`, `google-play-release`, `testing`.

### Dart mastery (write excellent Dart) — `references/dart/`
- `references/dart/README.md` — index + the Dart quality bar (start here).
- `references/dart/dart-language-essentials.md`, `dart-async-isolates.md`, `dart-api-design.md`,
  `flutter-widgets-mastery.md`, `dart-memory-performance.md`, `dart-patterns-idioms.md`.

## Assets (copy & adapt)
`assets/gdd-template.md`, `assets/level-schema-template.json`, `assets/flame_game_template.dart`,
`assets/flutter_game_widget_template.dart`, `assets/seeded_random.dart`, `assets/analysis_options.yaml`,
`assets/review-checklist.md`, `assets/privacy-checklist.md`.

## Scripts
- `scripts/sync-skill.sh` — mirror canonical skill into `.claude/` and `.cursor/` (`--check` for CI).
- `scripts/verify-flutter-project.sh` — detect a Flutter/Dart project; run `dart analyze` + tests.
- `scripts/scaffold-game-module.py` — non-destructive buildable Dart package skeleton for a genre.
- `scripts/validate-skill.sh` — structural quality gate (frontmatter, sync, JSON, formats).
- `scripts/validate-levels.py` — validate level JSON against `level-schema-template.json`.
- `scripts/dart-doctor.py` — project health-check CLI (the analog of swift-doctor / `flutter doctor`
  for *project quality*): environment, architecture, Dart quality, performance, kids-safety,
  accessibility, assets/licensing, build/tests.

## Workflow playbooks — `workflows/`
Step-by-step recipes the agent executes top-to-bottom. Each file is a self-contained guide with
decision criteria, concrete commands, code snippets, and common pitfalls:

- `create-new-game.md` — full session: idea → GDD → scaffold → architecture decision → MVP.
- `choose-game-architecture.md` — Flutter-widgets vs Flame vs hybrid decision tree with
  tradeoff table, concrete checklist, and anti-patterns.
- `setup-flutter-project.md` — `flutter create` → analysis options → folder layout → CI stub.
- `setup-flame-project.md` — Flame dep → pubspec → FlameGame skeleton → dt clamping → first component.
- `add-game-loop.md` — world state, `update`/`render` cycle, frame-rate independence, pausing.
- `add-level-system.md` — JSON schema, `LevelRepository`, `LevelLoader`, level-select UI.
- `add-animations.md` — `AnimationController`/implicit animations, Flame sprite sheets, reduce-motion gate.
- `add-assets-pipeline.md` — `pubspec.yaml` assets declaration, `flutter_svg`, placeholder shapes, audio.
- `add-audio.md` — `flame_audio`/`audioplayers`, background music + SFX, mute toggle, lifecycle.
- `add-state-management.md` — `ValueNotifier`→ Provider → Riverpod progression, game-state binding.
- `add-navigation.md` — `go_router` setup, route table, deep-link guards, game-state handoff.
- `add-save-system.md` — `shared_preferences`/JSON file persistence, migration, encryption gate.
- `write-tests.md` — unit (pure Dart), widget, integration/Patrol; seeded RNG; golden tests.

## Worked example
- `examples/` — a complete, buildable & tested reference game: a pure Dart package core
  (`dart test`) plus a Flutter UI. Copy its architecture for new games.
