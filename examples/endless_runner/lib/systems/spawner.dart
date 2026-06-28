import 'dart:math' show Random;

import '../models/run_config.dart';

/// Produces obstacle spacing and heights from an injected [Random], guaranteeing
/// **clearable** runs: every obstacle is below the jump apex, and gaps are wide
/// enough that a player can land and jump again between them. Pure Dart.
abstract final class Spawner {
  /// Horizontal gap (world units) to the next obstacle. At least the jump air-time
  /// times the current speed (so two obstacles can't be un-jumpable back-to-back),
  /// plus some variability.
  static double nextGap(Random rng, double speed, RunConfig c) {
    final airTime = 2 * c.jumpVelocity / c.gravity; // up + down
    final minGap = airTime * speed + c.playerSize * 3;
    final extra = rng.nextDouble() * 220;
    return minGap + extra;
  }

  /// Obstacle height (world units), strictly below the jump apex (with margin), so
  /// a well-timed jump always clears it.
  static double nextHeight(Random rng, RunConfig c) {
    const minH = 20.0;
    final maxH = c.maxJumpHeight * 0.7; // margin below the apex
    return minH + rng.nextDouble() * (maxH - minH);
  }
}
