import 'package:flutter_test/flutter_test.dart';
import 'package:memory_match/widgets/app.dart';
import 'package:memory_match/widgets/card_tile.dart';

void main() {
  testWidgets('menu → play deals a 12-card board; a card is tappable', (tester) async {
    await tester.pumpWidget(const MemoryMatchApp());

    // Menu
    expect(find.text('Memory Match'), findsOneWidget);
    expect(find.text('Play'), findsOneWidget);

    // Start a game
    await tester.tap(find.text('Play'));
    await tester.pumpAndSettle();

    // 6 pairs → 12 tiles
    expect(find.byType(CardTile), findsNWidgets(12));

    // Tapping a face-down card doesn't throw and keeps the board intact
    await tester.tap(find.byType(CardTile).first);
    await tester.pump(const Duration(milliseconds: 300));
    expect(find.byType(CardTile), findsNWidgets(12));
  });
}
