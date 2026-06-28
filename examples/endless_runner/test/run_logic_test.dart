import 'package:endless_runner/models/game_phase.dart';
import 'package:endless_runner/models/obstacle.dart';
import 'package:endless_runner/models/run_config.dart';
import 'package:endless_runner/models/run_state.dart';
import 'package:endless_runner/models/runner.dart';
import 'package:endless_runner/systems/physics.dart';
import 'package:endless_runner/systems/run_logic.dart';
import 'package:endless_runner/systems/seeded_random.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const config = RunConfig();

  group('start', () {
    test('deals a playing run at base speed, grounded', () {
      final s = RunLogic.start(config, SeededRandom(1));
      expect(s.phase, GamePhase.playing);
      expect(s.speed, config.baseSpeed);
      expect(s.runner.grounded, isTrue);
      expect(s.distance, 0);
    });
  });

  group('advance', () {
    test('scores distance while playing', () {
      var s = RunLogic.start(config, SeededRandom(1));
      final rng = SeededRandom(1);
      s = RunLogic.advance(s, 1 / 60, rng);
      expect(s.distance, greaterThan(0));
    });

    test('is a no-op when not playing', () {
      final over = RunLogic.start(config, SeededRandom(1)).copyWith(phase: GamePhase.gameOver);
      expect(RunLogic.advance(over, 1 / 60, SeededRandom(1)), equals(over));
    });

    test('a collision ends the run', () {
      // Obstacle parked on the player; big untilSpawn so nothing else spawns.
      final s = RunState(
        phase: GamePhase.playing,
        config: config,
        runner: const Runner(),
        obstacles: [Obstacle(id: 0, x: config.playerX, height: 60)],
        speed: config.baseSpeed,
        untilSpawn: 1e9,
      );
      expect(RunLogic.advance(s, 1 / 60, SeededRandom(1)).phase, GamePhase.gameOver);
    });

    test('clamps a huge dt (no teleport)', () {
      final s = RunLogic.start(config, SeededRandom(1));
      final huge = RunLogic.advance(s, 5, SeededRandom(1)); // 5s frame
      // distance gained is bounded by maxSpeed * the clamped step.
      expect(huge.distance, lessThan(config.maxSpeed * Physics.maxStep + 1));
    });

    test('is frame-rate independent (ramp off → exact)', () {
      const c = RunConfig(rampPerSecond: 0); // constant speed isolates the check
      final base = RunState(
        phase: GamePhase.playing,
        config: c,
        runner: const Runner(y: 500), // high up: no landing, no spawn, no obstacles
        obstacles: const [],
        speed: c.baseSpeed,
        untilSpawn: 1e9,
      );
      var two = RunLogic.advance(base, 1 / 120, SeededRandom(1));
      two = RunLogic.advance(two, 1 / 120, SeededRandom(1));
      final one = RunLogic.advance(base, 1 / 60, SeededRandom(1));
      expect(two.distance, closeTo(one.distance, 1e-9));
    });
  });

  group('jump', () {
    test('launches only when grounded; no double-jump', () {
      final s = RunLogic.start(config, SeededRandom(1));
      final j = RunLogic.jump(s);
      expect(j.runner.vy, config.jumpVelocity);
      expect(j.runner.grounded, isFalse);
      expect(RunLogic.jump(j), equals(j)); // airborne → no-op
    });

    test('is a no-op when not playing', () {
      final menu = RunLogic.start(config, SeededRandom(1)).copyWith(phase: GamePhase.menu);
      expect(RunLogic.jump(menu), equals(menu));
    });
  });

  group('determinism', () {
    RunState playOut(int seed) {
      var s = RunLogic.start(config, SeededRandom(seed));
      final rng = SeededRandom(seed);
      for (var i = 0; i < 400; i++) {
        s = RunLogic.advance(s, 1 / 60, rng);
      }
      return s;
    }

    test('same seed → identical run', () {
      expect(playOut(42), equals(playOut(42)));
    });
  });
}
