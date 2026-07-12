#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

[[ -f VERSION ]] || { printf 'error: VERSION is missing\n' >&2; exit 2; }
version=$(<VERSION)
[[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] || {
  printf 'error: invalid semantic version: %s\n' "$version" >&2
  exit 2
}

git diff --quiet && git diff --cached --quiet || {
  printf 'error: release packaging requires a clean tracked worktree\n' >&2
  exit 2
}

output=${OUTPUT_DIR:-"$ROOT/dist"}
rm -rf "$output"
mkdir -p "$output"

full="dart-mobile-game-studio-v${version}.zip"
skill="dart-mobile-game-studio-skill-only-v${version}.zip"
prefix="dart-mobile-game-studio-${version}/"

git archive --format=zip --prefix="$prefix" -o "$output/$full" HEAD
git archive --format=zip --prefix="$prefix" -o "$output/$skill" HEAD \
  .agents/skills/dart-mobile-game-studio \
  .agents/agents \
  .claude/skills/dart-mobile-game-studio \
  .claude/agents \
  .cursor/skills/dart-mobile-game-studio \
  .cursor/rules \
  .codex/agents \
  scripts/install.sh \
  README.md README.ru.md LICENSE VERSION CHANGELOG.md

(
  cd "$output"
  shasum -a 256 "$full" "$skill" > SHA256SUMS
)

commit=$(git rev-parse HEAD)
generated=$(date -u +%Y-%m-%dT%H:%M:%SZ)
cat > "$output/release-manifest.json" <<EOF
{
  "name": "dart-mobile-game-studio",
  "version": "$version",
  "commit": "$commit",
  "generated_at": "$generated",
  "artifacts": ["$full", "$skill", "SHA256SUMS"]
}
EOF

printf 'release artifacts written to %s\n' "$output"
