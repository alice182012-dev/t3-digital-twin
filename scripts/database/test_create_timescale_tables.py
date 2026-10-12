"""The TimescaleDB schema of create_timescale_tables.py.

    python3 -m pytest test_create_timescale_tables.py

Needs a real TimescaleDB in FLOOD_TEST_TIMESCALE_DSN and skips without it. Each run works in its own schema and
drops it afterwards. test_load_run.py reuses open_test_schema.
"""

from __future__ import annotations

import os
import unittest

import psycopg2

import create_timescale_tables

DSN = os.environ.get("FLOOD_TEST_TIMESCALE_DSN")


def open_test_schema(dsn: str, schema: str):
    """A connection whose search_path starts at a fresh `schema`, with the timescale tables created in it."""
    conn = psycopg2.connect(dsn)
    with conn, conn.cursor() as cur:
        # Created before the search_path moves, so the extension lands in public and outlives the test schema.
        cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
        cur.execute(f"CREATE SCHEMA {schema}")
        cur.execute(f"SET search_path TO {schema}, public")
        cur.execute(create_timescale_tables.SQL)
    return conn


def drop_test_schema(conn, schema: str) -> None:
    with conn, conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA {schema} CASCADE")
    conn.close()


@unittest.skipUnless(DSN, "FLOOD_TEST_TIMESCALE_DSN unset")
class TimescaleSchemaTests(unittest.TestCase):
    schema = f"timescale_schema_test_{os.getpid()}"

    @classmethod
    def setUpClass(cls):
        cls.conn = open_test_schema(DSN, cls.schema)
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(create_timescale_tables.SQL)

    @classmethod
    def tearDownClass(cls):
        drop_test_schema(cls.conn, cls.schema)

    def query(self, sql):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(sql, {"schema": self.schema})
            return cur.fetchall()

    def test_depth_history_and_history_moment_are_hypertables_on_valid_time(self):
        rows = self.query(
            """
            SELECT hypertable_name, column_name, time_interval::text
            FROM timescaledb_information.dimensions
            WHERE hypertable_schema = %(schema)s AND hypertable_name IN ('depth_history', 'history_moment')
            ORDER BY hypertable_name
            """
        )

        self.assertEqual(rows, [("depth_history", "valid_time", "7 days"), ("history_moment", "valid_time", "7 days")])

    def test_depth_history_compresses_by_segment_ordered_by_time(self):
        rows = self.query(
            """
            SELECT segmentby, orderby FROM timescaledb_information.hypertable_compression_settings
            WHERE hypertable = format('%%I.depth_history', %(schema)s::text)::regclass
            """
        )

        self.assertEqual(rows, [("segment_id", "valid_time")])

    def test_the_compression_and_drop_policies_exist_once_after_two_runs(self):
        rows = self.query(
            """
            SELECT hypertable_name, proc_name,
                   coalesce(config->>'compress_after', config->>'drop_after')::interval::text
            FROM timescaledb_information.jobs
            WHERE hypertable_schema = %(schema)s
            ORDER BY hypertable_name, proc_name
            """
        )

        self.assertEqual(
            rows,
            [
                ("depth_history", "policy_compression", "7 days"),
                ("depth_history", "policy_retention", "365 days"),
                ("history_moment", "policy_retention", "365 days"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
