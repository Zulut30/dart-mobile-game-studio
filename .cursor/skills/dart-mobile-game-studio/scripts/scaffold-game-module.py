#!/usr/bin/env python3
"""
scaffold-game-module.py — create a small, BUILDABLE pure-Dart game-core package for a requested
game type. NON-DESTRUCTIVE: never overwrites existing files; only creates what's missing.

The output is a real Dart package: `dart pub get && dart test` works immediately, so the "pure,
testable game core" rule is true from the first command. The Flutter UI / Flame layer is added on
top in a Flutter app that depends on this core (see the generated README).

Usage:
    scaffold-game-module.py --name SpaceJump --type simple-platformer
    scaffold-game-module.py --name ColorPals --type coloring-shapes --dest ./packages
    scaffold-game-module.py --list-types
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SUPPORTED_TYPES = [
    "coloring-shapes", "simple-platformer", "drag-and-drop-puzzle", "memory-cards",
    "shape-matching", "endless-runner-lite", "tap-reaction",
]
# Types that need continuous motion/physics -> Flame (hybrid). Others -> Flutter-widgets-only.
FLAME_TYPES = {"simple-platformer", "endless-runner-lite"}


def to_snake(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", name)
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", s)  # camelCase boundary
    return re.sub(r"_+", "_", s).strip("_").lower()


def to_pascal(name: str) -> str:
    return "".join(w[:1].upper() + w[1:] for w in to_snake(name).split("_") if w)


def pubspec(snake: str, gtype: str) -> str:
    return f"""name: {snake}
description: Pure-Dart game core for a {gtype} game (no Flutter/Flame imports). Unit-tested with dart test.
publish_to: none
version: 0.1.0

environment:
  sdk: ^3.4.0

dev_dependencies:
  lints: ^4.0.0
  test: ^1.25.0
"""


def analysis_options() -> str:
    return "include: package:lints/recommended.yaml\n"


def model_stub(snake: str, pascal: str, gtype: str) -> str:
    return f"""/// Pure, testable game logic for the {gtype} game. NO Flutter/Flame imports.
///
/// This is the single source of truth: the UI/Flame layer renders it and forwards input.
/// Advance time-based systems with a clamped [dt]; inject a seeded Random for determinism.
library;

enum {pascal}State {{ menu, playing, paused, won, lost }}

/// The game model. Keep all rules here so they are unit-testable with `dart test`.
class {pascal}Game {{
  {pascal}State state = {pascal}State.menu;
  int score = 0;

  /// Begin a fresh run.
  void start() {{
    score = 0;
    state = {pascal}State.playing;
  }}

  /// Advance the simulation by [dt] seconds. Frame-rate independent; the renderer passes an
  /// already-clamped [dt] (Flame does NOT clamp it for you).
  void advance(double dt) {{
    if (state != {pascal}State.playing) return;
    // TODO: advance spawners/timers/difficulty for {gtype} here.
  }}

  // TODO: add the {gtype} rules — legal moves, scoring, win/lose detection.
}}
"""


def lib_export(snake: str) -> str:
    return f"/// {snake} — pure-Dart game core. Import this from your Flutter/Flame app.\n" \
           f"library {snake};\n\nexport 'src/{snake}_game.dart';\n"


def test_stub(snake: str, pascal: str) -> str:
    return f"""import 'package:test/test.dart';
import 'package:{snake}/{snake}.dart';

void main() {{
  test('starts in playing with zero score', () {{
    final game = {pascal}Game()..start();
    expect(game.state, {pascal}State.playing);
    expect(game.score, 0);
  }});

  test('advance does nothing unless playing', () {{
    final game = {pascal}Game();
    game.advance(0.016);
    expect(game.state, {pascal}State.menu);
  }});
}}
"""


def readme(snake: str, pascal: str, gtype: str, mode: str) -> str:
    return f"""# {snake}

Scaffolded **{gtype}** game core ({mode}).

- **Source of truth:** `lib/src/{snake}_game.dart` (`{pascal}Game`) — pure Dart, no Flutter/Flame.

## Build & test the core (runs anywhere — no device)
```bash
cd {snake}
dart pub get
dart analyze
dart test
```

## Layout
- `pubspec.yaml` — the pure-Dart core package (dev deps: `lints`, `test`).
- `lib/{snake}.dart` — public export.
- `lib/src/{snake}_game.dart` — the rules/state (single source of truth).
- `test/{snake}_test.dart` — unit tests (`dart test`).

## Add the Flutter UI / Flame layer
Create a Flutter app and depend on this core:
```yaml
# in the app's pubspec.yaml
dependencies:
  {snake}:
    path: ../{snake}
```
Then build the UI from the skill's `assets/flutter_game_widget_template.dart` (widgets-only) or
`assets/flame_game_template.dart` (Flame/hybrid), keeping the widgets/components thin over
`{pascal}Game`. The UI imports `package:{snake}/{snake}.dart`; the core never imports Flutter.

## Next steps
1. Flesh out `{pascal}Game` with the {gtype} rules (and split systems into `lib/systems/`).
2. Add level data as JSON (validate vs the skill's `level-schema-template.json`).
3. Wire persistence for progress/settings only.
4. Run the skill's review checklists (kids/privacy, accessibility, performance, release).

> No copyrighted assets. Use placeholder vector art (`CustomPainter`/`flutter_svg`) or user-owned only.
"""


def create_file(path: Path, content: str, created: list[str], skipped: list[str]) -> None:
    if path.exists():
        skipped.append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(str(path))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Scaffold a buildable pure-Dart game-core package.")
    ap.add_argument("--name", help="Game name, e.g. SpaceJump (becomes package space_jump).")
    ap.add_argument("--type", dest="gtype", help="Game type (see --list-types).")
    ap.add_argument("--dest", default=".", help="Destination directory (default: current dir).")
    ap.add_argument("--list-types", action="store_true", help="List supported game types and exit.")
    args = ap.parse_args(argv)

    if args.list_types:
        print("Supported types:")
        for t in SUPPORTED_TYPES:
            mode = "Flame (hybrid)" if t in FLAME_TYPES else "Flutter-widgets-only"
            print(f"  - {t:<22} -> {mode}")
        return 0

    if not args.name or not args.gtype:
        ap.error("--name and --type are required (or use --list-types)")
    if args.gtype not in SUPPORTED_TYPES:
        print(f"error: unknown type '{args.gtype}'. Use --list-types.", file=sys.stderr)
        return 2

    snake = to_snake(args.name)
    pascal = to_pascal(args.name)
    if not snake:
        print(f"error: --name '{args.name}' has no usable identifier characters.", file=sys.stderr)
        return 2
    gtype = args.gtype
    mode = "Flame (hybrid)" if gtype in FLAME_TYPES else "Flutter-widgets-only"
    root = Path(args.dest).expanduser().resolve() / snake

    created: list[str] = []
    skipped: list[str] = []
    create_file(root / "pubspec.yaml", pubspec(snake, gtype), created, skipped)
    create_file(root / "analysis_options.yaml", analysis_options(), created, skipped)
    create_file(root / "lib" / f"{snake}.dart", lib_export(snake), created, skipped)
    create_file(root / "lib" / "src" / f"{snake}_game.dart", model_stub(snake, pascal, gtype), created, skipped)
    create_file(root / "test" / f"{snake}_test.dart", test_stub(snake, pascal), created, skipped)
    create_file(root / "README.md", readme(snake, pascal, gtype, mode), created, skipped)

    print(f"Scaffolded '{pascal}Game' (package {snake}, {gtype}, {mode}) at: {root}")
    if created:
        print("\nCreated:")
        for p in created:
            print(f"  + {p}")
    if skipped:
        print("\nSkipped (already exist, left untouched):")
        for p in skipped:
            print(f"  = {p}")
    print(f"\nNext: cd {snake} && dart pub get && dart test  — then add the UI per the README.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
