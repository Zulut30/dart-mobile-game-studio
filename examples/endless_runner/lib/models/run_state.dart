import 'game_phase.dart';
import 'obstacle.dart';
import 'run_config.dart';
import 'runner.dart';

/// The whole run as one immutable value. The pure systems (`run_logic`) produce a
/// new `RunState` each step; the Flame layer renders it. No engine import.
class RunState {
  const RunState({
    required this.phase,
    required this.config,
    required this.runner,
    required this.obstacles,
    required this.speed,
    this.distance = 0,
    this.nextId = 0,
    this.untilSpawn = 0,
  });

  final GamePhase phase;
  final RunConfig config;
  final Runner runner;

  /// Live obstacles, left-to-right by spawn order.
  final List<Obstacle> obstacles;

  /// Current scroll speed (world units / s).
  final double speed;

  /// Distance run so far (world units).
  final double distance;

  /// Next obstacle id to assign.
  final int nextId;

  /// World distance remaining until the next spawn.
  final double untilSpawn;

  /// Player-facing score (1 point per 10 world units).
  int get score => distance ~/ 10;

  bool get isOver => phase == GamePhase.gameOver;

  RunState copyWith({
    GamePhase? phase,
    Runner? runner,
    List<Obstacle>? obstacles,
    double? speed,
    double? distance,
    int? nextId,
    double? untilSpawn,
  }) =>
      RunState(
        phase: phase ?? this.phase,
        config: config,
        runner: runner ?? this.runner,
        obstacles: obstacles ?? this.obstacles,
        speed: speed ?? this.speed,
        distance: distance ?? this.distance,
        nextId: nextId ?? this.nextId,
        untilSpawn: untilSpawn ?? this.untilSpawn,
      );

  @override
  bool operator ==(Object other) =>
      other is RunState &&
      other.phase == phase &&
      other.runner == runner &&
      other.speed == speed &&
      other.distance == distance &&
      other.nextId == nextId &&
      other.untilSpawn == untilSpawn &&
      _obstaclesEqual(other.obstacles, obstacles);

  @override
  int get hashCode => Object.hash(
        phase,
        runner,
        speed,
        distance,
        nextId,
        untilSpawn,
        Object.hashAll(obstacles),
      );
}

bool _obstaclesEqual(List<Obstacle> a, List<Obstacle> b) {
  if (identical(a, b)) return true;
  if (a.length != b.length) return false;
  for (var i = 0; i < a.length; i++) {
    if (a[i] != b[i]) return false;
  }
  return true;
}
