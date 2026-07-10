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
import math
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SCHEMA = SCRIPT_DIR.parent / "assets" / "level-schema-template.json"
SUPPORTED_BUILTIN_KEYWORDS = {
    "$schema", "title", "description", "default", "type", "required", "additionalProperties",
    "properties", "items", "enum", "const", "pattern", "minimum", "maximum",
    "exclusiveMinimum", "exclusiveMaximum", "minLength",
}


def load_json_strict(path: Path):
    def reject_constant(value: str):
        raise ValueError(f"non-standard JSON constant {value!r}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def unsupported_schema_keywords(schema: dict, path: str = "<schema>") -> list[str]:
    errors = [f"{path}: unsupported built-in keyword {key!r}" for key in schema if key not in SUPPORTED_BUILTIN_KEYWORDS]
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        for key, child in properties.items():
            if isinstance(child, dict):
                errors.extend(unsupported_schema_keywords(child, f"{path}.properties.{key}"))
    items = schema.get("items")
    if isinstance(items, dict):
        errors.extend(unsupported_schema_keywords(items, f"{path}.items"))
    additional = schema.get("additionalProperties")
    if isinstance(additional, dict):
        errors.extend(unsupported_schema_keywords(additional, f"{path}.additionalProperties"))
    return errors

def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def matches_type(value, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": is_number(value),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, False)


def builtin_validate(value, schema: dict, path: str = "<root>") -> list[str]:
    """Validate the Draft-07 subset used by the canonical level schema."""
    errors: list[str] = []
    expected = schema.get("type")
    expected_types = expected if isinstance(expected, list) else [expected] if expected else []
    if expected_types and not any(matches_type(value, item) for item in expected_types):
        return [f"{path}: must be {' or '.join(expected_types)}"]

    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: must be one of {schema['enum']!r}")

    if is_number(value):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: must be >= {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: must be <= {schema['maximum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: must be > {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: must be < {schema['exclusiveMaximum']}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: length must be >= {schema['minLength']}")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: must match {schema['pattern']!r}")

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}: missing required property {required!r}")
        additional = schema.get("additionalProperties", {})
        for key, item in value.items():
            child_path = f"{path}.{key}" if path != "<root>" else key
            if key in properties:
                errors.extend(builtin_validate(item, properties[key], child_path))
            elif additional is False:
                errors.append(f"{path}: unknown property {key!r}")
            elif isinstance(additional, dict):
                errors.extend(builtin_validate(item, additional, child_path))

    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            errors.extend(builtin_validate(item, schema["items"], f"{path}[{index}]"))
    return errors


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
    ap.add_argument("--force-builtin", action="store_true", help="use the dependency-free validator")
    args = ap.parse_args(argv)

    try:
        schema = load_json_strict(Path(args.schema))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: cannot load schema {args.schema}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(schema, dict):
        print(f"error: schema must be a JSON object: {args.schema}", file=sys.stderr)
        return 2

    validator = None
    if not args.force_builtin:
        try:
            import jsonschema  # type: ignore
            jsonschema.Draft7Validator.check_schema(schema)
            validator = jsonschema.Draft7Validator(schema)
        except ModuleNotFoundError:
            pass
        except jsonschema.exceptions.SchemaError as exc:
            print(f"error: invalid Draft-07 schema {args.schema}: {exc.message}", file=sys.stderr)
            return 2
    if validator is None:
        unsupported = unsupported_schema_keywords(schema)
        if unsupported:
            print("error: built-in validator cannot safely evaluate this schema:", file=sys.stderr)
            for error in unsupported:
                print(f"  - {error}", file=sys.stderr)
            print("Install jsonschema or use only the documented built-in subset.", file=sys.stderr)
            return 2
    mode = "jsonschema (full Draft-07)" if validator is not None else "built-in (schema-driven subset)"

    files = collect(args.paths)
    if not files:
        print("error: no level files to validate", file=sys.stderr)
        return 2

    print(f"Validating {len(files)} level file(s) with {mode}\n")
    bad = 0
    for f in files:
        try:
            level = load_json_strict(f)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"  INVALID  {f}: not valid JSON: {exc}")
            bad += 1
            continue
        if validator is not None:
            errors = [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}"
                      for e in sorted(validator.iter_errors(level), key=lambda e: list(e.path))]
        else:
            try:
                errors = builtin_validate(level, schema)
            except (TypeError, ValueError, re.error) as exc:
                print(f"error: built-in validator cannot evaluate schema {args.schema}: {exc}", file=sys.stderr)
                return 2
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
