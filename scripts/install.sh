#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TOOL=""
TARGET=""
DRY_RUN=0
FORCE=0
UNINSTALL=0
MANIFEST_NAME=".dart-mobile-game-studio-install"

usage() {
  cat <<'EOF'
Usage: scripts/install.sh --tool codex|claude|cursor|all --target DIR [options]

Options:
  --dry-run      Print operations without writing files.
  --force        Back up and replace an existing managed destination.
  --uninstall    Remove only paths recorded by this installer's manifest.
  -h, --help     Show this help.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 2
}

while (($#)); do
  case "$1" in
    --tool)
      (($# >= 2)) || die "--tool requires a value"
      TOOL=$2
      shift 2
      ;;
    --target)
      (($# >= 2)) || die "--target requires a value"
      TARGET=$2
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --uninstall)
      UNINSTALL=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[[ -n "$TARGET" ]] || die "--target is required"
TARGET=$(cd "$(dirname "$TARGET")" && pwd)/$(basename "$TARGET")
MANIFEST="$TARGET/$MANIFEST_NAME"

if ((UNINSTALL)); then
  [[ -f "$MANIFEST" ]] || die "no installer manifest found at $MANIFEST"
  while IFS= read -r relative; do
    case "$relative" in
      .agents/skills/dart-mobile-game-studio|.agents/agents|.claude/skills/dart-mobile-game-studio|.claude/agents|.cursor/skills/dart-mobile-game-studio|.cursor/rules|.codex/agents)
        if ((DRY_RUN)); then
          printf 'would remove %s\n' "$TARGET/$relative"
        else
          rm -rf "$TARGET/$relative"
          printf 'removed %s\n' "$TARGET/$relative"
        fi
        ;;
      "") ;;
      *) die "manifest contains an unsafe path: $relative" ;;
    esac
  done < "$MANIFEST"
  if ((DRY_RUN == 0)); then
    rm -f "$MANIFEST"
  fi
  exit 0
fi

case "$TOOL" in
  codex|claude|cursor|all) ;;
  *) die "--tool must be codex, claude, cursor, or all" ;;
esac

[[ -f "$ROOT/VERSION" ]] || die "VERSION is missing from the distribution"
mkdir -p "$TARGET"

backup_root="$TARGET/.dart-mobile-game-studio-backup-$(date -u +%Y%m%dT%H%M%SZ)"
declare -a installed=()
declare -a selected=()

select_tree() {
  selected+=("$1")
}

select_codex() {
  select_tree ".agents/skills/dart-mobile-game-studio"
  select_tree ".agents/agents"
  select_tree ".codex/agents"
}

select_claude() {
  select_tree ".claude/skills/dart-mobile-game-studio"
  select_tree ".claude/agents"
}

select_cursor() {
  select_tree ".cursor/skills/dart-mobile-game-studio"
  select_tree ".cursor/rules"
}

case "$TOOL" in
  codex) select_codex ;;
  claude) select_claude ;;
  cursor) select_cursor ;;
  all)
    select_codex
    select_claude
    select_cursor
    ;;
esac

for relative in "${selected[@]}"; do
  [[ -e "$ROOT/$relative" ]] || die "distribution path is missing: $relative"
  if [[ -e "$TARGET/$relative" ]] && ((FORCE == 0)); then
    die "$TARGET/$relative already exists; rerun with --force to back it up"
  fi
done

copy_tree() {
  local relative=$1
  local source="$ROOT/$relative"
  local destination="$TARGET/$relative"
  [[ -e "$source" ]] || die "distribution path is missing: $relative"

  if [[ -e "$destination" ]]; then
    ((FORCE)) || die "$destination already exists; rerun with --force to back it up"
    if ((DRY_RUN)); then
      printf 'would back up %s to %s\n' "$destination" "$backup_root/$relative"
    else
      mkdir -p "$(dirname "$backup_root/$relative")"
      cp -R "$destination" "$backup_root/$relative"
      rm -rf "$destination"
    fi
  fi

  if ((DRY_RUN)); then
    printf 'would install %s\n' "$relative"
  else
    mkdir -p "$(dirname "$destination")"
    cp -R "$source" "$destination"
    printf 'installed %s\n' "$relative"
  fi
  installed+=("$relative")
}

for relative in "${selected[@]}"; do
  copy_tree "$relative"
done

if ((DRY_RUN == 0)); then
  printf '%s\n' "${installed[@]}" | awk '!seen[$0]++' > "$MANIFEST"
  printf 'Dart Mobile Game Studio %s installed for %s in %s\n' \
    "$(<"$ROOT/VERSION")" "$TOOL" "$TARGET"
fi
