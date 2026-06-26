import 'package:flutter_test/flutter_test.dart';
import 'package:memory_match/widgets/app.dart';
import 'package:memory_match/widgets/card_tile.dart';

void main() {
  testWidgets('menu → play deals the board and a card is tappable', (tester) async {
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
}
