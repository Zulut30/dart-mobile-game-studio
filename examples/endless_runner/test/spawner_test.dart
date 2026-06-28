import 'package:endless_runner/models/run_config.dart';
import 'package:endless_runner/systems/seeded_random.dart';
import 'package:endless_runner/systems/spawner.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Spawner', () {
    test('every obstacle height is clearable (below the jump apex)', () {
      const c = RunConfig();
      for (var seed = 0; seed < 100; seed++) {
        final rng = SeededRandom(seed);
        for (var i = 0; i < 20; i++) {
          final h = Spawner.nextHeight(rng, c);
          expect(h, lessThan(c.maxJumpHeight)); // a jump always clears it
          expect(h, greaterThanOrEqualTo(20));
        }
      }
    });

    test('gap is at least the jump air-time times speed (never un-jumpable)', () {
      const c = RunConfig();
      final rng = SeededRandom(1);
      final airTime = 2 * c.jumpVelocity / c.gravity;
      final minGap = airTime * c.baseSpeed + c.playerSize * 3;
      for (var i = 0; i < 50; i++) {
        expect(Spawner.nextGap(rng, c.baseSpeed, c), greaterThanOrEqualTo(minGap));
      }
    });

    test('is deterministic for a seed', () {
      const c = RunConfig();
      final a = SeededRandom(5);
      final b = SeededRandom(5);
      for (var i = 0; i < 10; i++) {
        expect(Spawner.nextGap(a, 300, c), Spawner.nextGap(b, 300, c));
        expect(Spawner.nextHeight(a, c), Spawner.nextHeight(b, c));
      }
    });
  });
}
