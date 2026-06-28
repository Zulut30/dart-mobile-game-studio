/// Immutable tuning for a run. Pure Dart — no engine import. All distances are in
/// world units; the renderer scales them to the screen.
///
/// A `balance-economist` (or a JSON file) can supply these; the rules read them.
class RunConfig {
  const RunConfig({
    this.baseSpeed = 220,
    this.rampPerSecond = 6,
    this.maxSpeed = 520,
    this.gravity = 2400,
    this.jumpVelocity = 760,
    this.groundY = 0,
    this.playerX = 120,
    this.playerSize = 44,
    this.spawnX = 900,
    this.obstacleWidth = 36,
  });

  /// Starting scroll speed (world units / second).
  final double baseSpeed;

  /// Speed gained per second of running.
  final double rampPerSecond;

  /// Speed ceiling so the run stays fair/clearable.
  final double maxSpeed;

  /// Downward acceleration (units / s²); positive pulls toward the ground.
  final double gravity;

  /// Upward launch speed on a jump (units / s).
  final double jumpVelocity;

  /// Ground line (the player's resting `y`). Up is negative `y`.
  final double groundY;

  /// Fixed horizontal position of the player.
  final double playerX;

  /// Player hit-box side (square).
  final double playerSize;

  /// X where a new obstacle enters from the right.
  final double spawnX;

  /// Obstacle hit-box width.
  final double obstacleWidth;

  /// Apex height a single jump reaches: `v² / 2g`. Used to keep spawns clearable.
  double get maxJumpHeight => (jumpVelocity * jumpVelocity) / (2 * gravity);
}
