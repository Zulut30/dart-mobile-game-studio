import 'dart:math' as math;
import 'dart:math' show Random;

import '../models/game_phase.dart';
import '../models/obstacle.dart';
import '../models/run_config.dart';
import '../models/run_state.dart';
import '../models/runner.dart';
import 'collision.dart';
import 'physics.dart';
import 'spawner.dart';

/// The rules of the runner as pure functions. No engine import, no clock — given
/// the same (state, dt, Random) the result is identical, so `dart test` verifies
/// the simulation on the VM. The Flame layer calls these and renders the result.
abstract final class RunLogic {
  /// Deals a fresh run in the `playing` phase from an injected [Random].
  static RunState start(RunConfig config, Random rng) => RunState(
        phase: GamePhase.playing,
        config: config,
        runner: const Runner(),
        obstacles: const [],
        speed: config.baseSpeed,
        untilSpawn: Spawner.nextGap(rng, config.baseSpeed, config) * 0.5,
      );

  /// Advances one step by `rawDt` seconds: ramps speed, integrates the jump,
  /// scrolls + spawns obstacles, scores distance, and ends the run on a hit.
  /// `rawDt` is clamped internally ([Physics.clampDt]). A no-op when not playing.
  static RunState advance(RunState s, double rawDt, Random rng) {
    if (s.phase != GamePhase.playing) return s;
    final dt = Physics.clampDt(rawDt);
    final c = s.config;

    final speed = math.min(c.maxSpeed, s.speed + c.rampPerSecond * dt);
    final runner = Physics.integrate(s.runner, dt, c);

    // Scroll, then drop anything fully off the left edge.
    var obstacles = [
      for (final o in s.obstacles) o.copyWith(x: o.x - speed * dt),
    ]..removeWhere((o) => o.x + c.obstacleWidth < -50);

    var untilSpawn = s.untilSpawn - speed * dt;
    var nextId = s.nextId;
    if (untilSpawn <= 0) {
      obstacles = [
        ...obstacles,
        Obstacle(id: nextId, x: c.spawnX, height: Spawner.nextHeight(rng, c)),
      ];
      nextId++;
      untilSpawn += Spawner.nextGap(rng, speed, c);
    }

    final crashed = obstacles.any((o) => Collision.hits(runner, o, c));
    final next = s.copyWith(
      runner: runner,
      obstacles: obstacles,
      speed: speed,
      distance: s.distance + speed * dt,
      nextId: nextId,
      untilSpawn: untilSpawn,
    );
    return crashed ? next.copyWith(phase: GamePhase.gameOver) : next;
  }

  /// Launches a jump if the runner is grounded and playing; otherwise a no-op
  /// (no double-jumps). The view calls this on tap.
  static RunState jump(RunState s) {
    if (s.phase != GamePhase.playing || !s.runner.grounded) return s;
    return s.copyWith(runner: s.runner.copyWith(vy: s.config.jumpVelocity, grounded: false));
  }
}
