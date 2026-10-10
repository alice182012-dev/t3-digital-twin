"""The run manifest flood_run_output (US-108).

    python3 -m pytest test_run_output.py

The record and prune tests need a real PostgreSQL in FLOOD_TEST_DSN and skip without it.
FakeConnection is shared with the writers' tests, which check where each writer records its row.
"""

from __future__ import annotations

import os
import re
import unittest

import psycopg2

import create_flood_run_output_table
import run_output
from create_routing_reader_role import page_path
from run_output import Output


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self._rows = list(self.conn.rows(sql))
        self.conn.pending.append((sql, params))

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


class FakeConnection:
    """psycopg2's transaction rules without a database: `with conn` commits on success and rolls back on an
    exception, and only committed statements count. `rows(sql)` answers a query, or raises to fail it."""

    def __init__(self, rows=lambda sql: ()):
        self.rows = rows
        self.pending = []
        self.committed = []

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed += self.pending
        self.pending = []

    def rollback(self):
        self.pending = []

    def close(self):
        self.rollback()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *exc):
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False


def published(conn: FakeConnection) -> set[tuple[str, str]]:
    """The (run_ts, output) rows that `conn` committed to flood_run_output."""
    return {
        (params["run_ts"], params["output"])
        for sql, params in conn.committed
        if isinstance(sql, str) and sql.lstrip().startswith("INSERT INTO flood_run_output")
    }


def test_the_contract_page_names_exactly_the_registered_outputs():
    text = page_path().read_text(encoding="utf-8")
    section = text.split("### flood_run_output", 1)[1].split("\n### ", 1)[0]

    assert set(re.findall(r"^\s+- `(\w+)`: task", section, re.MULTILINE)) == {output.value for output in Output}


@unittest.skipUnless(os.environ.get("FLOOD_TEST_DSN"), "FLOOD_TEST_DSN unset")
class RunOutputTests(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg2.connect(os.environ["FLOOD_TEST_DSN"])
        self.addCleanup(self.conn.close)
        with self.conn, self.conn.cursor() as cur:
            cur.execute(create_flood_run_output_table.SQL)
            cur.execute("TRUNCATE flood_run_output;")

    def rows(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT run_ts, output FROM flood_run_output ORDER BY run_ts, output;")
            return cur.fetchall()

    def record(self, run_ts, output):
        with self.conn, self.conn.cursor() as cur:
            run_output.record(cur, run_ts, output)

    def test_recording_an_output_twice_keeps_one_row_and_refreshes_published_at(self):
        self.record("20261010T100000", Output.EXTENT)
        with self.conn, self.conn.cursor() as cur:
            cur.execute("UPDATE flood_run_output SET published_at = '2000-01-01';")

        self.record("20261010T100000", Output.EXTENT)

        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT run_ts, output, published_at > '2000-01-01' FROM flood_run_output;")
            self.assertEqual(cur.fetchall(), [("20261010T100000", "extent", True)])

    def test_each_output_of_a_run_gets_its_own_row(self):
        self.record("20261010T100000", Output.DEPTH_RASTER)
        self.record("20261010T100000", Output.EDGE_DEPTH)

        self.assertEqual(self.rows(), [("20261010T100000", "depth_raster"), ("20261010T100000", "edge_depth")])

    def test_prune_keeps_the_newest_runs_and_the_run_being_published(self):
        for run_ts in ("20261010T100000", "20261010T101500", "20261010T103000", "20261010T104500"):
            self.record(run_ts, Output.DEPTH_RASTER)
        self.record("20261010T104500", Output.EXTENT)

        with self.conn, self.conn.cursor() as cur:
            run_output.prune(cur, 2, always_keep="20261010T100000")

        self.assertEqual(
            self.rows(),
            [
                ("20261010T100000", "depth_raster"),
                ("20261010T103000", "depth_raster"),
                ("20261010T104500", "depth_raster"),
                ("20261010T104500", "extent"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
