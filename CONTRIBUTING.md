# Contributing

Thanks for improving Dart Mobile Game Studio. Contributions should preserve the
skill's core promises: testable pure-Dart game logic, thin Flutter/Flame
renderers, deterministic behavior, accessibility, and honest release evidence.

## Before you start

1. Search existing issues and discussions.
2. Open an issue for broad behavior changes or new dependencies.
3. Keep edits canonical: change `.agents/` first, then regenerate mirrors.
4. Never add copyrighted game art, fonts, music, characters, or logos.

## Development workflow

```bash
git clone https://github.com/Zulut30/dart-mobile-game-studio.git
cd dart-mobile-game-studio
git switch -c feature/short-description

.agents/skills/dart-mobile-game-studio/scripts/sync-skill.sh
python3 .agents/agents/sync-agents.py
.agents/skills/dart-mobile-game-studio/scripts/validate-skill.sh
```

For changes affecting the examples, also run:

```bash
cd examples/memory_match && flutter analyze --fatal-infos && flutter test
cd ../endless_runner && flutter analyze --fatal-infos && flutter test
```

## Pull requests

- Explain the user impact and why the change belongs in the skill.
- List the real commands you ran and their results.
- Update documentation, tests, mirrors, and `CHANGELOG.md` when behavior changes.
- Keep generated `.claude/`, `.cursor/`, and `.codex/` copies synchronized.
- Call out manual device checks and unresolved release risks explicitly.

By contributing, you agree that your contribution is licensed under the MIT
License in this repository.
