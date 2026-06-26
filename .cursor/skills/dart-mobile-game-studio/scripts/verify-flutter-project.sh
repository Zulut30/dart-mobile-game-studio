#!/usr/bin/env bash
#
# verify-flutter-project.sh — detect a Flutter/Dart project and run SAFE, read-only quality gates:
# format check, analyze, and tests. Never mutates source. Degrades gracefully when the toolchain or
# a project is absent (prints the exact commands instead of failing).
#
# Usage:
#   scripts/verify-flutter-project.sh                 # discover + analyze + test in the current dir
#   ROOT=path/to/app scripts/verify-flutter-project.sh
#   ACTION=analyze scripts/verify-flutter-project.sh  # analyze only (skip tests)
#
# Env: ROOT (default cwd), ACTION = all|analyze|test (default all).
#
set -uo pipefail

ROOT="${ROOT:-$(pwd)}"
ACTION="${ACTION:-all}"

echo "== Environment =="
if command -v flutter >/dev/null 2>&1; then flutter --version 2>&1 | head -1; fi
if command -v dart >/dev/null 2>&1; then dart --version 2>&1 | head -1; fi
if ! command -v dart >/dev/null 2>&1 && ! command -v flutter >/dev/null 2>&1; then
  echo "warning: neither 'dart' nor 'flutter' is on PATH — discovery only." >&2
fi
echo

echo "== Discovering Dart/Flutter project under: ${ROOT} =="
PUBSPEC="$(find "${ROOT}" -maxdepth 3 -name pubspec.yaml -not -path '*/.*' 2>/dev/null | head -n 1 || true)"
if [[ -z "${PUBSPEC}" ]]; then
  echo "No pubspec.yaml found under ${ROOT}. Create one with: flutter create <app>  (or: dart create <pkg>)."
  exit 0
fi
PKG_DIR="$(dirname "${PUBSPEC}")"
IS_FLUTTER="no"
grep -qE '^\s*flutter\s*:' "${PUBSPEC}" 2>/dev/null && IS_FLUTTER="yes"
echo "Found: ${PUBSPEC}  (flutter project: ${IS_FLUTTER})"
echo

# Pick the driver: flutter if it's a flutter app, else dart.
if [[ "${IS_FLUTTER}" == "yes" ]] && command -v flutter >/dev/null 2>&1; then DRV="flutter"
elif command -v dart >/dev/null 2>&1; then DRV="dart"
else
  echo "Toolchain not available here. Run these in the project (${PKG_DIR}):"
  echo "  ${IS_FLUTTER:+flutter }pub get"
  echo "  dart format --output=none --set-exit-if-changed ."
  echo "  ${IS_FLUTTER:+flutter analyze || }dart analyze"
  echo "  ${IS_FLUTTER:+flutter test ; }dart test"
  exit 0
fi

run() { echo "+ $*"; ( cd "${PKG_DIR}" && "$@" ); }

echo "== pub get =="
run "${DRV}" pub get || { echo "pub get failed" >&2; exit 1; }
echo

echo "== format check (no writes) =="
run dart format --output=none --set-exit-if-changed . || echo "warning: code is not dart-format clean (run: dart format .)" >&2
echo

if [[ "${ACTION}" == "all" || "${ACTION}" == "analyze" ]]; then
  echo "== analyze =="
  if [[ "${DRV}" == "flutter" ]]; then run flutter analyze; else run dart analyze; fi
  echo
fi

if [[ "${ACTION}" == "all" || "${ACTION}" == "test" ]]; then
  echo "== test =="
  if [[ "${DRV}" == "flutter" ]]; then run flutter test; else run dart test; fi
fi
