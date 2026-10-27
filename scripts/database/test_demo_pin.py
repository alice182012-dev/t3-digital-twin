"""The pinned step of the demo flood. The tests need a real PostgreSQL in EDGE_DEPTH_TEST_DSN and skip without it."""

import os
import unittest
from datetime import datetime

import psycopg2

import create_demo_pin_table
import create_edge_depth_tables
import demo_pin
from demo_pin import Pin

DSN = os.getenv("EDGE_DEPTH_TEST_DSN")
SCHEMA = f"demo_pin_test_{os.getpid()}"
T1 = datetime(2026, 10, 10, 14, 0)
T2 = datetime(2026, 10, 10, 14, 15)
EARLY, LATE = "20261010T210000", "20261010T211500"


@unittest.skipUnless(DSN, "EDGE_DEPTH_TEST_DSN is not set")
class DemoPinTests(unittest.TestCase):
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
            cur.execute("DROP TABLE IF EXISTS demo_pin")

    def add_run(self, run_ts, wet_per_step):
        """wet_per_step maps a UTC step to the number of wet edges at it."""
        with self.conn, self.conn.cursor() as cur:
            cur.execute("INSERT INTO edge_depth_run (run_ts, graph_hash, valid_times) VALUES (%s, 'h', %s::timestamp[])",
                        (run_ts, list(wet_per_step)))
            for step, count in wet_per_step.items():
                for edge in range(count):
                    cur.execute("INSERT INTO edge_depth VALUES (%s, %s, %s, 10)", (run_ts, step, f"{edge}:0"))

    def read(self):
        with self.conn, self.conn.cursor() as cur:
            return demo_pin.read_pin(cur)

    def test_a_database_without_the_table_has_no_pin_and_keeps_only_the_run_being_published(self):
        with self.conn, self.conn.cursor() as cur:
            self.assertEqual(demo_pin.kept_runs(cur, LATE), {LATE})

    def test_the_peak_is_the_step_with_the_most_wet_edges_over_all_runs(self):
        self.add_run(EARLY, {T1: 2, T2: 5})
        self.add_run(LATE, {T1: 3, T2: 4})

        pin = demo_pin.write_pin(self.conn)

        self.assertEqual(pin, Pin(EARLY, T2, 5))
        self.assertEqual(self.read(), pin)

    def test_a_tie_goes_to_the_earliest_run_and_step(self):
        self.add_run(LATE, {T1: 3})
        self.add_run(EARLY, {T2: 3, T1: 3})

        self.assertEqual(demo_pin.write_pin(self.conn), Pin(EARLY, T1, 3))

    def test_pinning_again_replaces_the_row(self):
        self.add_run(EARLY, {T1: 2, T2: 5})
        demo_pin.write_pin(self.conn)
        self.add_run(LATE, {T1: 9})

        demo_pin.write_pin(self.conn)

        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM demo_pin")
            self.assertEqual(cur.fetchone()[0], 1)
        self.assertEqual(self.read(), Pin(LATE, T1, 9))

    def test_a_chosen_run_and_step_are_taken_when_they_have_wet_edges(self):
        self.add_run(EARLY, {T1: 2, T2: 5})

        self.assertEqual(demo_pin.write_pin(self.conn, EARLY, T1), Pin(EARLY, T1, 2))

    def test_a_step_with_no_wet_edge_cannot_be_pinned(self):
        self.add_run(EARLY, {T1: 2})

        with self.assertRaises(ValueError):
            demo_pin.write_pin(self.conn, EARLY, T2)

    def test_no_wet_edge_anywhere_cannot_be_pinned(self):
        with self.assertRaises(ValueError):
            demo_pin.write_pin(self.conn)

    def test_a_prune_keeps_the_pinned_run_and_the_run_it_publishes(self):
        self.add_run(EARLY, {T1: 2})
        demo_pin.write_pin(self.conn)

        with self.conn, self.conn.cursor() as cur:
            self.assertEqual(demo_pin.kept_runs(cur, LATE), {EARLY, LATE})
            self.assertEqual(demo_pin.kept_runs(cur, EARLY), {EARLY})


if __name__ == "__main__":
    unittest.main()
