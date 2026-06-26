#!/usr/bin/env python3
"""
sync-agents.py — generate tool-specific subagent files from the canonical specs in
.agents/agents/. The canonical files use Claude-Code-compatible frontmatter (name, description,
tools), so:

  * Claude Code  ->  .claude/agents/<name>.md          (verbatim copy)
  * Cursor       ->  .cursor/rules/agents/<name>.mdc    (frontmatter rewritten: description +
                                                         alwaysApply:false; body preserved)

Usage:
    .agents/agents/sync-agents.py            # write both targets
    .agents/agents/sync-agents.py --check    # exit non-zero if any target is out of date
    .agents/agents/sync-agents.py --dry-run  # print what would change, write nothing
"""
from __future__ import annotations

import sys
from pathlib import Path

CANON_DIR = Path(__file__).resolve().parent
REPO_ROOT = CANON_DIR.parents[1]
CLAUDE_DIR = REPO_ROOT / ".claude" / "agents"
CURSOR_DIR = REPO_ROOT / ".cursor" / "rules" / "agents"
SKIP = {"README.md"}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    fm: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm, body


def claude_content(src_text: str) -> str:
    return src_text if src_text.endswith("\n") else src_text + "\n"


def cursor_content(fm: dict, body: str) -> str:
    desc = fm.get("description", fm.get("name", "Dart/Flutter game subagent role."))
    return f"---\ndescription: {desc}\nalwaysApply: false\n---\n\n{body}"


def main(argv: list[str]) -> int:
    check = "--check" in argv
    dry = "--dry-run" in argv
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    CURSOR_DIR.mkdir(parents=True, exist_ok=True)

    sources = sorted(p for p in CANON_DIR.glob("*.md") if p.name not in SKIP)
    if not sources:
        print("error: no canonical agent specs found in .agents/agents/", file=sys.stderr)
        return 1

    drift = False
    written = 0
    for src in sources:
        text = src.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        name = fm.get("name", src.stem)
        targets = {
            CLAUDE_DIR / f"{name}.md": claude_content(text),
            CURSOR_DIR / f"{name}.mdc": cursor_content(fm, body),
        }
        for path, content in targets.items():
            current = path.read_text(encoding="utf-8") if path.exists() else None
            if current == content:
                continue
            drift = True
            rel = path.relative_to(REPO_ROOT)
            if check:
                print(f"DRIFT: {rel} is out of date")
            elif dry:
                print(f"[dry-run] would write {rel}")
            else:
                path.write_text(content, encoding="utf-8")
                written += 1
                print(f"wrote {rel}")

    if check:
        if drift:
            print("Agent copies have drifted. Run: .agents/agents/sync-agents.py", file=sys.stderr)
            return 1
        print(f"All agent copies are in sync ({len(sources)} agents).")
        return 0
    if dry:
        print("dry-run complete." + ("" if drift else " Nothing to change."))
        return 0
    print(f"Done. Synced {len(sources)} agents -> .claude/agents and .cursor/rules/agents "
          f"({written} file(s) updated).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
