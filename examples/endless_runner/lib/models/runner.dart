/// The player's vertical state. Immutable value type; pure Dart.
///
/// `y` is height above the ground (0 = standing, positive = airborne); `vy` is
/// vertical velocity (positive = rising). Horizontal position is fixed (the world
/// scrolls past), so it lives in [RunConfig], not here.
class Runner {
  const Runner({this.y = 0, this.vy = 0, this.grounded = true});

  /// Height above the ground line (≥ 0).
  final double y;

  /// Vertical velocity (positive = up).
  final double vy;

  /// Whether the runner is on the ground (can jump).
  final bool grounded;

  Runner copyWith({double? y, double? vy, bool? grounded}) => Runner(
        y: y ?? this.y,
        vy: vy ?? this.vy,
        grounded: grounded ?? this.grounded,
      );

  @override
  bool operator ==(Object other) =>
      other is Runner && other.y == y && other.vy == vy && other.grounded == grounded;

  @override
  int get hashCode => Object.hash(y, vy, grounded);

  @override
  String toString() => 'Runner(y: $y, vy: $vy, grounded: $grounded)';
}
