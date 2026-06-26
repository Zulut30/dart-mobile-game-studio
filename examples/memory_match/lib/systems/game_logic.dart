import '../models/game_phase.dart';
import '../models/game_state.dart';
import '../models/memory_card.dart';

/// The rules of memory-match as pure functions: `(state, action) -> state`.
///
/// No Flutter import, no `Random`, no clock, no I/O — same input always yields
/// the same output, so every rule is verified with `dart test` on the VM. The UI
/// calls these and renders the returned state; it owns timing (the brief reveal
/// before `resolveMismatch`), not the rules.
abstract final class GameLogic {
  /// Flips the card at [index]. Ignored (returns the same state) when not
  /// playing, while a mismatch is shown ([GameState.isLocked]), out of range, or
  /// on an already-matched / already-face-up card.
  ///
  /// First flip of a turn: reveals the card and records it as `firstFlipped`.
  /// Second flip: reveals it, counts a move, then either matches both (and may
  /// transition to `won`) or sets `pendingMismatch` and locks input until
  /// [resolveMismatch].
  static GameState flip(GameState state, int index) {
    if (state.phase != GamePhase.playing) return state;
    if (state.isLocked) return state;
    if (index < 0 || index >= state.cards.length) return state;

    final card = state.cards[index];
    if (card.isMatched || card.isFaceUp) return state;

    // First flip of the turn.
    if (state.firstFlipped == null) {
      final cards = _replace(state.cards, index, card.copyWith(isFaceUp: true));
      return state.copyWith(cards: cards, firstFlipped: index);
    }

    // Second flip: reveal it, count the move, resolve the pair.
    final firstIndex = state.firstFlipped!;
    final firstCard = state.cards[firstIndex];
    var cards = _replace(state.cards, index, card.copyWith(isFaceUp: true));
    final moves = state.moves + 1;

    if (firstCard.faceId == card.faceId) {
      // Match: lock both face-up.
      cards = _replace(cards, firstIndex, firstCard.copyWith(isMatched: true, isFaceUp: true));
      cards = _replace(cards, index, card.copyWith(isMatched: true, isFaceUp: true));
      final next = state.copyWith(cards: cards, moves: moves, clearFirstFlipped: true);
      return next.isWon ? next.copyWith(phase: GamePhase.won) : next;
    }

    // Mismatch: both stay up; lock input until resolveMismatch flips them back.
    return state.copyWith(
      cards: cards,
      moves: moves,
      clearFirstFlipped: true,
      pendingMismatch: <int>[firstIndex, index],
    );
  }

  /// Flips the pending mismatched pair back face-down and unlocks input. A no-op
  /// when there is no pending mismatch. The UI calls this after a short reveal
  /// delay (gated on Reduce Motion).
  static GameState resolveMismatch(GameState state) {
    final pending = state.pendingMismatch;
    if (pending == null) return state;
    var cards = state.cards;
    for (final i in pending) {
      cards = _replace(cards, i, cards[i].copyWith(isFaceUp: false));
    }
    return state.copyWith(cards: cards, clearPendingMismatch: true);
  }

  /// Toggles between `playing` and `paused`; a no-op in any other phase.
  static GameState togglePause(GameState state) => switch (state.phase) {
        GamePhase.playing => state.copyWith(phase: GamePhase.paused),
        GamePhase.paused => state.copyWith(phase: GamePhase.playing),
        _ => state,
      };

  static List<MemoryCard> _replace(List<MemoryCard> cards, int index, MemoryCard card) {
    final next = List<MemoryCard>.of(cards);
    next[index] = card;
    return next;
  }
}
