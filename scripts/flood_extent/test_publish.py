import os
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import psycopg2
from shapely.geometry import box

import create_flood_extent_tables
import publish
import flood_extent

RUN = "20260925T171500"
# Vietnam-local depth file names; 17:15, 17:30, 17:45 local are 10:15, 10:30, 10:45 UTC.
DEPTH_FILES = ["depth_20260925_171500.tif", "depth_20260925_173000.tif", "depth_20260925_174500.tif"]
STEP_1, STEP_2, STEP_3 = (flood_extent.stamp_key(name) for name in DEPTH_FILES)
UTC_1, UTC_2 = datetime(2026, 9, 25, 10, 15), datetime(2026, 9, 25, 10, 30)


class FakeS3:
    """Records uploaded keys. The bucket starts empty, so pruning has nothing to list."""

    def __init__(self):
        self.keys = []

    def upload_file(self, path, bucket, key, ExtraArgs=None):
        self.keys.append(key)

    def get_paginator(self, name):
        return self

    def paginate(self, **kwargs):
        return []


def fake_build(dry=(), failing=()):
    """Stands in for flood_extent.build_flood_extent: one tile and one band polygon per wet step."""

    def build(depth_file, tiles_dir, **options):
        stamp = flood_extent.stamp_key(depth_file)
        if stamp in failing:
            raise flood_extent.FloodExtentError("build failed")
        if stamp in dry:
            return flood_extent.FloodExtentResult(tile_count=0)
        tile = Path(tiles_dir) / "10" / "1" / "2.pbf"
        tile.parent.mkdir(parents=True)
        tile.write_bytes(b"pbf")
        return flood_extent.FloodExtentResult(
            tile_count=1, area_by_band={1: 50.0}, polygons_4326={1: box(105.8, 21.0, 105.9, 21.1).wkb}
        )

    return build


class PublishRunTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.s3 = FakeS3()

    def publish(self, run=RUN, build=None, **options):
        depth_dir = self.root / "depth" / run
        depth_dir.mkdir(parents=True, exist_ok=True)
        for name in reversed(DEPTH_FILES):
            (depth_dir / name).write_bytes(b"")
        with mock.patch.object(flood_extent, "build_flood_extent", build or fake_build()):
            return publish.publish_run(depth_dir, run, self.root / "work", self.s3, "bucket", **options)


class PublishRunTileStepsTests(PublishRunTestCase):
    def test_builds_only_the_first_tile_steps_by_time(self):
        results = self.publish(tile_steps=2)

        self.assertEqual(sorted(results), [STEP_1, STEP_2])
        self.assertEqual(
            sorted(self.s3.keys), [f"runs/{RUN}/{STEP_1}/10/1/2.pbf", f"runs/{RUN}/{STEP_2}/10/1/2.pbf"]
        )

    def test_defaults_to_two_steps(self):
        self.assertEqual(sorted(self.publish()), [STEP_1, STEP_2])

    def test_rejects_tile_steps_below_one(self):
        with self.assertRaises(ValueError):
            self.publish(tile_steps=0)


@unittest.skipUnless(os.environ.get("FLOOD_TEST_DSN"), "FLOOD_TEST_DSN unset")
class PublishRunStepRowTests(PublishRunTestCase):
    """Runs against a real PostGIS: the polygon rows go through ST_GeomFromWKB."""

    def setUp(self):
        super().setUp()
        self.conn = psycopg2.connect(os.environ["FLOOD_TEST_DSN"])
        self.addCleanup(self.conn.close)
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'UTC';")
            # Dropped, not truncated: test_flood_extent_runs.py leaves a geom-less flood_extent_polygon
            # in the same database, which CREATE TABLE IF NOT EXISTS would keep.
            cur.execute("DROP TABLE IF EXISTS flood_extent_polygon, flood_extent_step;")
            cur.execute(create_flood_extent_tables.SQL)
            cur.execute(create_flood_extent_tables.SQL)

    def fetch(self, sql):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()

    def test_writes_a_step_row_for_wet_and_dry_steps(self):
        self.publish(build=fake_build(dry={STEP_2}), db_conn=self.conn)

        self.assertEqual(
            self.fetch("SELECT run_ts, valid_time_utc, is_empty FROM flood_extent_step ORDER BY valid_time_utc;"),
            [(RUN, UTC_1, False), (RUN, UTC_2, True)],
        )
        self.assertEqual(
            self.fetch("SELECT run_ts, valid_time_utc, dn_code FROM flood_extent_polygon;"), [(RUN, UTC_1, 1)]
        )

    def test_republishing_a_step_keeps_one_row_per_step(self):
        self.publish(db_conn=self.conn)
        self.publish(build=fake_build(dry={STEP_1}), db_conn=self.conn)

        self.assertEqual(
            self.fetch("SELECT valid_time_utc, is_empty FROM flood_extent_step ORDER BY valid_time_utc;"),
            [(UTC_1, True), (UTC_2, False)],
        )

    def test_a_failed_step_gets_no_step_row_and_the_run_raises(self):
        with self.assertRaises(flood_extent.FloodExtentError):
            self.publish(build=fake_build(failing={STEP_2}), db_conn=self.conn)

        self.assertEqual(self.fetch("SELECT valid_time_utc FROM flood_extent_step;"), [(UTC_1,)])

    def test_a_failed_step_write_does_not_stop_the_next_steps_write(self):
        build = fake_build()

        def build_with_bad_polygon(depth_file, tiles_dir, **options):
            result = build(depth_file, tiles_dir, **options)
            if flood_extent.stamp_key(depth_file) == STEP_1:
                return flood_extent.FloodExtentResult(
                    tile_count=1, area_by_band={1: 50.0}, polygons_4326={1: b"not wkb"}
                )
            return result

        with self.assertRaises(flood_extent.FloodExtentError):
            self.publish(build=build_with_bad_polygon, db_conn=self.conn)

        self.assertEqual(self.fetch("SELECT valid_time_utc FROM flood_extent_step;"), [(UTC_2,)])

    def test_keeps_the_step_rows_of_only_the_newest_keep_runs(self):
        for run in ("20260925T170000", "20260925T171500", "20260925T173000"):
            self.publish(run=run, db_conn=self.conn, keep_runs=2)

        self.assertEqual(
            self.fetch("SELECT DISTINCT run_ts FROM flood_extent_step ORDER BY run_ts;"),
            [("20260925T171500",), ("20260925T173000",)],
        )

    def test_keeps_the_polygon_rows_of_only_the_newest_keep_runs(self):
        for run in ("20260925T170000", "20260925T171500", "20260925T173000"):
            self.publish(run=run, db_conn=self.conn, keep_runs=2)

        self.assertEqual(
            self.fetch("SELECT DISTINCT run_ts FROM flood_extent_polygon ORDER BY run_ts;"),
            [("20260925T171500",), ("20260925T173000",)],
        )


@unittest.skipUnless(os.environ.get("FLOOD_TEST_DSN"), "FLOOD_TEST_DSN unset")
class StepBackfillTests(unittest.TestCase):
    """create_flood_extent_tables.SQL lists runs published before flood_extent_step existed."""

    RUNS = ("20260925T160000", "20260925T163000", "20260925T170000", "20260925T173000")

    def setUp(self):
        self.conn = psycopg2.connect(os.environ["FLOOD_TEST_DSN"])
        self.addCleanup(self.conn.close)
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'UTC';")
            cur.execute("DROP TABLE IF EXISTS flood_extent_polygon, flood_extent_step;")
            cur.execute(create_flood_extent_tables.SQL)
            for run in self.RUNS:
                for valid_time in (UTC_1, UTC_2):
                    for dn_code in (1, 2):
                        cur.execute(
                            "INSERT INTO flood_extent_polygon (run_ts, valid_time_utc, dn_code, area_m2, geom)"
                            " VALUES (%s, %s, %s, 1.0, ST_GeomFromText('POINT(105.8 21.0)', 4326));",
                            (run, valid_time, dn_code),
                        )

    def ensure_schema(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(create_flood_extent_tables.SQL)

    def steps(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT run_ts, valid_time_utc, is_empty FROM flood_extent_step ORDER BY 1, 2;")
            return cur.fetchall()

    def test_lists_each_wet_step_of_the_newest_three_runs(self):
        self.ensure_schema()

        self.assertEqual(
            self.steps(),
            [(run, time, False) for run in self.RUNS[1:] for time in (UTC_1, UTC_2)],
        )

    def test_a_later_call_does_not_bring_back_pruned_steps(self):
        self.ensure_schema()
        with self.conn, self.conn.cursor() as cur:
            cur.execute("DELETE FROM flood_extent_step WHERE run_ts = %s;", (self.RUNS[1],))

        self.ensure_schema()

        self.assertEqual(
            self.steps(),
            [(run, time, False) for run in self.RUNS[2:] for time in (UTC_1, UTC_2)],
        )


class PrunePolygonRowsNoDbTests(unittest.TestCase):
    def test_does_nothing_when_db_conn_is_none(self):
        # Matches prune_step_rows's own no-op: publish_run can call this unconditionally even
        # when no db_conn was passed in (db_conn is an optional kwarg, default None).
        publish.prune_polygon_rows(None, keep_runs=3, always_keep="20260925T171500")


@unittest.skipUnless(os.environ.get("FLOOD_TEST_DSN"), "FLOOD_TEST_DSN unset")
class PrunePolygonRowsTests(unittest.TestCase):
    """Calls prune_polygon_rows directly against rows inserted by raw SQL, rather than through
    publish_run, so always_keep can be an older run than the newest keep_runs — a case
    publish_run itself never actually produces (the run it is publishing is always the newest
    insert) but the function's own contract promises regardless, the same way prune_step_rows
    does."""

    RUNS = ("20260925T160000", "20260925T170000", "20260925T173000", "20260925T180000")

    def setUp(self):
        self.conn = psycopg2.connect(os.environ["FLOOD_TEST_DSN"])
        self.addCleanup(self.conn.close)
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'UTC';")
            cur.execute("DROP TABLE IF EXISTS flood_extent_polygon, flood_extent_step;")
            cur.execute(create_flood_extent_tables.SQL)
            for run in self.RUNS:
                cur.execute(
                    "INSERT INTO flood_extent_polygon (run_ts, valid_time_utc, dn_code, area_m2, geom)"
                    " VALUES (%s, %s, 1, 1.0, ST_GeomFromText('POINT(105.8 21.0)', 4326));",
                    (run, UTC_1),
                )

    def runs(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT DISTINCT run_ts FROM flood_extent_polygon ORDER BY run_ts;")
            return [row[0] for row in cur.fetchall()]

    def test_keeps_only_the_newest_keep_runs(self):
        publish.prune_polygon_rows(self.conn, keep_runs=2, always_keep="20260925T173000")

        self.assertEqual(self.runs(), ["20260925T173000", "20260925T180000"])

    def test_always_keep_survives_even_outside_the_window(self):
        publish.prune_polygon_rows(self.conn, keep_runs=1, always_keep="20260925T160000")

        self.assertEqual(self.runs(), ["20260925T160000", "20260925T180000"])


class ValidTimeUtcTests(unittest.TestCase):
    def test_converts_vietnam_local_filename_to_utc(self):
        self.assertEqual(
            publish.valid_time_utc("depth_20260704_170000.tif"),
            datetime(2026, 7, 4, 10, 0, 0, tzinfo=timezone.utc),
        )

    def test_crosses_a_utc_day_boundary(self):
        self.assertEqual(
            publish.valid_time_utc("depth_20260704_030000.tif"),
            datetime(2026, 7, 3, 20, 0, 0, tzinfo=timezone.utc),
        )

    def test_rejects_a_filename_that_is_not_depth_tif(self):
        with self.assertRaises(flood_extent.FloodExtentError):
            publish.valid_time_utc("not_a_depth_file.tif")


class CleanupOldFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def age(self, path, hours):
        stamp = time.time() - hours * 3600
        os.utime(path, (stamp, stamp))

    def test_deletes_a_stale_loose_file_but_keeps_a_fresh_one(self):
        stale, fresh = self.root / "stale.tif", self.root / "fresh.tif"
        stale.write_text("x")
        fresh.write_text("x")
        self.age(stale, hours=25)

        publish.cleanup_old_files([self.root], max_age_hours=24)

        self.assertFalse(stale.exists())
        self.assertTrue(fresh.exists())

    def test_a_directory_ages_by_its_newest_file_not_its_own_mtime(self):
        run_dir = self.root / "run"
        run_dir.mkdir()
        old_file = run_dir / "old.tif"
        old_file.write_text("x")
        self.age(old_file, hours=25)
        # The directory itself was just created (fresh mtime), but its only file is stale.
        publish.cleanup_old_files([self.root], max_age_hours=24)

        self.assertFalse(run_dir.exists())

    def test_keeps_a_directory_with_any_recent_file(self):
        run_dir = self.root / "run"
        run_dir.mkdir()
        old_file, new_file = run_dir / "old.tif", run_dir / "new.tif"
        old_file.write_text("x")
        new_file.write_text("x")
        self.age(old_file, hours=25)

        publish.cleanup_old_files([self.root], max_age_hours=24)

        self.assertTrue(run_dir.exists())
        self.assertTrue(new_file.exists())

    def test_missing_root_is_not_an_error(self):
        publish.cleanup_old_files([self.root / "does-not-exist"], max_age_hours=24)


if __name__ == "__main__":
    unittest.main()
