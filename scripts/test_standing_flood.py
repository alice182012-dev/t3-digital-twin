import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from standing_flood import DRY_DEPTH_M, DRY_RUNS_TO_STOP, RunDepth, assess, read_standing_flood

START = datetime(2026, 10, 9, 19, 0)
NO_RAIN = 0.0


def runs_newest_first(max_depths, age=timedelta(minutes=12), step=timedelta(minutes=15)):
    """One RunDepth per max depth in metres, newest first, one slot apart. The newest run is `age` old."""
    return [
        RunDepth(START - step * index, depth, age + step * index)
        for index, depth in enumerate(max_depths)
    ]


class AssessTests(unittest.TestCase):
    def test_no_run_in_the_table_is_a_dry_state_whatever_the_forecast(self):
        result = assess([], max_rain_mm_hr=3.0)

        self.assertFalse(result["stands"])
        self.assertEqual(result["reason"], "no_run")

    def test_a_wet_newest_run_keeps_the_simulation_going_with_no_rain(self):
        result = assess(runs_newest_first([2.4, 2.9, 3.0]), NO_RAIN)

        self.assertTrue(result["stands"])
        self.assertEqual(result["reason"], "standing_flood")
        self.assertEqual(result["dry_runs_in_a_row"], 0)

    def test_four_dry_runs_after_a_wet_one_keep_it_going(self):
        result = assess(runs_newest_first([0, 0, 0.01, 0.04, 0.3]), NO_RAIN)

        self.assertTrue(result["stands"])
        self.assertEqual(result["dry_runs_in_a_row"], 4)

    def test_five_dry_runs_and_no_rain_end_it(self):
        result = assess(runs_newest_first([0.04] * DRY_RUNS_TO_STOP), NO_RAIN)

        self.assertFalse(result["stands"])
        self.assertEqual(result["reason"], "dry_and_no_rain")
        self.assertEqual(result["dry_runs_in_a_row"], 5)

    def test_five_dry_runs_with_any_forecast_rain_keep_it_going(self):
        result = assess(runs_newest_first([0] * DRY_RUNS_TO_STOP), max_rain_mm_hr=0.2)

        self.assertTrue(result["stands"])
        self.assertEqual(result["reason"], "rain_forecast")

    def test_a_depth_of_exactly_5_cm_is_wet(self):
        self.assertEqual(DRY_DEPTH_M, 0.05)
        result = assess(runs_newest_first([0.05] + [0] * 4), NO_RAIN)

        self.assertTrue(result["stands"])
        self.assertEqual(result["dry_runs_in_a_row"], 0)

    def test_a_wet_run_inside_the_last_five_breaks_the_dry_count(self):
        result = assess(runs_newest_first([0, 0, 0, 0.1, 0]), NO_RAIN)

        self.assertTrue(result["stands"])
        self.assertEqual(result["dry_runs_in_a_row"], 3)

    def test_a_newest_run_older_than_the_limit_means_the_chain_ended(self):
        result = assess(runs_newest_first([3.0], age=timedelta(minutes=46)), max_rain_mm_hr=4.0)

        self.assertFalse(result["stands"])
        self.assertEqual(result["reason"], "chain_ended")

    def test_a_run_just_inside_the_age_limit_still_counts(self):
        self.assertTrue(assess(runs_newest_first([3.0], age=timedelta(minutes=45)), NO_RAIN)["stands"])

    def test_dry_runs_before_a_long_gap_do_not_count_with_the_new_ones(self):
        newer = runs_newest_first([0, 0])
        older_start = newer[-1].timestamp - timedelta(hours=3)
        older = [RunDepth(older_start - timedelta(minutes=15) * i, 0, timedelta(hours=4)) for i in range(3)]

        result = assess(newer + older, NO_RAIN)

        self.assertTrue(result["stands"])
        self.assertEqual(result["dry_runs_in_a_row"], 2)


class ReadStandingFloodTests(unittest.TestCase):
    def connection(self, table_exists, rows):
        cursor = MagicMock()
        cursor.fetchone.return_value = (table_exists,)
        cursor.fetchall.return_value = rows
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cursor
        return conn, cursor

    def test_a_missing_table_is_a_dry_state_and_is_not_queried_further(self):
        conn, cursor = self.connection(False, [])

        result = read_standing_flood(conn, max_rain_mm_hr=2.0)

        self.assertFalse(result["stands"])
        self.assertEqual(result["reason"], "no_run")
        cursor.fetchall.assert_not_called()

    def test_rows_from_the_table_are_assessed_with_the_forecast(self):
        rows = [(START, 4.2, timedelta(minutes=10)), (START - timedelta(minutes=15), 4.1, timedelta(minutes=25))]
        conn, cursor = self.connection(True, rows)

        result = read_standing_flood(conn, max_rain_mm_hr=0.0)

        self.assertTrue(result["stands"])
        self.assertEqual(cursor.execute.call_args_list[1].args[1]["limit"], DRY_RUNS_TO_STOP)


if __name__ == "__main__":
    unittest.main()
