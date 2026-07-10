#!/usr/bin/env python3
"""Generate Claude, Cursor, and Codex profiles from canonical agent specs.

The target directories are exact generated mirrors. Check/dry-run modes never create files or
directories; normal sync writes changed files and removes stale generated profiles.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable


SCRIPT_CANON_DIR = Path(__file__).resolve().parent
DEFAULT_REPO_ROOT = SCRIPT_CANON_DIR.parents[1]
SKIP = {"README.md"}

CLAUDE_TIER_MODEL = {"heavy": "opus", "medium": "sonnet", "light": "haiku"}
TIER_LABEL = {"heavy": "Opus-class", "medium": "Sonnet-class", "light": "Haiku-class"}
VALID_TIERS = set(CLAUDE_TIER_MODEL)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    frontmatter: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip()
    return frontmatter, body


def claude_content(frontmatter: dict[str, str], body: str) -> str:
    lines = ["---", f"name: {frontmatter['name']}"]
    if frontmatter.get("description"):
        lines.append(f"description: {frontmatter['description']}")
    if frontmatter.get("tools"):
        lines.append(f"tools: {frontmatter['tools']}")
    lines.append(f"model: {CLAUDE_TIER_MODEL[frontmatter['tier']]}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


def cursor_content(frontmatter: dict[str, str], body: str) -> str:
    description = frontmatter["description"]
    tier = frontmatter["tier"]
    note = (
        f"> **Model tier:** {tier} ({TIER_LABEL[tier]}). Resolve per "
        "`references/model-routing.md`.\n\n"
    )
    return f"---\ndescription: {description}\nalwaysApply: false\n---\n\n{note}{body}"


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def codex_content(frontmatter: dict[str, str], body: str) -> str:
    instructions = body.rstrip() + "\n"
    if "'''" in instructions:
        rendered_instructions = toml_string(instructions)
    else:
        rendered_instructions = "'''\n" + instructions + "'''"
    return (
        f"name = {toml_string(frontmatter['name'])}\n"
        f"description = {toml_string(frontmatter['description'])}\n"
        f"developer_instructions = {rendered_instructions}\n"
    )


def validate_source(path: Path, frontmatter: dict[str, str]) -> list[str]:
    errors: list[str] = []
    name = frontmatter.get("name", "")
    if not name:
        errors.append(f"{path.name}: missing frontmatter name")
    elif name != path.stem:
        errors.append(f"{path.name}: name {name!r} must equal filename {path.stem!r}")
    if not frontmatter.get("description"):
        errors.append(f"{path.name}: missing frontmatter description")
    tier = frontmatter.get("tier", "")
    if tier not in VALID_TIERS:
        errors.append(f"{path.name}: tier {tier!r} must be one of {sorted(VALID_TIERS)}")
    return errors


def expected_outputs(
    canonical_dir: Path,
    repo_root: Path,
) -> tuple[dict[Path, str], dict[Path, str], list[str]]:
    targets: dict[Path, str] = {}
    suffixes: dict[Path, str] = {
        repo_root / ".claude" / "agents": ".md",
        repo_root / ".cursor" / "rules" / "agents": ".mdc",
        repo_root / ".codex" / "agents": ".toml",
    }
    renderers: list[tuple[Path, str, Callable[[dict[str, str], str], str]]] = [
        (repo_root / ".claude" / "agents", ".md", claude_content),
        (repo_root / ".cursor" / "rules" / "agents", ".mdc", cursor_content),
        (repo_root / ".codex" / "agents", ".toml", codex_content),
    ]
    errors: list[str] = []
    sources = sorted(path for path in canonical_dir.glob("*.md") if path.name not in SKIP)
    if not sources:
        return {}, suffixes, [f"no canonical agent specs found in {canonical_dir}"]

    seen_names: set[str] = set()
    for source in sources:
        frontmatter, body = parse_frontmatter(source.read_text(encoding="utf-8"))
        source_errors = validate_source(source, frontmatter)
        errors.extend(source_errors)
        if source_errors:
            continue
        name = frontmatter["name"]
        if name in seen_names:
            errors.append(f"duplicate canonical agent name: {name}")
            continue
        seen_names.add(name)
        for directory, suffix, renderer in renderers:
            targets[directory / f"{name}{suffix}"] = renderer(frontmatter, body)
    return targets, suffixes, errors


def relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Sync canonical game-studio agent profiles.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report drift without writing")
    mode.add_argument("--dry-run", action="store_true", help="show sync actions without writing")
    parser.add_argument("--root", default=str(DEFAULT_REPO_ROOT), help="repository root")
    args = parser.parse_args(argv)

    repo_root = Path(args.root).expanduser().resolve()
    canonical_dir = repo_root / ".agents" / "agents"
    if not repo_root.is_dir() or not canonical_dir.is_dir():
        print(f"error: canonical agent directory not found: {canonical_dir}", file=sys.stderr)
        return 2

    targets, suffixes, errors = expected_outputs(canonical_dir, repo_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    expected_paths = set(targets)
    stale_paths: list[Path] = []
    for directory, suffix in suffixes.items():
        if directory.is_dir():
            stale_paths.extend(sorted(set(directory.glob(f"*{suffix}")) - expected_paths))

    changed_paths: list[Path] = []
    for path, content in sorted(targets.items(), key=lambda item: str(item[0])):
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            changed_paths.append(path)

    drift = bool(changed_paths or stale_paths)
    if args.check:
        for path in changed_paths:
            print(f"DRIFT: {relative(path, repo_root)} is missing or out of date")
        for path in stale_paths:
            print(f"STALE: {relative(path, repo_root)} has no canonical source")
        if drift:
            print("Agent mirrors have drifted. Run: .agents/agents/sync-agents.py", file=sys.stderr)
            return 1
        print(f"All agent mirrors are exact and in sync ({len(targets) // 3} agents x 3 tools).")
        return 0

    if args.dry_run:
        for path in changed_paths:
            print(f"[dry-run] would write {relative(path, repo_root)}")
        for path in stale_paths:
            print(f"[dry-run] would remove stale {relative(path, repo_root)}")
        print("dry-run complete." + ("" if drift else " Nothing to change."))
        return 0

    for directory in suffixes:
        directory.mkdir(parents=True, exist_ok=True)
    for path in stale_paths:
        path.unlink()
        print(f"removed stale {relative(path, repo_root)}")
    for path in changed_paths:
        path.write_text(targets[path], encoding="utf-8")
        print(f"wrote {relative(path, repo_root)}")
    print(
        f"Done. Synced {len(targets) // 3} agents to Claude, Cursor, and Codex "
        f"({len(changed_paths)} written, {len(stale_paths)} stale removed)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
