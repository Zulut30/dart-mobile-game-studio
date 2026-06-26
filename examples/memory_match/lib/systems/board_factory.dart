import 'dart:math' show Random;

import '../models/game_phase.dart';
import '../models/game_state.dart';
import '../models/memory_card.dart';

/// Deals fresh memory-match boards. Pure Dart — the shuffle is driven by an
/// injected [Random] (use `SeededRandom` for reproducible, testable layouts).
abstract final class BoardFactory {
  /// Builds a `playing` [GameState] with [pairs] pairs (so `2 * pairs` cards),
  /// shuffled with [rng]. Each `faceId` in `0 .. pairs-1` appears exactly twice;
  /// each card's `id` is its final slot index.
  ///
  /// Throws [ArgumentError] if [pairs] < 1.
  static GameState newGame({required int pairs, required Random rng}) {
    if (pairs < 1) {
      throw ArgumentError.value(pairs, 'pairs', 'must be >= 1');
    }
    final faces = <int>[
      for (var f = 0; f < pairs; f++) ...[f, f],
    ];
    faces.shuffle(rng); // dart:core List.shuffle takes a Random — inject the seeded one
    final cards = <MemoryCard>[
      for (var i = 0; i < faces.length; i++) MemoryCard(id: i, faceId: faces[i]),
    ];
    return GameState(cards: cards, phase: GamePhase.playing);
  }
}
