#!/usr/bin/env python3
"""Validate canonical Markdown links and skill-local inline path references."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


TOOL_NAME = "doc-doctor"
TOOL_VERSION = "0.1"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = SCRIPT_DIR.parents[3]
SKILL_PREFIXES = {"assets", "references", "workflows", "checklists", "templates", "scripts"}
ROOT_PREFIXES = {".agents", ".claude", ".cursor", ".codex", "examples", "docs", "tests"}
PATH_PATTERN = re.compile(
    r"(?<![\w./-])((?:(?:\.\.?/)+)?(?:\.agents|\.claude|\.cursor|\.codex|assets|references|"
    r"workflows|checklists|templates|scripts|examples|docs|tests)/[A-Za-z0-9_.*/-]+)"
)
MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
INLINE_CODE_PATTERN = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")


def markdown_files(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for path in (root / "README.md", root / "AGENTS.md"):
        if path.is_file():
            candidates.append(path)
    for directory in (
        root / ".agents" / "agents",
        root / ".agents" / "skills" / "dart-mobile-game-studio",
        root / "docs",
    ):
        if directory.is_dir():
            candidates.extend(directory.rglob("*.md"))
    return sorted(set(path.resolve() for path in candidates))


def clean_link_destination(raw: str) -> str:
    value = raw.strip()
    if value.startswith("<") and ">" in value:
        value = value[1:value.index(">")]
    else:
        value = value.split(maxsplit=1)[0]
    return unquote(value.split("#", 1)[0].split("?", 1)[0])


def candidate_paths(path: Path) -> list[Path]:
    candidates = [path]
    if path.suffix == "":
        candidates.append(path.with_suffix(".md"))
    return candidates


def path_exists(path: Path) -> bool:
    return any(candidate.exists() for candidate in candidate_paths(path))


def resolve_markdown_link(source: Path, destination: str, root: Path) -> Path | None:
    if not destination or destination.startswith(("#", "http://", "https://", "mailto:", "data:")):
        return None
    path = Path(destination)
    if path.is_absolute():
        return path
    return (source.parent / path).resolve()


def resolve_inline_path(source: Path, token: str, root: Path, skill_root: Path) -> Path | None:
    if any(marker in token for marker in ("*", "<", ">", "$", "{", "}")):
        return None
    token = token.rstrip(".,:;)")
    first = token.split("/", 1)[0]
    if token.startswith(("./", "../")):
        return (source.parent / token).resolve()
    if first in ROOT_PREFIXES:
        candidate = (root / token).resolve()
        return candidate if candidate.exists() or Path(token).suffix else None
    if first in SKILL_PREFIXES:
        # Asset paths in workflow examples often describe a future app. Check them only when they
        # are explicit file references from canonical role/entrypoint docs.
        if first == "assets" and not (
            source.parent == root / ".agents" / "agents"
            or source == skill_root / "SKILL.md"
        ):
            return None
        if first == "templates" and not (
            Path(token).suffix
            or source.parent == root / ".agents" / "agents"
            or source == skill_root / "SKILL.md"
        ):
            return None
        return (skill_root / token).resolve()
    return None


def finding(source: Path, root: Path, line: int, kind: str, target: str) -> dict:
    try:
        relative = source.relative_to(root).as_posix()
    except ValueError:
        relative = str(source)
    return {
        "file": relative,
        "line": line,
        "kind": kind,
        "target": target,
        "message": f"missing local target: {target}",
    }


def scan_file(source: Path, root: Path, skill_root: Path) -> tuple[list[dict], int, int]:
    findings: list[dict] = []
    markdown_links = 0
    inline_paths = 0
    in_fence = False
    for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        for match in MARKDOWN_LINK_PATTERN.finditer(line):
            destination = clean_link_destination(match.group(1))
            resolved = resolve_markdown_link(source, destination, root)
            if resolved is None:
                continue
            markdown_links += 1
            if not path_exists(resolved):
                findings.append(finding(source, root, line_number, "markdown-link", destination))

        for code_match in INLINE_CODE_PATTERN.finditer(line):
            for path_match in PATH_PATTERN.finditer(code_match.group(1)):
                token = path_match.group(1)
                resolved = resolve_inline_path(source, token, root, skill_root)
                if resolved is None:
                    continue
                inline_paths += 1
                if not path_exists(resolved):
                    findings.append(finding(source, root, line_number, "inline-path", token))
    return findings, markdown_links, inline_paths


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Validate canonical documentation path integrity.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="repository root")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    skill_root = root / ".agents" / "skills" / "dart-mobile-game-studio"
    if not root.is_dir() or not skill_root.is_dir():
        print(f"{TOOL_NAME}: skill root not found under {root}", file=sys.stderr)
        return 2

    files = markdown_files(root)
    all_findings: list[dict] = []
    markdown_count = 0
    inline_count = 0
    for source in files:
        try:
            file_findings, links, inline = scan_file(source, root, skill_root)
        except (OSError, UnicodeError) as exc:
            print(f"{TOOL_NAME}: cannot read {source}: {exc}", file=sys.stderr)
            return 2
        all_findings.extend(file_findings)
        markdown_count += links
        inline_count += inline

    payload = {
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "root": str(root),
        "summary": {
            "files": len(files),
            "markdown_links": markdown_count,
            "inline_paths": inline_count,
            "errors": len(all_findings),
        },
        "findings": all_findings,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for item in all_findings:
            print(f"{item['file']}:{item['line']}: {item['kind']}: {item['target']}")
        summary = payload["summary"]
        print(
            f"Scanned {summary['files']} files, {summary['markdown_links']} Markdown links, "
            f"{summary['inline_paths']} inline paths: {summary['errors']} error(s)."
        )
    return 1 if all_findings else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
