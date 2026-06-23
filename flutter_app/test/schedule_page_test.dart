import 'package:flutter_test/flutter_test.dart';
import 'package:worldcup_predictor/pages/schedule/schedule_page.dart';

void main() {
  test('schedule page defaults to upcoming and removes all-status option', () {
    expect(SchedulePage.defaultStatus, MatchStatus.upcoming);
    expect(
        SchedulePage.statusFilterValues,
        containsAll(<String>[
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

  test('sorts only completed schedule times descending', () {
    final times = <DateTime?>[
      DateTime(2026, 6, 12, 3),
      DateTime(2026, 6, 23, 11),
      DateTime(2026, 6, 14, 9),
    ];

    expect(
      sortScheduleTimesForStatus(times, MatchStatus.completed),
      <DateTime?>[
        DateTime(2026, 6, 23, 11),
        DateTime(2026, 6, 14, 9),
        DateTime(2026, 6, 12, 3),
      ],
    );
    expect(sortScheduleTimesForStatus(times, MatchStatus.upcoming), times);
    expect(sortScheduleTimesForStatus(times, MatchStatus.live), times);
  });
}
