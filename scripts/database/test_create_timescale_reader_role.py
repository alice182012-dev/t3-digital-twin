"""The analysis service's timescaledb role reads depth_history and history_moment and writes nothing (US-109).

    python3 -m pytest test_create_timescale_reader_role.py

The statement tests are offline. The live tests need a throwaway TimescaleDB in FLOOD_TEST_TIMESCALE_DSN, connected
as a superuser, and skip without it. They run create_timescale_tables.py's SQL in schema public, which creates the
tables when they are missing and changes nothing otherwise, and drop the role they create.
"""

from __future__ import annotations

import contextlib
import io
import os
import unittest

import psycopg2
from psycopg2.errors import InsufficientPrivilege

import create_timescale_reader_role
import create_timescale_tables
from create_timescale_reader_role import statements

DSN = os.environ.get("FLOOD_TEST_TIMESCALE_DSN")


def test_the_role_can_select_exactly_the_two_history_tables():
    assert statements("analysis_timescale_reader", "flood_metrics") == [
        'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM "analysis_timescale_reader"',
        'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM "analysis_timescale_reader"',
        'REVOKE CREATE ON SCHEMA public FROM "analysis_timescale_reader"',
        'GRANT CONNECT ON DATABASE "flood_metrics" TO "analysis_timescale_reader"',
        'GRANT USAGE ON SCHEMA public TO "analysis_timescale_reader"',
        'GRANT SELECT ON public."depth_history" TO "analysis_timescale_reader"',
        'GRANT SELECT ON public."history_moment" TO "analysis_timescale_reader"',
    ]


def test_no_password_stops_before_connecting():
    saved = os.environ.pop("ANALYSIS_TIMESCALE_READER_PASSWORD", None)
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr):
            code = create_timescale_reader_role.main()
    finally:
        if saved is not None:
            os.environ["ANALYSIS_TIMESCALE_READER_PASSWORD"] = saved
    user = os.environ.get("ANALYSIS_TIMESCALE_READER_USER", "analysis_timescale_reader")
    assert (code, stderr.getvalue()) == (
        1,
        f"Set ANALYSIS_TIMESCALE_READER_PASSWORD to the password {user} will use.\n",
    )


@unittest.skipUnless(DSN, "FLOOD_TEST_TIMESCALE_DSN unset")
class TimescaleReaderRoleTests(unittest.TestCase):
    role = f"analysis_timescale_reader_test_{os.getpid()}"

    def setUp(self):
        self.conn = psycopg2.connect(DSN)
        self.addCleanup(self.conn.close)
        self.query(create_timescale_tables.SQL)
        self.addCleanup(self._drop_role)
        create_timescale_reader_role.apply(self.conn, self.role, "test-password")
        create_timescale_reader_role.apply(self.conn, self.role, "test-password")

    def _drop_role(self):
        self.query(f"DROP OWNED BY {self.role}")
        self.query(f"DROP ROLE {self.role}")

    def query(self, sql, as_role=False):
        with self.conn, self.conn.cursor() as cur:
            if as_role:
                cur.execute(f"SET LOCAL ROLE {self.role}")
            cur.execute(sql)
            return cur.fetchall() if cur.description else None

    def test_the_role_can_select_both_history_tables(self):
        for table in ("depth_history", "history_moment"):
            self.assertIsNotNone(self.query(f"SELECT count(*) FROM public.{table}", as_role=True), table)

    def test_the_role_cannot_insert_into_depth_history(self):
        with self.assertRaises(InsufficientPrivilege):
            self.query(
                "INSERT INTO public.depth_history (segment_id, valid_time, depth_m, cycle, issued_at) "
                "VALUES ('s', '2026-10-11T00:00:00Z', 0.1, 'constant_cycle', '2026-10-11T00:00:00Z')",
                as_role=True,
            )

    def test_the_role_cannot_read_another_table_or_create_one(self):
        for sql in (
            "SELECT count(*) FROM public.institution_histogram_bar",
            "CREATE TABLE public.analysis_timescale_reader_should_not_exist (x int)",
        ):
            with self.assertRaises(InsufficientPrivilege, msg=sql):
                self.query(sql, as_role=True)


if __name__ == "__main__":
    unittest.main()
