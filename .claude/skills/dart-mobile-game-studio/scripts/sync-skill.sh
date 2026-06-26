#!/usr/bin/env bash
#
# sync-skill.sh — mirror the canonical dart-mobile-game-studio skill into tool-specific
# locations (.claude/skills and .cursor/skills). Canonical source of truth:
# .agents/skills/dart-mobile-game-studio. Run after editing the canonical skill.
#
# Usage:
#   scripts/sync-skill.sh            # copy canonical into .claude and .cursor
#   DRY_RUN=1 scripts/sync-skill.sh  # show what would happen, change nothing
#   scripts/sync-skill.sh --check    # CI: exit non-zero if any copy has drifted (content-based)
#
set -euo pipefail

SKILL_NAME="dart-mobile-game-studio"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANONICAL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"          # .agents/skills/<skill>
REPO_ROOT="$(cd "${CANONICAL_DIR}/../../.." && pwd)"     # repo root

if [[ ! -f "${CANONICAL_DIR}/SKILL.md" ]]; then
  echo "error: canonical SKILL.md not found at ${CANONICAL_DIR}/SKILL.md" >&2
  exit 1
fi

TARGETS=(
  "${REPO_ROOT}/.claude/skills/${SKILL_NAME}"
  "${REPO_ROOT}/.cursor/skills/${SKILL_NAME}"
)

MODE="sync"
[[ "${1:-}" == "--check" ]] && MODE="check"
DRY_RUN="${DRY_RUN:-0}"

run() {
  if [[ "${DRY_RUN}" == "1" ]]; then echo "[dry-run] $*"; else eval "$@"; fi
}

# --check: compare each target against canonical by CONTENT only (ignore timestamps, which differ
# harmlessly on a fresh git checkout). diff -rq reports differing/missing files; exclude caches.
if [[ "${MODE}" == "check" ]]; then
  drift=0
  for target in "${TARGETS[@]}"; do
    if [[ ! -d "${target}" ]]; then echo "DRIFT: missing copy ${target}"; drift=1; continue; fi
    out="$(diff -rq -x '__pycache__' -x '*.pyc' "${CANONICAL_DIR}" "${target}" 2>&1 || true)"
    if [[ -n "${out}" ]]; then
      echo "DRIFT: ${target} differs from canonical:"; echo "${out}" | sed 's/^/    /'; drift=1
    else
      echo "OK:    ${target} is in sync"
    fi
  done
  if [[ "${drift}" -ne 0 ]]; then echo "Copies have drifted. Run: scripts/sync-skill.sh" >&2; exit 1; fi
  echo "All skill copies are in sync with canonical."
  exit 0
fi

echo "Canonical skill: ${CANONICAL_DIR}"
for target in "${TARGETS[@]}"; do
  echo "Syncing -> ${target}"
  run "mkdir -p \"${target}\""
  if command -v rsync >/dev/null 2>&1; then
    run "rsync -a --delete --exclude '__pycache__' --exclude '*.pyc' \"${CANONICAL_DIR}/\" \"${target}/\""
  else
    run "rm -rf \"${target:?}\"/*"
    run "cp -R \"${CANONICAL_DIR}/.\" \"${target}/\""
    run "find \"${target}\" -name '__pycache__' -type d -prune -exec rm -rf {} +"
  fi
done

echo "Done. ${SKILL_NAME} synced to .claude/skills and .cursor/skills."
