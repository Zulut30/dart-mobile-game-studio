#!/usr/bin/env bash
#
# verify-flutter-project.sh — detect a Flutter/Dart project and run source-preserving quality gates:
# format check, analyze, and tests. Dependency resolution is opt-in because pub get can update
# lockfiles and .dart_tool. Missing projects/toolchains are reported as unverified, never as success.
#
# Usage:
#   scripts/verify-flutter-project.sh                 # discover + analyze + test in the current dir
#   ROOT=path/to/app scripts/verify-flutter-project.sh
#   ALL_PROJECTS=yes scripts/verify-flutter-project.sh  # verify every discovered project
#   ACTION=analyze scripts/verify-flutter-project.sh  # analyze only (skip tests)
#   RESOLVE_DEPS=yes scripts/verify-flutter-project.sh # explicitly run pub get before checks
#
# Env: ROOT (default cwd), ACTION=all|analyze|test, ALL_PROJECTS=auto|yes|no,
#      RESOLVE_DEPS=yes|no (default no).
# Exit: 0 = every requested check ran and passed; 1 = a check failed; 2 = invalid usage/config;
#       4 = no project or required toolchain, so verification did not run.
#
set -uo pipefail

ROOT="${ROOT:-$(pwd)}"
ACTION="${ACTION:-all}"
ALL_PROJECTS="${ALL_PROJECTS:-auto}"
RESOLVE_DEPS="${RESOLVE_DEPS:-no}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "${ACTION}" in all|analyze|test) : ;; *) echo "verify: invalid ACTION '${ACTION}'" >&2; exit 2 ;; esac
case "${ALL_PROJECTS}" in auto|yes|no) : ;; *) echo "verify: invalid ALL_PROJECTS '${ALL_PROJECTS}'" >&2; exit 2 ;; esac
case "${RESOLVE_DEPS}" in yes|no) : ;; *) echo "verify: invalid RESOLVE_DEPS '${RESOLVE_DEPS}'" >&2; exit 2 ;; esac
if [[ ! -d "${ROOT}" ]]; then
  echo "verify: root not found: ${ROOT}" >&2
  exit 2
fi

echo "== Environment =="
if command -v flutter >/dev/null 2>&1; then flutter --version 2>&1 | head -1; fi
if command -v dart >/dev/null 2>&1; then dart --version 2>&1 | head -1; fi
if ! command -v dart >/dev/null 2>&1 && ! command -v flutter >/dev/null 2>&1; then
  echo "warning: neither 'dart' nor 'flutter' is on PATH — discovery only." >&2
fi
echo

echo "== Discovering Dart/Flutter project under: ${ROOT} =="
DISCOVER_ARGS=(--root "${ROOT}" --all)
pubspecs=()
if ! discovery_output="$("${SCRIPT_DIR}/discover-projects.sh" "${DISCOVER_ARGS[@]}")"; then
  echo "verify: project discovery failed" >&2
  exit 1
fi
while IFS= read -r p; do
  [[ -n "${p}" ]] && pubspecs+=("${p}")
done <<< "${discovery_output}"
if [[ ${#pubspecs[@]} -eq 0 ]]; then
  echo "No pubspec.yaml found under ${ROOT}. Create one with: flutter create <app>  (or: dart create <pkg>)."
  exit 4
fi

root_abs="$(cd "${ROOT}" && pwd)"
if [[ "${ALL_PROJECTS}" != "yes" && -f "${root_abs}/pubspec.yaml" ]]; then
  pubspecs=("${root_abs}/pubspec.yaml")
elif [[ "${ALL_PROJECTS}" == "no" ]]; then
  pubspecs=("${pubspecs[0]}")
fi

echo "Found ${#pubspecs[@]} project(s):"
for p in "${pubspecs[@]}"; do
  is_flutter="no"
  grep -qE '^[[:space:]]*flutter[[:space:]]*:' "${p}" 2>/dev/null && is_flutter="yes"
  echo "  - ${p}  (flutter project: ${is_flutter})"
done
echo

failed=0
skipped=0

run() { echo "+ $*"; ( cd "${PKG_DIR}" && "$@" ); }

for PUBSPEC in "${pubspecs[@]}"; do
  PKG_DIR="$(dirname "${PUBSPEC}")"
  IS_FLUTTER="no"
  grep -qE '^[[:space:]]*flutter[[:space:]]*:' "${PUBSPEC}" 2>/dev/null && IS_FLUTTER="yes"

  # A Flutter project needs both commands: flutter for analyze/test and dart for format.
  if [[ "${IS_FLUTTER}" == "yes" ]] && command -v flutter >/dev/null 2>&1 && command -v dart >/dev/null 2>&1; then
    DRV="flutter"
  elif [[ "${IS_FLUTTER}" == "no" ]] && command -v dart >/dev/null 2>&1; then
    DRV="dart"
  else
    echo "Toolchain not available here. Run these in the project (${PKG_DIR}):"
    if [[ "${IS_FLUTTER}" == "yes" ]]; then echo "  flutter pub get"; else echo "  dart pub get"; fi
    echo "  dart format --output=none --set-exit-if-changed ."
    if [[ "${IS_FLUTTER}" == "yes" ]]; then echo "  flutter analyze"; else echo "  dart analyze"; fi
    if [[ "${IS_FLUTTER}" == "yes" ]]; then echo "  flutter test"; else echo "  dart test"; fi
    echo
    skipped=1
    continue
  fi

  if [[ "${RESOLVE_DEPS}" == "yes" ]]; then
    echo "== ${PKG_DIR}: pub get (explicitly enabled) =="
    run "${DRV}" pub get || { echo "pub get failed" >&2; failed=1; continue; }
    echo
  fi

  echo "== ${PKG_DIR}: format check (no writes) =="
  if ! run dart format --output=none --set-exit-if-changed .; then
    echo "format check failed (run: dart format .)" >&2
    failed=1
  fi
  echo

  if [[ "${ACTION}" == "all" || "${ACTION}" == "analyze" ]]; then
    echo "== ${PKG_DIR}: analyze =="
    if [[ "${DRV}" == "flutter" ]]; then run flutter analyze || failed=1; else run dart analyze || failed=1; fi
    echo
  fi

  if [[ "${ACTION}" == "all" || "${ACTION}" == "test" ]]; then
    echo "== ${PKG_DIR}: test =="
    if [[ "${DRV}" == "flutter" ]]; then run flutter test || failed=1; else run dart test || failed=1; fi
  fi
done

if [[ "${failed}" -ne 0 ]]; then
  exit 1
fi
if [[ "${skipped}" -ne 0 ]]; then
  echo "verify: one or more projects were not verified because the required toolchain is missing." >&2
  exit 4
fi
exit 0
