// flame_game_model_template.dart
// Pure-Dart core paired with flame_game_template.dart. Copy into lib/models/.

/// Explicit game state machine: menu -> playing -> paused -> won/lost -> menu.
enum GameStatus { menu, playing, paused, won, lost }

double _validateWorldExtent(double value, String name) {
  if (!value.isFinite || value <= 0) {
    throw ArgumentError.value(value, name, 'must be finite and positive');
  }
  return value;
}

/// A renderer intent expressed only in model/world coordinates.
class TapIntent {
  const TapIntent(this.x, this.y);

  final double x;
  final double y;
}

/// Deterministic game model with no Flutter, Flame, dart:ui, I/O, or plugins.
class GameModel {
  GameModel({double worldWidth = 400, double worldHeight = 600})
      : worldWidth = _validateWorldExtent(worldWidth, 'worldWidth'),
        worldHeight = _validateWorldExtent(worldHeight, 'worldHeight');

  final double worldWidth;
  final double worldHeight;

  double entityX = 0;
  double entityY = 300;

  static const double _driftPerSecond = 60;
  static const double _tapNudge = 48;

  GameStatus _status = GameStatus.menu;
  GameStatus get status => _status;

  void start() {
    if (_status != GameStatus.menu &&
        _status != GameStatus.won &&
        _status != GameStatus.lost) {
      return;
    }
    entityX = 0;
    entityY = worldHeight / 2;
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

  /// Advance by a renderer-clamped [dt] in seconds.
  void advance(double dt) {
    if (_status != GameStatus.playing || !dt.isFinite || dt <= 0) return;
    entityX += _driftPerSecond * dt;
    if (entityX >= worldWidth) {
      entityX = worldWidth;
      _status = GameStatus.won;
    }
  }

  void handleTap(TapIntent intent) {
    if (_status != GameStatus.playing) return;
    if (!intent.x.isFinite || !intent.y.isFinite) return;
    final direction = intent.y < entityY ? -1.0 : 1.0;
    entityY =
        (entityY + direction * _tapNudge).clamp(0.0, worldHeight).toDouble();
  }
}
