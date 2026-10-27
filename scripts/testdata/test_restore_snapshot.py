"""Runs against a real PostGIS. Set RESTORE_TEST_DSN to a superuser DSN of a throwaway PostGIS database:

    docker run -d --rm --name restore-test-pg -e POSTGRES_PASSWORD=test -e POSTGRES_DB=floodtest \
        -p 55432:5432 postgis/postgis:15-3.4
    RESTORE_TEST_DSN=postgresql://postgres:test@127.0.0.1:55432/floodtest python test_restore_snapshot.py

The tests make a small snapshot from the real DDL with COPY ... CSV HEADER, the form US-124 wrote, and restore it into a
database of their own, which they drop afterwards.
"""

import gzip
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import psycopg2
from psycopg2 import sql

sys.path.insert(0, str(Path(__file__).resolve().parent))
import restore_snapshot  # noqa: E402

DSN = os.getenv("RESTORE_TEST_DSN")
TEST_DB = f"restore_snapshot_{os.getpid()}_test"

SEGMENT_WKT = "LINESTRING(105.7610 21.0214, 105.7615 21.0216)"


def config_of(dsn: str) -> dict:
    return psycopg2.extensions.parse_dsn(dsn)


class GuardTests(unittest.TestCase):
    def test_a_name_without_the_suffix_is_refused(self):
        with self.assertRaises(ValueError):
            restore_snapshot.check_test_database("minio_custom", "minio_custom")

    def test_the_production_name_is_refused_even_with_the_suffix(self):
        with self.assertRaises(ValueError):
            restore_snapshot.check_test_database("flood_test", "flood_test")

    def test_a_test_name_passes(self):
        restore_snapshot.check_test_database("minio_custom_test", "minio_custom")


class ManifestTests(unittest.TestCase):
    def read(self, tables):
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = Path(tmp) / "snapshot"
            snapshot.mkdir()
            entries = [
                {"file": f"snapshot/{table}.csv.gz", "table": table, "columns": ["a"], "rows": 1, "sha256": "x"}
                for table in tables
            ]
            (snapshot / "MANIFEST.json").write_text(json.dumps({"tables": entries}))
            return [file.table for file in restore_snapshot.read_manifest(snapshot)]

    def test_a_table_beyond_the_order_is_left_out_of_the_files_to_load(self):
        listed = [*reversed(restore_snapshot.RESTORE_ORDER), "retired_a", "retired_b"]
        self.assertEqual(self.read(listed), list(restore_snapshot.RESTORE_ORDER))

    def test_a_table_of_the_order_missing_from_the_manifest_is_refused(self):
        with self.assertRaises(ValueError):
            self.read(restore_snapshot.RESTORE_ORDER[1:])


@unittest.skipUnless(DSN, "RESTORE_TEST_DSN is not set")
class RestoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.admin = config_of(DSN)
        cls.production = cls.admin["dbname"]
        cls.config = {k: v for k, v in cls.admin.items() if k != "dbname"} | {"database": cls.production}
        restore_snapshot.ensure_database(cls.config, TEST_DB, cls.production)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.snapshot_dir = Path(cls.tmp.name) / "snapshot"
        cls.snapshot_dir.mkdir()
        cls.expected = cls.write_snapshot(cls.snapshot_dir)

    @classmethod
    def tearDownClass(cls):
        conn = psycopg2.connect(**cls.config)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(TEST_DB)))
        conn.close()
        cls.tmp.cleanup()

    @classmethod
    def write_snapshot(cls, snapshot_dir: Path) -> dict:
        """Fills the restored tables of a source database, exports them as US-124 did, and returns their rows."""
        source_name = f"restore_snapshot_{os.getpid()}_source_test"
        restore_snapshot.check_test_database(source_name, cls.production)
        admin = psycopg2.connect(**cls.config)
        admin.autocommit = True
        with admin.cursor() as cur:
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(source_name)))
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(source_name)))
        admin.close()

        source = psycopg2.connect(**{**cls.config, "database": source_name})
        restore_snapshot.create_schema(source, restore_snapshot.POSTGIS_DDL)
        with source.cursor() as cur:
            cur.execute(
                "INSERT INTO flood_segment_metrics (id, run_ts, segment_key, road_name, vehicle_type, impassable_from_m,"
                " window_start, window_end, passability, geom_4326)"
                " VALUES (40, '20261010T041500', 'k1', 'Đường \"A\", số 1', 'car', 0.3, '2026-10-10 04:15',"
                " '2026-10-10 06:15', 'never_impassable', ST_GeomFromText(%s, 4326)),"
                " (41, '20261010T041500', 'k2', NULL, 'car', 0.3, '2026-10-10 04:15', '2026-10-10 06:15',"
                " 'never_impassable', ST_GeomFromText(%s, 4326))",
                (SEGMENT_WKT, SEGMENT_WKT),
            )
            cur.execute("INSERT INTO graph_edge (edge_id, length_m, geom) VALUES (1, 55.5, ST_GeomFromText(%s, 4326))", (SEGMENT_WKT,))
            cur.execute("INSERT INTO graph_edge_export (graph_hash, edge_count) VALUES ('abc', 1)")
            cur.execute("INSERT INTO flood_extent_step (run_ts, valid_time_utc, is_empty) VALUES ('20261010T041500', '2026-10-09 21:15', true)")
        source.commit()

        tables, rows = [], {}
        for table in restore_snapshot.RESTORE_ORDER:
            with source.cursor() as cur:
                cur.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position",
                    (table,),
                )
                columns = [row[0] for row in cur.fetchall() if row[0] != "edge_key"]
                path = snapshot_dir / f"{table}.csv.gz"
                with gzip.open(path, "wt", encoding="utf-8", newline="") as out:
                    cur.copy_expert(
                        sql.SQL("COPY {} ({}) TO STDOUT WITH (FORMAT csv, HEADER true)").format(
                            sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns))
                        ),
                        out,
                    )
                cur.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table)))
                count = cur.fetchone()[0]
                cur.execute(
                    sql.SQL("SELECT {} FROM {} ORDER BY 1::text").format(
                        sql.SQL(", ").join(sql.SQL("{}::text").format(sql.Identifier(c)) for c in columns), sql.Identifier(table)
                    )
                )
                rows[table] = cur.fetchall()
            tables.append(
                {
                    "file": f"snapshot/{table}.csv.gz",
                    "table": table,
                    "columns": columns,
                    "rows": count,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        source.close()
        (snapshot_dir / "MANIFEST.json").write_text(json.dumps({"tables": tables}))
        admin = psycopg2.connect(**cls.config)
        admin.autocommit = True
        with admin.cursor() as cur:
            cur.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(source_name)))
        admin.close()
        return rows

    def connect(self):
        return psycopg2.connect(**{**self.config, "database": TEST_DB})

    def restored_rows(self, conn, table: str, columns) -> list:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT {} FROM {} ORDER BY 1::text").format(
                    sql.SQL(", ").join(sql.SQL("{}::text").format(sql.Identifier(c)) for c in columns), sql.Identifier(table)
                )
            )
            return cur.fetchall()

    def restore(self):
        files = restore_snapshot.read_manifest(self.snapshot_dir)
        restore_snapshot.verify_files(files)
        conn = self.connect()
        try:
            restore_snapshot.create_schema(conn, restore_snapshot.POSTGIS_DDL)
            counts = restore_snapshot.load_snapshot(conn, files)
        finally:
            conn.close()
        return files, counts

    def test_every_table_has_the_rows_of_the_snapshot(self):
        files, counts = self.restore()
        self.assertEqual(restore_snapshot.check_counts(files, counts), [])
        conn = self.connect()
        for file in files:
            self.assertEqual(self.restored_rows(conn, file.table, file.columns), self.expected[file.table], file.table)
        conn.close()

    def test_a_second_restore_gives_the_same_counts(self):
        _, first = self.restore()
        _, second = self.restore()
        self.assertEqual(first, second)
        self.assertEqual(first["flood_segment_metrics"], 2)

    def test_the_serial_columns_continue_after_the_restored_ids(self):
        self.restore()
        conn = self.connect()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO flood_segment_metrics (run_ts, segment_key, vehicle_type, impassable_from_m, window_start,"
                " window_end, passability, geom_4326) VALUES ('next', 'k3', 'car', 0.3, '2026-10-11 00:00',"
                " '2026-10-11 02:00', 'never_impassable', ST_GeomFromText(%s, 4326)) RETURNING id",
                (SEGMENT_WKT,),
            )
            self.assertEqual(cur.fetchone()[0], 42)
        conn.rollback()
        conn.close()

    def test_a_changed_file_is_refused_before_anything_loads(self):
        files = restore_snapshot.read_manifest(self.snapshot_dir)
        path = self.snapshot_dir / "graph_edge.csv.gz"
        original = path.read_bytes()
        try:
            path.write_bytes(original + b"x")
            with self.assertRaises(ValueError):
                restore_snapshot.verify_files(files)
        finally:
            path.write_bytes(original)

    def test_a_failed_load_keeps_the_previous_rows(self):
        files, _ = self.restore()
        broken = self.snapshot_dir / "flood_extent_step.csv.gz"
        original = broken.read_bytes()
        try:
            with gzip.open(broken, "wt", encoding="utf-8") as out:
                out.write("run_ts,valid_time_utc,is_empty,published_at\nr,not a time,true,\n")
            conn = self.connect()
            with self.assertRaises(psycopg2.Error):
                restore_snapshot.load_snapshot(conn, files)
            conn.rollback()
            self.assertEqual(restore_snapshot.table_counts(conn, ["flood_segment_metrics"])["flood_segment_metrics"], 2)
            conn.close()
        finally:
            broken.write_bytes(original)

    def test_the_production_database_is_not_touched(self):
        conn = psycopg2.connect(**self.config)
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('flood_segment_metrics')")
            before = cur.fetchone()[0]
        conn.close()
        self.restore()
        conn = psycopg2.connect(**self.config)
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('flood_segment_metrics')")
            self.assertEqual(cur.fetchone()[0], before)
        conn.close()

    def test_a_manifest_with_another_table_is_refused(self):
        manifest = json.loads((self.snapshot_dir / "MANIFEST.json").read_text())
        manifest["tables"][0]["table"] = "other"
        other = Path(self.tmp.name) / "other" / "snapshot"
        other.mkdir(parents=True)
        (other / "MANIFEST.json").write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            restore_snapshot.read_manifest(other)


if __name__ == "__main__":
    unittest.main()
