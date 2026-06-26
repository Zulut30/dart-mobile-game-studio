/// A single card on the board. Immutable value type — edits produce a copy via
/// [copyWith], and equality is by value so two boards compare correctly.
///
/// Pure Dart: no Flutter import, so it runs under `dart test` on the VM.
class MemoryCard {
  /// Creates a card. [id] is the board slot (unique, stable for a match);
  /// [faceId] is the pair identity — two cards share a [faceId].
  const MemoryCard({
    required this.id,
    required this.faceId,
    this.isFaceUp = false,
    this.isMatched = false,
  });

  /// Unique board-slot index (`0 .. cards.length - 1`). Stable for the match;
  /// good as a widget `ValueKey`.
  final int id;

  /// Pair identity (`0 .. pairs - 1`). The two cards of a pair share this.
  final int faceId;

  /// Whether the face is currently revealed.
  final bool isFaceUp;

  /// Whether this card has been matched (stays face-up, locked).
  final bool isMatched;

  /// Returns a copy with the given fields replaced.
  MemoryCard copyWith({bool? isFaceUp, bool? isMatched}) => MemoryCard(
        id: id,
        faceId: faceId,
        isFaceUp: isFaceUp ?? this.isFaceUp,
        isMatched: isMatched ?? this.isMatched,
      );

  @override
  bool operator ==(Object other) =>
      other is MemoryCard &&
      other.id == id &&
      other.faceId == faceId &&
      other.isFaceUp == isFaceUp &&
      other.isMatched == isMatched;

  @override
  int get hashCode => Object.hash(id, faceId, isFaceUp, isMatched);

  @override
  String toString() =>
      'MemoryCard(id: $id, faceId: $faceId, up: $isFaceUp, matched: $isMatched)';
}
