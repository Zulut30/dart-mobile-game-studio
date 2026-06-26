#!/usr/bin/env bash
#
# flutter-preflight.sh — run this FIRST, before any build/codegen/release step.
#
# Solves two production hazards:
#   1. Environment Lock — the skill's build steps assume a toolchain (Flutter/Dart SDK, Android SDK,
#      Xcode) that may be absent on a clean machine. This checks what's present and degrades
#      GRACEFULLY: it reports MISSING with the install hint instead of crashing a later step with a
#      cryptic error.
#   2. Workspace safety — before destructive commands (build_runner, flutter clean) you want a clean,
#      known git state. This reports branch, dirtiness, and detached HEAD so the agent can stash or
#      warn (see safe-run.sh).
#
# It NEVER mutates anything (read-only). Exit code is 0 unless a --require'd tool is missing or
# --git-clean is set and the tree is dirty — so it can gate a workflow.
#
# Usage:
#   scripts/flutter-preflight.sh                       # report env + git + project; exit 0
#   scripts/flutter-preflight.sh --require dart        # FAIL (exit 3) if dart is absent
#   scripts/flutter-preflight.sh --require flutter,android   # need both Flutter and Android SDK
#   scripts/flutter-preflight.sh --git-clean           # FAIL (exit 4) if the work tree is dirty
#   scripts/flutter-preflight.sh --json                # machine-readable report
#   ROOT=path/to/app scripts/flutter-preflight.sh
#
# Env: ROOT (default cwd). Flags: --require <csv: dart,flutter,android,xcode>, --git-clean, --json.
#
set -uo pipefail

ROOT="${ROOT:-$(pwd)}"
REQUIRE=""
WANT_JSON="no"
REQUIRE_GIT_CLEAN="no"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --require) REQUIRE="${REQUIRE},${2:-}"; shift 2 ;;
    --require=*) REQUIRE="${REQUIRE},${1#*=}"; shift ;;
    --git-clean) REQUIRE_GIT_CLEAN="yes"; shift ;;
    --json) WANT_JSON="yes"; shift ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# normalize the require list to spaces
REQUIRE="$(printf '%s' "${REQUIRE}" | tr ',' ' ')"

# ---- collected state (filled by the checks below) ----
DART_V="" ; FLUTTER_V="" ; ANDROID_V="" ; XCODE_V="" ; POD_V=""
GIT_REPO="no" ; GIT_BRANCH="" ; GIT_DIRTY="" ; GIT_DETACHED="no"
PUBSPEC="" ; IS_FLUTTER="no"
FAIL_REASONS=""

have() { command -v "$1" >/dev/null 2>&1; }
add_fail() { FAIL_REASONS="${FAIL_REASONS}${FAIL_REASONS:+; }$1"; }

# ---- toolchain ----
if have dart; then DART_V="$(dart --version 2>&1 | head -1)"; fi
if have flutter; then FLUTTER_V="$(flutter --version 2>&1 | head -1)"; fi

# Android: SDK root env or sdkmanager/adb on PATH
if [[ -n "${ANDROID_HOME:-}" && -d "${ANDROID_HOME:-}" ]]; then ANDROID_V="ANDROID_HOME=${ANDROID_HOME}"
elif [[ -n "${ANDROID_SDK_ROOT:-}" && -d "${ANDROID_SDK_ROOT:-}" ]]; then ANDROID_V="ANDROID_SDK_ROOT=${ANDROID_SDK_ROOT}"
elif have sdkmanager; then ANDROID_V="sdkmanager on PATH"
elif have adb; then ANDROID_V="adb on PATH"
fi

# Xcode/CocoaPods only meaningful on macOS
if [[ "$(uname -s)" == "Darwin" ]]; then
  if have xcodebuild; then XCODE_V="$(xcodebuild -version 2>/dev/null | head -1)"; fi
  if have pod; then POD_V="CocoaPods $(pod --version 2>/dev/null)"; fi
fi

# ---- git workspace ----
if git -C "${ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_REPO="yes"
  GIT_BRANCH="$(git -C "${ROOT}" rev-parse --abbrev-ref HEAD 2>/dev/null)"
  [[ "${GIT_BRANCH}" == "HEAD" ]] && GIT_DETACHED="yes"
  GIT_DIRTY="$(git -C "${ROOT}" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
fi

# ---- project ----
PUBSPEC="$(find "${ROOT}" -maxdepth 3 -name pubspec.yaml -not -path '*/.*' 2>/dev/null | head -n 1 || true)"
if [[ -n "${PUBSPEC}" ]]; then
  grep -qE '^\s*flutter\s*:' "${PUBSPEC}" 2>/dev/null && IS_FLUTTER="yes"
fi

# ---- evaluate --require ----
for tool in ${REQUIRE}; do
  case "${tool}" in
    dart)    [[ -n "${DART_V}" ]]    || add_fail "dart not found (install the Dart SDK: https://dart.dev/get-dart)" ;;
    flutter) [[ -n "${FLUTTER_V}" ]] || add_fail "flutter not found (install Flutter: https://docs.flutter.dev/get-started/install)" ;;
    android) [[ -n "${ANDROID_V}" ]] || add_fail "Android SDK not found (set ANDROID_HOME / install via Android Studio)" ;;
    xcode)   [[ -n "${XCODE_V}" ]]   || add_fail "Xcode not found (macOS only; install from the App Store + 'xcode-select --install')" ;;
    "" )     ;;
    * )      add_fail "unknown --require target: ${tool}" ;;
  esac
done

# ---- evaluate --git-clean ----
if [[ "${REQUIRE_GIT_CLEAN}" == "yes" ]]; then
  if [[ "${GIT_REPO}" != "yes" ]]; then add_fail "--git-clean: not a git repository"
  elif [[ "${GIT_DIRTY}" != "0" ]]; then add_fail "--git-clean: working tree has ${GIT_DIRTY} uncommitted change(s) — commit, stash, or use safe-run.sh --stash"
  fi
fi

# ---- output ----
mark() { [[ -n "$1" ]] && printf 'ok  ' || printf 'MISS'; }

if [[ "${WANT_JSON}" == "yes" ]]; then
  esc() { printf '%s' "${1:-}" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
  printf '{\n'
  printf '  "dart": "%s",\n'        "$(esc "${DART_V}")"
  printf '  "flutter": "%s",\n'     "$(esc "${FLUTTER_V}")"
  printf '  "android": "%s",\n'     "$(esc "${ANDROID_V}")"
  printf '  "xcode": "%s",\n'       "$(esc "${XCODE_V}")"
  printf '  "cocoapods": "%s",\n'   "$(esc "${POD_V}")"
  printf '  "git_repo": "%s",\n'    "${GIT_REPO}"
  printf '  "git_branch": "%s",\n'  "$(esc "${GIT_BRANCH}")"
  printf '  "git_detached": "%s",\n' "${GIT_DETACHED}"
  printf '  "git_dirty_count": %s,\n' "${GIT_DIRTY:-0}"
  printf '  "pubspec": "%s",\n'     "$(esc "${PUBSPEC}")"
  printf '  "is_flutter": "%s",\n'  "${IS_FLUTTER}"
  printf '  "ok": %s,\n'            "$([[ -z "${FAIL_REASONS}" ]] && echo true || echo false)"
  printf '  "fail_reasons": "%s"\n' "$(esc "${FAIL_REASONS}")"
  printf '}\n'
else
  echo "== Toolchain =="
  printf '  [%s] dart       %s\n'    "$(mark "${DART_V}")"     "${DART_V:-not found — https://dart.dev/get-dart}"
  printf '  [%s] flutter    %s\n'    "$(mark "${FLUTTER_V}")"  "${FLUTTER_V:-not found — https://docs.flutter.dev/get-started/install}"
  printf '  [%s] android    %s\n'    "$(mark "${ANDROID_V}")"  "${ANDROID_V:-not found — set ANDROID_HOME or install Android Studio}"
  if [[ "$(uname -s)" == "Darwin" ]]; then
    printf '  [%s] xcode      %s\n'  "$(mark "${XCODE_V}")"    "${XCODE_V:-not found — App Store + xcode-select --install}"
    printf '  [%s] cocoapods  %s\n'  "$(mark "${POD_V}")"      "${POD_V:-not found — sudo gem install cocoapods}"
  fi
  echo
  echo "== Git workspace =="
  if [[ "${GIT_REPO}" == "yes" ]]; then
    printf '  branch: %s%s\n' "${GIT_BRANCH}" "$([[ "${GIT_DETACHED}" == "yes" ]] && echo '  (DETACHED HEAD — commit to a branch before generating)')"
    if [[ "${GIT_DIRTY}" == "0" ]]; then
      printf '  tree:   clean ✓ (safe for destructive steps)\n'
    else
      printf '  tree:   %s uncommitted change(s) — stash/commit before codegen, or use safe-run.sh --stash\n' "${GIT_DIRTY}"
    fi
  else
    echo "  not a git repository — no rollback safety net (run 'git init' before destructive/codegen steps)"
  fi
  echo
  echo "== Project =="
  if [[ -n "${PUBSPEC}" ]]; then
    printf '  found: %s  (flutter project: %s)\n' "${PUBSPEC}" "${IS_FLUTTER}"
  else
    echo "  no pubspec.yaml under ${ROOT} — scaffold with: flutter create <app>  (or: dart create <pkg>)"
  fi
  echo
  if [[ -n "${FAIL_REASONS}" ]]; then
    echo "== PREFLIGHT FAILED =="
    IFS=';' read -ra _R <<< "${FAIL_REASONS}"
    for r in "${_R[@]}"; do echo "  - ${r# }"; done
  else
    echo "== Preflight OK =="
  fi
fi

# ---- exit code (gates the workflow) ----
if [[ -n "${FAIL_REASONS}" ]]; then
  # 3 = a required tool missing; 4 = git-clean gate failed; prefer the git code if that's the only kind
  if [[ "${REQUIRE_GIT_CLEAN}" == "yes" && "${FAIL_REASONS}" == *"--git-clean"* && -z "${REQUIRE// /}" ]]; then exit 4; fi
  exit 3
fi
exit 0
