/// The game's lifecycle states. Pure Dart — no Flutter import, so the whole
/// model is unit-testable with `dart test` on the VM.
///
/// Memory-match is a no-fail game, so there is no `lost` phase: you can only win.
/// `paused` is included to model the full menu → playing → paused → won machine.
enum GamePhase {
  /// Title screen; no board yet.
  menu,

  /// A board is dealt and the player is flipping cards.
  playing,

  /// The player paused; the board is frozen.
  paused,

  /// Every pair is matched.
  won,
}
