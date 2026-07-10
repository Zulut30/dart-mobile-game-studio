#!/usr/bin/env python3
"""task-router - route a user task to workflows, references, agents, and checks.

Dependency-free: Python 3 standard library only. It consumes the local
ai-context-pack output so routing decisions are grounded in the current repo
shape instead of hard-coded guesses.

Usage:
    task-router.py "add levels to memory match" [--json | --markdown]
    task-router.py --project examples/endless_runner "add pause overlay"
    task-router.py --stdin --json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

TOOL_NAME = "task-router"
TOOL_VERSION = "0.3"


def script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def repo_root_from_skill() -> str:
    return os.path.abspath(os.path.join(script_dir(), "../../../.."))


def rel(path: str, root: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def run_json(cmd: list[str], cwd: str):
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"error": str(e)}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "invalid json", "stderr": result.stderr.strip()[:500]}


def load_context(root: str) -> dict:
    script = os.path.join(script_dir(), "ai-context-pack.py")
    return run_json([script, root, "--json", "--no-findings"], cwd=root)


def norm(text: str) -> str:
    return " ".join(re.findall(r"[^\W_]+", text.lower(), flags=re.UNICODE))


def keyword_matches(keyword: str, text: str) -> bool:
    """Match whole tokens/phrases; a trailing * explicitly opts into prefix matching."""
    normalized_text = norm(text)
    tokens = normalized_text.split()
    raw_keyword = keyword.strip().lower()
    prefix = raw_keyword.endswith("*")
    normalized_keyword = norm(raw_keyword[:-1] if prefix else raw_keyword)
    if not normalized_keyword:
        return False
    keyword_tokens = normalized_keyword.split()
    if prefix and len(keyword_tokens) == 1:
        return any(token.startswith(keyword_tokens[0]) for token in tokens)
    if len(keyword_tokens) == 1:
        return keyword_tokens[0] in tokens
    width = len(keyword_tokens)
    return any(tokens[index:index + width] == keyword_tokens for index in range(len(tokens) - width + 1))


def contains(text: str, words: list[str]) -> bool:
    return any(keyword_matches(word, text) for word in words)


def score(words: list[str], text: str) -> int:
    return sum(1 for word in words if keyword_matches(word, text))


ROUTES = [
    {
        "type": "create-game",
        "keywords": [
            "new game", "create game", "create a game", "build game", "build a game", "start game",
            "новая игра", "новую игру", "создай*", "сделай игру", "mvp",
        ],
        "workflows": ["create-new-game.md", "choose-game-architecture.md", "setup-flutter-project.md"],
        "references": ["game-development-pipeline.md", "game-templates.md", "flutter-game-architecture.md", "dart/README.md"],
        "templates": ["casual.md", "puzzle.md", "endless-runner.md", "educational-kids.md"],
        "agents": ["game-coordinator", "game-designer", "engine-architect", "gameplay-programmer", "qa-tester"],
    },
    {
        "type": "add-level-system",
        "keywords": ["level", "levels", "level system", "json", "уров*", "карта уров*", "level select"],
        "workflows": ["add-level-system.md"],
        "references": ["asset-pipeline.md", "game-templates.md", "testing-and-release.md"],
        "templates": ["puzzle.md", "quiz.md", "educational-kids.md"],
        "agents": ["engine-architect", "gameplay-programmer", "qa-tester"],
        "checks": ["validate-levels.py"],
    },
    {
        "type": "balance-tuning",
        "keywords": [
            "balance", "difficulty", "difficulty curve", "tuning", "pacing", "win rate",
            "spawn curve", "game economy", "баланс*", "сложност*", "настройка сложности",
            "темп", "винрейт", "экономика игры",
        ],
        "workflows": ["add-level-system.md"],
        "references": ["game-templates.md", "flutter-game-architecture.md", "testing-and-release.md"],
        "templates": ["endless-runner.md", "platformer-flame.md", "puzzle.md"],
        "agents": ["balance-economist", "game-designer", "gameplay-programmer", "qa-tester"],
        "checks": ["validate-levels.py", "dart-doctor.py"],
    },
    {
        "type": "add-save-system",
        "keywords": ["save", "saving", "persistence", "progress", "сохран*", "прогресс", "shared preferences"],
        "workflows": ["add-save-system.md"],
        "references": ["flutter-game-architecture.md", "quality-policy.md", "accessibility-child-safety.md"],
        "agents": ["engine-architect", "gameplay-programmer", "qa-tester"],
    },
    {
        "type": "state-management",
        "keywords": [
            "state management", "provider", "riverpod", "bloc", "cubit", "change notifier",
            "value notifier", "ui state", "управление состоянием", "состояние приложения",
            "провайдер", "риверпод",
        ],
        "workflows": ["add-state-management.md"],
        "references": ["flutter-game-architecture.md", "dart/dart-patterns-idioms.md", "quality-policy.md"],
        "agents": ["engine-architect", "gameplay-programmer", "qa-tester"],
        "checks": ["dart-doctor.py", "design-doctor.py"],
    },
    {
        "type": "flame-gameplay",
        "keywords": ["flame", "runner", "platformer", "physics", "jump", "obstacle", "collision", "game loop", "update dt", "раннер*", "платформ*", "физик*", "прыж*", "коллиз*"],
        "workflows": ["setup-flame-project.md", "add-game-loop.md", "run-performance-audit.md"],
        "references": ["flutter-flame-patterns.md", "flutter-game-architecture.md", "performance-checklist.md", "dart/dart-memory-performance.md"],
        "templates": ["endless-runner.md", "platformer-flame.md"],
        "agents": ["engine-architect", "gameplay-programmer", "performance-auditor", "qa-tester"],
    },
    {
        "type": "assets-art",
        "keywords": [
            "asset", "assets", "art", "sprite", "sprites", "sprite atlas", "texture atlas",
            "image", "images", "icon", "icons", "font", "fonts", "illustration", "арт",
            "ассет*", "спрайт*", "атлас", "изображен*", "иконк*", "шрифт*", "иллюстрац*",
        ],
        "workflows": ["add-assets-pipeline.md"],
        "references": ["asset-pipeline.md", "ui-and-animations.md", "performance-checklist.md"],
        "checklists": ["asset-licensing.md", "flutter-ui-quality.md"],
        "agents": ["art-director", "gameplay-programmer", "performance-auditor", "legal-compliance"],
        "checks": ["doc-doctor.py", "design-doctor.py"],
    },
    {
        "type": "audio",
        "keywords": [
            "audio", "music", "sound", "sound effect", "sfx", "voice over", "mute", "volume",
            "аудио", "музык*", "звук*", "озвучк*", "громкост*", "выключить звук",
        ],
        "workflows": ["add-audio.md"],
        "references": ["asset-pipeline.md", "accessibility-child-safety.md", "package-policy.md"],
        "checklists": ["asset-licensing.md", "accessibility.md"],
        "agents": ["art-director", "narrative-writer", "gameplay-programmer", "legal-compliance", "qa-tester"],
        "checks": ["design-doctor.py"],
    },
    {
        "type": "ui-ux",
        "keywords": [
            "ui", "ux", "menu", "hud", "settings", "overlay", "screen", "responsive", "design",
            "navigation", "routing", "animation", "animations", "дизайн", "меню", "экран",
            "интерфейс", "адаптив*", "навигац*", "анимац*",
        ],
        "workflows": ["add-navigation.md", "add-animations.md"],
        "references": ["ui-and-animations.md", "production-quality.md", "dart/flutter-widgets-mastery.md", "accessibility-child-safety.md"],
        "templates": ["ui-heavy.md"],
        "agents": ["game-designer", "engine-architect", "gameplay-programmer", "qa-tester"],
        "checks": ["design-doctor.py"],
    },
    {
        "type": "localization-narrative",
        "keywords": [
            "localization", "localisation", "l10n", "arb", "translation", "translations",
            "game copy", "narrative", "story", "tutorial copy", "onboarding copy", "локализац*",
            "перевод*", "текст игры", "сюжет", "нарратив", "обучение игрока",
        ],
        "workflows": ["add-localization.md"],
        "references": ["ui-and-animations.md", "accessibility-child-safety.md", "dart/flutter-widgets-mastery.md"],
        "checklists": ["accessibility.md", "flutter-ui-quality.md"],
        "agents": ["narrative-writer", "game-designer", "gameplay-programmer", "qa-tester"],
        "checks": ["design-doctor.py"],
    },
    {
        "type": "accessibility",
        "keywords": ["accessibility", "a11y", "semantics", "contrast", "tap target", "screen reader", "доступ*", "семантик*", "контраст"],
        "workflows": ["write-tests.md"],
        "references": ["accessibility-child-safety.md", "dart/flutter-widgets-mastery.md", "ui-and-animations.md"],
        "checklists": ["accessibility.md", "flutter-ui-quality.md"],
        "agents": ["gameplay-programmer", "qa-tester", "legal-compliance"],
        "checks": ["design-doctor.py"],
    },
    {
        "type": "testing",
        "keywords": [
            "write test", "write tests", "add test", "add tests", "test coverage", "unit test",
            "unit tests", "widget test", "widget tests", "golden test", "golden tests",
            "integration test", "integration tests", "написать тест*", "напиши тест", "напиши тесты",
            "добавить тест*", "добавь тест", "добавь тесты", "покрыть тест*", "покрой тест*", "покрой тестами",
        ],
        "workflows": ["write-tests.md"],
        "references": ["testing-and-release.md", "dart/README.md"],
        "checklists": ["testing.md"],
        "agents": ["qa-tester", "gameplay-programmer", "code-reviewer"],
        "checks": ["dart-doctor.py", "verify-flutter-project.sh"],
    },
    {
        "type": "fix-analyzer-test-failure",
        "keywords": ["bug", "fix", "error", "failure", "failing", "test failure", "failing test", "analyzer", "lint", "пофикс*", "ошиб*", "анализатор", "падает"],
        "workflows": ["debug-common-errors.md", "write-tests.md"],
        "references": ["common-pitfalls.md", "testing-and-release.md", "dart/README.md"],
        "agents": ["gameplay-programmer", "qa-tester", "code-reviewer"],
        "checks": ["triage-log.py", "dart-doctor.py", "verify-flutter-project.sh"],
    },
    {
        "type": "performance",
        "keywords": ["performance", "perf", "fps", "jank", "slow", "lag", "memory", "allocation", "производ*", "фпс", "лаг", "памят*"],
        "workflows": ["run-performance-audit.md"],
        "references": ["performance-checklist.md", "dart/dart-memory-performance.md", "flutter-flame-patterns.md"],
        "agents": ["performance-auditor", "engine-architect", "gameplay-programmer"],
        "checks": ["dart-doctor.py --only performance", "design-doctor.py"],
    },
    {
        "type": "privacy-security",
        "keywords": [
            "security", "privacy", "data safety", "permission", "permissions", "secret", "secrets",
            "coppa", "gdpr", "kids policy", "families policy", "безопасност*", "приватност*",
            "конфиденциальност*", "разрешен*", "секрет*", "детская политика",
        ],
        "workflows": ["prepare-ios-release.md", "prepare-android-release.md"],
        "references": ["accessibility-child-safety.md", "release-policy.md", "quality-policy.md"],
        "checklists": ["app-store-release.md", "google-play-release.md", "asset-licensing.md"],
        "agents": ["security-auditor", "legal-compliance", "release-engineer", "qa-tester"],
        "checks": ["dart-doctor.py", "validate-skill.sh"],
    },
    {
        "type": "release",
        "keywords": ["release", "store", "app store", "google play", "ipa", "appbundle", "релиз", "публикац*", "стор"],
        "workflows": ["prepare-ios-release.md", "prepare-android-release.md"],
        "references": ["release-policy.md", "testing-and-release.md", "accessibility-child-safety.md"],
        "checklists": ["app-store-release.md", "google-play-release.md"],
        "agents": ["release-engineer", "legal-compliance", "qa-tester"],
    },
    {
        "type": "monetization",
        "keywords": ["ads", "iap", "purchase", "subscription", "monetization", "admob", "реклам*", "покуп*", "подпис*", "монетизац*"],
        "workflows": ["add-monetization.md", "add-ads.md", "add-in-app-purchases.md"],
        "references": ["monetization-policy.md", "package-policy.md", "release-policy.md"],
        "checklists": ["monetization.md", "app-store-release.md", "google-play-release.md"],
        "agents": ["legal-compliance", "engine-architect", "gameplay-programmer", "qa-tester"],
    },
    {
        "type": "audit-review",
        "keywords": ["audit", "review", "analyze repo", "анализ", "аудит", "ревью", "провер*"],
        "workflows": ["debug-common-errors.md", "run-performance-audit.md"],
        "references": ["common-pitfalls.md", "quality-policy.md", "testing-and-release.md"],
        "checklists": ["dart-code-quality.md", "game-architecture.md", "testing.md", "performance.md"],
        "agents": ["code-auditor", "security-auditor", "performance-auditor", "legal-compliance"],
        "checks": ["dart-doctor.py", "design-doctor.py", "validate-skill.sh"],
    },
]


MODE_HINTS = [
    ("flame-hybrid", ["flame", "runner", "platformer", "physics", "obstacle", "jump", "game loop", "раннер*", "платформ*", "физик*"]),
    ("flutter-widgets", ["memory", "card", "puzzle", "quiz", "coloring", "drag", "match", "пазл*", "карточ*", "виктор*", "раскраск*"]),
]


def find_existing(inventory: dict, group: str, basenames: list[str]) -> list[str]:
    available = inventory.get(group, [])
    by_name = {os.path.basename(p): p for p in available}
    found = []
    for name in basenames:
        if name in by_name:
            found.append(by_name[name])
            continue
        match = next((p for p in available if p.endswith("/" + name) or p.endswith(name)), "")
        if match:
            found.append(match)
    return found


def choose_project(context: dict, task: str, explicit: str = "") -> dict | None:
    projects = context.get("projects", [])
    if explicit:
        wanted = explicit.rstrip("/")
        for project in projects:
            path = project["path"]
            if path == wanted or path.endswith("/" + wanted) or project.get("name") == wanted:
                return project
        return None

    t = norm(task)
    best = None
    best_score = 0
    for project in projects:
        names = [project["path"], project["name"], project["path"].replace("/", " ")]
        aliases = names[:]
        if "runner" in project["name"]:
            aliases += ["runner", "раннер"]
        if "memory" in project["name"]:
            aliases += ["memory", "memory match", "карточ", "памят"]
        s = sum(1 for alias in aliases if norm(alias) in t)
        if s > best_score:
            best = project
            best_score = s
    return best if best_score else None


def infer_mode(task: str, project: dict | None) -> str:
    if project:
        return project.get("mode", "auto")
    for mode, words in MODE_HINTS:
        if contains(task, words):
            return mode
    return "auto"


def choose_routes(task: str) -> list[tuple[dict, int]]:
    scored = [(score(route["keywords"], task), index, route) for index, route in enumerate(ROUTES)]
    matched = [(value, index, route) for value, index, route in scored if value > 0]
    matched.sort(key=lambda item: (-item[0], item[1]))
    if matched:
        return [(route, value) for value, _, route in matched[:4]]
    return [(
        {
            "type": "general-change",
            "workflows": ["choose-game-architecture.md", "write-tests.md"],
            "references": ["flutter-game-architecture.md", "dart/README.md", "common-pitfalls.md"],
            "agents": ["engine-architect", "gameplay-programmer", "qa-tester"],
            "keywords": [],
        },
        0,
    )]


def unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def route_checks(project: dict | None, route: dict, root: str) -> list[str]:
    checks = []
    cmds = project.get("commands", {}) if project else {}
    for check in route.get("checks", []):
        if project and check.startswith("design-doctor.py"):
            suffix = check[len("design-doctor.py") :].strip()
            checks.append((cmds.get("design_doctor", "") + (" " + suffix if suffix else "")).strip())
        elif project and check.startswith("dart-doctor.py"):
            suffix = check[len("dart-doctor.py") :].strip()
            checks.append((cmds.get("dart_doctor", "") + (" " + suffix if suffix else "")).strip())
        elif check.endswith(".py") or check.endswith(".sh"):
            checks.append(f".agents/skills/dart-mobile-game-studio/scripts/{check}")
        else:
            checks.append(check)
    if project:
        checks += [
            cmds.get("dart_doctor", ""),
            cmds.get("design_doctor", ""),
            cmds.get("format_check", ""),
            cmds.get("analyze", ""),
            cmds.get("test", ""),
        ]
    else:
        checks += [
            ".agents/skills/dart-mobile-game-studio/scripts/ai-context-pack.py --markdown",
            ".agents/skills/dart-mobile-game-studio/scripts/design-doctor.py .",
            ".agents/skills/dart-mobile-game-studio/scripts/dart-doctor.py <project>",
        ]
    return [c for i, c in enumerate(checks) if c and c not in checks[:i]]


def build_route(root: str, task: str, project_arg: str = "") -> dict:
    context = load_context(root)
    inventory = context.get("inventory", {})
    project = choose_project(context, task, project_arg)
    matched_routes = choose_routes(task)
    route, score_value = matched_routes[0]
    mode = infer_mode(task, project)

    def merged(field: str) -> list[str]:
        return unique([item for matched, _ in matched_routes for item in matched.get(field, [])])

    workflows = find_existing(inventory, "workflows", merged("workflows"))
    references = find_existing(inventory, "references", merged("references"))
    templates = find_existing(inventory, "templates", merged("templates"))
    checklists = find_existing(inventory, "checklists", merged("checklists"))
    agents = merged("agents")
    combined_route = {"checks": merged("checks")}

    append_project_agents = route["type"] not in {"release", "audit-review", "monetization"}
    if project:
        for p in project.get("read_first", []):
            if p not in references:
                references.append(p)
        if append_project_agents:
            for a in project.get("recommended_agents", []):
                if a not in agents:
                    agents.append(a)

    return {
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "task": task,
        "task_type": route["type"],
        "task_types": [matched["type"] for matched, _ in matched_routes],
        "matched_routes": [
            {"type": matched["type"], "matched_keyword_count": matched_score}
            for matched, matched_score in matched_routes
        ],
        "confidence": "high" if score_value >= 2 else ("medium" if score_value == 1 else "low"),
        "matched_keyword_count": score_value,
        "project": project,
        "mode": mode,
        "read_first": references[:10],
        "workflows": workflows,
        "templates": templates,
        "checklists": checklists,
        "agents": agents,
        "required_checks": route_checks(project, combined_route, root),
        "must_not": [
            "Do not put game rules in Flutter widgets or Flame components.",
            "Do not claim analyze/test/build passed unless the commands actually ran.",
            "Do not add ads, tracking, accounts, external links, or copyrighted assets for kids builds.",
            "Do not skip Semantics/Reduce Motion/tap target considerations for custom UI.",
        ],
        "next_steps": [
            "Run ai-context-pack.py --markdown for the final current context.",
            "Read the listed workflows/references before editing.",
            "Make the smallest project-scoped change.",
            "Run the required checks that are available in this environment.",
        ],
        "context_summary": {
            "projects": [p["path"] + ":" + p["mode"] for p in context.get("projects", [])],
            "toolchain": context.get("toolchain", {}),
        },
    }


def render_markdown(route: dict) -> str:
    lines = [
        "# Task Route",
        "",
        f"- Task: {route['task']}",
        f"- Type: `{route['task_type']}`",
        f"- Matched types: `{', '.join(route['task_types'])}`",
        f"- Confidence: `{route['confidence']}` ({route['matched_keyword_count']} keyword hits)",
        f"- Mode: `{route['mode']}`",
    ]
    project = route.get("project")
    if project:
        lines += [
            f"- Project: `{project['path']}`",
            f"- Project mode: `{project.get('mode', '')}`",
        ]
    else:
        lines.append("- Project: `not selected`")

    def section(title: str, items: list[str]):
        lines.extend(["", f"## {title}"])
        if not items:
            lines.append("- none")
        else:
            lines.extend(f"- `{item}`" for item in items)

    section("Read First", route["read_first"])
    section("Workflows", route["workflows"])
    section("Templates", route["templates"])
    section("Checklists", route["checklists"])
    section("Agents", route["agents"])
    section("Required Checks", route["required_checks"])
    lines.extend(["", "## Must Not"])
    lines.extend(f"- {item}" for item in route["must_not"])
    lines.extend(["", "## Next Steps"])
    lines.extend(f"- {item}" for item in route["next_steps"])
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(prog=TOOL_NAME, description="Route a task to the right game-studio workflow.")
    ap.add_argument("task", nargs="*", help="task text")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true", help="emit JSON")
    group.add_argument("--markdown", action="store_true", help="emit Markdown (default)")
    ap.add_argument("--stdin", action="store_true", help="read task text from stdin")
    ap.add_argument("--root", default=repo_root_from_skill(), help="repo root")
    ap.add_argument("--project", default="", help="force target project path or name")
    ap.add_argument("--output", default="", help="write route to file")
    args = ap.parse_args()

    task = " ".join(args.task).strip()
    if args.stdin:
        task = sys.stdin.read().strip()
    if not task:
        print(f"{TOOL_NAME}: provide task text or --stdin", file=sys.stderr)
        return 2

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"{TOOL_NAME}: root not found: {root}", file=sys.stderr)
        return 2

    route = build_route(root, task, args.project)
    payload = json.dumps(route, indent=2, ensure_ascii=False) + "\n" if args.json else render_markdown(route)
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(payload)
        except OSError as e:
            print(f"{TOOL_NAME}: could not write {args.output}: {e}", file=sys.stderr)
            return 2
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
