"""The database tests run against a real PostGIS. Set FLOOD_ROADS_TEST_DSN (for example
"host=/tmp port=55433 dbname=flowtest user=postgres"); each run works in its own schema and drops
it afterwards. The command line tests need no database."""

import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import psycopg2

import prune_flood_road_values
from prune_flood_road_values import PruneResult

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "database"))
import create_flood_road_tables  # noqa: E402

DSN = os.getenv("FLOOD_ROADS_TEST_DSN")
SCHEMA = f"flood_roads_prune_test_{os.getpid()}"

NEWEST = datetime(2026, 10, 9, 16, 0, 0)


def hours_before_newest(*hours):
    return [NEWEST - timedelta(hours=h) for h in hours]


@unittest.skipUnless(DSN, "FLOOD_ROADS_TEST_DSN is not set")
class PruneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg2.connect(DSN)
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {SCHEMA}")
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.execute(create_flood_road_tables.SQL)

    @classmethod
    def tearDownClass(cls):
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
        cls.conn.close()

    def setUp(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("TRUNCATE flood_road_values, flood_road_file")

    def add_runs(self, timestamps, rows_per_run=3):
        with self.conn, self.conn.cursor() as cur:
            for timestamp in timestamps:
                cur.execute(
                    "INSERT INTO flood_road_file (timestamp, source_file) VALUES (%s, %s) RETURNING id",
                    (timestamp, f"flood_on_roads_{timestamp:%Y%m%dT%H%M%S}"),
                )
                file_id = cur.fetchone()[0]
                for i in range(rows_per_run):
                    cur.execute(
                        """INSERT INTO flood_road_values (file_id, timestamp, forecast_time, depth, segment_id)
                           VALUES (%s, %s, %s, 0.2, %s)""",
                        (file_id, timestamp, timestamp, f"way/{i}#0"),
                    )

    def runs(self, table):
        with self.conn.cursor() as cur:
            cur.execute(f"SELECT DISTINCT timestamp FROM {table} ORDER BY 1")
            return [row[0] for row in cur.fetchall()]

    def row_count(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM flood_road_values")
            return cur.fetchone()[0]

    def test_runs_across_30_hours_keep_only_the_last_24_hours_in_both_tables(self):
        self.add_runs(hours_before_newest(30, 27, 25, 21, 12, 3, 0))

        result = prune_flood_road_values.prune(self.conn, 24)

        kept = hours_before_newest(21, 12, 3, 0)
        self.assertEqual(self.runs("flood_road_values"), sorted(kept))
        self.assertEqual(self.runs("flood_road_file"), sorted(kept))
        self.assertEqual(self.row_count(), 12)
        self.assertEqual(
            result,
            PruneResult(
                cutoff=datetime(2026, 10, 8, 16, 0, 0), newest_run=NEWEST, runs_deleted=3, rows_deleted=9, runs_kept=4
            ),
        )

    def test_a_run_exactly_at_the_cutoff_is_kept(self):
        self.add_runs(hours_before_newest(24, 0))

        result = prune_flood_road_values.prune(self.conn, 24)

        self.assertEqual(self.runs("flood_road_values"), hours_before_newest(24, 0))
        self.assertEqual((result.runs_deleted, result.runs_kept), (0, 2))

    def test_a_single_run_is_kept(self):
        self.add_runs([NEWEST])

        result = prune_flood_road_values.prune(self.conn, 1)

        self.assertEqual(self.runs("flood_road_values"), [NEWEST])
        self.assertEqual(self.runs("flood_road_file"), [NEWEST])
        self.assertEqual((result.runs_deleted, result.rows_deleted, result.runs_kept), (0, 0, 1))

    def test_a_newest_run_weeks_old_is_measured_from_itself_not_from_the_clock(self):
        old = datetime(2026, 8, 1, 7, 30, 0)
        self.add_runs([old - timedelta(hours=30), old - timedelta(hours=10), old])

        result = prune_flood_road_values.prune(self.conn, 24)

        self.assertEqual(self.runs("flood_road_values"), [old - timedelta(hours=10), old])
        self.assertEqual((result.newest_run, result.runs_deleted, result.runs_kept), (old, 1, 2))

    def test_an_empty_table_is_a_no_op_that_reports_zero(self):
        result = prune_flood_road_values.prune(self.conn, 24)

        self.assertEqual(
            result, PruneResult(cutoff=None, newest_run=None, runs_deleted=0, rows_deleted=0, runs_kept=0)
        )

    def test_a_dry_run_counts_and_deletes_nothing(self):
        self.add_runs(hours_before_newest(30, 27, 0))

        result = prune_flood_road_values.prune(self.conn, 24, dry_run=True)

        self.assertEqual(self.runs("flood_road_values"), hours_before_newest(30, 27, 0))
        self.assertEqual(self.runs("flood_road_file"), hours_before_newest(30, 27, 0))
        self.assertEqual((result.runs_deleted, result.rows_deleted, result.runs_kept), (2, 6, 1))


class CommandLineTests(unittest.TestCase):
    def test_keep_hours_that_is_not_a_positive_integer_exits_before_connecting(self):
        for value in ("0", "-1", "1.5", "abc"):
            with self.subTest(value=value), patch.object(psycopg2, "connect") as connect:
                with patch("sys.stderr"), self.assertRaises(SystemExit):
                    prune_flood_road_values.main(["--keep-hours", value])
                connect.assert_not_called()

    def test_main_prunes_with_the_given_window_and_dry_run(self):
        with patch.object(psycopg2, "connect"), patch.object(prune_flood_road_values, "prune") as prune, \
                patch("builtins.print"):
            prune.return_value = PruneResult(
                cutoff=None, newest_run=None, runs_deleted=0, rows_deleted=0, runs_kept=0
            )
            prune_flood_road_values.main(["--keep-hours", "6", "--dry-run"])

        self.assertEqual(prune.call_args.args[1:], (6,))
        self.assertEqual(prune.call_args.kwargs, {"target_table": "flood_road_values", "dry_run": True})


if __name__ == "__main__":
    unittest.main()
