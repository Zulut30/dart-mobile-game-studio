#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SOURCE="$ROOT"
ARCHIVE=""
KEEP=0

while (($#)); do
  case "$1" in
    --archive)
      ARCHIVE=${2:?--archive requires a path}
      shift 2
      ;;
    --keep)
      KEEP=1
      shift
      ;;
    -h|--help)
      printf 'Usage: scripts/smoke-install.sh [--archive FILE] [--keep]\n'
      exit 0
      ;;
    *)
      printf 'error: unknown argument: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

work=$(mktemp -d "${TMPDIR:-/tmp}/dmgs-smoke.XXXXXX")
cleanup() {
  if ((KEEP)); then
    printf 'kept smoke workspace: %s\n' "$work"
  else
    rm -rf "$work"
  fi
}
trap cleanup EXIT

if [[ -n "$ARCHIVE" ]]; then
  [[ -f "$ARCHIVE" ]] || { printf 'error: archive not found: %s\n' "$ARCHIVE" >&2; exit 2; }
  mkdir -p "$work/source"
  unzip -q "$ARCHIVE" -d "$work/source"
  SOURCE=$(find "$work/source" -mindepth 1 -maxdepth 1 -type d -print -quit)
  [[ -n "$SOURCE" ]] || { printf 'error: archive has no distribution root\n' >&2; exit 2; }
fi

target="$work/target"
mkdir -p "$target"
"$SOURCE/scripts/install.sh" --tool all --target "$target"

test -f "$target/.dart-mobile-game-studio-install"
test -f "$target/.agents/skills/dart-mobile-game-studio/SKILL.md"
test -f "$target/.codex/agents/game-coordinator.toml"
test -f "$target/.claude/agents/game-coordinator.md"
test -f "$target/.cursor/rules/agents/game-coordinator.mdc"

"$target/.agents/skills/dart-mobile-game-studio/scripts/sync-skill.sh" --check
python3 "$target/.agents/agents/sync-agents.py" --check

"$SOURCE/scripts/install.sh" --target "$target" --uninstall
test ! -e "$target/.agents/skills/dart-mobile-game-studio"
test ! -e "$target/.dart-mobile-game-studio-install"

printf 'clean install and uninstall smoke test passed\n'
