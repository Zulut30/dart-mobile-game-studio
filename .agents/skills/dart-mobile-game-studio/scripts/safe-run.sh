#!/usr/bin/env bash
#
# safe-run.sh — run a destructive/generative command inside a git safety net.
#
# Codegen (build_runner) and CLI steps (flutter clean) mutate the project in place. If the agent
# passes a wrong arg or the step half-completes, you can be left with a broken, half-generated tree.
# This wraps the command with a savepoint:
#
#   1. record the current commit (START_SHA) and ensure a safe savepoint exists;
#   2. run the command, capturing output to a log;
#   3. on SUCCESS  → optionally create one atomic commit of the result;
#   4. on FAILURE  → roll the working tree back to START_SHA (so you never keep a broken state),
#                    and optionally triage the log into a short summary.
#
# The rollback uses `git reset --hard` + `git clean -fd`, which are themselves destructive — so this
# script auto-rolls-back ONLY when it can prove nothing is lost: either the tree was already clean, or
# it stashed your changes (incl. untracked) first. On a dirty tree without --stash it refuses to run
# (or, with --allow-dirty, runs but DISABLES auto-rollback). Safety of the safety net comes first.
#
# Usage:
#   scripts/safe-run.sh [options] -- <command> [args...]
#
# Options:
#   --label <text>       short name for the savepoint/log (default: the command)
#   --commit             on success, create one atomic commit of the changes
#   --commit-msg <msg>   commit message (default: "chore(auto): <label> via skill")
#   --stash              if the tree is dirty, stash (incl. untracked) before running; restore after
#   --allow-dirty        run on a dirty tree with NO savepoint (auto-rollback disabled)
#   --no-rollback        on failure, do not reset; just report (and triage if asked)
#   --triage             on failure, pipe the captured log through triage-log.py
#   -h | --help
#
# Default (no --stash/--allow-dirty): require a clean tree, else abort with guidance.
#
# Examples:
#   scripts/safe-run.sh --label "regen serialization" --commit \
#     --commit-msg "chore(auto): regenerate json/freezed via build_runner" \
#     -- dart run build_runner build --delete-conflicting-outputs
#   scripts/safe-run.sh --stash --triage -- flutter clean
#
# Exit: the command's exit code (0 on success). 2 = usage; 3 = unsafe/dirty refusal.
#
set -uo pipefail

LABEL=""
DO_COMMIT="no"
COMMIT_MSG=""
MODE="require-clean"     # require-clean | stash | allow-dirty
DO_ROLLBACK="yes"
DO_TRIAGE="no"
CMD=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --label) LABEL="${2:?--label needs text}"; shift 2 ;;
    --label=*) LABEL="${1#*=}"; shift ;;
    --commit) DO_COMMIT="yes"; shift ;;
    --commit-msg) COMMIT_MSG="${2:?--commit-msg needs text}"; shift 2 ;;
    --commit-msg=*) COMMIT_MSG="${1#*=}"; shift ;;
    --stash) MODE="stash"; shift ;;
    --allow-dirty) MODE="allow-dirty"; shift ;;
    --no-rollback) DO_ROLLBACK="no"; shift ;;
    --triage) DO_TRIAGE="yes"; shift ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    --) shift; CMD=("$@"); break ;;
    *) echo "unknown arg: $1 (did you forget '--' before the command?)" >&2; exit 2 ;;
  esac
done

if [[ ${#CMD[@]} -eq 0 ]]; then echo "safe-run: no command given after '--'" >&2; exit 2; fi
[[ -z "${LABEL}" ]] && LABEL="${CMD[*]}"
[[ -z "${COMMIT_MSG}" ]] && COMMIT_MSG="chore(auto): ${LABEL} via skill"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$(mktemp -t safe-run.XXXXXX.log 2>/dev/null || echo "/tmp/safe-run.$$.log")"

# ---- git context ----
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "safe-run: not a git repository — running WITHOUT a safety net (no rollback available)." >&2
  echo "+ ${CMD[*]}"
  "${CMD[@]}"; rc=$?
  [[ $rc -ne 0 && "${DO_TRIAGE}" == "yes" ]] && true   # no log captured in this degraded path
  exit $rc
fi

HAS_HEAD="yes"; git rev-parse HEAD >/dev/null 2>&1 || HAS_HEAD="no"
START_SHA=""; [[ "${HAS_HEAD}" == "yes" ]] && START_SHA="$(git rev-parse HEAD)"
DIRTY_COUNT="$(git status --porcelain | wc -l | tr -d ' ')"
STASHED="no"
SAFE_ROLLBACK="no"   # only true when we can prove rollback loses nothing

# ---- establish a savepoint per mode ----
case "${MODE}" in
  require-clean)
    if [[ "${DIRTY_COUNT}" != "0" ]]; then
      echo "safe-run: working tree has ${DIRTY_COUNT} uncommitted change(s)." >&2
      echo "  Commit or stash them first, or pass --stash (auto-stash) / --allow-dirty (no rollback)." >&2
      exit 3
    fi
    SAFE_ROLLBACK="yes"   # clean start → reset+clean cannot lose user work
    ;;
  stash)
    if [[ "${DIRTY_COUNT}" != "0" ]]; then
      echo "+ git stash push -u -m 'safe-run savepoint: ${LABEL}'"
      if git stash push -u -m "safe-run savepoint: ${LABEL}" >/dev/null 2>&1; then
        STASHED="yes"
      else
        echo "safe-run: git stash failed; aborting to avoid an unsafe run." >&2
        exit 3
      fi
    fi
    SAFE_ROLLBACK="yes"   # user work is in the stash → reset+clean is recoverable
    ;;
  allow-dirty)
    echo "safe-run: --allow-dirty — running on a dirty tree; AUTO-ROLLBACK DISABLED." >&2
    SAFE_ROLLBACK="no"
    ;;
esac

restore_stash() {
  if [[ "${STASHED}" == "yes" ]]; then
    echo "+ git stash pop  (restoring your pre-run changes)"
    if ! git stash pop >/dev/null 2>&1; then
      echo "safe-run: 'git stash pop' hit a conflict — your changes are safe in 'git stash list'." >&2
    fi
  fi
}

rollback() {
  if [[ "${SAFE_ROLLBACK}" == "yes" && "${HAS_HEAD}" == "yes" ]]; then
    echo "+ git reset --hard ${START_SHA}   &&   git clean -fd   (undo the broken/partial state)"
    git reset --hard "${START_SHA}" >/dev/null 2>&1
    git clean -fd >/dev/null 2>&1
    echo "safe-run: rolled the working tree back to ${START_SHA:0:9}."
    restore_stash
  else
    echo "safe-run: NOT auto-rolling back (unsafe mode or no commit yet) — inspect the tree manually." >&2
  fi
}

# ---- run the command, tee to the log (capture rc of the command, not tee) ----
echo "+ ${CMD[*]}"
set -o pipefail
"${CMD[@]}" 2>&1 | tee "${LOG}"
rc=${PIPESTATUS[0]}

echo
if [[ $rc -eq 0 ]]; then
  echo "safe-run: command succeeded."
  if [[ "${DO_COMMIT}" == "yes" ]]; then
    if [[ -n "$(git status --porcelain)" ]]; then
      echo "+ git add -A && git commit -m \"${COMMIT_MSG}\""
      git add -A
      if git commit -m "${COMMIT_MSG}" >/dev/null 2>&1; then
        echo "safe-run: committed result as: ${COMMIT_MSG}"
      else
        echo "safe-run: nothing committed (a pre-commit hook may have blocked it — check 'git status')." >&2
      fi
    else
      echo "safe-run: no file changes to commit."
    fi
  fi
  restore_stash    # bring back any stashed user edits on top of the (committed) result
  rm -f "${LOG}"
  exit 0
else
  echo "safe-run: command FAILED (exit ${rc})." >&2
  if [[ "${DO_TRIAGE}" == "yes" && -f "${SCRIPT_DIR}/triage-log.py" ]]; then
    echo "---- log triage ----"
    python3 "${SCRIPT_DIR}/triage-log.py" "${LOG}" || true
    echo "--------------------"
  fi
  [[ "${DO_ROLLBACK}" == "yes" ]] && rollback || { [[ "${DO_ROLLBACK}" == "no" ]] && restore_stash; }
  echo "safe-run: full log kept at ${LOG}"
  exit $rc
fi
