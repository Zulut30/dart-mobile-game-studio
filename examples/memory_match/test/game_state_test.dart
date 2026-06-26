import 'package:flutter_test/flutter_test.dart';
import 'package:memory_match/models/game_phase.dart';
import 'package:memory_match/models/game_state.dart';
import 'package:memory_match/models/memory_card.dart';

GameState sample() => const GameState(
      cards: [
        MemoryCard(id: 0, faceId: 0),
        MemoryCard(id: 1, faceId: 0),
      ],
      phase: GamePhase.playing,
      firstFlipped: 0,
    );

void main() {
  group('value equality', () {
    test('two identical states are equal and share a hashCode', () {
      expect(sample(), equals(sample()));
      expect(sample().hashCode, sample().hashCode);
    });

    test('a differing field breaks equality', () {
      expect(sample().copyWith(moves: 1), isNot(equals(sample())));
      final flipped = sample().copyWith(
        cards: [
          const MemoryCard(id: 0, faceId: 0, isFaceUp: true),
          const MemoryCard(id: 1, faceId: 0),
        ],
      );
      expect(flipped, isNot(equals(sample())));
    });
  });

  group('copyWith', () {
    test('clearFirstFlipped sets it to null; a null arg leaves it unchanged', () {
      expect(sample().copyWith(clearFirstFlipped: true).firstFlipped, isNull);
      expect(sample().copyWith().firstFlipped, 0); // unchanged
    });

    test('clearPendingMismatch sets it to null', () {
      final pending = sample().copyWith(pendingMismatch: [0, 1]);
      expect(pending.isLocked, isTrue);
      expect(pending.copyWith(clearPendingMismatch: true).pendingMismatch, isNull);
    });
  });

  group('derived getters', () {
    test('matchedPairs / totalPairs / isWon', () {
      const won = GameState(
        cards: [
          MemoryCard(id: 0, faceId: 0, isFaceUp: true, isMatched: true),
          MemoryCard(id: 1, faceId: 0, isFaceUp: true, isMatched: true),
        ],
        phase: GamePhase.won,
      );
      expect(won.totalPairs, 1);
      expect(won.matchedPairs, 1);
      expect(won.isWon, isTrue);
      expect(sample().isWon, isFalse);
    });
  });
}
