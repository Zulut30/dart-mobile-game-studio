# Installation

Dart Mobile Game Studio is installed into a project as agent configuration, not
as a Dart dependency. The installer copies only the surfaces requested for the
selected host tool and records them in a local manifest.

## Requirements

- macOS or Linux with Bash 3.2 or newer;
- Git for source installs and release checksum verification;
- Python 3 for agent mirror validation;
- Flutter only when building or testing Flutter projects.

## Install from source

```bash
git clone --depth 1 https://github.com/Zulut30/dart-mobile-game-studio.git
cd dart-mobile-game-studio

./scripts/install.sh --tool codex --target /path/to/project
./scripts/install.sh --tool claude --target /path/to/project
./scripts/install.sh --tool cursor --target /path/to/project
./scripts/install.sh --tool all --target /path/to/project
```

The target project may already contain unrelated agent configuration. The
installer manages only these destinations:

| Tool | Installed paths |
|---|---|
| Codex | `.agents/skills/dart-mobile-game-studio`, `.agents/agents`, `.codex/agents` |
| Claude Code | `.claude/skills/dart-mobile-game-studio`, `.claude/agents` |
| Cursor | `.cursor/skills/dart-mobile-game-studio`, `.cursor/rules` |

The installer deliberately does not overwrite root `AGENTS.md` or `CLAUDE.md`
files because those normally contain project-owned instructions.

## Preview, replace, and remove

```bash
# Show operations without writing:
./scripts/install.sh --tool all --target /path/to/project --dry-run

# Back up and replace existing managed destinations:
./scripts/install.sh --tool all --target /path/to/project --force

# Remove only paths recorded by the installation manifest:
./scripts/install.sh --target /path/to/project --uninstall
```

Backups are written inside the target as
`.dart-mobile-game-studio-backup-<UTC timestamp>` and are never deleted by the
installer.

## Install a GitHub Release archive

Download the `skill-only` archive and `SHA256SUMS` from the release page, then:

```bash
shasum -a 256 -c SHA256SUMS
unzip dart-mobile-game-studio-skill-only-v1.0.0.zip
cd dart-mobile-game-studio-1.0.0
./scripts/install.sh --tool all --target /path/to/project
```

Never execute an installer from an unverified third-party mirror.

## Verify the installed skill

For an `all` installation:

```bash
/path/to/project/.agents/skills/dart-mobile-game-studio/scripts/sync-skill.sh --check
python3 /path/to/project/.agents/agents/sync-agents.py --check
```

To verify a real Flutter project:

```bash
/path/to/project/.agents/skills/dart-mobile-game-studio/scripts/verify-flutter-project.sh /path/to/project
```

The verifier returns exit code `4` when Dart/Flutter is unavailable. That means
unverified, not passed.

## Host integration

Codex discovers repository-local skills under `.agents/skills` and profiles in
`.codex/agents`. Claude Code uses the generated `.claude/skills` and
`.claude/agents` copies. Cursor uses `.cursor/skills` plus the generated rules.

If the host does not auto-discover repository skills, add a short project-owned
instruction pointing to:

```text
.agents/skills/dart-mobile-game-studio/SKILL.md
```

Do not copy the entire upstream `AGENTS.md` into an existing project without
reviewing it; project instructions always remain project-owned.

## Updating

```bash
git -C /path/to/dart-mobile-game-studio pull --ff-only
/path/to/dart-mobile-game-studio/scripts/install.sh \
  --tool all --target /path/to/project --force
```

Review the [changelog](../CHANGELOG.md) before updating across a major version.
