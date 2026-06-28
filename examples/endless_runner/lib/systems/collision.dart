import '../models/obstacle.dart';
import '../models/run_config.dart';
import '../models/runner.dart';

/// Axis-aligned bounding-box overlap between the player and an obstacle. Pure Dart
/// (no Flame `HasCollisionDetection` here) so the *verdict* is unit-testable on the
/// VM; the Flame layer may also use hitboxes, but this is the authoritative check.
abstract final class Collision {
  /// True if the player box overlaps the obstacle box. The player clears an
  /// obstacle by being above its `height` (`runner.y >= height`) as it passes.
  static bool hits(Runner r, Obstacle o, RunConfig c) {
    final px0 = c.playerX;
    final px1 = c.playerX + c.playerSize;
    final py0 = r.y;
    final py1 = r.y + c.playerSize;

    final ox0 = o.x;
    final ox1 = o.x + c.obstacleWidth;
    const oy0 = 0.0;
    final oy1 = o.height;

    return px0 < ox1 && px1 > ox0 && py0 < oy1 && py1 > oy0;
  }
}
