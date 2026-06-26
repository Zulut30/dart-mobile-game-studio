import 'dart:async';

import 'package:flutter/material.dart';

import '../models/game_phase.dart';
import '../models/game_state.dart';
import '../systems/board_factory.dart';
import '../systems/game_logic.dart';
import '../systems/seeded_random.dart';
import 'card_tile.dart';
import 'status_bar.dart';

/// Hosts the board. This is the ONLY stateful piece: it owns the [GameState] and
/// the mismatch-reveal [Timer]. Every rule decision is delegated to the pure-Dart
/// `GameLogic`; the widget just renders the returned state and schedules the brief
/// reveal before flipping a mismatch back.
class GameScreen extends StatefulWidget {
  const GameScreen({required this.pairs, super.key});

  final int pairs;

  @override
  State<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends State<GameScreen> {
  late GameState _state;
  Timer? _mismatchTimer;
  int _seed = 0;

  @override
  void initState() {
    super.initState();
    // Seed from the clock at the UI edge (NOT in the pure core); same seed → same
    // board, so the core stays deterministic and testable.
    _seed = DateTime.now().millisecondsSinceEpoch & 0x7fffffff;
    _state = BoardFactory.newGame(pairs: widget.pairs, rng: SeededRandom(_seed));
  }

  void _restart() {
    _mismatchTimer?.cancel();
    setState(() {
      _seed += 1;
      _state = BoardFactory.newGame(pairs: widget.pairs, rng: SeededRandom(_seed));
    });
  }

  void _onTapCard(int index) {
    if (_state.isLocked) return;
    setState(() => _state = GameLogic.flip(_state, index));
    if (_state.isLocked) {
      final reduceMotion = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
      final delay = reduceMotion
          ? const Duration(milliseconds: 150)
          : const Duration(milliseconds: 800);
      _mismatchTimer?.cancel();
      _mismatchTimer = Timer(delay, () {
        if (!mounted) return;
        setState(() => _state = GameLogic.resolveMismatch(_state));
      });
    }
  }

  @override
  void dispose() {
    _mismatchTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cols = widget.pairs <= 4 ? 2 : 3;
    final won = _state.phase == GamePhase.won;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Memory Match'),
        actions: [
          IconButton(
            onPressed: _restart,
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'New board',
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            StatusBar(state: _state),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: GridView.builder(
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: cols,
                    crossAxisSpacing: 12,
                    mainAxisSpacing: 12,
                  ),
                  itemCount: _state.cards.length,
                  itemBuilder: (context, i) {
                    final card = _state.cards[i];
                    return CardTile(
                      key: ValueKey<int>(card.id),
                      card: card,
                      onTap: () => _onTapCard(i),
                    );
                  },
                ),
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: won
          ? FloatingActionButton.extended(
              onPressed: _restart,
              icon: const Icon(Icons.replay_rounded),
              label: Text('You won in ${_state.moves} moves — play again'),
            )
          : null,
    );
  }
}
