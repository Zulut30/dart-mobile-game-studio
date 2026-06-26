import 'package:flutter/material.dart';

import 'game_screen.dart';

/// Title screen. A single Play action deals a fresh board.
class MenuScreen extends StatelessWidget {
  const MenuScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.grid_view_rounded, size: 96, color: theme.colorScheme.primary),
              const SizedBox(height: 16),
              Text('Memory Match', style: theme.textTheme.headlineMedium),
              const SizedBox(height: 8),
              Text('Flip cards, find the pairs.', style: theme.textTheme.bodyMedium),
              const SizedBox(height: 32),
              FilledButton.icon(
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(builder: (_) => const GameScreen(pairs: 6)),
                ),
                icon: const Icon(Icons.play_arrow_rounded),
                label: const Text('Play'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
