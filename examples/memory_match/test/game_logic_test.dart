import 'package:flutter_test/flutter_test.dart';
import 'package:memory_match/models/game_phase.dart';
import 'package:memory_match/models/game_state.dart';
import 'package:memory_match/models/memory_card.dart';
import 'package:memory_match/systems/game_logic.dart';

/// A hand-built 4-card board with known positions, so every expected result is
/// exact: pair 0 sits in slots 0 & 2, pair 1 in slots 1 & 3.
GameState board() => const GameState(
      cards: [
        MemoryCard(id: 0, faceId: 0),
        MemoryCard(id: 1, faceId: 1),
        MemoryCard(id: 2, faceId: 0),
        MemoryCard(id: 3, faceId: 1),
      ],
      phase: GamePhase.playing,
    );

void main() {
  group('first flip', () {
    test('reveals the card and records firstFlipped, no move counted', () {
      final s = GameLogic.flip(board(), 0);
      expect(s.cards[0].isFaceUp, isTrue);
      expect(s.firstFlipped, 0);
      expect(s.moves, 0);
    });

    test('re-flipping the same up card is a no-op', () {
      final s = GameLogic.flip(board(), 0);
      expect(GameLogic.flip(s, 0), equals(s));
    });
  });

  group('second flip', () {
    test('matching pair locks both as matched, counts one move', () {
      final s = GameLogic.flip(GameLogic.flip(board(), 0), 2); // slots 0 & 2 = pair 0
      expect(s.cards[0].isMatched, isTrue);
      expect(s.cards[2].isMatched, isTrue);
      expect(s.cards[0].isFaceUp, isTrue);
      expect(s.moves, 1);
      expect(s.firstFlipped, isNull);
      expect(s.isLocked, isFalse);
      expect(s.matchedPairs, 1);
      expect(s.phase, GamePhase.playing); // pair 1 still unmatched
    });

    test('mismatch reveals both, counts a move, and locks input', () {
      final s = GameLogic.flip(GameLogic.flip(board(), 0), 1); // face 0 vs face 1
      expect(s.cards[0].isFaceUp, isTrue);
      expect(s.cards[1].isFaceUp, isTrue);
      expect(s.cards[0].isMatched, isFalse);
      expect(s.moves, 1);
      expect(s.firstFlipped, isNull);
      expect(s.isLocked, isTrue);
      expect(s.pendingMismatch, [0, 1]);
    });

    test('input is ignored while a mismatch is shown', () {
      final locked = GameLogic.flip(GameLogic.flip(board(), 0), 1);
      expect(GameLogic.flip(locked, 3), equals(locked));
    });
  });

  group('resolveMismatch', () {
    test('flips the pending pair back down and unlocks', () {
      final locked = GameLogic.flip(GameLogic.flip(board(), 0), 1);
      final resolved = GameLogic.resolveMismatch(locked);
      expect(resolved.cards[0].isFaceUp, isFalse);
      expect(resolved.cards[1].isFaceUp, isFalse);
      expect(resolved.isLocked, isFalse);
      expect(resolved.pendingMismatch, isNull);
      expect(resolved.moves, 1); // the move still counted
    });

    test('is a no-op when nothing is pending', () {
      final s = board();
      expect(GameLogic.resolveMismatch(s), equals(s));
    });
  });

  group('guards', () {
    test('flip on a matched card is a no-op', () {
      final matched = GameLogic.flip(GameLogic.flip(board(), 0), 2);
      expect(GameLogic.flip(matched, 0), equals(matched));
    });

    test('flip out of phase (menu) is a no-op', () {
      final menu = board().copyWith(phase: GamePhase.menu);
      expect(GameLogic.flip(menu, 0), equals(menu));
    });

    test('flip out of range is a no-op', () {
      final s = board();
      expect(GameLogic.flip(s, 99), equals(s));
      expect(GameLogic.flip(s, -1), equals(s));
    });
  });

  group('winning', () {
    test('matching every pair transitions to won', () {
      var s = board();
      s = GameLogic.flip(s, 0);
      s = GameLogic.flip(s, 2); // pair 0
      s = GameLogic.flip(s, 1);
      s = GameLogic.flip(s, 3); // pair 1
      expect(s.isWon, isTrue);
      expect(s.phase, GamePhase.won);
      expect(s.moves, 2);
      expect(s.matchedPairs, 2);
    });
  });

  group('pause', () {
    test('toggles playing <-> paused only', () {
      final paused = GameLogic.togglePause(board());
      expect(paused.phase, GamePhase.paused);
      expect(GameLogic.togglePause(paused).phase, GamePhase.playing);
      final won = board().copyWith(phase: GamePhase.won);
      expect(GameLogic.togglePause(won), equals(won)); // no-op
    });
  });
}
