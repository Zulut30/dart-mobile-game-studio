import 'package:endless_runner/widgets/app.dart';
import 'package:flutter_test/flutter_test.dart';

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
      await tester.pumpWidget(const RunnerApp());
      await tester.pump();
      await expectFlutterAccessibilityGuidelines(tester);
    } finally {
      handle.dispose();
    }
  });

  testWidgets('play surface follows Flutter accessibility guidelines', (
    tester,
  ) async {
    final handle = tester.ensureSemantics();
    try {
      await tester.pumpWidget(const RunnerApp());
      await tester.pump();
      await tester.tap(find.text('Play'));
      await tester.pump(const Duration(milliseconds: 16));
      await expectFlutterAccessibilityGuidelines(tester);
    } finally {
      handle.dispose();
    }
  });
}
