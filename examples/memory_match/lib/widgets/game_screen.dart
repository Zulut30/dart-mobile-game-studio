import 'dart:async';
import 'dart:math' as math;

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

class _GameScreenState extends State<GameScreen> with WidgetsBindingObserver {
  late GameState _state;
  Timer? _mismatchTimer;
  int _seed = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Seed from the clock at the UI edge (NOT in the pure core); same seed → same
    // board, so the core stays deterministic and testable.
    _seed = DateTime.now().millisecondsSinceEpoch & 0x7fffffff;
    _state = BoardFactory.newGame(
      pairs: widget.pairs,
      rng: SeededRandom(_seed),
    );
  }

  void _restart() {
    _mismatchTimer?.cancel();
    setState(() {
      _seed += 1;
      _state = BoardFactory.newGame(
        pairs: widget.pairs,
        rng: SeededRandom(_seed),
      );
    });
  }

  void _pause() {
    if (_state.phase != GamePhase.playing) return;
    _mismatchTimer?.cancel();
    setState(() {
      _state = GameLogic.pause(GameLogic.resolveMismatch(_state));
    });
  }

  void _resume() {
    if (_state.phase != GamePhase.paused) return;
    setState(() => _state = GameLogic.resume(_state));
  }

  void _quitToMenu() {
    _mismatchTimer?.cancel();
    _state = GameLogic.quitToMenu(_state);
    Navigator.of(context).pop();
  }

  void _onTapCard(int index) {
    if (_state.isLocked) return;
    setState(() => _state = GameLogic.flip(_state, index));
    if (_state.isLocked) {
      final reduceMotion =
          MediaQuery.maybeOf(context)?.disableAnimations ?? false;
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
    WidgetsBinding.instance.removeObserver(this);
    _mismatchTimer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) _pause();
  }

  @override
  Widget build(BuildContext context) {
    final won = _state.phase == GamePhase.won;
    final paused = _state.phase == GamePhase.paused;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Memory Match'),
        actions: [
          if (_state.phase == GamePhase.playing)
            IconButton(
              onPressed: _pause,
              icon: const Icon(Icons.pause_rounded),
              tooltip: 'Pause',
            ),
          IconButton(
            onPressed: _restart,
            icon: const Icon(Icons.refresh_rounded),
            tooltip: 'New board',
          ),
        ],
      ),
      body: SafeArea(
        child: Stack(
          children: [
            ExcludeSemantics(
              excluding: paused || won,
              child: Column(
                children: [
                  StatusBar(state: _state),
                  Expanded(
                    child: LayoutBuilder(
                      builder: (context, constraints) =>
                          _buildBoard(constraints),
                    ),
                  ),
                ],
              ),
            ),
            if (paused)
              _PhaseOverlay(
                title: 'Paused',
                primaryLabel: 'Resume',
                primaryIcon: Icons.play_arrow_rounded,
                onPrimary: _resume,
                secondaryLabel: 'Menu',
                secondaryIcon: Icons.home_rounded,
                onSecondary: _quitToMenu,
              ),
            if (won)
              _PhaseOverlay(
                title: 'You won in ${_state.moves} moves',
                primaryLabel: 'Play again',
                primaryIcon: Icons.replay_rounded,
                onPrimary: _restart,
                secondaryLabel: 'Menu',
                secondaryIcon: Icons.home_rounded,
                onSecondary: _quitToMenu,
                liveRegion: true,
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildBoard(BoxConstraints constraints) {
    final cardCount = _state.cards.length;
    final landscape = constraints.maxWidth > constraints.maxHeight;
    final columns = landscape
        ? (cardCount <= 8 ? 4 : (cardCount <= 12 ? 6 : 8))
        : (cardCount <= 8 ? 2 : (cardCount <= 12 ? 3 : 4));
    final rows = (cardCount / columns).ceil();
    const gap = 12.0;
    const padding = 12.0;
    final boardWidth = math.min(constraints.maxWidth, 960.0);
    final tileWidth =
        (boardWidth - padding * 2 - gap * (columns - 1)) / columns;
    final availableTileHeight =
        (constraints.maxHeight - padding * 2 - gap * (rows - 1)) / rows;
    final tileHeight = math.max(48.0, availableTileHeight);
    final aspectRatio = (tileWidth / tileHeight).clamp(0.7, 1.4).toDouble();

    return Center(
      child: SizedBox(
        width: boardWidth,
        child: GridView.builder(
          padding: const EdgeInsets.all(padding),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            crossAxisSpacing: gap,
            mainAxisSpacing: gap,
            childAspectRatio: aspectRatio,
          ),
          itemCount: cardCount,
          itemBuilder: (context, index) {
            final card = _state.cards[index];
            return CardTile(
              key: ValueKey<int>(card.id),
              card: card,
              onTap: () => _onTapCard(index),
            );
          },
        ),
      ),
    );
  }
}

class _PhaseOverlay extends StatelessWidget {
  const _PhaseOverlay({
    required this.title,
    required this.primaryLabel,
    required this.primaryIcon,
    required this.onPrimary,
    required this.secondaryLabel,
    required this.secondaryIcon,
    required this.onSecondary,
    this.liveRegion = false,
  });

  final String title;
  final String primaryLabel;
  final IconData primaryIcon;
  final VoidCallback onPrimary;
  final String secondaryLabel;
  final IconData secondaryIcon;
  final VoidCallback onSecondary;
  final bool liveRegion;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: Colors.black54,
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 360),
            child: Semantics(
              container: true,
              liveRegion: liveRegion,
              label: title,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  ExcludeSemantics(
                    child: Text(
                      title,
                      textAlign: TextAlign.center,
                      style: Theme.of(
                        context,
                      ).textTheme.headlineSmall?.copyWith(color: Colors.white),
                    ),
                  ),
                  const SizedBox(height: 24),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: onPrimary,
                      icon: Icon(primaryIcon),
                      label: Text(primaryLabel),
                    ),
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: onSecondary,
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.white,
                        side: const BorderSide(color: Colors.white70),
                      ),
                      icon: Icon(secondaryIcon),
                      label: Text(secondaryLabel),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
