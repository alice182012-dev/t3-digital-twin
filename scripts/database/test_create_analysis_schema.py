"""The owner role of schema analysis writes only there (US-109).

    python3 -m pytest test_create_analysis_schema.py

The statement tests are offline. The live tests need a throwaway PostgreSQL in FLOOD_TEST_DSN, connected as a
superuser, and skip without it. They skip as well when the database already has a schema `analysis`, and drop the
schema and the role they create.
"""

from __future__ import annotations

import contextlib
import io
import os
import unittest

import psycopg2
from psycopg2.errors import InsufficientPrivilege

import create_analysis_schema
from create_analysis_schema import statements

DSN = os.environ.get("FLOOD_TEST_DSN")


def test_the_owner_owns_analysis_and_holds_nothing_in_public():
    assert statements("analysis_owner", "minio_custom") == [
        'REVOKE ALL ON ALL TABLES IN SCHEMA public FROM "analysis_owner"',
        'REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM "analysis_owner"',
        'REVOKE ALL ON SCHEMA public FROM "analysis_owner"',
        'GRANT CONNECT ON DATABASE "minio_custom" TO "analysis_owner"',
        'CREATE SCHEMA IF NOT EXISTS "analysis" AUTHORIZATION "analysis_owner"',
        'ALTER SCHEMA "analysis" OWNER TO "analysis_owner"',
        'ALTER ROLE "analysis_owner" SET search_path TO "analysis", public',
    ]


def test_an_owner_name_that_needs_quoting_is_refused():
    try:
        statements('owner"; DROP ROLE x; --', "minio_custom")
    except ValueError:
        return
    raise AssertionError("the name was accepted")


def test_no_password_stops_before_connecting():
    saved = os.environ.pop("ANALYSIS_OWNER_PASSWORD", None)
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stderr(stderr):
            code = create_analysis_schema.main()
    finally:
        if saved is not None:
            os.environ["ANALYSIS_OWNER_PASSWORD"] = saved
    expected_user = os.environ.get("ANALYSIS_OWNER_USER", "analysis_owner")
    assert (code, stderr.getvalue()) == (1, f"Set ANALYSIS_OWNER_PASSWORD to the password {expected_user} will use.\n")


@unittest.skipUnless(DSN, "FLOOD_TEST_DSN unset")
class AnalysisSchemaTests(unittest.TestCase):
    owner = f"analysis_owner_test_{os.getpid()}"
    probe = f"analysis_owner_probe_{os.getpid()}"

    def setUp(self):
        self.conn = psycopg2.connect(DSN)
        self.addCleanup(self.conn.close)
        if self.query("SELECT 1 FROM pg_namespace WHERE nspname = 'analysis'"):
            self.skipTest("the database already has a schema analysis")
        self.addCleanup(self._drop)
        self.query(f"CREATE TABLE public.{self.probe} (x int)")
        create_analysis_schema.apply(self.conn, self.owner, "test-password")

    def _drop(self):
        self.query(f"DROP TABLE IF EXISTS public.{self.probe}")
        self.query("DROP SCHEMA IF EXISTS analysis CASCADE")
        if self.query(f"SELECT 1 FROM pg_roles WHERE rolname = '{self.owner}'"):
            self.query(f"DROP OWNED BY {self.owner}")
            self.query(f"DROP ROLE {self.owner}")

    def query(self, sql, as_owner=False):
        with self.conn, self.conn.cursor() as cur:
            if as_owner:
                cur.execute(f"SET LOCAL ROLE {self.owner}")
            cur.execute(sql)
            return cur.fetchall() if cur.description else None

    def test_a_second_run_succeeds_and_leaves_the_same_owner(self):
        create_analysis_schema.apply(self.conn, self.owner, "test-password")

        self.assertEqual(
            self.query("SELECT nspowner::regrole::text FROM pg_namespace WHERE nspname = 'analysis'"),
            [(self.owner,)],
        )

    def test_the_owner_can_create_and_write_a_table_in_analysis(self):
        self.query("CREATE TABLE analysis.probe (x int)", as_owner=True)
        self.query("INSERT INTO analysis.probe VALUES (1)", as_owner=True)

        self.assertEqual(self.query("SELECT x FROM analysis.probe", as_owner=True), [(1,)])

    def test_the_owner_cannot_write_or_read_a_public_table(self):
        for sql in (f"INSERT INTO public.{self.probe} VALUES (1)", f"SELECT x FROM public.{self.probe}"):
            with self.assertRaises(InsufficientPrivilege, msg=sql):
                self.query(sql, as_owner=True)

    def test_the_owner_cannot_create_a_table_in_public(self):
        with self.assertRaises(InsufficientPrivilege):
            self.query("CREATE TABLE public.analysis_owner_should_not_exist (x int)", as_owner=True)


if __name__ == "__main__":
    unittest.main()
