"""Runs against a real PostgreSQL. Set EDGE_DEPTH_TEST_DSN; the tests work in their own schema and drop it afterwards."""

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

import psycopg2

import edge_depth_rows
from edge_depth_rows import WetEdge

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "database"))
import create_demo_pin_table  # noqa: E402
import create_edge_depth_tables  # noqa: E402

DSN = os.getenv("EDGE_DEPTH_TEST_DSN")
SCHEMA = f"edge_depth_rows_test_{os.getpid()}"

T1 = datetime(2026, 9, 24, 9, 48, 3)
T2 = datetime(2026, 9, 24, 10, 18, 9)
RUN = "20260924T164803"
WET = [WetEdge(T1, "100:0", 60), WetEdge(T1, "101:0", 40), WetEdge(T2, "100:0", 55)]


class RunTimestampTests(unittest.TestCase):
    def test_parses_the_name_the_dag_gives(self):
        self.assertEqual(edge_depth_rows.run_time("20260924T164803"), datetime(2026, 9, 24, 16, 48, 3))

    def test_a_name_of_another_shape_is_an_error(self):
        with self.assertRaises(ValueError):
            edge_depth_rows.run_time("2026-09-24 16:48")

    def test_a_keep_window_below_one_hour_is_an_error(self):
        with self.assertRaises(ValueError):
            edge_depth_rows.check_keep_hours(0)


@unittest.skipUnless(DSN, "EDGE_DEPTH_TEST_DSN is not set")
class WriteRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg2.connect(DSN)
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {SCHEMA}")
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.execute(create_edge_depth_tables.SQL)
            cur.execute(create_demo_pin_table.SQL)

    @classmethod
    def tearDownClass(cls):
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
        cls.conn.close()

    def setUp(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("TRUNCATE edge_depth_run CASCADE")
            cur.execute("TRUNCATE demo_pin")

    def query(self, sql, args=None):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()

    def test_writes_one_row_per_wet_edge_and_step_and_one_registry_row(self):
        result = edge_depth_rows.write_run(self.conn, RUN, "a" * 64, [T1, T2], WET)

        self.assertEqual(result.rows, 3)
        self.assertEqual(
            self.query("SELECT valid_time_utc, edge_key, depth_cm FROM edge_depth ORDER BY 1, 2"),
            [(T1, "100:0", 60), (T1, "101:0", 40), (T2, "100:0", 55)],
        )
        self.assertEqual(
            self.query("SELECT run_ts, graph_hash, valid_times FROM edge_depth_run"),
            [(RUN, "a" * 64, [T1, T2])],
        )

    def test_a_run_with_no_wet_edge_has_a_registry_row_and_no_rows(self):
        result = edge_depth_rows.write_run(self.conn, RUN, "a" * 64, [T1, T2], [])

        self.assertEqual(result.rows, 0)
        self.assertEqual(self.query("SELECT valid_times FROM edge_depth_run WHERE run_ts = %s", (RUN,)), [([T1, T2],)])
        self.assertEqual(self.query("SELECT count(*) FROM edge_depth"), [(0,)])

    def test_the_same_run_written_twice_keeps_the_same_rows(self):
        edge_depth_rows.write_run(self.conn, RUN, "a" * 64, [T1, T2], WET)
        edge_depth_rows.write_run(self.conn, RUN, "a" * 64, [T1, T2], WET)

        self.assertEqual(self.query("SELECT count(*) FROM edge_depth"), [(3,)])
        self.assertEqual(self.query("SELECT count(*) FROM edge_depth_run"), [(1,)])

    def test_a_rebuild_replaces_the_rows_of_the_run(self):
        edge_depth_rows.write_run(self.conn, RUN, "a" * 64, [T1, T2], WET)

        edge_depth_rows.write_run(self.conn, RUN, "b" * 64, [T1, T2], [WetEdge(T2, "102:0", 20)])

        self.assertEqual(self.query("SELECT valid_time_utc, edge_key, depth_cm FROM edge_depth"), [(T2, "102:0", 20)])
        self.assertEqual(self.query("SELECT graph_hash FROM edge_depth_run"), [("b" * 64,)])

    def test_a_row_for_a_time_outside_the_run_is_refused_and_nothing_is_written(self):
        with self.assertRaises(ValueError):
            edge_depth_rows.write_run(self.conn, RUN, "a" * 64, [T1], WET)

        self.assertEqual(self.query("SELECT count(*) FROM edge_depth_run"), [(0,)])

    def test_a_failed_write_leaves_the_earlier_run_in_place(self):
        edge_depth_rows.write_run(self.conn, RUN, "a" * 64, [T1, T2], WET)

        with self.assertRaises(psycopg2.Error):
            edge_depth_rows.write_run(self.conn, RUN, "b" * 64, [T1, T2], [WetEdge(T1, "100:0", 0)])
        self.conn.rollback()

        self.assertEqual(self.query("SELECT count(*) FROM edge_depth"), [(3,)])
        self.assertEqual(self.query("SELECT graph_hash FROM edge_depth_run"), [("a" * 64,)])

    def test_runs_older_than_the_window_before_the_newest_run_are_deleted_with_their_rows(self):
        edge_depth_rows.write_run(self.conn, "20260923T090000", "a" * 64, [T1], [WetEdge(T1, "100:0", 10)])
        edge_depth_rows.write_run(self.conn, "20260923T170000", "a" * 64, [T1], [WetEdge(T1, "100:0", 11)])

        result = edge_depth_rows.write_run(self.conn, RUN, "a" * 64, [T1, T2], WET, keep_hours=24)

        self.assertEqual(result.runs_pruned, 1)
        self.assertEqual(
            self.query("SELECT run_ts FROM edge_depth_run ORDER BY run_ts"), [("20260923T170000",), (RUN,)]
        )
        self.assertEqual(self.query("SELECT count(*) FROM edge_depth WHERE run_ts = '20260923T090000'"), [(0,)])

    def test_the_pinned_run_stays_however_old_it_is(self):
        edge_depth_rows.write_run(self.conn, "20260901T090000", "a" * 64, [T1], [WetEdge(T1, "100:0", 70)])
        with self.conn, self.conn.cursor() as cur:
            cur.execute("INSERT INTO demo_pin (run_ts, valid_time_utc, wet_edges) VALUES ('20260901T090000', %s, 1)", (T1,))

        edge_depth_rows.write_run(self.conn, RUN, "a" * 64, [T1, T2], WET, keep_hours=24)

        self.assertEqual(
            self.query("SELECT run_ts FROM edge_depth_run ORDER BY run_ts"), [("20260901T090000",), (RUN,)]
        )
        self.assertEqual(self.query("SELECT count(*) FROM edge_depth WHERE run_ts = '20260901T090000'"), [(1,)])

    def test_a_run_exactly_at_the_cutoff_is_kept(self):
        edge_depth_rows.write_run(self.conn, "20260923T164803", "a" * 64, [T1], [])

        edge_depth_rows.write_run(self.conn, RUN, "a" * 64, [T1], [], keep_hours=24)

        self.assertEqual(self.query("SELECT count(*) FROM edge_depth_run"), [(2,)])

    def test_the_run_just_written_is_never_pruned_even_when_older_than_the_newest(self):
        edge_depth_rows.write_run(self.conn, RUN, "a" * 64, [T1], [])

        edge_depth_rows.write_run(self.conn, "20260920T000000", "a" * 64, [T1], [], keep_hours=24)

        self.assertEqual(
            self.query("SELECT run_ts FROM edge_depth_run ORDER BY run_ts"), [("20260920T000000",), (RUN,)]
        )


if __name__ == "__main__":
    unittest.main()
