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
# Exit: the command's exit code (0 on success). 2 = usage; 3 = unsafe refusal;
# 4 = requested commit failed; 5 = stashed user changes could not be restored cleanly.
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

if [[ "${MODE}" == "allow-dirty" && "${DO_COMMIT}" == "yes" ]]; then
  echo "safe-run: --allow-dirty cannot be combined with --commit." >&2
  echo "  Commit/stash existing work first, or use --stash --commit." >&2
  exit 3
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---- git context ----
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "safe-run: not a git repository; refusing to run without a safety net." >&2
  exit 3
fi

if ! START_SHA="$(git rev-parse HEAD 2>/dev/null)"; then
  echo "safe-run: repository has no commit yet; create an initial commit before using safe-run." >&2
  exit 3
fi

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
    STASHED="no" # Never retry automatically after a conflict.
    if ! git stash pop >/dev/null 2>&1; then
      echo "safe-run: 'git stash pop' hit a conflict — your changes are safe in 'git stash list'." >&2
      return 1
    fi
  fi
  return 0
}

rollback() {
  if [[ "${SAFE_ROLLBACK}" == "yes" ]]; then
    echo "+ git reset --hard ${START_SHA}   &&   git clean -fd   (undo the broken/partial state)"
    if ! git reset --hard "${START_SHA}" >/dev/null 2>&1 || ! git clean -fd >/dev/null 2>&1; then
      echo "safe-run: rollback failed; inspect the working tree manually." >&2
      return 1
    fi
    echo "safe-run: rolled the working tree back to ${START_SHA:0:9}."
    restore_stash || return 1
  else
    echo "safe-run: NOT auto-rolling back (unsafe mode) — inspect the tree manually." >&2
  fi
  return 0
}

LOG="$(mktemp -t safe-run.XXXXXX.log 2>/dev/null || echo "/tmp/safe-run.$$.log")"
FINISHED="no"

cleanup_on_exit() {
  local exit_code=$?
  trap - EXIT INT TERM HUP
  if [[ "${FINISHED}" != "yes" ]]; then
    echo "safe-run: interrupted; restoring the pre-run state." >&2
    if [[ "${DO_ROLLBACK}" == "yes" ]]; then
      rollback || true
    else
      restore_stash || true
    fi
    echo "safe-run: full log kept at ${LOG}" >&2
  fi
  exit "${exit_code}"
}

trap cleanup_on_exit EXIT
trap 'exit 130' INT TERM HUP

# ---- run the command, tee to the log (capture rc of the command, not tee) ----
echo "+ ${CMD[*]}"
set -o pipefail
"${CMD[@]}" 2>&1 | tee "${LOG}"
rc=${PIPESTATUS[0]}

echo
if [[ $rc -eq 0 ]]; then
  echo "safe-run: command succeeded."
  post_rc=0
  if [[ "${DO_COMMIT}" == "yes" ]]; then
    if [[ -n "$(git status --porcelain)" ]]; then
      echo "+ git add -A && git commit -m \"${COMMIT_MSG}\""
      if ! git add -A; then
        echo "safe-run: could not stage the generated changes." >&2
        post_rc=4
      elif git commit -m "${COMMIT_MSG}" >/dev/null 2>&1; then
        echo "safe-run: committed result as: ${COMMIT_MSG}"
      else
        echo "safe-run: commit failed (a hook may have blocked it — check 'git status')." >&2
        post_rc=4
      fi
    else
      echo "safe-run: no file changes to commit."
    fi
  fi
  if ! restore_stash; then
    post_rc=5
  fi
  FINISHED="yes"
  if [[ "${post_rc}" -eq 0 ]]; then
    rm -f "${LOG}"
  else
    echo "safe-run: full log kept at ${LOG}" >&2
  fi
  exit "${post_rc}"
else
  echo "safe-run: command FAILED (exit ${rc})." >&2
  if [[ "${DO_TRIAGE}" == "yes" && -f "${SCRIPT_DIR}/triage-log.py" ]]; then
    echo "---- log triage ----"
    python3 "${SCRIPT_DIR}/triage-log.py" "${LOG}" || true
    echo "--------------------"
  fi
  post_rc="${rc}"
  if [[ "${DO_ROLLBACK}" == "yes" ]]; then
    rollback || post_rc=5
  elif ! restore_stash; then
    post_rc=5
  fi
  FINISHED="yes"
  echo "safe-run: full log kept at ${LOG}"
  exit "${post_rc}"
fi
