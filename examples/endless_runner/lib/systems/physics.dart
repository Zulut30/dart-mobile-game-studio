import '../models/run_config.dart';
import '../models/runner.dart';

/// Vertical integration for the runner. Pure Dart — no engine import.
abstract final class Physics {
  /// The maximum step the simulation will take. Flame supplies `dt` but does NOT
  /// clamp it, so a GC/load/backgrounding hitch could otherwise teleport the
  /// player through an obstacle. Clamp it here, the single source of truth.
  static const double maxStep = 1 / 30;

  /// Clamp a raw frame delta to a safe step.
  static double clampDt(double dt) => dt.clamp(0.0, maxStep);

  /// Semi-implicit Euler step: gravity pulls `vy` down, `y` integrates `vy`, and
  /// landing snaps to the ground. Frame-rate independent (everything scales by `dt`).
  static Runner integrate(Runner r, double dt, RunConfig c) {
    var vy = r.vy - c.gravity * dt;
    var y = r.y + vy * dt;
    var grounded = false;
    if (y <= 0) {
      y = 0;
      vy = 0;
      grounded = true;
    }
    return Runner(y: y, vy: vy, grounded: grounded);
  }
}
