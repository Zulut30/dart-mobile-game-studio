import 'package:flutter_test/flutter_test.dart';
import 'package:memory_match/models/game_phase.dart';
import 'package:memory_match/systems/board_factory.dart';
import 'package:memory_match/systems/seeded_random.dart';

void main() {
  group('BoardFactory.newGame', () {
    test('deals 2 * pairs cards in the playing phase', () {
      final state = BoardFactory.newGame(pairs: 6, rng: SeededRandom(1));
      expect(state.cards, hasLength(12));
      expect(state.totalPairs, 6);
      expect(state.phase, GamePhase.playing);
      expect(state.moves, 0);
      expect(state.firstFlipped, isNull);
    });

    test('every faceId appears exactly twice', () {
      final state = BoardFactory.newGame(pairs: 8, rng: SeededRandom(99));
      final counts = <int, int>{};
      for (final card in state.cards) {
        counts[card.faceId] = (counts[card.faceId] ?? 0) + 1;
      }
      expect(counts.keys.toList()..sort(), List<int>.generate(8, (i) => i));
      expect(counts.values.every((c) => c == 2), isTrue);
    });

    test('ids are the slot indices (0 .. n-1), all face-down and unmatched', () {
      final state = BoardFactory.newGame(pairs: 5, rng: SeededRandom(7));
      for (var i = 0; i < state.cards.length; i++) {
        expect(state.cards[i].id, i);
        expect(state.cards[i].isFaceUp, isFalse);
        expect(state.cards[i].isMatched, isFalse);
      }
    });

    test('is deterministic: same seed yields an identical layout', () {
      final a = BoardFactory.newGame(pairs: 6, rng: SeededRandom(42));
      final b = BoardFactory.newGame(pairs: 6, rng: SeededRandom(42));
      // value equality on GameState compares the whole card list
      expect(a, equals(b));
      expect([for (final c in a.cards) c.faceId], [for (final c in b.cards) c.faceId]);
    });

    test('rejects fewer than one pair', () {
      expect(() => BoardFactory.newGame(pairs: 0, rng: SeededRandom(1)), throwsArgumentError);
    });
  });
}
