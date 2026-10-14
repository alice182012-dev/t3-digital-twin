import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2

from standing_flood import STEADY_RUNS_TO_STOP, RunDepth, assess, read_standing_flood

sys.path.insert(0, str(Path(__file__).resolve().parent / "database"))
import create_edge_depth_tables  # noqa: E402

DSN = os.getenv("EDGE_DEPTH_TEST_DSN")
SCHEMA = f"standing_flood_test_{os.getpid()}"

START = datetime(2026, 10, 9, 19, 0)
NO_RAIN = 0.0


POND = {f"pond:{n}": 100 + n for n in range(157)}


def runs_newest_first(depths_per_run, age=timedelta(minutes=12), step=timedelta(minutes=15)):
    """One RunDepth per depth mapping (edge key to centimetres), newest first, one slot apart. The newest run is `age` old."""
    return [
        RunDepth(START - step * index, depths, age + step * index)
        for index, depths in enumerate(depths_per_run)
    ]


class AssessTests(unittest.TestCase):
    def test_no_run_in_the_table_is_a_dry_state_whatever_the_forecast(self):
        result = assess([], max_rain_mm_hr=3.0)

        self.assertFalse(result["stands"])
        self.assertEqual(result["reason"], "no_run")

    def test_five_flat_runs_and_no_rain_end_it(self):
        result = assess(runs_newest_first([{"a": 40}] * STEADY_RUNS_TO_STOP), NO_RAIN)

        self.assertEqual(
            (result["stands"], result["reason"], result["steady_runs_in_a_row"]), (False, "steady_and_no_rain", 5)
        )

    def test_five_flat_runs_and_any_forecast_rain_keep_it_going(self):
        result = assess(runs_newest_first([{"a": 40}] * 5), max_rain_mm_hr=0.2)

        self.assertEqual((result["stands"], result["reason"]), (True, "rain_forecast"))

    def test_four_flat_runs_keep_it_going(self):
        result = assess(runs_newest_first([{"a": 40}] * 4), NO_RAIN)

        self.assertEqual((result["stands"], result["reason"], result["steady_runs_in_a_row"]), (True, "depths_changing", 4))

    def test_a_receding_flood_keeps_it_going(self):
        result = assess(runs_newest_first([{"a": 10}, {"a": 14}, {"a": 18}, {"a": 22}, {"a": 26}]), NO_RAIN)

        self.assertEqual((result["stands"], result["steady_runs_in_a_row"]), (True, 1))

    def test_a_flood_that_recedes_in_one_edge_while_the_rest_hold_keeps_it_going(self):
        newest = {"a": 223, "b": 50}
        older = {"a": 223, "b": 52}
        result = assess(runs_newest_first([newest, newest, newest, newest, older]), NO_RAIN)

        self.assertEqual((result["stands"], result["steady_runs_in_a_row"]), (True, 4))

    def test_a_move_of_exactly_1_cm_is_steady_and_1_1_cm_is_not(self):
        steady = assess(runs_newest_first([{"a": 101.0}, {"a": 100.0}, {"a": 101.0}, {"a": 100.0}, {"a": 101.0}]), NO_RAIN)
        moving = assess(runs_newest_first([{"a": 101.1}, {"a": 100.0}, {"a": 101.0}, {"a": 100.0}, {"a": 101.0}]), NO_RAIN)

        self.assertEqual((steady["stands"], steady["steady_runs_in_a_row"]), (False, 5))
        self.assertEqual((moving["stands"], moving["steady_runs_in_a_row"]), (True, 1))

    def test_157_permanent_water_edges_that_never_change_end_it(self):
        result = assess(runs_newest_first([POND] * 5), NO_RAIN)

        self.assertEqual((result["stands"], result["reason"]), (False, "steady_and_no_rain"))

    def test_permanent_water_does_not_hide_a_recession_elsewhere(self):
        runs = [{**POND, "road": 30}, {**POND, "road": 34}, {**POND, "road": 38}, {**POND, "road": 42}, {**POND, "road": 46}]

        self.assertTrue(assess(runs_newest_first(runs), NO_RAIN)["stands"])

    def test_an_edge_missing_from_a_run_is_dry_so_its_last_depth_counts_as_a_change(self):
        result = assess(runs_newest_first([{}, {"a": 3}, {"a": 3}, {"a": 3}, {"a": 3}]), NO_RAIN)

        self.assertEqual((result["stands"], result["steady_runs_in_a_row"]), (True, 1))

    def test_an_edge_missing_from_a_run_by_1_cm_or_less_is_steady(self):
        result = assess(runs_newest_first([{}, {"a": 1}, {"a": 1}, {"a": 1}, {}]), NO_RAIN)

        self.assertEqual((result["stands"], result["steady_runs_in_a_row"]), (False, 5))

    def test_runs_with_no_wet_edge_are_steady(self):
        self.assertFalse(assess(runs_newest_first([{}] * 5), NO_RAIN)["stands"])

    def test_a_newest_run_older_than_the_limit_means_the_chain_ended(self):
        result = assess(runs_newest_first([{"a": 300}], age=timedelta(minutes=46)), max_rain_mm_hr=4.0)

        self.assertEqual((result["stands"], result["reason"]), (False, "chain_ended"))

    def test_a_run_just_inside_the_age_limit_still_counts(self):
        self.assertTrue(assess(runs_newest_first([{"a": 300}], age=timedelta(minutes=45)), NO_RAIN)["stands"])

    def test_flat_runs_before_a_long_gap_do_not_count_with_the_new_ones(self):
        newer = runs_newest_first([{"a": 9}, {"a": 9}])
        older_start = newer[-1].timestamp - timedelta(hours=3)
        older = [RunDepth(older_start - timedelta(minutes=15) * i, {"a": 9}, timedelta(hours=4)) for i in range(3)]

        result = assess(newer + older, NO_RAIN)

        self.assertEqual((result["stands"], result["steady_runs_in_a_row"]), (True, 2))


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

    def add_runs(self, depths_cm):
        """One registered run per value, newest first, one slot apart, built 12 minutes after its slot. Edge '1:0'
        reads the value at two forecast times (the deeper one counts) and edge '2:0' reads 1 cm. A value of None is a
        run with no wet edge."""
        with self.conn, self.conn.cursor() as cur:
            for index, depth_cm in enumerate(depths_cm):
                slot = START - timedelta(minutes=15) * index
                run_ts = slot.strftime("%Y%m%dT%H%M%S")
                cur.execute(
                    "INSERT INTO edge_depth_run (run_ts, graph_hash, valid_times, built_at) "
                    "VALUES (%s, 'h', ARRAY[%s]::timestamp[], LOCALTIMESTAMP - interval '12 minutes' - %s * interval '1 minute')",
                    (run_ts, slot, 15 * index),
                )
                if depth_cm is not None:
                    cur.execute(
                        "INSERT INTO edge_depth VALUES (%s, %s, '1:0', %s), (%s, %s, '2:0', 1), "
                        "(%s, %s + interval '15 minutes', '1:0', %s)",
                        (run_ts, slot, depth_cm - 1, run_ts, slot, run_ts, slot, depth_cm),
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

    def test_five_runs_of_the_same_depths_end_it(self):
        self.add_runs([42] * 5)

        result = self.read()

        self.assertEqual((result["stands"], result["reason"], result["steady_runs_in_a_row"]), (False, "steady_and_no_rain", 5))
        self.assertEqual(result["newest_run_age_min"], 12.0)

    def test_a_receding_flood_keeps_it_going(self):
        self.add_runs([42, 46, 50, 54, 58])

        result = self.read()

        self.assertEqual((result["stands"], result["reason"], result["steady_runs_in_a_row"]), (True, "depths_changing", 1))

    def test_runs_with_no_wet_edge_count_as_edges_gone_dry(self):
        self.add_runs([None, 4, 4, 4, 4])

        self.assertEqual(self.read()["steady_runs_in_a_row"], 1)

    def test_only_the_newest_five_runs_are_read(self):
        self.add_runs([42] * 5 + [90])

        self.assertEqual(self.read()["steady_runs_in_a_row"], 5)


if __name__ == "__main__":
    unittest.main()
