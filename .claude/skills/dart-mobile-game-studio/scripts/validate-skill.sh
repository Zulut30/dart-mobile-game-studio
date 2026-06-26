#!/usr/bin/env bash
#
# validate-skill.sh — structural quality gate for the dart-mobile-game-studio package.
# Fast, deterministic checks; exits non-zero on any failure. Safe locally or in CI.
#
# Checks:
#   1. Every SKILL.md frontmatter has name + description, and name == folder name.
#   2. Skill copies (.claude/.cursor) are in sync with canonical (sync-skill.sh --check).
#   3. Subagent copies are in sync (sync-agents.py --check) and each Claude agent name == filename.
#   4. All *.json under the skill are valid JSON.
#   5. Shell scripts pass `bash -n`; Python scripts compile.
#   6. Cursor .mdc rules use a string `globs:` (not a YAML list, which Cursor ignores).
#
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANONICAL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${CANONICAL_DIR}/../../.." && pwd)"
SKILL_NAME="dart-mobile-game-studio"

fail=0
pass() { printf '  \033[32mok\033[0m   %s\n' "$1"; }
err()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=1; }
section() { printf '\n== %s ==\n' "$1"; }

cd "${REPO_ROOT}"

section "1. SKILL.md frontmatter & name==folder"
for skill in .agents/skills/${SKILL_NAME} .claude/skills/${SKILL_NAME} .cursor/skills/${SKILL_NAME}; do
  md="${skill}/SKILL.md"
  if [[ ! -f "${md}" ]]; then err "missing ${md}"; continue; fi
  name=$(awk -F': *' '/^name:/{print $2; exit}' "${md}" | tr -d '[:space:]')
  desc=$(awk -F': *' '/^description:/{print $2; exit}' "${md}")
  [[ -n "${desc}" ]] || err "${md}: missing description"
  if [[ "${name}" == "$(basename "${skill}")" ]]; then pass "${skill} (name=${name})"; else err "${md}: name '${name}' != folder"; fi
done

section "2. Skill copies in sync"
if .agents/skills/${SKILL_NAME}/scripts/sync-skill.sh --check >/dev/null 2>&1; then pass "skill copies in sync"; else err "skill copies drifted (run sync-skill.sh)"; fi

section "3. Subagents in sync & name==filename"
if [[ -f .agents/agents/sync-agents.py ]]; then
  if .agents/agents/sync-agents.py --check >/dev/null 2>&1; then pass "agent copies in sync"; else err "agent copies drifted (run sync-agents.py)"; fi
  for f in .claude/agents/*.md; do
    [[ -e "$f" ]] || continue
    n=$(awk -F': *' '/^name:/{print $2; exit}' "$f" | tr -d '[:space:]')
    [[ "$n" == "$(basename "$f" .md)" ]] && pass "agent $(basename "$f")" || err "$f: name '$n' != filename"
  done
  # Model routing: every canonical agent declares a valid tier; every Claude copy resolves to a model.
  for f in .agents/agents/*.md; do
    [[ "$(basename "$f")" == "README.md" ]] && continue
    t=$(awk -F': *' '/^tier:/{print $2; exit}' "$f" | tr -d '[:space:]')
    case "$t" in heavy|medium|light) : ;; *) err "$(basename "$f"): missing/invalid tier '$t' (heavy|medium|light)";; esac
  done
  for f in .claude/agents/*.md; do
    [[ -e "$f" ]] || continue
    m=$(awk -F': *' '/^model:/{print $2; exit}' "$f" | tr -d '[:space:]')
    case "$m" in opus|sonnet|haiku) : ;; *) err "$(basename "$f" .md): no resolved model '$m' (tier→model failed)";; esac
  done
  [[ "${fail}" -eq 0 ]] && pass "agent tiers valid & models resolved"
else
  echo "  skip (.agents/agents/sync-agents.py not present yet)"
fi

section "4. JSON validity"
while IFS= read -r j; do
  if python3 -c "import json,sys;json.load(open(sys.argv[1]))" "$j" 2>/dev/null; then pass "$j"; else err "$j: invalid JSON"; fi
done < <(find .agents/skills/${SKILL_NAME} -name '*.json')

section "5. Script syntax"
for s in .agents/skills/${SKILL_NAME}/scripts/*.sh; do bash -n "$s" 2>/dev/null && pass "bash -n $(basename "$s")" || err "$s: bash syntax error"; done
pyfiles=$(find .agents/skills/${SKILL_NAME}/scripts .agents/agents -name '*.py' 2>/dev/null)
if [[ -n "${pyfiles}" ]]; then
  python3 -m py_compile ${pyfiles} 2>/dev/null && pass "python compile" || err "python compile error"
fi

section "6. Cursor .mdc globs format (string, not YAML list)"
shopt -s nullglob
for mdc in .cursor/rules/*.mdc; do
  if awk '/^globs:[[:space:]]*$/{getline n; if (n ~ /^[[:space:]]*-/) exit 1}' "$mdc"; then
    pass "$(basename "$mdc")"
  else
    err "$mdc: 'globs' uses a YAML list; Cursor expects a comma-separated string"
  fi
done
shopt -u nullglob

echo
if [[ "${fail}" -eq 0 ]]; then echo "All skill-structure checks passed."; else echo "Skill-structure checks FAILED." >&2; fi
exit "${fail}"
