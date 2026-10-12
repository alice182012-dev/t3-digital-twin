import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2

from standing_flood import DRY_DEPTH_M, DRY_RUNS_TO_STOP, RunDepth, assess, read_standing_flood

sys.path.insert(0, str(Path(__file__).resolve().parent / "database"))
import create_edge_depth_tables  # noqa: E402

DSN = os.getenv("EDGE_DEPTH_TEST_DSN")
SCHEMA = f"standing_flood_test_{os.getpid()}"

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


@unittest.skipUnless(DSN, "EDGE_DEPTH_TEST_DSN is not set")
class ReadStandingFloodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg2.connect(DSN)
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {SCHEMA}")
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.execute(create_edge_depth_tables.SQL)

    @classmethod
    def tearDownClass(cls):
        cls.conn.rollback()
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
        cls.conn.close()

    def setUp(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.execute("TRUNCATE edge_depth_run CASCADE")

    def add_runs(self, max_depths_cm):
        """One registered run per value, newest first, one slot apart, built 12 minutes after its slot. A value of
        None is a run with no wet edge."""
        with self.conn, self.conn.cursor() as cur:
            for index, depth_cm in enumerate(max_depths_cm):
                slot = START - timedelta(minutes=15) * index
                run_ts = slot.strftime("%Y%m%dT%H%M%S")
                cur.execute(
                    "INSERT INTO edge_depth_run (run_ts, graph_hash, valid_times, built_at) "
                    "VALUES (%s, 'h', ARRAY[%s]::timestamp[], LOCALTIMESTAMP - interval '12 minutes' - %s * interval '1 minute')",
                    (run_ts, slot, 15 * index),
                )
                if depth_cm is not None:
                    cur.execute(
                        "INSERT INTO edge_depth VALUES (%s, %s, '1:0', %s), (%s, %s, '2:0', 1)",
                        (run_ts, slot, depth_cm, run_ts, slot),
                    )

    def read(self, rain=NO_RAIN):
        return read_standing_flood(self.conn, rain)

    def test_a_database_with_no_registry_table_is_a_dry_state(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("DROP TABLE edge_depth, edge_depth_run")
        try:
            result = read_standing_flood(self.conn, max_rain_mm_hr=2.0)
        finally:
            with self.conn, self.conn.cursor() as cur:
                cur.execute(create_edge_depth_tables.SQL)

        self.assertEqual((result["stands"], result["reason"]), (False, "no_run"))

    def test_an_empty_registry_is_a_dry_state(self):
        self.assertEqual(self.read(rain=2.0)["reason"], "no_run")

    def test_a_wet_newest_run_stands(self):
        self.add_runs([42, 30, 12, 8, 6])

        result = self.read()

        self.assertEqual((result["stands"], result["reason"], result["dry_runs_in_a_row"]), (True, "standing_flood", 0))
        self.assertEqual(result["newest_run_age_min"], 12.0)

    def test_five_dry_runs_among_them_runs_with_no_wet_edge_end_it(self):
        self.add_runs([None, 4, None, 4, None])

        result = self.read()

        self.assertEqual((result["stands"], result["reason"], result["dry_runs_in_a_row"]), (False, "dry_and_no_rain", 5))

    def test_a_dry_run_among_the_newest_five_counts_as_dry_not_missing(self):
        self.add_runs([None, 60, 60, 60, 60])

        self.assertEqual(self.read()["dry_runs_in_a_row"], 1)

    def test_only_the_newest_five_runs_are_read(self):
        self.add_runs([None] * 5 + [90])

        self.assertEqual(self.read()["dry_runs_in_a_row"], 5)

    def test_a_depth_of_exactly_5_cm_is_wet(self):
        self.add_runs([5, None, None, None, None])

        self.assertEqual(self.read()["dry_runs_in_a_row"], 0)


if __name__ == "__main__":
    unittest.main()
