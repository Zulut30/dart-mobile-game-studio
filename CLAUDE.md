# CLAUDE.md

Guidance for Claude Code working in this repository.

## Primary skill
For any Dart / Flutter **mobile game** task (iOS + Android), use the **`dart-mobile-game-studio`**
skill — invoke it as `/dart-mobile-game-studio`. It is installed at
[`.claude/skills/dart-mobile-game-studio/SKILL.md`](.claude/skills/dart-mobile-game-studio/SKILL.md)
and mirrored from the canonical source at
[`.agents/skills/dart-mobile-game-studio/`](.agents/skills/dart-mobile-game-studio/).

The skill covers simple 2D games: coloring, jigsaw/sliding puzzles, light platformers, drag-and-drop,
memory/matching, lite endless runners, tap-reaction, and educational mini-games. Read its SKILL.md and
follow the execution workflow before writing code. Ground decisions in the official Flutter org —
**flutter/games** (Casual Games Toolkit) and **flame-engine/flame**.

## Subagents (14 specialist roles)
Fourteen project subagents live in `.claude/agents/` (generated from canonical specs in
`.agents/agents/`). Invoke one with `@<name>` or just describe the need and let Claude route.
- **Build:** `game-coordinator` (PM/decompose) → `game-designer` → `engine-architect` →
  `gameplay-programmer` (+ `art-director`, `narrative-writer`, `balance-economist` in parallel) → `qa-tester`.
- **Review & audit (read-only):** `code-reviewer` (diff/PR), and the pre-release gate —
  `code-auditor` (whole codebase), `security-auditor`, `performance-auditor`, `legal-compliance`.
- **Release:** `release-engineer` — App Store **and** Google Play submission readiness.

Subagents can't spawn each other, so `game-coordinator` returns a delegation plan. See
`.agents/agents/README.md`.

## Source of truth & sync
- **Canonical skill:** `.agents/skills/dart-mobile-game-studio/`. Edit it there.
- **Canonical agents:** `.agents/agents/`. Edit there, then regenerate tool copies.
- After editing, mirror into tool copies:
  ```bash
  .agents/skills/dart-mobile-game-studio/scripts/sync-skill.sh   # skill -> .claude/.cursor
  .agents/agents/sync-agents.py                                  # agents -> .claude/.cursor
  ```

## Project conventions
- **Logic vs rendering:** pure Dart model (no `package:flutter` imports) holds all rules and is
  unit-tested with `dart test`; Flutter widgets and Flame `FlameGame`s stay thin.
- **State machine:** menu → playing → paused → win/lose → menu (sealed classes / enums).
- **Layout:** `lib/models/ lib/systems/ lib/game/ lib/widgets/ assets/ test/`. Small, focused files;
  prefer `const` constructors.
- **Mode choice:** Flutter-widgets-only for static/turn-based; Flame for motion/physics; hybrid
  (`GameWidget` + overlays) for action games that also need real menus/HUD.
- **Assets:** no copyrighted material — placeholder vector art (`CustomPainter`/`flutter_svg`) or
  user-owned assets only. Levels as JSON data, not code.
- **Dependencies:** Flutter SDK + Flame preferred; justify any other pub.dev package.
- **Accessibility:** `Semantics` (label/value/button) on every interactive control; text scaling;
  reduce motion; TalkBack + VoiceOver.
- **Kids apps:** no tracking/analytics/ads/AdvertisingId/external-links/accounts; offline-first; no
  personal data; minimal permissions (no Android `INTERNET` if offline); parental gate for sensitive
  actions. Must satisfy **both** Apple Kids Category and Google Play Families policy.

## Verification expectations
- Discover commands with `scripts/verify-flutter-project.sh`; build/test with `dart analyze`,
  `dart test`, `flutter test`, `flutter build appbundle`/`ipa` when a project + toolchain exist.
- **Report honestly.** Only claim analyze/build/tests passed if you ran them and saw the output. If
  you can't run here (no toolchain), state that and give the exact commands.
- Run `scripts/dart-doctor.py <project>` and `assets/review-checklist.md` before handoff.
  **No store-compliance guarantees** — provide a checklist and a risk list instead.

## Handoff format
Finish with: what was built, mode chosen and why, **changed files**, **commands run + real output**
(or why none ran), assumptions, and open risks/next steps.
