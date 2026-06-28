/// An obstacle scrolling right-to-left. Immutable value type; pure Dart.
///
/// `x` is the left edge in world units (decreases as it scrolls); `height` is how
/// tall it stands from the ground — the runner must be above it to clear it.
class Obstacle {
  const Obstacle({required this.id, required this.x, required this.height});

  /// Stable identity (good as a widget/component key).
  final int id;

  /// Left-edge world X (scrolls toward 0 and negative).
  final double x;

  /// Height from the ground; clear it by jumping above `height`.
  final double height;

  Obstacle copyWith({double? x}) => Obstacle(id: id, x: x ?? this.x, height: height);

  @override
  bool operator ==(Object other) =>
      other is Obstacle && other.id == id && other.x == x && other.height == height;

  @override
  int get hashCode => Object.hash(id, x, height);

  @override
  String toString() => 'Obstacle(id: $id, x: $x, h: $height)';
}
