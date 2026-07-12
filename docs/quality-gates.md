# Quality gates

Production readiness is evidence-based. A passing structural check does not
substitute for compiler, device, or store evidence.

## Pull request CI

| Gate | Evidence |
|---|---|
| Structure | Frontmatter, JSON, script syntax, exact skill and agent mirrors |
| CLI contracts | Black-box safety, exit-code, schema, scaffold, and rollback tests on Linux and macOS |
| AI routing | 52 RU/EN scenarios, all critical cases, all workflows, all agents |
| Generated contracts | Fresh pure-Dart, widgets, Flame, and scaffold packages compile and test |
| Reference games | Format, analyze, VM core tests, Flutter widget and accessibility tests |

Run the main local gate with:

```bash
.agents/skills/dart-mobile-game-studio/scripts/validate-skill.sh
```

## Release evidence

The release canary creates platform runners outside the repository and verifies:

- Android AAB for `memory_match`;
- Android AAB for `endless_runner`;
- unsigned iOS release app for `memory_match`;
- unsigned iOS release app for `endless_runner`.

The tag-driven release workflow repeats these builds before publishing archives.

## Static doctors

`dart-doctor.py` checks architecture, Dart quality, performance signals,
kids-safety, accessibility, asset licensing, environment, and build evidence.

`design-doctor.py` checks screen-state coverage, semantics, Reduce Motion,
responsive layout, visual states, Flame overlays, kids UX, and accessibility
test hooks.

These tools inspect code and project structure. They do not replace visual or
runtime inspection.

## Manual release checks

The release owner still verifies:

- phone and tablet layouts in portrait and landscape;
- VoiceOver and TalkBack navigation;
- 200% text scaling, contrast, and tap targets;
- frame pacing and memory on the oldest supported device;
- app background/foreground, interruption, and audio behavior;
- ownership and license evidence for every shipped asset;
- signing, privacy labels, data safety, age rating, and store metadata.

No document or automated check in this repository is a guarantee of store
approval.
