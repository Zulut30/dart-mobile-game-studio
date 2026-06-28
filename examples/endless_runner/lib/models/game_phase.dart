/// Runner lifecycle. Pure Dart — VM-testable with `dart test`.
///
/// A lite endless runner is single-life and infinite, so it has no `won`: you run
/// until you crash (`gameOver`), then restart.
enum GamePhase {
  /// Title screen; no run yet.
  menu,

  /// Auto-running; tap to jump.
  playing,

  /// Crashed into an obstacle; show the score and a restart.
  gameOver,
}
