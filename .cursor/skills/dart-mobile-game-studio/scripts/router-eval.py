#!/usr/bin/env python3
"""Evaluate task-router behavior against a versioned RU/EN JSONL corpus."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


TOOL_NAME = "router-eval"
TOOL_VERSION = "0.1"
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = SCRIPT_DIR.parents[3]
DEFAULT_CORPUS = DEFAULT_ROOT / "evals" / "task-routing.jsonl"


def load_cases(path: Path) -> list[dict]:
    cases: list[dict] = []
    seen: set[str] = set()
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or not isinstance(case.get("task"), str):
            raise ValueError(f"{path}:{line_number}: each case needs string id and task")
        if case["id"] in seen:
            raise ValueError(f"{path}:{line_number}: duplicate case id {case['id']!r}")
        seen.add(case["id"])
        cases.append(case)
    if not cases:
        raise ValueError(f"{path}: no eval cases")
    return cases


def run_router(root: Path, task: str, timeout: int) -> tuple[dict | None, str]:
    command = [sys.executable, str(SCRIPT_DIR / "task-router.py"), task, "--json", "--root", str(root)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if result.returncode != 0:
        return None, f"router exit {result.returncode}: {result.stderr.strip()}"
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return None, f"invalid router JSON: {exc.msg}"
    return payload, ""


def evaluate_case(case: dict, route: dict | None, route_error: str) -> dict:
    failures: list[str] = []
    if route is None:
        failures.append(route_error or "router did not return a payload")
        return {"id": case["id"], "task": case["task"], "passed": False, "failures": failures}

    actual_types = set(route.get("task_types") or [route.get("task_type", "")])
    actual_workflows = {Path(item).name for item in route.get("workflows", [])}
    actual_agents = set(route.get("agents", []))
    primary = case.get("primary_type")
    if primary and route.get("task_type") != primary:
        failures.append(f"primary type: expected {primary!r}, got {route.get('task_type')!r}")

    for expected in case.get("expected_types", []):
        if expected not in actual_types:
            failures.append(f"missing task type {expected!r}; got {sorted(actual_types)}")
    for forbidden in case.get("forbidden_types", []):
        if forbidden in actual_types:
            failures.append(f"forbidden task type {forbidden!r} was selected")
    for expected in case.get("expected_workflows", []):
        if expected not in actual_workflows:
            failures.append(f"missing workflow {expected!r}; got {sorted(actual_workflows)}")
    for expected in case.get("expected_agents", []):
        if expected not in actual_agents:
            failures.append(f"missing agent {expected!r}; got {sorted(actual_agents)}")

    return {
        "id": case["id"],
        "task": case["task"],
        "critical": bool(case.get("critical")),
        "passed": not failures,
        "failures": failures,
        "actual": {
            "primary_type": route.get("task_type", ""),
            "task_types": sorted(actual_types),
            "workflows": sorted(actual_workflows),
            "agents": sorted(actual_agents),
        },
    }


def corpus_coverage(root: Path, cases: list[dict]) -> dict:
    workflow_dir = root / ".agents" / "skills" / "dart-mobile-game-studio" / "workflows"
    agent_dir = root / ".agents" / "agents"
    available_workflows = {path.name for path in workflow_dir.glob("*.md")}
    available_agents = {path.stem for path in agent_dir.glob("*.md") if path.name != "README.md"}
    expected_workflows = {item for case in cases for item in case.get("expected_workflows", [])}
    expected_agents = {item for case in cases for item in case.get("expected_agents", [])}
    return {
        "available_workflows": len(available_workflows),
        "covered_workflows": len(available_workflows & expected_workflows),
        "missing_workflows": sorted(available_workflows - expected_workflows),
        "available_agents": len(available_agents),
        "covered_agents": len(available_agents & expected_agents),
        "missing_agents": sorted(available_agents - expected_agents),
        "unknown_workflows": sorted(expected_workflows - available_workflows),
        "unknown_agents": sorted(expected_agents - available_agents),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Evaluate task-router against the RU/EN corpus.")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="repository root")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS), help="JSONL eval corpus")
    parser.add_argument("--case", action="append", default=[], help="run only a named case")
    parser.add_argument("--min-accuracy", type=float, default=0.95)
    parser.add_argument("--timeout", type=int, default=30, help="seconds per router invocation")
    parser.add_argument("--no-coverage", action="store_true", help="do not require full inventory coverage")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser().resolve()
    corpus = Path(args.corpus).expanduser().resolve()
    if not root.is_dir() or not corpus.is_file() or not 0 <= args.min_accuracy <= 1 or args.timeout < 1:
        print(f"{TOOL_NAME}: invalid root/corpus/threshold/timeout", file=sys.stderr)
        return 2
    try:
        cases = load_cases(corpus)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"{TOOL_NAME}: {exc}", file=sys.stderr)
        return 2
    if args.case:
        requested = set(args.case)
        cases = [case for case in cases if case["id"] in requested]
        missing = requested - {case["id"] for case in cases}
        if missing:
            print(f"{TOOL_NAME}: unknown case(s): {', '.join(sorted(missing))}", file=sys.stderr)
            return 2

    results = []
    for case in cases:
        route, error = run_router(root, case["task"], args.timeout)
        results.append(evaluate_case(case, route, error))

    passed = sum(1 for result in results if result["passed"])
    critical = [result for result in results if result.get("critical")]
    critical_passed = sum(1 for result in critical if result["passed"])
    accuracy = passed / len(results)
    coverage = corpus_coverage(root, cases) if not args.case else {}
    coverage_ok = args.no_coverage or args.case or not any(
        coverage.get(key) for key in ("missing_workflows", "missing_agents", "unknown_workflows", "unknown_agents")
    )
    threshold_ok = accuracy >= args.min_accuracy
    critical_ok = critical_passed == len(critical)
    outcome = "PASS" if threshold_ok and critical_ok and coverage_ok else "FAIL"
    payload = {
        "tool": TOOL_NAME,
        "version": TOOL_VERSION,
        "corpus": str(corpus),
        "summary": {
            "outcome": outcome,
            "cases": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "accuracy": round(accuracy, 4),
            "minimum_accuracy": args.min_accuracy,
            "critical_cases": len(critical),
            "critical_passed": critical_passed,
        },
        "coverage": coverage,
        "results": results,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for result in results:
            if not result["passed"]:
                print(f"FAIL {result['id']}: {result['task']}")
                for failure in result["failures"]:
                    print(f"  - {failure}")
        summary = payload["summary"]
        print(
            f"Router eval {outcome}: {passed}/{len(results)} passed "
            f"({accuracy:.1%}, threshold {args.min_accuracy:.1%}); "
            f"critical {critical_passed}/{len(critical)}."
        )
        if coverage:
            print(
                f"Coverage: workflows {coverage['covered_workflows']}/{coverage['available_workflows']}, "
                f"agents {coverage['covered_agents']}/{coverage['available_agents']}."
            )
            for key in ("missing_workflows", "missing_agents", "unknown_workflows", "unknown_agents"):
                if coverage[key]:
                    print(f"  {key}: {', '.join(coverage[key])}")
    return 0 if outcome == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
