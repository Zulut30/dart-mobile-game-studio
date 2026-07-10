#!/usr/bin/env python3
"""Run a closed-loop, evidence-based review for a Dart/Flutter game task.

The script refreshes the AI context, routes the task, runs known read-only
checks, and emits one compact report. It never executes arbitrary command text
from task-router output and never runs pub get, codegen, clean, or builds.

Usage:
    self-review-loop.py "add levels to memory match" [--json | --markdown]
    self-review-loop.py --project examples/endless_runner "fix accessibility"
    self-review-loop.py --stdin --json

Exit codes: 0 = no failed checks (WARN is allowed unless --strict);
            1 = at least one FAIL, or a WARN with --strict;
            2 = usage error.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

TOOL_NAME = "self-review-loop"
TOOL_VERSION = "0.2"
STATUSES = ("PASS", "WARN", "FAIL", "SKIP")


def script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def repo_root_from_skill() -> str:
    return os.path.abspath(os.path.join(script_dir(), "../../../.."))


def display_command(command: list[str], cwd: str, root: str) -> str:
    rendered = shlex.join(command)
    cwd = os.path.abspath(cwd)
    root = os.path.abspath(root)
    if cwd == root:
        return rendered
    try:
        relative = os.path.relpath(cwd, root).replace(os.sep, "/")
    except ValueError:
        relative = cwd
    return f"(cd {shlex.quote(relative)} && {rendered})"


def trim_output(text: str, max_lines: int = 60, max_chars: int = 8000) -> str:
    lines = [line.rstrip() for line in text.strip().splitlines()]
    if len(lines) > max_lines:
        lines = [f"... {len(lines) - max_lines} earlier line(s) omitted ...", *lines[-max_lines:]]
    out = "\n".join(lines)
    if len(out) > max_chars:
        out = "... earlier output omitted ...\n" + out[-max_chars:]
    return out


def run_command(command: list[str], cwd: str, root: str, timeout: int) -> dict:
    started = time.monotonic()
    shown = display_command(command, cwd, root)
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        combined = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
        return {
            "command": shown,
            "exit_code": result.returncode,
            "timed_out": False,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": result.stdout,
            "output": trim_output(combined),
        }
    except subprocess.TimeoutExpired as exc:
        output = "\n".join(
            part.decode(errors="replace") if isinstance(part, bytes) else (part or "")
            for part in (exc.stdout, exc.stderr)
        )
        return {
            "command": shown,
            "exit_code": None,
            "timed_out": True,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": "",
            "output": trim_output(output),
        }
    except OSError as exc:
        return {
            "command": shown,
            "exit_code": None,
            "timed_out": False,
            "duration_ms": round((time.monotonic() - started) * 1000),
            "stdout": "",
            "output": str(exc),
        }


def check(
    check_id: str,
    label: str,
    status: str,
    summary: str,
    *,
    command: str = "",
    executed: bool = False,
    exit_code: int | None = None,
    duration_ms: int = 0,
    output: str = "",
) -> dict:
    return {
        "id": check_id,
        "label": label,
        "status": status,
        "summary": summary,
        "command": command,
        "executed": executed,
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "output": output,
    }


def load_json_tool(
    check_id: str,
    label: str,
    command: list[str],
    cwd: str,
    root: str,
    timeout: int,
) -> tuple[dict | None, dict]:
    result = run_command(command, cwd, root, timeout)
    try:
        payload = json.loads(result["stdout"])
    except (json.JSONDecodeError, TypeError):
        payload = None
    if payload is None:
        reason = "timed out" if result["timed_out"] else "did not return valid JSON"
        item = check(
            check_id,
            label,
            "FAIL",
            reason,
            command=result["command"],
            executed=True,
            exit_code=result["exit_code"],
            duration_ms=result["duration_ms"],
            output=result["output"],
        )
        return None, item
    status = "PASS" if result["exit_code"] == 0 else "FAIL"
    item = check(
        check_id,
        label,
        status,
        "valid JSON produced" if status == "PASS" else f"exited with {result['exit_code']}",
        command=result["command"],
        executed=True,
        exit_code=result["exit_code"],
        duration_ms=result["duration_ms"],
        output="" if status == "PASS" else result["output"],
    )
    return payload, item


def flatten_doctor_findings(payload: dict, source: str) -> list[dict]:
    findings = []
    if source == "dart-doctor":
        groups = payload.get("dimensions", {}).items()
    else:
        groups = []
        for project_groups in payload.get("projects", {}).values():
            groups.extend(project_groups.items())
    for dimension, items in groups:
        for item in items:
            status = item.get("status", "INFO")
            if status not in {"WARN", "FAIL"}:
                continue
            findings.append(
                {
                    "source": source,
                    "dimension": dimension,
                    "status": status,
                    "title": item.get("title", "Untitled finding"),
                    "detail": item.get("detail", ""),
                    "fix": item.get("fix", ""),
                    "code": item.get("code", ""),
                    "locations": item.get("locations", [])[:10],
                }
            )
    return findings


def run_doctor(
    source: str,
    filename: str,
    project_root: str,
    root: str,
    timeout: int,
) -> tuple[dict, list[dict]]:
    command = [sys.executable, os.path.join(script_dir(), filename), project_root, "--json", "--no-color"]
    result = run_command(command, root, root, timeout)
    try:
        payload = json.loads(result["stdout"])
    except (json.JSONDecodeError, TypeError):
        payload = None
    if payload is None:
        item = check(
            source,
            source,
            "FAIL",
            "timed out" if result["timed_out"] else "did not return valid JSON",
            command=result["command"],
            executed=True,
            exit_code=result["exit_code"],
            duration_ms=result["duration_ms"],
            output=result["output"],
        )
        return item, []

    summary = payload.get("summary", {})
    fail_count = int(summary.get("fail", 0))
    warn_count = int(summary.get("warn", 0))
    pass_count = int(summary.get("pass", 0))
    status = "FAIL" if fail_count else ("WARN" if warn_count else "PASS")
    item = check(
        source,
        source,
        status,
        f"{pass_count} pass, {warn_count} warn, {fail_count} fail",
        command=result["command"],
        executed=True,
        exit_code=result["exit_code"],
        duration_ms=result["duration_ms"],
        output="" if status != "FAIL" else result["output"],
    )
    return item, flatten_doctor_findings(payload, source)


def run_cli_check(
    check_id: str,
    label: str,
    executable: str,
    args: list[str],
    project_root: str,
    root: str,
    timeout: int,
    *,
    skip_reason: str = "",
) -> dict:
    shown = display_command([executable, *args], project_root, root)
    if skip_reason:
        return check(check_id, label, "SKIP", skip_reason, command=shown)
    path = shutil.which(executable)
    if not path:
        return check(
            check_id,
            label,
            "WARN",
            f"{executable} is not available on PATH; check was not run",
            command=shown,
        )
    result = run_command([path, *args], project_root, root, timeout)
    status = "PASS" if result["exit_code"] == 0 else "FAIL"
    if result["timed_out"]:
        summary = f"timed out after {timeout}s"
    elif status == "PASS":
        summary = "command passed"
    else:
        summary = f"command failed with exit code {result['exit_code']}"
    return check(
        check_id,
        label,
        status,
        summary,
        command=shown,
        executed=True,
        exit_code=result["exit_code"],
        duration_ms=result["duration_ms"],
        output=result["output"],
    )


def changed_files(root: str) -> list[str]:
    result = run_command(["git", "status", "--porcelain=v1", "--untracked-files=normal"], root, root, 20)
    if result["exit_code"] != 0:
        return []
    files = []
    for line in result["stdout"].splitlines():
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path and path not in files:
            files.append(path)
    return files


def project_path(root: str, project: dict) -> str | None:
    path = os.path.realpath(os.path.join(root, project.get("path", "")))
    try:
        if os.path.commonpath([os.path.realpath(root), path]) != os.path.realpath(root):
            return None
    except ValueError:
        return None
    return path if os.path.isdir(path) else None


def run_level_validation(project_root: str, root: str, timeout: int) -> dict:
    level_dir = os.path.join(project_root, "assets", "levels")
    files = sorted(Path(level_dir).rglob("*.json")) if os.path.isdir(level_dir) else []
    shown = display_command(
        [os.path.join(script_dir(), "validate-levels.py"), os.path.relpath(level_dir, root)],
        root,
        root,
    )
    if not files:
        return check(
            "validate-levels",
            "level data validation",
            "WARN",
            "level-system task selected, but no JSON files were found under assets/levels",
            command=shown,
        )
    result = run_command(
        [sys.executable, os.path.join(script_dir(), "validate-levels.py"), level_dir],
        root,
        root,
        timeout,
    )
    status = "PASS" if result["exit_code"] == 0 else "FAIL"
    return check(
        "validate-levels",
        "level data validation",
        status,
        f"validated {len(files)} level file(s)" if status == "PASS" else "level validation failed",
        command=result["command"],
        executed=True,
        exit_code=result["exit_code"],
        duration_ms=result["duration_ms"],
        output=result["output"],
    )


def run_skill_validation(root: str, timeout: int) -> dict:
    command = [os.path.join(script_dir(), "validate-skill.sh")]
    result = run_command(command, root, root, timeout)
    status = "PASS" if result["exit_code"] == 0 else "FAIL"
    return check(
        "validate-skill",
        "skill structure and mirrors",
        status,
        "skill validation passed" if status == "PASS" else "skill validation failed",
        command=result["command"],
        executed=True,
        exit_code=result["exit_code"],
        duration_ms=result["duration_ms"],
        output=result["output"],
    )


def summarize_checks(checks: list[dict]) -> dict:
    counts = {status.lower(): 0 for status in STATUSES}
    for item in checks:
        counts[item["status"].lower()] += 1
    counts["outcome"] = "FAIL" if counts["fail"] else ("WARN" if counts["warn"] else "PASS")
    return counts


def command_issues(checks: list[dict]) -> list[dict]:
    issues = []
    for item in checks:
        if item["status"] not in {"WARN", "FAIL"}:
            continue
        if item["id"].startswith(("dart-doctor", "design-doctor")):
            continue
        issues.append(
            {
                "source": item["id"],
                "dimension": "execution",
                "status": item["status"],
                "title": item["label"],
                "detail": item["summary"],
                "fix": f"Run: {item['command']}" if item.get("command") and not item["executed"] else "",
                "code": "",
                "locations": [],
            }
        )
    return issues


def recommended_actions(issues: list[dict], checks: list[dict]) -> list[str]:
    actions = []
    for issue in issues:
        action = issue.get("fix", "").strip()
        if action and action not in actions:
            actions.append(action)
    for item in checks:
        needs_command = not item["executed"] or item["status"] == "FAIL"
        if needs_command and item["status"] in {"WARN", "FAIL", "SKIP"} and item.get("command"):
            if any(item["command"] in action for action in actions):
                continue
            action = f"Run or resolve: {item['command']}"
            if action not in actions:
                actions.append(action)
    if not actions:
        actions.append("No automated blocker found; complete the manual device review before handoff.")
    return actions[:12]


def manual_review_items(mode: str) -> list[str]:
    items = [
        "Verify phone and tablet layouts in portrait and landscape.",
        "Verify TalkBack/VoiceOver, 200% text scaling, contrast, and tap targets on a real device.",
        "Confirm every shipped image, font, sound, and music file is original, licensed, or a placeholder.",
    ]
    if mode in {"flame", "flame-hybrid"}:
        items.append("Profile gameplay on the oldest supported device and inspect frame pacing, memory, pause, and resume.")
    return items


def finalize_report(report: dict) -> dict:
    report["summary"] = summarize_checks(report["checks"])
    report["issues"] = [*report.get("doctor_findings", []), *command_issues(report["checks"])]
    report.pop("doctor_findings", None)
    report["recommended_actions"] = recommended_actions(report["issues"], report["checks"])
    report["commands_to_run"] = [
        item["command"]
        for item in report["checks"]
        if item.get("command")
        and item["status"] in {"WARN", "FAIL", "SKIP"}
        and (not item["executed"] or item["status"] == "FAIL")
    ]
    return report


def build_review(args: argparse.Namespace, task: str) -> dict:
    root = os.path.abspath(args.root)
    checks = []
    findings = []
    report = {
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "task": task,
        "root": root,
        "options": {
            "project": args.project,
            "static_only": args.static_only,
            "skip_tests": args.skip_tests,
            "strict": args.strict,
            "timeout_seconds": args.timeout,
        },
        "route": {},
        "context": {},
        "changed_files": changed_files(root),
        "checks": checks,
        "doctor_findings": findings,
        "manual_review_required": [],
    }

    context_command = [
        sys.executable,
        os.path.join(script_dir(), "ai-context-pack.py"),
        root,
        "--json",
        "--no-findings",
    ]
    context, context_check = load_json_tool(
        "ai-context-pack", "AI context refresh", context_command, root, root, args.timeout
    )
    checks.append(context_check)
    if context is None:
        return finalize_report(report)
    report["context"] = {
        "projects": [f"{item['path']}:{item['mode']}" for item in context.get("projects", [])],
        "toolchain": context.get("toolchain", {}),
    }

    route_command = [
        sys.executable,
        os.path.join(script_dir(), "task-router.py"),
        task,
        "--json",
        "--root",
        root,
    ]
    if args.project:
        route_command.extend(["--project", args.project])
    route, route_check = load_json_tool("task-router", "task routing", route_command, root, root, args.timeout)
    checks.append(route_check)
    if route is None:
        return finalize_report(report)

    project = route.get("project")
    report["route"] = {
        "task_type": route.get("task_type", ""),
        "task_types": route.get("task_types", [route.get("task_type", "")]),
        "confidence": route.get("confidence", ""),
        "mode": route.get("mode", "auto"),
        "project": project.get("path") if project else "",
        "agents": route.get("agents", []),
        "workflows": route.get("workflows", []),
        "read_first": route.get("read_first", []),
        "required_checks": route.get("required_checks", []),
    }
    report["manual_review_required"] = manual_review_items(route.get("mode", "auto"))

    route_types = set(route.get("task_types", [route.get("task_type", "")]))
    projects_to_review: list[tuple[dict, str]] = []
    if project:
        target = project_path(root, project)
        if target is None:
            checks.append(check("project-selection", "target project", "FAIL", "selected project path is invalid"))
        else:
            projects_to_review.append((project, target))
            checks.append(check("project-selection", "target project", "PASS", project.get("path", target)))
    elif args.project:
        checks.append(
            check(
                "project-selection",
                "target project",
                "FAIL",
                f"project '{args.project}' was not found",
                command=f"{TOOL_NAME} --project <project> {shlex.quote(task)}",
            )
        )
    elif "audit-review" in route_types:
        for candidate in context.get("projects", []):
            target = project_path(root, candidate)
            if target is not None:
                projects_to_review.append((candidate, target))
        status = "PASS" if projects_to_review else "FAIL"
        checks.append(
            check(
                "project-selection",
                "repo-wide project selection",
                status,
                f"selected all {len(projects_to_review)} discovered project(s)"
                if projects_to_review else "no valid projects were discovered for the repository audit",
            )
        )
    else:
        checks.append(
            check(
                "project-selection",
                "target project",
                "WARN",
                "task did not identify one target project",
                command=f"{TOOL_NAME} --project <project> {shlex.quote(task)}",
            )
        )

    multiple_projects = len(projects_to_review) > 1
    report["route"]["projects_reviewed"] = [item.get("path", target) for item, target in projects_to_review]
    for selected_project, target in projects_to_review:
        project_name = selected_project.get("path", target)
        suffix = f":{project_name}" if multiple_projects else ""
        label_suffix = f" ({project_name})" if multiple_projects else ""
        for source, filename in (("dart-doctor", "dart-doctor.py"), ("design-doctor", "design-doctor.py")):
            item, doctor_findings = run_doctor(source, filename, target, root, args.timeout)
            item["id"] = f"{item['id']}{suffix}"
            item["label"] = f"{item['label']}{label_suffix}"
            if multiple_projects:
                for finding in doctor_findings:
                    finding["source"] = f"{finding['source']}:{project_name}"
            checks.append(item)
            findings.extend(doctor_findings)

        if "add-level-system" in route_types:
            item = run_level_validation(target, root, args.timeout)
            item["id"] = f"{item['id']}{suffix}"
            item["label"] = f"{item['label']}{label_suffix}"
            checks.append(item)

        mode = selected_project.get("mode", route.get("mode", "auto"))
        flutter_project = mode in {"flutter-widgets", "flame", "flame-hybrid"}
        skip_reason = "disabled by --static-only" if args.static_only else ""
        cli_specs = [
            ("format", "Dart formatting", "dart", ["format", "--output=none", "--set-exit-if-changed", "."], skip_reason),
            ("analyze", "static analysis", "flutter" if flutter_project else "dart", ["analyze"], skip_reason),
            (
                "test",
                "automated tests",
                "flutter" if flutter_project else "dart",
                ["test"],
                skip_reason or ("disabled by --skip-tests" if args.skip_tests else ""),
            ),
        ]
        for check_id, label, executable, command_args, reason in cli_specs:
            item = run_cli_check(
                f"{check_id}{suffix}",
                f"{label}{label_suffix}",
                executable,
                command_args,
                target,
                root,
                args.timeout,
                skip_reason=reason,
            )
            checks.append(item)

    if any(
        selected.get("mode") in {"flame", "flame-hybrid"}
        for selected, _ in projects_to_review
    ):
        report["manual_review_required"] = manual_review_items("flame-hybrid")

    skill_prefixes = (
        ".agents/skills/dart-mobile-game-studio/",
        ".claude/skills/dart-mobile-game-studio/",
        ".cursor/skills/dart-mobile-game-studio/",
    )
    skill_changed = any(path.startswith(skill_prefixes) for path in report["changed_files"])
    if "audit-review" in route_types or skill_changed:
        checks.append(run_skill_validation(root, args.timeout))

    return finalize_report(report)


def md_escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    route = report.get("route", {})
    project_label = route.get("project") or ", ".join(route.get("projects_reviewed", [])) or "not selected"
    lines = [
        "# AI Self-Review",
        "",
        f"- Task: {report['task']}",
        f"- Outcome: `{summary['outcome']}`",
        f"- Checks: {summary['pass']} pass, {summary['warn']} warn, {summary['fail']} fail, {summary['skip']} skip",
        f"- Route: `{route.get('task_type', 'unavailable')}` (`{route.get('confidence', 'unknown')}` confidence)",
        f"- Project: `{project_label}`",
        f"- Mode: `{route.get('mode', 'auto')}`",
        "",
        "## Checks",
        "",
        "| Status | Check | Result |",
        "|---|---|---|",
    ]
    for item in report["checks"]:
        lines.append(f"| `{item['status']}` | {md_escape(item['label'])} | {md_escape(item['summary'])} |")

    lines.extend(["", "## Issues", ""])
    if report["issues"]:
        for issue in report["issues"]:
            label = issue.get("code") or issue.get("source", "review")
            detail = f": {issue['detail']}" if issue.get("detail") else ""
            lines.append(f"- [{issue['status']}] `{label}` {issue['title']}{detail}")
            if issue.get("fix"):
                lines.append(f"  Fix: {issue['fix']}")
            if issue.get("locations"):
                lines.append(f"  Locations: {', '.join(issue['locations'])}")
    else:
        lines.append("- No automated WARN or FAIL findings.")

    lines.extend(["", "## Changed Files", ""])
    if report["changed_files"]:
        lines.extend(f"- `{path}`" for path in report["changed_files"])
    else:
        lines.append("- none detected")

    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"{index}. {action}" for index, action in enumerate(report["recommended_actions"], start=1))

    lines.extend(["", "## Manual Review", ""])
    lines.extend(f"- {item}" for item in report["manual_review_required"])

    commands = [item["command"] for item in report["checks"] if item.get("command")]
    lines.extend(["", "## Commands", "", "```bash"])
    lines.extend(commands or ["# no commands recorded"])
    lines.append("```")

    failed_outputs = [item for item in report["checks"] if item["status"] == "FAIL" and item.get("output")]
    if failed_outputs:
        lines.extend(["", "## Failure Output", ""])
        for item in failed_outputs:
            lines.extend([f"### {item['label']}", "", "```text", item["output"], "```"])
    return "\n".join(lines) + "\n"


def write_payload(payload: str, output: str) -> bool:
    if not output:
        print(payload, end="")
        return True
    try:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(payload)
        return True
    except OSError as exc:
        print(f"{TOOL_NAME}: could not write {output}: {exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Run the task-aware self-review loop for a Dart/Flutter game change.",
    )
    parser.add_argument("task", nargs="*", help="task text")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--json", action="store_true", help="emit JSON")
    output_group.add_argument("--markdown", action="store_true", help="emit Markdown (default)")
    parser.add_argument("--stdin", action="store_true", help="read task text from stdin")
    parser.add_argument("--root", default=repo_root_from_skill(), help="repository or project root")
    parser.add_argument("--project", default="", help="force a project path or name")
    parser.add_argument("--output", default="", help="write the report to a file")
    parser.add_argument("--static-only", action="store_true", help="skip format, analyze, and tests")
    parser.add_argument("--skip-tests", action="store_true", help="run format/analyze but skip tests")
    parser.add_argument("--strict", action="store_true", help="treat WARN as a failing exit status")
    parser.add_argument("--no-color", action="store_true", help="accepted for CLI compatibility; output is plain")
    parser.add_argument("--timeout", type=int, default=180, help="timeout per check in seconds")
    args = parser.parse_args()

    task = " ".join(args.task).strip()
    if args.stdin:
        task = sys.stdin.read().strip()
    if not task:
        print(f"{TOOL_NAME}: provide task text or --stdin", file=sys.stderr)
        return 2
    if not os.path.isdir(args.root):
        print(f"{TOOL_NAME}: root not found: {args.root}", file=sys.stderr)
        return 2
    if args.timeout < 1:
        print(f"{TOOL_NAME}: --timeout must be positive", file=sys.stderr)
        return 2

    report = build_review(args, task)
    payload = (
        json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.json
        else render_markdown(report)
    )
    if not write_payload(payload, args.output):
        return 2
    summary = report["summary"]
    if summary["fail"] or (args.strict and summary["warn"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
