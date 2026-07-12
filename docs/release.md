# Release process

This document is for maintainers publishing the skill itself. Downstream game
release instructions live in the skill's iOS and Android workflows.

## Versioning

The project follows Semantic Versioning:

- patch: documentation, checks, and compatible fixes;
- minor: new workflows, genres, templates, or compatible agent behavior;
- major: installation layout, canonical contracts, or behavior requiring user
  migration.

`VERSION`, `CHANGELOG.md`, the annotated Git tag, and the GitHub Release must agree.
Sign the tag when a trusted signing key is configured.

## Release candidate

1. Update `VERSION` and `CHANGELOG.md`.
2. Synchronize the skill and all agent mirrors.
3. Run local validation and clean-install smoke tests.
4. Open a release PR and wait for all required checks.
5. Optionally publish `vX.Y.Z-rc.N` when installer or host compatibility changed.

## Local verification

```bash
.agents/skills/dart-mobile-game-studio/scripts/sync-skill.sh --check
python3 .agents/agents/sync-agents.py --check
.agents/skills/dart-mobile-game-studio/scripts/validate-skill.sh

git diff --check
```

After committing the release state:

```bash
scripts/package-release.sh
scripts/smoke-install.sh \
  --archive "dist/dart-mobile-game-studio-skill-only-v$(cat VERSION).zip"
```

## Publish

Create an annotated tag from the verified `main` commit. Use `git tag -s` instead
when a trusted signing key is configured:

```bash
git tag -a "v$(cat VERSION)" -m "Dart Mobile Game Studio v$(cat VERSION)"
git push origin "v$(cat VERSION)"
```

The `Release` workflow verifies the tag/version match, reruns the skill and
example gates, rebuilds both examples for Android and iOS, packages deterministic
archives, smoke-tests installation, and creates the GitHub Release only after
every dependency succeeds.

## Artifacts

- full repository ZIP;
- skill-only multi-host ZIP;
- SHA-256 checksums;
- JSON manifest containing version, commit, generation time, and artifact names.

If the workflow fails, do not recreate a tag at a different commit. Delete an
unpublished broken tag, fix through a reviewed commit, and create a new release
candidate or patch version.
