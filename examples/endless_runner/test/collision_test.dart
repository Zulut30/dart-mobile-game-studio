import 'package:endless_runner/models/obstacle.dart';
import 'package:endless_runner/models/run_config.dart';
import 'package:endless_runner/models/runner.dart';
import 'package:endless_runner/systems/collision.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const c = RunConfig();

  group('Collision.hits', () {
    test('a grounded player overlapping an obstacle is a hit', () {
      expect(Collision.hits(const Runner(), Obstacle(id: 0, x: c.playerX, height: 50), c), isTrue);
    });

    test('a player jumping above the obstacle clears it', () {
      // y = 200 is above height 50, so the boxes do not overlap vertically.
      expect(Collision.hits(const Runner(y: 200), Obstacle(id: 0, x: c.playerX, height: 50), c), isFalse);
    });

    test('an obstacle far to the right does not hit', () {
      expect(Collision.hits(const Runner(), const Obstacle(id: 0, x: 1000, height: 50), c), isFalse);
    });

    test('an obstacle already passed (to the left) does not hit', () {
      expect(Collision.hits(const Runner(), const Obstacle(id: 0, x: -200, height: 50), c), isFalse);
    });
  });
}
