import 'dart:ui' show Size;

import 'package:endless_runner/widgets/app.dart';
import 'package:flutter/widgets.dart' show AppLifecycleState, SizedBox;
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('menu, pause, resume, and lifecycle states are reachable', (
    tester,
  ) async {
    await tester.pumpWidget(const RunnerApp());
    await tester.pump();
    expect(find.text('Endless Runner'), findsOneWidget);
    expect(find.text('Play'), findsOneWidget);

    await tester.tap(find.text('Play'));
    await tester.pump(const Duration(milliseconds: 16));
    expect(find.byTooltip('Pause'), findsOneWidget);

    await tester.tap(find.byTooltip('Pause'));
    await tester.pump();
    expect(find.text('Paused'), findsOneWidget);
    expect(find.text('Resume'), findsOneWidget);

    await tester.tap(find.text('Resume'));
    await tester.pump(const Duration(milliseconds: 16));
    expect(find.byTooltip('Pause'), findsOneWidget);

    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.paused);
    tester.binding.handleAppLifecycleStateChanged(AppLifecycleState.resumed);
    await tester.pump();
    expect(find.text('Paused'), findsOneWidget);
    await tester.pumpWidget(const SizedBox.shrink());
  });

  testWidgets('runner shell adapts to a wide viewport without layout errors', (
    tester,
  ) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(1200, 600);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.view.resetPhysicalSize);

    await tester.pumpWidget(const RunnerApp());
    await tester.pump();
    await tester.tap(find.text('Play'));
    await tester.pump(const Duration(milliseconds: 16));

    expect(find.byTooltip('Pause'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox.shrink());
  });
}
