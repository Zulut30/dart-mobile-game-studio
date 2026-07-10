#!/usr/bin/env bash
#
# discover-projects.sh — list Dart/Flutter pubspec.yaml files under a root.
#
# This repo can contain several buildable examples/packages. Keep project discovery
# in one place so verify/preflight/pub-get agree on what "the project" means.
#
# Usage:
#   scripts/discover-projects.sh                  # first selected pubspec
#   scripts/discover-projects.sh --all            # all pubspec.yaml files
#   scripts/discover-projects.sh --dirs --all     # project directories
#   scripts/discover-projects.sh --json --all     # machine-readable list
#   scripts/discover-projects.sh --root path
#
# Selection:
# - If ROOT/pubspec.yaml exists, it is listed first.
# - Otherwise nested pubspecs are listed in stable sorted order.
#
set -uo pipefail

ROOT="$(pwd)"
ALL="no"
DIRS="no"
JSON="no"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ROOT="${2:?--root needs a path}"; shift 2 ;;
    --root=*) ROOT="${1#*=}"; shift ;;
    --all) ALL="yes"; shift ;;
    --dirs) DIRS="yes"; shift ;;
    --json) JSON="yes"; shift ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ ! -d "${ROOT}" ]]; then
  echo "discover-projects: root not found: ${ROOT}" >&2
  exit 2
fi

ROOT="$(cd "${ROOT}" && pwd)"
root_pubspec="${ROOT}/pubspec.yaml"

pubspecs=()
if [[ -f "${root_pubspec}" ]]; then
  pubspecs+=("${root_pubspec}")
fi

while IFS= read -r p; do
  [[ "${p}" == "${root_pubspec}" ]] && continue
  pubspecs+=("${p}")
done < <(
  find "${ROOT}" \
    \( -path '*/.*' -o -path '*/build/*' -o -path '*/.dart_tool/*' \) -prune -o \
    -type f -name pubspec.yaml -print 2>/dev/null | sort
)

if [[ "${ALL}" != "yes" && ${#pubspecs[@]} -gt 1 ]]; then
  pubspecs=("${pubspecs[0]}")
fi

emit_value() {
  local p="$1"
  if [[ "${DIRS}" == "yes" ]]; then
    dirname "${p}"
  else
    printf '%s\n' "${p}"
  fi
}

if [[ "${JSON}" == "yes" ]]; then
  printf '['
  first="yes"
  for p in "${pubspecs[@]}"; do
    if [[ "${first}" == "yes" ]]; then first="no"; else printf ','; fi
    v="$(emit_value "${p}")"
    v="${v//\\/\\\\}"
    v="${v//\"/\\\"}"
    printf '"%s"' "${v}"
  done
  printf ']\n'
else
  for p in "${pubspecs[@]}"; do
    emit_value "${p}"
  done
fi
