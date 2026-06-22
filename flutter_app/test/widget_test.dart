import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:flutter_app/app.dart';

void main() {
  testWidgets('App can be built', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: WorldCupApp()));
    expect(find.byType(ProviderScope), findsOneWidget);
  });
}
