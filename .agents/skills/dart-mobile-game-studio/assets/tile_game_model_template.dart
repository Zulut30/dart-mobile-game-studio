// tile_game_model_template.dart
// Pure-Dart core paired with flutter_game_widget_template.dart. Copy into lib/models/.

import 'dart:math' as math;

enum GameStatus { menu, playing, paused, won, lost }

List<int> _validatePalette(List<int> palette) {
  if (palette.isEmpty) {
    throw ArgumentError.value(palette, 'palette', 'must not be empty');
  }
  return List<int>.unmodifiable(palette);
}

int _validateTileCount(int tileCount) {
  if (tileCount <= 0) {
    throw ArgumentError.value(tileCount, 'tileCount', 'must be positive');
  }
  return tileCount;
}

class Tile {
  const Tile({
    required this.id,
    required this.colorValue,
    this.matched = false,
  });

  final int id;
  final int colorValue;
  final bool matched;

  Tile copyWith({bool? matched}) =>
      Tile(id: id, colorValue: colorValue, matched: matched ?? this.matched);
}

/// Pure rules and transitions. Randomness is required and injected by the caller.
class TileGameModel {
  TileGameModel({
    required List<int> palette,
    required math.Random rng,
    int tileCount = 12,
  })  : palette = _validatePalette(palette),
        tileCount = _validateTileCount(tileCount),
        _rng = rng;

  final List<int> palette;
  final int tileCount;
  final math.Random _rng;

  GameStatus _status = GameStatus.menu;
  GameStatus get status => _status;

  List<Tile> _tiles = const <Tile>[];
  List<Tile> get tiles => _tiles;

  int _score = 0;
  int get score => _score;
  int get matchedCount => _score;
  double get progress => matchedCount / tileCount;

  void start() {
    if (_status != GameStatus.menu &&
        _status != GameStatus.won &&
        _status != GameStatus.lost) {
      return;
    }
    _tiles = _deal();
    _score = 0;
    _status = GameStatus.playing;
  }

  void pause() {
    if (_status == GameStatus.playing) _status = GameStatus.paused;
  }

  void resume() {
    if (_status == GameStatus.paused) _status = GameStatus.playing;
  }

  void lose() {
    if (_status == GameStatus.playing) _status = GameStatus.lost;
  }

  void quitToMenu() => _status = GameStatus.menu;

  bool tapTile(int id) {
    if (_status != GameStatus.playing) return false;
    final index = _tiles.indexWhere((tile) => tile.id == id);
    if (index < 0 || _tiles[index].matched) return false;

    _tiles = List<Tile>.unmodifiable(
      List<Tile>.of(_tiles)..[index] = _tiles[index].copyWith(matched: true),
    );
    _score++;
    if (_tiles.every((tile) => tile.matched)) _status = GameStatus.won;
    return true;
  }

  List<Tile> _deal() {
    final dealt = List<Tile>.generate(
      tileCount,
      (index) => Tile(id: index, colorValue: palette[index % palette.length]),
    );
    for (var index = dealt.length - 1; index > 0; index--) {
      final swapIndex = _rng.nextInt(index + 1);
      final current = dealt[index];
      dealt[index] = dealt[swapIndex];
      dealt[swapIndex] = current;
    }
    return List<Tile>.unmodifiable(
      List<Tile>.generate(
        tileCount,
        (index) => Tile(id: index, colorValue: dealt[index].colorValue),
      ),
    );
  }
}
