import 'package:flutter_test/flutter_test.dart';
import 'package:memory_match/widgets/app.dart';

Future<void> expectFlutterAccessibilityGuidelines(WidgetTester tester) async {
  await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
  await expectLater(tester, meetsGuideline(iOSTapTargetGuideline));
  await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
  await expectLater(tester, meetsGuideline(textContrastGuideline));
}

void main() {
  testWidgets('menu follows Flutter accessibility guidelines', (tester) async {
    final handle = tester.ensureSemantics();
    try {
      await tester.pumpWidget(const MemoryMatchApp());
      await expectFlutterAccessibilityGuidelines(tester);
    } finally {
      handle.dispose();
    }
  });

  testWidgets('game board follows Flutter accessibility guidelines', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    try {
      await tester.pumpWidget(const MemoryMatchApp());
      await tester.tap(find.text('Play'));
      await tester.pumpAndSettle();
      await expectFlutterAccessibilityGuidelines(tester);
    } finally {
      handle.dispose();
    }
  });
}
