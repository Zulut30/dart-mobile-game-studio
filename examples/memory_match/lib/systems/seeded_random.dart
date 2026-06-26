// seeded_random.dart
// Dart Mobile Game Studio — drop-in deterministic RNG.
//
// A seedable `Random` (SplitMix64) so shuffles, spawns, and any randomness are
// REPRODUCIBLE in tests. Inject it everywhere you would otherwise reach for the
// default `Random()`. Same seed -> same sequence.
//
// Why: `Random()` without a seed is non-deterministic, so a test that depends on
// a "random" outcome can't assert anything stable. With a seed the sequence is
// fixed, so `dart test` on the VM verifies game logic without a device.
//
// This implements `dart:math`'s `Random` interface, so it is a drop-in anywhere a
// `Random` is accepted (e.g. `List.shuffle(rng)`).
//
// Scope: the pure-Dart game core is tested with `dart test` on the Dart VM, where
// `int` is a true signed 64-bit value — exactly what SplitMix64 needs. The same
// holds for AOT-compiled iOS/Android. On the web (compiled to JavaScript) `int`
// is a 53-bit double, so the 64-bit mixing below would NOT match the VM. Keep RNG
// use inside the VM-tested core (the doctrine here anyway); don't rely on this for
// reproducibility in web builds.
//
// Usage:
//   final rng = SeededRandom(42);
//   cards.shuffle(rng);                 // dart:core List.shuffle takes a Random
//   final i = rng.nextInt(cards.length);
//   final x = rng.nextDouble();         // [0.0, 1.0)
//   final flip = rng.nextBool();
//
// Convenience helpers for game code:
//   final n = rng.intInRange(1, 6);     // inclusive 1..6 (a die)
//   final f = rng.doubleInRange(-1, 1); // [-1.0, 1.0)
//   final card = rng.pick(deck);        // a uniformly chosen element
//   rng.shuffle(tiles);                 // in-place Fisher-Yates with this RNG
//
// In a model, store the generator and thread it through the rules:
//   class Board {
//     Board(int seed) : _rng = SeededRandom(seed);
//     final SeededRandom _rng;
//     void deal() => _rng.shuffle(cards);
//   }

import 'dart:math' show Random;

/// A deterministic [Random] based on SplitMix64.
///
/// The same [seed] always produces the same sequence, which makes randomized
/// game logic unit-testable. See the file header for the web/VM `int` caveat.
class SeededRandom implements Random {
  /// Creates a generator from a 64-bit [seed].
  ///
  /// A seed of `0` is remapped to the SplitMix64 golden-ratio constant so the
  /// state never starts degenerate.
  SeededRandom(int seed)
      : _state = (seed == 0 ? _goldenGamma : seed) & _mask64;

  /// SplitMix64 increment / golden-ratio constant (`floor(2^64 / phi)`).
  static const int _goldenGamma = 0x9E3779B97F4A7C15;

  /// 64-bit mask. On the VM/AOT, masking with this keeps arithmetic in the
  /// unsigned 64-bit lane even though Dart `int` is signed.
  static const int _mask64 = 0xFFFFFFFFFFFFFFFF;

  /// 32-bit mask, used to draw bounded integers from the high-quality low word.
  static const int _mask32 = 0xFFFFFFFF;

  int _state;

  /// Advances the state and returns the next raw 64-bit SplitMix64 output.
  ///
  /// All shifts are the unsigned `>>>`: VM `int` is signed, so an arithmetic
  /// `>>` would sign-extend a high-bit-set value and diverge from canonical
  /// SplitMix64. The `& _mask64` after each multiply keeps the lane to 64 bits.
  int _next64() {
    _state = (_state + _goldenGamma) & _mask64;
    var z = _state;
    z = ((z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9) & _mask64;
    z = ((z ^ (z >>> 27)) * 0x94D049BB133111EB) & _mask64;
    return (z ^ (z >>> 31)) & _mask64;
  }

  /// Returns a non-negative integer uniformly distributed in `[0, max)`.
  ///
  /// Per the [Random] contract, [max] must satisfy `1 <= max <= 2^32`.
  /// Uses rejection sampling on the low 32 bits, so the result is bias-free
  /// (plain modulo would over-represent small values when `max` is not a power
  /// of two).
  @override
  int nextInt(int max) {
    if (max < 1 || max > 0x100000000) {
      throw RangeError.range(max, 1, 0x100000000, 'max');
    }
    // Largest multiple of `max` that fits in 32 bits; draws above it are
    // rejected to keep the distribution uniform.
    final limit = (0x100000000 ~/ max) * max;
    int bits;
    do {
      bits = _next64() & _mask32;
    } while (bits >= limit);
    return bits % max;
  }

  /// Returns a `double` uniformly distributed in `[0.0, 1.0)`.
  ///
  /// Built from 53 random bits (the mantissa width of a `double`) divided by
  /// `2^53`, so every value is exactly representable and the result never
  /// reaches `1.0`.
  ///
  /// Uses the unsigned right shift `>>>`: VM `int` is signed 64-bit, so the raw
  /// output's top bit must not sign-extend or the result could go negative.
  @override
  double nextDouble() => (_next64() >>> 11) * (1.0 / 9007199254740992.0);

  /// Returns `true` or `false` with equal probability.
  @override
  bool nextBool() => (_next64() & 1) == 1;

  // --- Convenience helpers for game logic (not part of the Random interface). ---

  /// Returns an integer in the inclusive range `[min, max]`.
  ///
  /// Throws [ArgumentError] if `min > max`. Example: `intInRange(1, 6)` rolls a
  /// six-sided die.
  int intInRange(int min, int max) {
    if (min > max) {
      throw ArgumentError('min ($min) must be <= max ($max)');
    }
    return min + nextInt(max - min + 1);
  }

  /// Returns a `double` in the half-open range `[min, max)`.
  ///
  /// Throws [ArgumentError] if `min >= max`.
  double doubleInRange(double min, double max) {
    if (min >= max) {
      throw ArgumentError('min ($min) must be < max ($max)');
    }
    return min + nextDouble() * (max - min);
  }

  /// Returns a uniformly chosen element of [items].
  ///
  /// Throws [ArgumentError] if [items] is empty.
  T pick<T>(List<T> items) {
    if (items.isEmpty) {
      throw ArgumentError('cannot pick from an empty list');
    }
    return items[nextInt(items.length)];
  }

  /// Shuffles [items] in place using Fisher-Yates driven by this generator.
  ///
  /// Deterministic for a given seed and starting list — prefer this over
  /// `items.shuffle(rng)` when you want the shuffle algorithm itself pinned.
  void shuffle<T>(List<T> items) {
    for (var i = items.length - 1; i > 0; i--) {
      final j = nextInt(i + 1);
      final tmp = items[i];
      items[i] = items[j];
      items[j] = tmp;
    }
  }
}
