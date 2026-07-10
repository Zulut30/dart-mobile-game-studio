#!/usr/bin/env python3
"""ai-context-pack - build a compact context pack for coding agents.

Dependency-free: Python 3 standard library only. The pack is intended to be
read before a Dart/Flutter mobile-game task so an agent does not have to infer
the repo shape, project modes, command contract, rules, and current findings
from scratch every time.

Usage:
    ai-context-pack.py [PATH] [--json | --markdown] [--project PATH]
                       [--no-findings] [--output PATH] [-h|--help]

Defaults to Markdown on stdout. Use --json for machine consumers.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys

TOOL_NAME = "ai-context-pack"
TOOL_VERSION = "0.1"

EXCLUDED_DIR_NAMES = {".dart_tool", ".git", ".idea", ".vscode", "build", "ios", "linux", "macos", "windows"}


def read(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def rel(path: str, root: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def walk(root: str, suffix: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIR_NAMES and not d.startswith(".")]
        for fn in filenames:
            if fn.endswith(suffix):
                yield os.path.join(dirpath, fn)


def run(cmd: list[str], cwd: str, timeout: int = 30) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None


def run_json(cmd: list[str], cwd: str, timeout: int = 30):
    result = run(cmd, cwd, timeout)
    if result is None:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "invalid-json", "returncode": result.returncode, "stderr": result.stderr.strip()[:500]}


def first_match(text: str, pattern: str, default: str = "") -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else default


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    lines = []
    for line in text.splitlines():
        idx = line.find("//")
        if idx >= 0 and not re.search(r"https?:$", line[:idx]):
            line = line[:idx]
        lines.append(line)
    return "\n".join(lines)


def parse_frontmatter(path: str) -> dict[str, str]:
    text = read(path)
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    fields = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def skill_dir() -> str:
    return os.path.abspath(os.path.join(script_dir(), ".."))


def repo_root_from_skill() -> str:
    return os.path.abspath(os.path.join(skill_dir(), "../../.."))


def discover_projects(root: str) -> list[str]:
    discover = os.path.join(script_dir(), "discover-projects.sh")
    if os.path.isfile(discover):
        result = run([discover, "--root", root, "--all", "--dirs"], cwd=root)
        if result and result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    root_pubspec = os.path.join(root, "pubspec.yaml")
    if os.path.isfile(root_pubspec):
        return [root]
    return sorted({os.path.dirname(p) for p in walk(root, "pubspec.yaml")})


def list_skill_files(subdir: str, suffix: str | None = None) -> list[str]:
    base = os.path.join(skill_dir(), subdir)
    if not os.path.isdir(base):
        return []
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
        for fn in filenames:
            if suffix is None or fn.endswith(suffix):
                out.append(rel(os.path.join(dirpath, fn), repo_root_from_skill()))
    return sorted(out)


def tool_version(exe: str) -> str:
    path = shutil.which(exe)
    if not path:
        return ""
    result = run([path, "--version"], cwd=repo_root_from_skill(), timeout=10)
    if result and (result.stdout or result.stderr):
        return (result.stdout + result.stderr).splitlines()[0][:200]
    return path


def git_state(root: str) -> dict[str, object]:
    inside = run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root)
    if not inside or inside.returncode != 0:
        return {"is_repo": False}
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    status = run(["git", "status", "--porcelain"], cwd=root)
    changed = status.stdout.splitlines() if status else []
    return {
        "is_repo": True,
        "branch": branch.stdout.strip() if branch else "",
        "dirty_count": len(changed),
        "has_untracked_codex_dir": any(line.endswith(" .codex/") or line == "?? .codex/" for line in changed),
    }


def project_source_text(project: str) -> str:
    parts = []
    for path in walk(os.path.join(project, "lib"), ".dart"):
        parts.append(strip_comments(read(path)))
    return "\n".join(parts)


def infer_mode(pubspec_text: str, src: str) -> str:
    is_flutter = bool(re.search(r"(?m)^\s*flutter\s*:", pubspec_text))
    uses_flame = "package:flame/" in src or bool(re.search(r"(?m)^\s*flame\s*:", pubspec_text))
    has_game_widget = "GameWidget" in src
    has_update_loop = bool(re.search(r"\bupdate\s*\(\s*double\s+dt\b", src))
    if uses_flame and has_game_widget:
        return "flame-hybrid"
    if uses_flame or has_update_loop:
        return "flame"
    if is_flutter:
        return "flutter-widgets"
    return "dart-package"


def project_commands(project_rel: str, mode: str) -> dict[str, str]:
    flutterish = mode in {"flutter-widgets", "flame", "flame-hybrid"}
    pub = "flutter pub get" if flutterish else "dart pub get"
    analyze = "flutter analyze" if flutterish else "dart analyze"
    test = "flutter test" if flutterish else "dart test"
    return {
        "pub_get": f"(cd {project_rel} && {pub})",
        "format_check": f"(cd {project_rel} && dart format --output=none --set-exit-if-changed .)",
        "analyze": f"(cd {project_rel} && {analyze})",
        "test": f"(cd {project_rel} && {test})",
        "dart_doctor": f".agents/skills/dart-mobile-game-studio/scripts/dart-doctor.py {project_rel}",
        "design_doctor": f".agents/skills/dart-mobile-game-studio/scripts/design-doctor.py {project_rel}",
    }


def recommended_for_mode(mode: str) -> dict[str, list[str]]:
    common_refs = [
        ".agents/skills/dart-mobile-game-studio/references/dart/README.md",
        ".agents/skills/dart-mobile-game-studio/references/flutter-game-architecture.md",
        ".agents/skills/dart-mobile-game-studio/references/accessibility-child-safety.md",
        ".agents/skills/dart-mobile-game-studio/references/common-pitfalls.md",
    ]
    if mode == "flame-hybrid":
        return {
            "agents": ["game-designer", "engine-architect", "gameplay-programmer", "performance-auditor", "qa-tester"],
            "read_first": common_refs
            + [
                ".agents/skills/dart-mobile-game-studio/references/flutter-flame-patterns.md",
                ".agents/skills/dart-mobile-game-studio/templates/endless-runner.md",
            ],
        }
    if mode == "flame":
        return {
            "agents": ["engine-architect", "gameplay-programmer", "performance-auditor", "qa-tester"],
            "read_first": common_refs + [".agents/skills/dart-mobile-game-studio/references/flutter-flame-patterns.md"],
        }
    return {
        "agents": ["game-designer", "engine-architect", "gameplay-programmer", "qa-tester"],
        "read_first": common_refs + [".agents/skills/dart-mobile-game-studio/references/ui-and-animations.md"],
    }


def collect_project(project: str, root: str) -> dict[str, object]:
    pubspec = os.path.join(project, "pubspec.yaml")
    pubspec_text = read(pubspec)
    src = project_source_text(project)
    project_rel = rel(project, root)
    mode = infer_mode(pubspec_text, src)
    tests = list(walk(os.path.join(project, "test"), ".dart"))
    lib_files = list(walk(os.path.join(project, "lib"), ".dart"))
    rec = recommended_for_mode(mode)
    return {
        "name": first_match(pubspec_text, r"^name:\s*(.+)$", os.path.basename(project)),
        "path": project_rel,
        "pubspec": rel(pubspec, root),
        "mode": mode,
        "is_flutter": bool(re.search(r"(?m)^\s*flutter\s*:", pubspec_text)),
        "uses_flame": mode in {"flame", "flame-hybrid"},
        "source_files": len(lib_files),
        "test_files": len(tests),
        "has_core_dirs": {
            "models": os.path.isdir(os.path.join(project, "lib", "models")),
            "systems": os.path.isdir(os.path.join(project, "lib", "systems")),
            "game": os.path.isdir(os.path.join(project, "lib", "game")),
            "widgets": os.path.isdir(os.path.join(project, "lib", "widgets")),
        },
        "has_accessibility_guideline_tests": all(
            term in "\n".join(read(p) for p in tests)
            for term in ("meetsGuideline", "labeledTapTargetGuideline", "textContrastGuideline")
        ),
        "commands": project_commands(project_rel, mode),
        "recommended_agents": rec["agents"],
        "read_first": rec["read_first"],
    }


def collect_agents(root: str) -> list[dict[str, str]]:
    base = os.path.join(root, ".agents", "agents")
    agents = []
    if not os.path.isdir(base):
        return agents
    for path in sorted(walk(base, ".md")):
        if os.path.basename(path) == "README.md":
            continue
        fm = parse_frontmatter(path)
        agents.append(
            {
                "name": fm.get("name", os.path.basename(path)[:-3]),
                "tier": fm.get("tier", ""),
                "description": fm.get("description", "")[:220],
                "path": rel(path, root),
            }
        )
    return agents


def display_project_path(project: str, root: str) -> str:
    if os.path.isabs(project):
        try:
            return rel(project, root)
        except ValueError:
            return project
    return project


def flatten_design_warnings(design_report, root: str) -> list[dict[str, str]]:
    warnings = []
    if not isinstance(design_report, dict):
        return warnings
    projects = design_report.get("projects", {})
    for project, dimensions in projects.items():
        for dim, findings in dimensions.items():
            for finding in findings:
                if finding.get("status") == "WARN":
                    warnings.append(
                        {
                            "project": display_project_path(project, root),
                            "dimension": dim,
                            "title": finding.get("title", ""),
                            "detail": finding.get("detail", ""),
                        }
                    )
    return warnings


def flatten_dart_warnings(dart_reports: dict[str, object]) -> list[dict[str, str]]:
    warnings = []
    for project, report in dart_reports.items():
        if not isinstance(report, dict):
            continue
        for dim, findings in report.get("dimensions", {}).items():
            for finding in findings:
                if finding.get("status") in {"WARN", "FAIL"}:
                    warnings.append(
                        {
                            "project": project,
                            "dimension": dim,
                            "status": finding.get("status", ""),
                            "title": finding.get("title", ""),
                            "detail": finding.get("detail", ""),
                        }
                    )
    return warnings


def collect_findings(root: str, projects: list[dict[str, object]]) -> dict[str, object]:
    design_script = os.path.join(script_dir(), "design-doctor.py")
    dart_script = os.path.join(script_dir(), "dart-doctor.py")
    design = run_json([design_script, root, "--json"], cwd=root) if os.path.isfile(design_script) else None
    dart_reports = {}
    if os.path.isfile(dart_script):
        for project in projects:
            path = str(project["path"])
            dart_reports[path] = run_json([dart_script, path, "--json"], cwd=root)
    return {
        "design_doctor": {
            "summary": design.get("summary", {}) if isinstance(design, dict) else {},
            "warnings": flatten_design_warnings(design, root),
        },
        "dart_doctor": {
            "reports": dart_reports,
            "warnings": flatten_dart_warnings(dart_reports),
        },
    }


def collect_pack(root: str, project_filter: str = "", include_findings: bool = True) -> dict[str, object]:
    root = os.path.abspath(root)
    all_projects = [collect_project(p, root) for p in discover_projects(root)]
    if project_filter:
        wanted = rel(os.path.abspath(project_filter), root) if os.path.isabs(project_filter) else project_filter.rstrip("/")
        all_projects = [p for p in all_projects if p["path"] == wanted or str(p["path"]).endswith("/" + wanted)]

    pack = {
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "repo": {
            "root": root,
            "type": "dart-mobile-game-studio",
            "skill": rel(skill_dir(), root) if skill_dir().startswith(root) else skill_dir(),
            "git": git_state(root),
        },
        "toolchain": {
            "dart": tool_version("dart"),
            "flutter": tool_version("flutter"),
            "python": sys.version.split()[0],
        },
        "rules": {
            "core": "Game rules live in pure Dart under models/systems/core; no package:flutter or package:flame imports.",
            "mode": "Use Flutter widgets for static/turn-based games, Flame for continuous motion, hybrid for Flame gameplay with Flutter HUD/menus.",
            "tests": "Unit-test pure core; widget-test key screens; run analyze/test only when the toolchain is actually available.",
            "kids": "No ads, tracking, accounts, external links, AdvertisingId/IDFA/GAID, dark patterns, or personal data for kids builds.",
            "a11y": "Semantics labels/values on controls, text scaling, Reduce Motion, tap targets, contrast, not color alone.",
            "assets": "No copyrighted assets; use placeholders or user-owned assets and keep levels as data.",
        },
        "projects": all_projects,
        "inventory": {
            "scripts": list_skill_files("scripts"),
            "references": list_skill_files("references", ".md"),
            "templates": list_skill_files("templates", ".md"),
            "workflows": list_skill_files("workflows", ".md"),
            "checklists": list_skill_files("checklists", ".md"),
            "assets": list_skill_files("assets"),
            "agents": collect_agents(root),
        },
        "agent_boot_sequence": [
            "Read AGENTS.md and .agents/skills/dart-mobile-game-studio/SKILL.md.",
            "Run ai-context-pack.py --markdown before large edits.",
            "Use task-specific read_first references from the selected project or task router.",
            "Edit the pure-Dart core before renderer code; keep Flutter/Flame thin.",
            "Run design-doctor.py and dart-doctor.py, then verify-flutter-project.sh when toolchain exists.",
        ],
    }
    if include_findings:
        pack["findings"] = collect_findings(root, all_projects)
    return pack


def md_list(items: list[str], limit: int = 12) -> list[str]:
    out = [f"- `{item}`" for item in items[:limit]]
    if len(items) > limit:
        out.append(f"- ... {len(items) - limit} more")
    return out


def render_markdown(pack: dict[str, object]) -> str:
    repo = pack["repo"]
    toolchain = pack["toolchain"]
    lines = [
        "# AI Context Pack",
        "",
        f"- Repo: `{repo['root']}`",
        f"- Type: `{repo['type']}`",
        f"- Skill: `{repo['skill']}`",
        f"- Git: branch `{repo['git'].get('branch', '')}`, dirty `{repo['git'].get('dirty_count', 0)}`",
        f"- Toolchain: dart `{toolchain.get('dart') or 'missing'}`, flutter `{toolchain.get('flutter') or 'missing'}`",
        "",
        "## Non-Negotiable Rules",
    ]
    for key, value in pack["rules"].items():
        lines.append(f"- **{key}:** {value}")

    lines += ["", "## Projects"]
    for project in pack["projects"]:
        lines += [
            f"### `{project['path']}`",
            f"- name: `{project['name']}`",
            f"- mode: `{project['mode']}`",
            f"- files: `{project['source_files']}` source, `{project['test_files']}` test",
            f"- a11y guideline tests: `{project['has_accessibility_guideline_tests']}`",
            "- commands:",
        ]
        for name, cmd in project["commands"].items():
            lines.append(f"  - `{name}`: `{cmd}`")
        lines.append("- read first:")
        lines += [f"  - `{p}`" for p in project["read_first"][:8]]
        lines.append("- agents: " + ", ".join(f"`{a}`" for a in project["recommended_agents"]))
        lines.append("")

    inventory = pack["inventory"]
    lines += [
        "## Skill Inventory",
        f"- scripts: `{len(inventory['scripts'])}`",
        f"- references: `{len(inventory['references'])}`",
        f"- templates: `{len(inventory['templates'])}`",
        f"- workflows: `{len(inventory['workflows'])}`",
        f"- checklists: `{len(inventory['checklists'])}`",
        f"- agents: `{len(inventory['agents'])}`",
        "",
        "## Key Scripts",
    ]
    lines += md_list(inventory["scripts"], 16)

    if "findings" in pack:
        design = pack["findings"]["design_doctor"]
        dart = pack["findings"]["dart_doctor"]
        lines += ["", "## Current Findings"]
        lines.append(f"- design-doctor summary: `{design.get('summary', {})}`")
        for warning in design.get("warnings", [])[:10]:
            lines.append(
                f"  - `{warning['dimension']}` in `{warning['project']}`: {warning['title']} - {warning['detail']}"
            )
        lines.append(f"- dart-doctor warnings/fails: `{len(dart.get('warnings', []))}`")
        for warning in dart.get("warnings", [])[:10]:
            lines.append(
                f"  - `{warning['status']}` `{warning['dimension']}` in `{warning['project']}`: {warning['title']} - {warning['detail']}"
            )

    lines += ["", "## Agent Boot Sequence"]
    for step in pack["agent_boot_sequence"]:
        lines.append(f"- {step}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(prog=TOOL_NAME, description="Generate an AI context pack for this studio repo.")
    ap.add_argument("path", nargs="?", default=".", help="repo or project root (default: .)")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true", help="emit JSON")
    group.add_argument("--markdown", action="store_true", help="emit Markdown (default)")
    ap.add_argument("--project", default="", help="limit output to one project path")
    ap.add_argument("--no-findings", action="store_true", help="skip dart-doctor/design-doctor summaries")
    ap.add_argument("--output", default="", help="write output to this file instead of stdout")
    args = ap.parse_args()

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f"{TOOL_NAME}: not a directory: {root}", file=sys.stderr)
        return 2

    pack = collect_pack(root, args.project, include_findings=not args.no_findings)
    payload = json.dumps(pack, indent=2, ensure_ascii=False) + "\n" if args.json else render_markdown(pack)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(payload)
        except OSError as e:
            print(f"{TOOL_NAME}: could not write {args.output}: {e}", file=sys.stderr)
            return 2
    else:
        print(payload, end="" if payload.endswith("\n") else "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
