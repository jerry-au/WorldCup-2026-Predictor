import 'package:flutter_test/flutter_test.dart';
import 'package:worldcup_predictor/pages/schedule/schedule_page.dart';

void main() {
  test('schedule page defaults to upcoming and removes all-status option', () {
    expect(SchedulePage.defaultStatus, MatchStatus.upcoming);
    expect(SchedulePage.statusFilterValues, containsAll(<String>[
      MatchStatus.upcoming,
      MatchStatus.live,
      MatchStatus.completed,
    ]));
    expect(SchedulePage.statusFilterValues, isNot(contains(null)));
  });

  test('formats decimal probabilities as percentages', () {
    expect(formatScheduleProbability(0.6171), '62%');
    expect(formatScheduleProbability(0.1603), '16%');
    expect(formatScheduleProbability(0.2226), '22%');
  });
}
