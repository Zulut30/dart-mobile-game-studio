import 'game_phase.dart';
import 'memory_card.dart';

/// The whole game as one immutable value. The pure-Dart core (`board_factory`,
/// `game_logic`) produces new `GameState`s from old ones; the UI renders them.
///
/// No Flutter import — VM-testable with `dart test`.
class GameState {
  /// Creates a state. Prefer `BoardFactory.newGame` to deal a fresh board.
  const GameState({
    required this.cards,
    required this.phase,
    this.moves = 0,
    this.firstFlipped,
    this.pendingMismatch,
  });

  /// The board, in slot order.
  final List<MemoryCard> cards;

  /// Current lifecycle phase.
  final GamePhase phase;

  /// Completed turns (a turn = a second flip that resolves a pair).
  final int moves;

  /// Index of the first face-up unmatched card awaiting its partner, or `null`.
  final int? firstFlipped;

  /// The two slots of a just-revealed non-matching pair, awaiting flip-back, or
  /// `null`. While set, input is locked until `GameLogic.resolveMismatch`.
  final List<int>? pendingMismatch;

  /// Number of pairs matched so far.
  int get matchedPairs => cards.where((c) => c.isMatched).length ~/ 2;

  /// Total pairs on the board.
  int get totalPairs => cards.length ~/ 2;

  /// Whether every card is matched.
  bool get isWon => cards.isNotEmpty && cards.every((c) => c.isMatched);

  /// Whether input is currently locked (a mismatch is being shown).
  bool get isLocked => pendingMismatch != null;

  /// Returns a copy with the given fields replaced. Because [firstFlipped] and
  /// [pendingMismatch] are nullable, pass `clearFirstFlipped` / `clearPendingMismatch`
  /// to set them back to `null` (a plain `null` argument means "unchanged").
  GameState copyWith({
    List<MemoryCard>? cards,
    GamePhase? phase,
    int? moves,
    int? firstFlipped,
    bool clearFirstFlipped = false,
    List<int>? pendingMismatch,
    bool clearPendingMismatch = false,
  }) =>
      GameState(
        cards: cards ?? this.cards,
        phase: phase ?? this.phase,
        moves: moves ?? this.moves,
        firstFlipped: clearFirstFlipped ? null : (firstFlipped ?? this.firstFlipped),
        pendingMismatch:
            clearPendingMismatch ? null : (pendingMismatch ?? this.pendingMismatch),
      );

  @override
  bool operator ==(Object other) =>
      other is GameState &&
      other.phase == phase &&
      other.moves == moves &&
      other.firstFlipped == firstFlipped &&
      _intListEquals(other.pendingMismatch, pendingMismatch) &&
      _cardListEquals(other.cards, cards);

  @override
  int get hashCode => Object.hash(
        phase,
        moves,
        firstFlipped,
        Object.hashAll(pendingMismatch ?? const <int>[]),
        Object.hashAll(cards),
      );
}

bool _cardListEquals(List<MemoryCard> a, List<MemoryCard> b) {
  if (identical(a, b)) return true;
  if (a.length != b.length) return false;
  for (var i = 0; i < a.length; i++) {
    if (a[i] != b[i]) return false;
  }
  return true;
}

bool _intListEquals(List<int>? a, List<int>? b) {
  if (identical(a, b)) return true;
  if (a == null || b == null) return false;
  if (a.length != b.length) return false;
  for (var i = 0; i < a.length; i++) {
    if (a[i] != b[i]) return false;
  }
  return true;
}
