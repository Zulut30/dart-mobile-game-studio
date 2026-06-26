#!/usr/bin/env bash
#
# pub-get-if-changed.sh — skip the slow `pub get` when dependencies haven't changed.
#
# `flutter pub get` (and a cold `flutter clean`) is the classic "cure-all" but it is slow — re-running
# it on every workflow step wastes minutes. This caches a hash of the resolved-dependency inputs
# (pubspec.lock + pubspec.yaml) under the project's gitignored .dart_tool/. If the hash is unchanged
# AND packages are already resolved (package_config.json exists), it SKIPS pub get and exits 0. That
# turns a 5-minute init into a sub-second no-op when nothing moved.
#
# It is safe: it only ever runs the project's own `pub get` (never clean/destructive), and the cache
# lives in .dart_tool/ (already gitignored by Flutter/Dart), so it never touches tracked files.
#
# Usage:
#   scripts/pub-get-if-changed.sh                 # discover project; pub get only if inputs changed
#   scripts/pub-get-if-changed.sh --root path/to/app
#   scripts/pub-get-if-changed.sh --check-only    # don't run; exit 0 = up-to-date, 10 = stale
#   scripts/pub-get-if-changed.sh --force         # always run pub get and refresh the cache
#
# Exit: 0 = up-to-date or pub get succeeded; 10 = (--check-only) stale; 1 = pub get failed; 2 = usage.
#
set -uo pipefail

ROOT="$(pwd)"
CHECK_ONLY="no"
FORCE="no"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ROOT="${2:?--root needs a path}"; shift 2 ;;
    --root=*) ROOT="${1#*=}"; shift ;;
    --check-only) CHECK_ONLY="yes"; shift ;;
    --force) FORCE="yes"; shift ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# locate the project (nearest pubspec.yaml under ROOT)
PUBSPEC="$(find "${ROOT}" -maxdepth 3 -name pubspec.yaml -not -path '*/.*' 2>/dev/null | head -n 1 || true)"
if [[ -z "${PUBSPEC}" ]]; then
  echo "no pubspec.yaml under ${ROOT} — nothing to resolve (scaffold with flutter/dart create first)" >&2
  exit 0
fi
PKG_DIR="$(dirname "${PUBSPEC}")"
IS_FLUTTER="no"; grep -qE '^\s*flutter\s*:' "${PUBSPEC}" 2>/dev/null && IS_FLUTTER="yes"

# portable sha256 over the dependency-defining files
sha_of() {
  local f="$1"
  [[ -f "${f}" ]] || { printf 'absent'; return; }
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "${f}" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then sha256sum "${f}" | awk '{print $1}'
  else cksum "${f}" | awk '{print $1"-"$2}'; fi   # weak fallback, still change-detecting
}

HASH_NOW="$(sha_of "${PKG_DIR}/pubspec.yaml")-$(sha_of "${PKG_DIR}/pubspec.lock")"
CACHE="${PKG_DIR}/.dart_tool/.skill_pub_hash"
RESOLVED="${PKG_DIR}/.dart_tool/package_config.json"
HASH_WAS="$( [[ -f "${CACHE}" ]] && cat "${CACHE}" 2>/dev/null || echo "" )"

is_up_to_date() {
  [[ "${FORCE}" == "no" ]] && [[ -f "${RESOLVED}" ]] && [[ -n "${HASH_WAS}" ]] && [[ "${HASH_WAS}" == "${HASH_NOW}" ]]
}

if is_up_to_date; then
  echo "deps up-to-date (pubspec.lock unchanged, packages resolved) — skipping pub get"
  exit 0
fi

if [[ "${CHECK_ONLY}" == "yes" ]]; then
  echo "deps STALE — pub get needed (lock changed or packages not resolved)"
  exit 10
fi

# choose driver and run the project's own pub get
if [[ "${IS_FLUTTER}" == "yes" ]] && command -v flutter >/dev/null 2>&1; then DRV="flutter"
elif command -v dart >/dev/null 2>&1; then DRV="dart"
else
  echo "toolchain absent — run in ${PKG_DIR}:  ${IS_FLUTTER:+flutter }pub get" >&2
  exit 1
fi

echo "+ (cd ${PKG_DIR} && ${DRV} pub get)"
if ( cd "${PKG_DIR}" && "${DRV}" pub get ); then
  # refresh the cache only on success, and only with the POST-resolution lock hash
  HASH_AFTER="$(sha_of "${PKG_DIR}/pubspec.yaml")-$(sha_of "${PKG_DIR}/pubspec.lock")"
  mkdir -p "${PKG_DIR}/.dart_tool"
  printf '%s' "${HASH_AFTER}" > "${CACHE}"
  echo "pub get OK — dependency hash cached for next run"
  exit 0
else
  echo "pub get FAILED" >&2
  exit 1
fi
