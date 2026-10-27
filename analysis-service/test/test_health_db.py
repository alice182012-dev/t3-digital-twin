"""The manifest query of GET /health against a real PostgreSQL.

    FLOOD_TEST_DSN=postgresql://... python3 -m pytest analysis-service/test/test_health_db.py

Skips without FLOOD_TEST_DSN. Each run makes flood_run_output in its own schema, with the DDL of
scripts/database/create_flood_run_output_table.py, and drops the schema afterwards.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

import psycopg2

SERVICE = Path(__file__).resolve().parents[1]
REPO = SERVICE.parent
sys.path.insert(0, str(SERVICE / "app"))
sys.path.insert(0, str(REPO / "scripts" / "database"))

import create_flood_run_output_table  # noqa: E402
import server  # noqa: E402

DSN = os.environ.get("FLOOD_TEST_DSN")
ALL_OUTPUTS = ("depth_raster", "extent", "edge_depth")


@unittest.skipUnless(DSN, "FLOOD_TEST_DSN unset")
class NewestCompleteRunTests(unittest.TestCase):
    schema = f"analysis_health_test_{os.getpid()}"

    def setUp(self):
        self.conn = psycopg2.connect(DSN)
        with self.conn, self.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {self.schema}")
            cur.execute(f"SET search_path TO {self.schema}")
            cur.execute(create_flood_run_output_table.SQL)
        self.addCleanup(self._drop_schema)

    def _drop_schema(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {self.schema} CASCADE")
        self.conn.close()

    def publish(self, run_ts, outputs):
        with self.conn, self.conn.cursor() as cur:
            for output in outputs:
                cur.execute("INSERT INTO flood_run_output (run_ts, output) VALUES (%s, %s)", (run_ts, output))

    def test_no_run_gives_none(self):
        self.assertIsNone(server.newest_complete_run(self.conn))

    def test_a_newer_run_with_two_outputs_is_skipped_for_an_older_run_with_three(self):
        self.publish("20261011T000000", ALL_OUTPUTS)
        self.publish("20261011T001500", ALL_OUTPUTS[:2])

        self.assertEqual(server.newest_complete_run(self.conn), "20261011T000000")

    def test_the_newest_of_two_complete_runs_wins(self):
        self.publish("20261010T234500", ALL_OUTPUTS)
        self.publish("20261011T001500", ALL_OUTPUTS)
        self.publish("20261011T000000", ALL_OUTPUTS)

        self.assertEqual(server.newest_complete_run(self.conn), "20261011T001500")


if __name__ == "__main__":
    unittest.main()
