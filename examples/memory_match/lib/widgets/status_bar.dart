import 'package:flutter/material.dart';

import '../models/game_state.dart';

/// The HUD: pairs found and moves taken. Reads the model; holds no rules.
class StatusBar extends StatelessWidget {
  const StatusBar({required this.state, super.key});

  final GameState state;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Semantics(
            liveRegion: true,
            child: Text(
              'Pairs ${state.matchedPairs}/${state.totalPairs}',
              style: theme.textTheme.titleMedium,
            ),
          ),
          Text('Moves ${state.moves}', style: theme.textTheme.titleMedium),
        ],
      ),
    );
  }
}
