"""The depth history loader.

    python3 -m pytest test_load_run.py

The conversion and slice tests need no database. The write tests need a real TimescaleDB in
FLOOD_TEST_TIMESCALE_DSN and skip without it; each run works in its own schema and drops it afterwards.
"""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import load_run
from load_run import DepthRow, LoadRunError, RunSlice

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "database"))
from test_create_timescale_tables import drop_test_schema, open_test_schema  # noqa: E402
from test_run_output import FakeConnection  # noqa: E402

DSN = os.environ.get("FLOOD_TEST_TIMESCALE_DSN")
UTC = timezone.utc


def utc(*parts):
    return datetime(*parts, tzinfo=UTC)


class ConversionTests(unittest.TestCase):
    def test_vietnam_local_time_is_seven_hours_ahead_of_utc(self):
        self.assertEqual(load_run.vietnam_to_utc(datetime(2026, 9, 24, 16, 48, 3)), utc(2026, 9, 24, 9, 48, 3))

    def test_a_local_time_after_midnight_falls_on_the_previous_utc_day(self):
        self.assertEqual(load_run.vietnam_to_utc(datetime(2026, 10, 1, 3, 0)), utc(2026, 9, 30, 20, 0))


class BuildSliceTests(unittest.TestCase):
    def test_a_run_becomes_utc_moments_and_wet_rows_in_metres_issued_at_the_run_time(self):
        run = load_run.build_slice(
            "20260924T164803",
            [datetime(2026, 9, 24, 10, 3, 3), datetime(2026, 9, 24, 9, 48, 3)],
            [("100:0", datetime(2026, 9, 24, 9, 48, 3), 25), ("100:0", datetime(2026, 9, 24, 10, 3, 3), 7)],
        )

        self.assertEqual(
            run,
            RunSlice(
                run_ts="20260924T164803",
                issued_at=utc(2026, 9, 24, 9, 48, 3),
                moments=(utc(2026, 9, 24, 9, 48, 3), utc(2026, 9, 24, 10, 3, 3)),
                rows=(
                    DepthRow("100:0", utc(2026, 9, 24, 9, 48, 3), 0.25),
                    DepthRow("100:0", utc(2026, 9, 24, 10, 3, 3), 0.07),
                ),
            ),
        )

    def test_a_run_that_wets_no_edge_still_covers_its_moments(self):
        run = load_run.build_slice("20260924T164803", [datetime(2026, 9, 24, 9, 48, 3)], [])

        self.assertEqual((run.moments, run.rows), ((utc(2026, 9, 24, 9, 48, 3),), ()))

    def test_a_run_without_valid_times_fails(self):
        with self.assertRaisesRegex(LoadRunError, "no valid times in edge_depth_run for run 20260924T164803"):
            load_run.build_slice("20260924T164803", [], [("100:0", datetime(2026, 9, 24, 9, 48, 3), 25)])

    def test_a_row_at_a_time_the_valid_times_do_not_cover_fails(self):
        with self.assertRaisesRegex(LoadRunError, "which its valid times do not cover"):
            load_run.build_slice(
                "20260924T164803",
                [datetime(2026, 9, 24, 9, 48, 3)],
                [("100:0", datetime(2026, 9, 24, 9, 3, 3), 25)],
            )

    def test_read_run_queries_the_run_by_its_name(self):
        def rows(sql):
            if "edge_depth_run" in sql:
                return [([datetime(2026, 9, 24, 9, 48, 3)],)]
            return [("100:0", datetime(2026, 9, 24, 9, 48, 3), 40)]

        conn = FakeConnection(rows)

        run = load_run.read_run(conn, "20260924T164803")

        self.assertEqual(run.rows, (DepthRow("100:0", utc(2026, 9, 24, 9, 48, 3), 0.4),))
        self.assertEqual([params for _, params in conn.committed], [("20260924T164803",), ("20260924T164803",)])

    def test_read_run_fails_for_a_run_the_registry_does_not_list(self):
        conn = FakeConnection(lambda sql: [])

        with self.assertRaisesRegex(LoadRunError, "no edge_depth_run row for run 20260924T164803"):
            load_run.read_run(conn, "20260924T164803")


class PlanWriteTests(unittest.TestCase):
    T1, T2 = utc(2026, 9, 24, 9, 45), utc(2026, 9, 24, 10, 0)
    RUN = RunSlice(
        run_ts="20260924T164500",
        issued_at=T1,
        moments=(T1, T2),
        rows=(DepthRow("seg-1", T1, 0.2), DepthRow("seg-1", T2, 0.3)),
    )

    def test_moments_held_by_a_later_run_are_skipped_with_their_rows(self):
        result = load_run.plan_write(self.RUN, {self.T2: utc(2026, 9, 24, 10, 0)})

        self.assertEqual(
            (result.written, result.skipped, result.rows), ((self.T1,), (self.T2,), (DepthRow("seg-1", self.T1, 0.2),))
        )

    def test_moments_held_by_an_earlier_run_or_by_this_run_are_written(self):
        result = load_run.plan_write(self.RUN, {self.T1: utc(2026, 9, 24, 9, 30), self.T2: self.T1})

        self.assertEqual((result.written, result.skipped, len(result.rows)), ((self.T1, self.T2), (), 2))

    def test_describe_counts_moments_and_rows(self):
        result = load_run.plan_write(self.RUN, {self.T2: utc(2026, 9, 24, 10, 0)})

        self.assertEqual(
            result.describe(), "Run 20260924T164500: 1 moments written, 1 skipped for a later run, 1 rows."
        )


def run_slice(run_ts, wet):
    """A run that covers four 15-minute moments from its own time on, with `wet` = {(edge_key, step): depth_cm}."""
    issued_at = load_run.vietnam_to_utc(datetime.strptime(run_ts, "%Y%m%dT%H%M%S"))
    valid_times = [(issued_at + i * timedelta(minutes=15)).replace(tzinfo=None) for i in range(4)]
    wet_rows = [(edge_key, valid_times[step], depth_cm) for (edge_key, step), depth_cm in wet.items()]
    return load_run.build_slice(run_ts, valid_times, wet_rows)


@unittest.skipUnless(DSN, "FLOOD_TEST_TIMESCALE_DSN unset")
class WriteRunTests(unittest.TestCase):
    schema = f"depth_history_test_{os.getpid()}"

    @classmethod
    def setUpClass(cls):
        cls.conn = open_test_schema(DSN, cls.schema)

    @classmethod
    def tearDownClass(cls):
        drop_test_schema(cls.conn, cls.schema)

    def setUp(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("TRUNCATE depth_history, history_moment")

    def history(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(
                "SELECT edge_key, valid_time, depth_m, cycle::text, issued_at FROM depth_history "
                "ORDER BY valid_time, edge_key"
            )
            return cur.fetchall()

    def moments(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT valid_time, issued_at FROM history_moment ORDER BY valid_time")
            return cur.fetchall()

    def write(self, run):
        return load_run.write_run(self.conn, run)

    def test_loading_a_run_writes_one_row_per_wet_edge_and_step(self):
        run = run_slice("20260924T164500", {("100:0", 0): 20, ("101:0", 0): 50, ("101:0", 1): 10})

        self.write(run)

        issued = utc(2026, 9, 24, 9, 45)
        self.assertEqual(
            self.history(),
            [
                ("100:0", utc(2026, 9, 24, 9, 45), 0.2, "constant_cycle", issued),
                ("101:0", utc(2026, 9, 24, 9, 45), 0.5, "constant_cycle", issued),
                ("101:0", utc(2026, 9, 24, 10, 0), 0.1, "constant_cycle", issued),
            ],
        )
        self.assertEqual(len(self.moments()), 4)

    def test_loading_the_same_run_twice_keeps_the_row_count(self):
        run = run_slice("20260924T164500", {("100:0", 0): 20, ("101:0", 3): 40})

        self.write(run)
        second = self.write(run)

        self.assertEqual((len(second.written), len(self.history()), len(self.moments())), (4, 2, 4))

    def test_a_later_run_takes_the_overlapping_moments_and_drops_an_edge_only_the_earlier_run_wet(self):
        self.write(run_slice("20260924T164500", {("100:0", 1): 20, ("101:0", 1): 30, ("100:0", 0): 10}))

        later = self.write(run_slice("20260924T170000", {("100:0", 0): 60}))

        self.assertEqual((len(later.written), later.skipped), (4, ()))
        self.assertEqual(
            self.history(),
            [
                ("100:0", utc(2026, 9, 24, 9, 45), 0.1, "constant_cycle", utc(2026, 9, 24, 9, 45)),
                ("100:0", utc(2026, 9, 24, 10, 0), 0.6, "constant_cycle", utc(2026, 9, 24, 10, 0)),
            ],
        )
        self.assertEqual(
            [issued for _, issued in self.moments()],
            [utc(2026, 9, 24, 9, 45)] + [utc(2026, 9, 24, 10, 0)] * 4,
        )

    def test_an_earlier_run_loaded_after_a_later_one_keeps_only_the_moments_nobody_later_covers(self):
        self.write(run_slice("20260924T170000", {("100:0", 0): 60}))

        earlier = self.write(run_slice("20260924T164500", {("100:0", 0): 10, ("100:0", 1): 20, ("101:0", 1): 30}))

        self.assertEqual(earlier.written, (utc(2026, 9, 24, 9, 45),))
        self.assertEqual(len(earlier.skipped), 3)
        self.assertEqual(
            self.history(),
            [
                ("100:0", utc(2026, 9, 24, 9, 45), 0.1, "constant_cycle", utc(2026, 9, 24, 9, 45)),
                ("100:0", utc(2026, 9, 24, 10, 0), 0.6, "constant_cycle", utc(2026, 9, 24, 10, 0)),
            ],
        )

    def test_a_run_that_wets_no_edge_records_its_moments_and_no_depths(self):
        result = self.write(run_slice("20260924T164500", {}))

        self.assertEqual((len(result.written), self.history()), (4, []))
        self.assertEqual(
            self.moments(),
            [
                (utc(2026, 9, 24, 9, 45), utc(2026, 9, 24, 9, 45)),
                (utc(2026, 9, 24, 10, 0), utc(2026, 9, 24, 9, 45)),
                (utc(2026, 9, 24, 10, 15), utc(2026, 9, 24, 9, 45)),
                (utc(2026, 9, 24, 10, 30), utc(2026, 9, 24, 9, 45)),
            ],
        )


if __name__ == "__main__":
    unittest.main()
