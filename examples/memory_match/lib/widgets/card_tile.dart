import 'package:flutter/material.dart';

import '../models/memory_card.dart';

/// One card. Face-down shows a neutral "?"; face-up shows a colored symbol keyed
/// to `faceId` (placeholder art — Material icons, no copyrighted assets). The flip
/// animation collapses to instant under Reduce Motion. `Semantics` makes it
/// screen-reader playable without color alone.
class CardTile extends StatelessWidget {
  const CardTile({required this.card, required this.onTap, super.key});

  final MemoryCard card;
  final VoidCallback onTap;

  // Distinct symbol + color per pair. Index by faceId; never rely on color alone
  // (the icon shape also differs), which keeps it color-blind safe.
  static const List<IconData> _faces = <IconData>[
    Icons.star_rounded,
    Icons.favorite_rounded,
    Icons.pets_rounded,
    Icons.wb_sunny_rounded,
    Icons.bolt_rounded,
    Icons.ac_unit_rounded,
    Icons.eco_rounded,
    Icons.cake_rounded,
  ];
  static const List<Color> _colors = <Color>[
    Color(0xFFEF5350),
    Color(0xFFAB47BC),
    Color(0xFF42A5F5),
    Color(0xFFFFA726),
    Color(0xFF66BB6A),
    Color(0xFF26C6DA),
    Color(0xFFEC407A),
    Color(0xFF8D6E63),
  ];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final faceUp = card.isFaceUp || card.isMatched;
    final reduceMotion = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    final color = _colors[card.faceId % _colors.length];
    final icon = _faces[card.faceId % _faces.length];

    final Widget face = faceUp
        ? Container(
            key: const ValueKey<bool>(true),
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(12),
              // a matched pair keeps a subtle ring so progress reads without color alone
              border: card.isMatched ? Border.all(color: Colors.white, width: 3) : null,
            ),
            child: Center(child: Icon(icon, color: Colors.white, size: 40)),
          )
        : Container(
            key: const ValueKey<bool>(false),
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(Icons.question_mark_rounded, color: theme.colorScheme.onPrimaryContainer),
          );

    return Semantics(
      label: 'Card ${card.id + 1}',
      value: card.isMatched
          ? 'matched, symbol ${card.faceId + 1}'
          : (faceUp ? 'showing symbol ${card.faceId + 1}' : 'face down'),
      button: !card.isMatched,
      enabled: !card.isMatched,
      child: GestureDetector(
        onTap: card.isMatched ? null : onTap,
        child: AnimatedSwitcher(
          duration: reduceMotion ? Duration.zero : const Duration(milliseconds: 200),
          child: face,
        ),
      ),
    );
  }
}
