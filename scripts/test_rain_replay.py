import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import rain_replay

EVENT_FILE = Path(__file__).resolve().parent / "rain_events" / "hanoi_20251005_48h.csv"
T0 = datetime(2025, 10, 5, 22, 30, tzinfo=timezone.utc)

SOURCE_ROWS = [
    ("2025-10-05T22:00:00+00:00", 0.0),
    ("2025-10-05T22:30:00+00:00", 1.0),
    ("2025-10-05T23:00:00+00:00", 2.0),
    ("2025-10-05T23:30:00+00:00", 4.0),
    ("2025-10-06T00:00:00+00:00", 0.5),
]


def starts(intervals):
    return [i["startTime"] for i in intervals]


def rates(intervals):
    return [i["values"]["precipitationIntensity"] for i in intervals]


class CutWindowTests(unittest.TestCase):
    def test_cut_keeps_rows_in_the_window_and_rebases_offsets(self):
        cut = rain_replay.cut_window(SOURCE_ROWS, "2025-10-05T22:30:00+00:00", hours=1)
        self.assertEqual(cut, [(0, 1.0), (30, 2.0), (60, 4.0)])

    def test_cut_rejects_a_window_that_runs_past_the_source(self):
        with self.assertRaises(ValueError):
            rain_replay.cut_window(SOURCE_ROWS, "2025-10-05T23:00:00+00:00", hours=2)

    def test_cut_rejects_a_start_that_is_not_a_source_row(self):
        with self.assertRaises(ValueError):
            rain_replay.cut_window(SOURCE_ROWS, "2025-10-05T22:45:00+00:00", hours=1)

    def test_written_event_loads_back_unchanged(self):
        event = [(0, 1.0), (30, 2.0), (60, 4.0)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "event.csv"
            rain_replay.write_event(path, event)
            self.assertEqual(path.read_text().splitlines()[0], "offset_minutes,precipitation_mm_hr")
            self.assertEqual(rain_replay.load_event(path), event)


class ReplayIntervalsTests(unittest.TestCase):
    EVENT = [(0, 1.0), (30, 2.0), (60, 0.0)]

    def test_each_half_hour_rate_holds_for_both_fifteen_minute_intervals(self):
        intervals = rain_replay.replay_intervals(self.EVENT, T0, T0, duration_hours=1, timestep_minutes=15)
        self.assertEqual(rates(intervals), [1.0, 1.0, 2.0, 2.0, 0.0])
        self.assertEqual(
            starts(intervals),
            [
                "2025-10-05T22:30:00Z",
                "2025-10-05T22:45:00Z",
                "2025-10-05T23:00:00Z",
                "2025-10-05T23:15:00Z",
                "2025-10-05T23:30:00Z",
            ],
        )

    def test_a_later_run_reads_its_lookahead_from_its_own_slot(self):
        later = datetime(2025, 10, 5, 23, 0, tzinfo=timezone.utc)
        intervals = rain_replay.replay_intervals(self.EVENT, T0, later, duration_hours=0.5, timestep_minutes=15)
        self.assertEqual(rates(intervals), [2.0, 2.0, 0.0])

    def test_before_the_event_and_after_its_last_sample_the_rate_is_zero(self):
        early = datetime(2025, 10, 5, 22, 0, tzinfo=timezone.utc)
        before = rain_replay.replay_intervals(self.EVENT, T0, early, duration_hours=1, timestep_minutes=15)
        self.assertEqual(rates(before), [0.0, 0.0, 1.0, 1.0, 2.0])
        late = datetime(2025, 10, 5, 23, 15, tzinfo=timezone.utc)
        after = rain_replay.replay_intervals(self.EVENT, T0, late, duration_hours=0.5, timestep_minutes=15)
        self.assertEqual(rates(after), [2.0, 0.0, 0.0])


class EventFileTests(unittest.TestCase):
    def test_committed_event_is_the_48_hour_window_of_the_hyetograph(self):
        event = rain_replay.load_event(EVENT_FILE)
        self.assertEqual(len(event), 97)
        self.assertEqual((event[0][0], event[-1][0]), (0, 2880))
        self.assertEqual(max(rate for _, rate in event), 56.481693)
        total_mm = sum(rate for _, rate in event) * 0.5
        self.assertAlmostEqual(total_mm, 246.8, delta=0.1)

    def test_run_at_the_peak_slot_sees_the_peak_inside_its_two_hour_lookahead(self):
        event = rain_replay.load_event(EVENT_FILE)
        slot = datetime(2025, 10, 6, 21, 0, tzinfo=timezone.utc)
        intervals = rain_replay.replay_intervals(event, T0, slot, duration_hours=2, timestep_minutes=15)
        self.assertEqual(max(rates(intervals)), 56.481693)


if __name__ == "__main__":
    unittest.main()
