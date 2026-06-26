#!/usr/bin/env python3
"""
validate-levels.py — validate game level JSON files against the level schema
(assets/level-schema-template.json).

If the `jsonschema` package is installed, it is used for full Draft-07 validation. Otherwise a
built-in, dependency-free validator checks the key invariants so this still runs in bare CI.

Usage:
    scripts/validate-levels.py LEVELS...          # files and/or directories (dirs scanned for *.json)
    scripts/validate-levels.py assets/levels/      # validate every *.json in a folder
    scripts/validate-levels.py --schema path.json LEVELS...

Exit code: 0 if all valid, 1 if any level is invalid, 2 on usage/schema error. Reads only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCHEMA = SCRIPT_DIR.parent / "assets" / "level-schema-template.json"

TEMPLATES = {
    "coloring-shapes", "simple-platformer", "drag-and-drop-puzzle", "memory-cards",
    "shape-matching", "endless-runner-lite", "tap-reaction",
}
SHAPES = {"circle", "rect", "roundedRect", "triangle", "path", "icon"}
GOAL_TYPES = {"reachGoal", "matchAll", "fillAll", "scoreAtLeast", "surviveTime", "placeAll"}
HEX = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def builtin_validate(level: dict) -> list[str]:
    errs: list[str] = []

    def req(cond: bool, msg: str):
        if not cond:
            errs.append(msg)

    if not isinstance(level, dict):
        return ["top level must be an object"]

    sv = level.get("schemaVersion")
    req(isinstance(sv, int) and not isinstance(sv, bool) and sv >= 1, "schemaVersion must be an integer >= 1")
    req(isinstance(level.get("id"), str) and level.get("id") != "", "id must be a non-empty string")
    if "template" in level:
        req(level["template"] in TEMPLATES, f"template must be one of {sorted(TEMPLATES)}")

    size = level.get("size")
    req(isinstance(size, dict), "size must be an object with width and height")
    if isinstance(size, dict):
        req(is_number(size.get("width")) and size["width"] > 0, "size.width must be a number > 0")
        req(is_number(size.get("height")) and size["height"] > 0, "size.height must be a number > 0")

    if "palette" in level:
        req(isinstance(level["palette"], list), "palette must be an array")
        for i, c in enumerate(level.get("palette", [])):
            req(isinstance(c, str) and bool(HEX.match(c)), f"palette[{i}] must be a #RRGGBB(AA) hex color")

    entities = level.get("entities")
    req(isinstance(entities, list), "entities must be an array")
    for i, e in enumerate(entities or []):
        if not isinstance(e, dict):
            errs.append(f"entities[{i}] must be an object")
            continue
        req(isinstance(e.get("id"), str) and e.get("id") != "", f"entities[{i}].id must be a non-empty string")
        req(isinstance(e.get("kind"), str) and e.get("kind") != "", f"entities[{i}].kind must be a non-empty string")
        if "shape" in e:
            req(e["shape"] in SHAPES, f"entities[{i}].shape must be one of {sorted(SHAPES)}")
        if "color" in e:
            req(isinstance(e["color"], str) and bool(HEX.match(e["color"])), f"entities[{i}].color must be a #RRGGBB(AA) hex")
        if "position" in e:
            p = e["position"]
            req(isinstance(p, dict) and is_number(p.get("x")) and is_number(p.get("y")),
                f"entities[{i}].position must be {{x:number, y:number}}")
        if "path" in e:
            req(isinstance(e["path"], list), f"entities[{i}].path must be an array of points")
            for j, pt in enumerate(e.get("path", [])):
                req(isinstance(pt, dict) and is_number(pt.get("x")) and is_number(pt.get("y")),
                    f"entities[{i}].path[{j}] must be {{x:number, y:number}}")

    goal = level.get("goal")
    if goal is not None:
        req(isinstance(goal, dict), "goal must be an object")
        if isinstance(goal, dict) and "type" in goal:
            req(goal["type"] in GOAL_TYPES, f"goal.type must be one of {sorted(GOAL_TYPES)}")
    return errs


def collect(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(p.rglob("*.json")))
        elif p.is_file():
            files.append(p)
        else:
            print(f"warning: not found: {raw}", file=sys.stderr)
    return files


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Validate level JSON files against the level schema.")
    ap.add_argument("paths", nargs="+", help="Level JSON files and/or directories.")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    args = ap.parse_args(argv)

    validator = None
    try:
        import jsonschema  # type: ignore
        schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
        validator = jsonschema.Draft7Validator(schema)
        mode = "jsonschema (full Draft-07)"
    except ModuleNotFoundError:
        mode = "built-in (dependency-free)"
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot load schema {args.schema}: {exc}", file=sys.stderr)
        return 2

    files = collect(args.paths)
    if not files:
        print("error: no level files to validate", file=sys.stderr)
        return 2

    print(f"Validating {len(files)} level file(s) with {mode}\n")
    bad = 0
    for f in files:
        try:
            level = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  INVALID  {f}: not valid JSON: {exc}")
            bad += 1
            continue
        if validator is not None:
            errors = [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}"
                      for e in sorted(validator.iter_errors(level), key=lambda e: list(e.path))]
        else:
            errors = builtin_validate(level)
        if errors:
            bad += 1
            print(f"  INVALID  {f}")
            for m in errors:
                print(f"             - {m}")
        else:
            print(f"  ok       {f}")

    print()
    if bad:
        print(f"{bad}/{len(files)} level file(s) FAILED validation.", file=sys.stderr)
        return 1
    print(f"All {len(files)} level file(s) valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
