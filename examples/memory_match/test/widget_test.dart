import 'dart:ui' show Size;

import 'package:flutter/widgets.dart' show AppLifecycleState;
import 'package:flutter_test/flutter_test.dart';
import 'package:memory_match/widgets/app.dart';
import 'package:memory_match/widgets/card_tile.dart';

void main() {
  testWidgets('menu → play deals the board and a card is tappable', (
    tester,
  ) async {
    await tester.pumpWidget(const MemoryMatchApp());

    // Menu
    expect(find.text('Memory Match'), findsOneWidget);
    expect(find.text('Play'), findsOneWidget);

    // Start a game
    await tester.tap(find.text('Play'));
    await tester.pumpAndSettle();

    // The board is dealt with 6 pairs — assert via the HUD, not the tile count:
    // GridView.builder is lazy, so only the on-screen tiles are built.
    expect(find.text('Pairs 0/6'), findsOneWidget);
    expect(find.byType(CardTile), findsWidgets);

    // Tapping a face-down card doesn't throw and keeps the board present.
    await tester.tap(find.byType(CardTile).first);
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(CardTile), findsWidgets);
  });

  testWidgets('pause, resume, and app lifecycle freeze the board', (
    tester,
  ) async {
    await tester.pumpWidget(const MemoryMatchApp());
    await tester.tap(find.text('Play'));
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Pause'));
    await tester.pumpAndSettle();
    expect(find.text('Paused'), findsOneWidget);
    expect(find.text('Resume'), findsOneWidget);

    await tester.tap(find.text('Resume'));
    await tester.pumpAndSettle();
    expect(find.byTooltip('Pause'), findsOneWidget);

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pumpAndSettle();
    expect(find.text('Paused'), findsOneWidget);
  });

  testWidgets('board adapts to a wide viewport without layout errors', (
    tester,
  ) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(1200, 600);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(const MemoryMatchApp());
    await tester.tap(find.text('Play'));
    await tester.pumpAndSettle();

    expect(find.byType(CardTile), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
