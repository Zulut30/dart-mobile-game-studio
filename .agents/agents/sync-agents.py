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

# Tier → tool-specific model. The canonical specs carry a tool-AGNOSTIC `tier`
# (heavy/medium/light); each tool resolves it to its own model line. Change a model
# here, not in 14 files. Claude Code reads `model:` from agent frontmatter.
# (Cross-vendor mapping for Codex/GPT lives in references/model-routing.md.)
CLAUDE_TIER_MODEL = {"heavy": "opus", "medium": "sonnet", "light": "haiku"}
TIER_LABEL = {"heavy": "Opus-class", "medium": "Sonnet-class", "light": "Haiku-class"}
VALID_TIERS = set(CLAUDE_TIER_MODEL)


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


def claude_content(fm: dict, body: str) -> str:
    """Rebuild Claude frontmatter, resolving `tier` → `model:` and dropping `tier`
    (Claude Code understands `model:`, not our tool-agnostic `tier`)."""
    lines = ["---", f"name: {fm['name']}"]
    if "description" in fm:
        lines.append(f"description: {fm['description']}")
    if "tools" in fm:
        lines.append(f"tools: {fm['tools']}")
    model = CLAUDE_TIER_MODEL.get(fm.get("tier", ""))
    if model:
        lines.append(f"model: {model}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body


def cursor_content(fm: dict, body: str) -> str:
    desc = fm.get("description", fm.get("name", "Dart/Flutter game subagent role."))
    tier = fm.get("tier", "")
    note = ""
    if tier in TIER_LABEL:
        note = (f"> **Model tier:** {tier} ({TIER_LABEL[tier]}). Resolve per "
                f"`references/model-routing.md`.\n\n")
    return f"---\ndescription: {desc}\nalwaysApply: false\n---\n\n{note}{body}"


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
        tier = fm.get("tier", "")
        if tier not in VALID_TIERS:
            print(f"warning: {src.name} has no valid tier "
                  f"(got {tier!r}; expected one of {sorted(VALID_TIERS)})", file=sys.stderr)
        targets = {
            CLAUDE_DIR / f"{name}.md": claude_content(fm, body),
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
