#!/usr/bin/env python3
"""Materialize canonical Dart/Flutter template pairs as disposable CI projects.

The generated projects prove three separate contracts:
1. both model templates compile and test on the standalone Dart VM;
2. the widgets renderer compiles, mounts, and exposes an accessible tap action;
3. the Flame renderer compiles and mounts against the pinned minimum Flame API.

The destination must be empty. Existing output is never overwritten or deleted.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
ASSETS_DIR = SKILL_DIR / "assets"


PURE_PUBSPEC = """name: template_models
description: VM-only compile and behavior fixture for canonical game model templates.
publish_to: none
version: 0.0.0

environment:
  sdk: ">=3.4.0 <4.0.0"

dev_dependencies:
  lints: ^4.0.0
  test: ^1.25.0
"""

WIDGETS_PUBSPEC = """name: template_widgets
description: Compile and widget-test fixture for the canonical widgets game template.
publish_to: none
version: 0.0.0

environment:
  sdk: ">=3.4.0 <4.0.0"
  flutter: ">=3.22.0"

dependencies:
  flutter:
    sdk: flutter

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^4.0.0

flutter:
  uses-material-design: true
"""

FLAME_PUBSPEC = """name: template_flame
description: Compile and widget-test fixture for the canonical Flame game template.
publish_to: none
version: 0.0.0

environment:
  sdk: ">=3.4.0 <4.0.0"
  flutter: ">=3.22.0"

dependencies:
  flame: ^1.22.0
  flutter:
    sdk: flutter

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^4.0.0

flutter:
  uses-material-design: true
"""

PURE_TEST = """import 'dart:math' as math;

import 'package:template_models/flame_game_model_template.dart' as flame;
import 'package:template_models/seeded_random.dart';
import 'package:template_models/tile_game_model_template.dart' as tiles;
import 'package:test/test.dart';

void main() {
  test('Flame model validates input and reaches a terminal state', () {
    expect(() => flame.GameModel(worldWidth: 0), throwsArgumentError);

    final model = flame.GameModel(worldWidth: 10, worldHeight: 20)..start();
    expect(model.status, flame.GameStatus.playing);
    model.advance(1);
    expect(model.status, flame.GameStatus.won);
    expect(model.entityX, 10);
  });

  test('tile deals are deterministic, immutable, and completable', () {
    tiles.TileGameModel create() => tiles.TileGameModel(
          palette: const [1, 2, 3],
          tileCount: 6,
          rng: math.Random(7),
        )..start();

    final first = create();
    final second = create();
    expect(
      first.tiles.map((tile) => tile.colorValue),
      second.tiles.map((tile) => tile.colorValue),
    );
    expect(
      () => first.tiles.add(const tiles.Tile(id: 99, colorValue: 1)),
      throwsUnsupportedError,
    );

    for (final tile in first.tiles) {
      expect(first.tapTile(tile.id), isTrue);
    }
    expect(first.status, tiles.GameStatus.won);
  });

  test('seeded random repeats sequences and enforces Random bounds', () {
    final first = SeededRandom(42);
    final second = SeededRandom(42);
    expect(
      List<int>.generate(16, (_) => first.nextInt(1000)),
      List<int>.generate(16, (_) => second.nextInt(1000)),
    );
    expect(() => first.nextInt(0), throwsRangeError);
  });
}
"""

WIDGETS_TEST = """import 'dart:ui' show SemanticsAction;

import 'package:flutter_test/flutter_test.dart';
import 'package:template_widgets/main.dart';

void main() {
  testWidgets('widgets template mounts and exposes tile tap semantics', (
    tester,
  ) async {
    final semantics = tester.ensureSemantics();
    try {
      await tester.pumpWidget(const TileGameApp());
      await tester.tap(find.text('Play'));
      await tester.pumpAndSettle();

      final tile = find.bySemanticsLabel('Tile 1 of 12');
      expect(tile, findsOneWidget);
      expect(
        tester
            .getSemantics(tile)
            .getSemanticsData()
            .hasAction(SemanticsAction.tap),
        isTrue,
      );

      await tester.tap(find.byTooltip('Pause'));
      await tester.pumpAndSettle();
      expect(find.text('Resume'), findsOneWidget);
    } finally {
      semantics.dispose();
    }
  });
}
"""

FLAME_TEST = """import 'package:flame/game.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:template_flame/flame_game_model_template.dart';
import 'package:template_flame/flame_game_template.dart';

void main() {
  testWidgets('Flame template mounts and starts its pure model', (
    tester,
  ) async {
    final model = GameModel();
    final game = PlaceholderGame(model: model);

    await tester.pumpWidget(
      MaterialApp(
        home: SizedBox(width: 400, height: 600, child: GameWidget(game: game)),
      ),
    );
    await tester.pump(const Duration(milliseconds: 16));

    expect(find.byType(GameWidget<PlaceholderGame>), findsOneWidget);
    expect(model.status, GameStatus.playing);

    await tester.pumpWidget(const SizedBox.shrink());
  });
}
"""


def write_new(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing fixture file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_asset(name: str, destination: Path) -> None:
    source = ASSETS_DIR / name
    if not source.is_file():
        raise FileNotFoundError(f"canonical asset is missing: {source}")
    write_new(destination, source.read_text(encoding="utf-8"))


def materialize(destination: Path) -> list[Path]:
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"destination must be empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)

    pure = destination / "pure_models"
    write_new(pure / "pubspec.yaml", PURE_PUBSPEC)
    write_new(pure / "analysis_options.yaml", "include: package:lints/recommended.yaml\n")
    copy_asset("flame_game_model_template.dart", pure / "lib/flame_game_model_template.dart")
    copy_asset("seeded_random.dart", pure / "lib/seeded_random.dart")
    copy_asset("tile_game_model_template.dart", pure / "lib/tile_game_model_template.dart")
    write_new(pure / "test/model_contract_test.dart", PURE_TEST)

    widgets = destination / "widgets"
    write_new(widgets / "pubspec.yaml", WIDGETS_PUBSPEC)
    copy_asset("analysis_options.yaml", widgets / "analysis_options.yaml")
    copy_asset("flutter_game_widget_template.dart", widgets / "lib/main.dart")
    copy_asset("tile_game_model_template.dart", widgets / "lib/tile_game_model_template.dart")
    write_new(widgets / "test/widget_smoke_test.dart", WIDGETS_TEST)

    flame = destination / "flame"
    write_new(flame / "pubspec.yaml", FLAME_PUBSPEC)
    copy_asset("analysis_options.yaml", flame / "analysis_options.yaml")
    copy_asset("flame_game_template.dart", flame / "lib/flame_game_template.dart")
    copy_asset("flame_game_model_template.dart", flame / "lib/flame_game_model_template.dart")
    write_new(flame / "test/flame_smoke_test.dart", FLAME_TEST)

    return [pure, widgets, flame]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", required=True, type=Path, help="Empty output directory.")
    args = parser.parse_args(argv)

    try:
        projects = materialize(args.dest.expanduser().resolve())
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    for project in projects:
        print(project)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
