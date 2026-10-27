import os
import unittest
from datetime import datetime, timezone

import psycopg2

import forecast_mode
from forecast_mode import DEMO, LIVE, PENDING, decide_mode, mark_live, record_decision

DSN = os.getenv("EDGE_DEPTH_TEST_DSN")
SCHEMA = f"forecast_mode_test_{os.getpid()}"
SLOT = datetime(2026, 10, 12, 3, 15, tzinfo=timezone.utc)
NEXT_SLOT = datetime(2026, 10, 12, 3, 30, tzinfo=timezone.utc)


class DecideModeTests(unittest.TestCase):
    def test_a_closed_gate_is_demo_whatever_was_published(self):
        self.assertEqual(decide_mode(False, True), DEMO)
        self.assertEqual(decide_mode(False, False), DEMO)

    def test_an_open_gate_is_pending_until_a_step_is_published(self):
        self.assertEqual(decide_mode(True, False), PENDING)
        self.assertEqual(decide_mode(True, True), LIVE)


@unittest.skipUnless(DSN, "EDGE_DEPTH_TEST_DSN is not set")
class ForecastModeTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg2.connect(DSN)
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {SCHEMA}")
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.execute("CREATE TABLE flood_run_output (run_ts TEXT NOT NULL, output TEXT NOT NULL, "
                        "published_at TIMESTAMP NOT NULL DEFAULT NOW(), PRIMARY KEY (run_ts, output))")

    @classmethod
    def tearDownClass(cls):
        cls.conn.rollback()
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
        cls.conn.close()

    def setUp(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.execute("TRUNCATE flood_run_output")
            cur.execute("DROP TABLE IF EXISTS forecast_mode")

    def publish(self, minutes_ago):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("INSERT INTO flood_run_output (run_ts, output, published_at) VALUES "
                        "('r', 'depth_raster', LOCALTIMESTAMP - %s * interval '1 minute')", (minutes_ago,))

    def rows(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT slot, rain_peak_mm_hr, gate_mm_hr, standing_flood, mode FROM forecast_mode ORDER BY slot")
            return cur.fetchall()

    def test_rain_above_the_gate_with_nothing_published_is_pending(self):
        mode = record_decision(self.conn, SLOT, 7.5, 5.0, None, gate_open=True)

        self.assertEqual(mode, PENDING)
        self.assertEqual(self.rows(), [(datetime(2026, 10, 12, 3, 15), 7.5, 5.0, None, "PENDING")])

    def test_an_open_gate_with_a_step_published_lately_is_live(self):
        self.publish(minutes_ago=14)

        self.assertEqual(record_decision(self.conn, SLOT, 0.0, 5.0, True, gate_open=True), LIVE)

    def test_a_step_published_over_45_minutes_ago_does_not_make_it_live(self):
        self.publish(minutes_ago=50)

        self.assertEqual(record_decision(self.conn, SLOT, 7.5, 5.0, None, gate_open=True), PENDING)

    def test_no_rain_and_no_standing_flood_is_demo(self):
        self.assertEqual(record_decision(self.conn, SLOT, 0.0, 5.0, False, gate_open=False), DEMO)
        self.assertEqual(self.rows(), [(datetime(2026, 10, 12, 3, 15), 0.0, 5.0, False, "DEMO")])

    def test_marking_live_moves_only_the_pending_row_of_that_slot(self):
        record_decision(self.conn, SLOT, 7.5, 5.0, None, gate_open=True)
        record_decision(self.conn, NEXT_SLOT, 0.0, 5.0, False, gate_open=False)

        self.assertTrue(mark_live(self.conn, SLOT))
        self.assertFalse(mark_live(self.conn, SLOT))
        self.assertFalse(mark_live(self.conn, NEXT_SLOT))

        self.assertEqual([row[4] for row in self.rows()], ["LIVE", "DEMO"])

    def test_a_rerun_of_the_same_slot_replaces_its_row(self):
        record_decision(self.conn, SLOT, 7.5, 5.0, None, gate_open=True)
        record_decision(self.conn, SLOT, 2.0, 5.0, False, gate_open=False)

        self.assertEqual(self.rows(), [(datetime(2026, 10, 12, 3, 15), 2.0, 5.0, False, "DEMO")])

    def test_rows_older_than_a_week_are_deleted(self):
        record_decision(self.conn, datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc), 0.0, 5.0, False, gate_open=False)
        record_decision(self.conn, datetime.now(timezone.utc), 0.0, 5.0, False, gate_open=False)

        self.assertEqual(len(self.rows()), 1)


if __name__ == "__main__":
    unittest.main()
