# AGENTS.md

Guidance for coding agents (Codex and any AGENTS.md-aware tool) working in this repo.

## Primary skill
For any Dart / Flutter **mobile game** task (iOS + Android), use the **`dart-mobile-game-studio`**
skill. Canonical location:
[`.agents/skills/dart-mobile-game-studio/SKILL.md`](.agents/skills/dart-mobile-game-studio/SKILL.md).
It covers simple 2D games: coloring, puzzles, platformers, drag-and-drop, memory/matching, lite
runners, tap-reaction, and educational mini-games.

Read SKILL.md first, then follow its workflow: understand → Mini-GDD → pick mode (Flutter-widgets /
Flame / hybrid) → architecture → MVP → tests → build/test → review (kids/privacy/a11y/perf) → handoff.
Ground decisions in the official Flutter org — **flutter/games** (Casual Games Toolkit) and
**flame-engine/flame**. Deep-dive references in `references/` (+ `references/dart/` for Dart mastery),
templates in `assets/`, scripts in `scripts/`.

## Subagents (14 specialist roles)
For larger work, play the roles in `.agents/agents/` ("act as the <role> agent"):
- **Build:** `game-coordinator` → `game-designer` → `engine-architect` → `gameplay-programmer`
  (+ `art-director`, `narrative-writer`, `balance-economist`) → `qa-tester`.
- **Review & audit (read-only):** `code-reviewer` (diff/PR) + the pre-release gate `code-auditor`,
  `security-auditor`, `performance-auditor`, `legal-compliance`.
- **Release:** `release-engineer` — App Store **and** Google Play readiness.
See `.agents/agents/README.md`.

## Build & test command discovery
Do not assume commands — discover them:
1. Run `.agents/skills/dart-mobile-game-studio/scripts/verify-flutter-project.sh` to detect a
   project and run a safe `dart analyze` + `dart test`.
2. Common commands:
   ```bash
   dart pub get            # or: flutter pub get
   dart analyze
   dart test               # pure-Dart core tests (VM, fast, no device)
   flutter test            # widget/golden tests
   flutter build appbundle # Android release
   flutter build ipa       # iOS release
   ```
3. **Honesty rule:** only report analyze/build/tests as passing if you actually ran them and saw it.
   If you can't run here, say so and provide the exact commands.

## Coding standards
- **Separate logic from rendering.** Game rules live in pure Dart (no `package:flutter` imports) so
  they are unit-tested with `dart test`. Widgets / Flame `FlameGame`s are thin.
- **State machine:** menu → playing → paused → win/lose → menu (sealed classes / enums).
- **Small, modular files;** `lib/models/ lib/systems/ lib/game/ lib/widgets/ assets/ test/`. Prefer
  `const` constructors; dispose controllers/notifiers.
- **Tests** for the model: legal moves, scoring, win/lose, level loading, transitions; seed RNG for
  deterministic shuffles/spawns. `dart test` for the core, `flutter_test` for widgets.
- **No copyrighted assets.** Placeholder vector art (`CustomPainter`/`flutter_svg`) or user-owned only.
- **Minimal dependencies** — Flutter SDK + Flame preferred; justify any other pub.dev package.
- **Accessibility** via `Semantics` on every interactive control; text scaling; reduce motion.
- **Children's apps:** no tracking/analytics/ads/AdvertisingId/external-links/accounts; offline-first;
  no personal data; minimal permissions. Must satisfy **both** Apple Kids and Google Play Families.
- **No store-compliance guarantees.** Produce checklists and risks.

## Handoff format
End with: what was built, mode and why, **changed files**, **commands run + real output** (or why
none ran), assumptions, and open risks/next steps.
