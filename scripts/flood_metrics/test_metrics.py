import unittest
from datetime import datetime, timedelta

from metrics import Closed, DepthSeries, NeverImpassable, Peak, extract

# The four VEHICLE_PROFILES thresholds (flood_utils.py), in metres, written out literally so
# every expected value below can be checked against the series by hand.
THRESHOLDS_M = {"motorbike": 0.20, "car": 0.30, "truck": 0.35, "foot": 0.40}


def at(hhmm: str) -> datetime:
    hour, minute = hhmm.split(":")
    return datetime(2026, 9, 23, int(hour), int(minute))


def series(*points: tuple[str, float]) -> DepthSeries:
    return DepthSeries(
        times=tuple(at(t) for t, _ in points),
        depths_m=tuple(d for _, d in points),
    )


# Rises through every threshold but foot's, peaks at 11:30, then drains.
RISE_AND_FALL = series(
    ("10:00", 0.05),
    ("10:30", 0.15),
    ("11:00", 0.25),
    ("11:30", 0.38),
    ("12:00", 0.30),
    ("12:30", 0.18),
    ("13:00", 0.10),
)


class RiseAndFallTests(unittest.TestCase):
    def setUp(self):
        self.metrics = extract(RISE_AND_FALL, THRESHOLDS_M)

    def test_peak_and_time_to_peak(self):
        self.assertEqual(self.metrics.peak, Peak(at=at("11:30"), depth_m=0.38, at_window_end=False))
        self.assertEqual(self.metrics.time_to_peak, timedelta(hours=1, minutes=30))

    def test_recession_onset_is_first_sample_below_peak(self):
        self.assertEqual(self.metrics.recession_onset, at("12:00"))

    def test_forecast_depths_read_the_samples_at_t_plus_1h_and_2h(self):
        self.assertEqual(self.metrics.forecast_depth_1h_m, 0.25)
        self.assertEqual(self.metrics.forecast_depth_2h_m, 0.30)

    def test_passability_per_vehicle(self):
        self.assertEqual(
            self.metrics.passability,
            {
                # Closes within the first hour, so pre-closure clamps to the window start.
                "motorbike": Closed(
                    closed_at=at("11:00"), pre_closure_at=at("10:00"), restored_at=at("12:30")
                ),
                # 12:00's 0.30 equals car's threshold and counts as impassable (inclusive).
                "car": Closed(
                    closed_at=at("11:30"), pre_closure_at=at("10:30"), restored_at=at("12:30")
                ),
                "truck": Closed(
                    closed_at=at("11:30"), pre_closure_at=at("10:30"), restored_at=at("12:00")
                ),
                "foot": NeverImpassable(),
            },
        )


class NotOccurredTests(unittest.TestCase):
    def test_still_rising_at_window_end(self):
        metrics = extract(
            series(("10:00", 0.10), ("10:30", 0.20), ("11:00", 0.30)), {"motorbike": 0.20}
        )
        self.assertEqual(metrics.peak, Peak(at=at("11:00"), depth_m=0.30, at_window_end=True))
        self.assertIsNone(metrics.recession_onset)
        self.assertEqual(metrics.forecast_depth_1h_m, 0.30)
        self.assertIsNone(metrics.forecast_depth_2h_m)
        self.assertEqual(
            metrics.passability["motorbike"],
            Closed(closed_at=at("10:30"), pre_closure_at=at("10:00"), restored_at=None),
        )

    def test_dry_segment_has_no_peak(self):
        metrics = extract(series(("10:00", 0.0), ("11:00", 0.0)), {"motorbike": 0.20})
        self.assertIsNone(metrics.peak)
        self.assertIsNone(metrics.time_to_peak)
        self.assertIsNone(metrics.recession_onset)
        self.assertEqual(metrics.forecast_depth_1h_m, 0.0)
        self.assertEqual(metrics.passability["motorbike"], NeverImpassable())

    def test_plateau_at_peak_recedes_only_when_depth_drops(self):
        metrics = extract(
            series(("10:00", 0.4), ("10:15", 0.4), ("10:30", 0.4), ("10:45", 0.3)), {}
        )
        self.assertEqual(metrics.peak.at, at("10:00"))
        self.assertEqual(metrics.recession_onset, at("10:45"))


class ClosureEdgeTests(unittest.TestCase):
    def test_reclosure_restores_only_after_the_last_impassable_sample(self):
        metrics = extract(
            series(
                ("10:00", 0.0),
                ("11:00", 0.25),
                ("11:15", 0.10),
                ("11:30", 0.22),
                ("11:45", 0.05),
                ("12:00", 0.0),
            ),
            {"motorbike": 0.20},
        )
        self.assertEqual(
            metrics.passability["motorbike"],
            Closed(closed_at=at("11:00"), pre_closure_at=at("10:00"), restored_at=at("11:45")),
        )

    def test_pre_closure_is_one_hour_before_a_late_closure(self):
        metrics = extract(
            series(("10:00", 0.0), ("12:15", 0.10), ("12:45", 0.21)), {"motorbike": 0.20}
        )
        self.assertEqual(metrics.passability["motorbike"].pre_closure_at, at("11:45"))

    def test_forecast_depth_interpolates_between_samples(self):
        metrics = extract(series(("10:00", 0.0), ("10:40", 0.2), ("11:20", 0.6)), {})
        self.assertAlmostEqual(metrics.forecast_depth_1h_m, 0.4)


class DepthSeriesValidationTests(unittest.TestCase):
    def test_rejects_duplicate_times(self):
        with self.assertRaises(ValueError):
            series(("10:00", 0.1), ("10:00", 0.2))

    def test_rejects_empty(self):
        with self.assertRaises(ValueError):
            DepthSeries(times=(), depths_m=())

    def test_rejects_mismatched_lengths(self):
        with self.assertRaises(ValueError):
            DepthSeries(times=(at("10:00"),), depths_m=(0.1, 0.2))


if __name__ == "__main__":
    unittest.main()
