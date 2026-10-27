import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import numpy as np
import psycopg2
from osgeo import gdal, osr

import create_demo_pin_table
import create_flood_depth_raster_tables
import create_flood_run_output_table
import raster_load
from test_run_output import FakeConnection, published

gdal.UseExceptions()


def write_synthetic_depth_tif(path: Path) -> None:
    """A tiny single-band raster in VN-2000 / UTM zone 48N (EPSG:3405), the same source SRID
    calculate_depth.py's real depth_*.tif files ship in (see raster_load's module docstring)."""
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3405)

    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(str(path), 4, 4, 1, gdal.GDT_Float32)
    ds.SetGeoTransform([583000.0, 10.0, 0.0, 2327000.0, 0.0, -10.0])
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    band.WriteArray(
        np.array(
            [
                [0.0, 0.0, 0.0, 0.0],
                [0.0, 1.5, 1.5, 0.0],
                [0.0, 1.5, 1.5, 0.0],
                [0.0, 0.0, 0.0, 0.0],
            ],
            dtype=np.float32,
        )
    )
    band.SetNoDataValue(0)
    ds.FlushCache()
    ds = None


class ReprojectTo4326Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / "depth_20260704_170000.tif"
        write_synthetic_depth_tif(self.src)

    def test_reprojects_native_srid_to_4326(self):
        dst = self.root / "reprojected.tif"
        raster_load.reproject_to_4326(self.src, dst)

        ds = gdal.Open(str(dst))
        srs = osr.SpatialReference(wkt=ds.GetProjection())
        self.assertEqual(srs.GetAuthorityCode(None), "4326")

    def test_preserves_pixel_values(self):
        dst = self.root / "reprojected.tif"
        raster_load.reproject_to_4326(self.src, dst)

        ds = gdal.Open(str(dst))
        band = ds.GetRasterBand(1)
        arr = band.ReadAsArray()
        # Nearest-neighbour resampling into a new grid shifts pixel boundaries, but the flooded
        # value itself (1.5) must still be present somewhere, and dry cells (0.0) still dominate.
        self.assertIn(1.5, arr)
        self.assertGreater((arr == 0.0).sum(), (arr == 1.5).sum())


def write_depth_grid_tif(path: Path, size: int) -> None:
    """A size x size EPSG:3405 raster with a distinct value per pixel, so a tile placed one
    position off fails an equality check."""
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3405)
    ds = gdal.GetDriverByName("GTiff").Create(str(path), size, size, 1, gdal.GDT_Float32)
    ds.SetGeoTransform([583000.0, 10.0, 0.0, 2327000.0, 0.0, -10.0])
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    band.WriteArray((np.arange(size * size, dtype=np.float32).reshape(size, size) + 1) * 0.01)
    band.SetNoDataValue(0)
    ds.FlushCache()
    ds = None


def fake_reproject(src, dst):
    Path(dst).write_bytes(b"warped")


def depth_files(root: Path, run: str, names=("depth_20260925_173000.tif",)) -> Path:
    (root / run).mkdir()
    for name in names:
        (root / run / name).write_bytes(b"")
    return root / run


class OverlappingRunsTests(unittest.TestCase):
    def test_a_run_loading_the_same_valid_time_keeps_the_other_runs_work_file(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        run_k, run_k1 = depth_files(root, "run_k"), depth_files(root, "run_k1")
        work_dir = root / "work"
        read_back = {}

        def write_tiles(cur, run_ts, valid_time, raster_path):
            if run_ts == "20260925T171500":
                raster_load.load_run(FakeConnection(), run_k1, "20260925T173000", work_dir, keep_runs=8)
            read_back[run_ts] = Path(raster_path).exists()

        with mock.patch.object(raster_load, "reproject_to_4326", fake_reproject), \
                mock.patch.object(raster_load, "write_tiles", write_tiles):
            raster_load.load_run(FakeConnection(), run_k, "20260925T171500", work_dir, keep_runs=8)

        self.assertEqual(read_back, {"20260925T173000": True, "20260925T171500": True})
        self.assertEqual(list(work_dir.iterdir()), [])


class DepthRasterRunOutputTests(unittest.TestCase):
    """The depth_raster row of flood_run_output commits with the run's last tiles, and only then."""

    STEPS = ("depth_20260925_173000.tif", "depth_20260925_174500.tif")

    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.depth_dir = depth_files(self.root, "run", self.STEPS)

    def load(self, conn, reproject=fake_reproject):
        with mock.patch.object(raster_load, "reproject_to_4326", reproject):
            return raster_load.load_run(conn, self.depth_dir, "20260925T173000", self.root / "work", keep_runs=8)

    def committed_tile_steps(self, conn):
        return [params["valid_time_utc"].strftime("%H:%M") for sql, params in conn.committed
                if sql is raster_load._INSERT_TILES_SQL]

    def test_a_loaded_run_records_its_depth_raster_row(self):
        conn = FakeConnection()

        self.load(conn)

        self.assertEqual(self.committed_tile_steps(conn), ["10:30", "10:45"])
        self.assertEqual(published(conn), {("20260925T173000", "depth_raster")})

    def test_a_timestep_that_fails_to_reproject_leaves_no_row(self):
        def reproject(src, dst):
            if src.name == self.STEPS[1]:
                raise RuntimeError("gdal.Warp failed")
            fake_reproject(src, dst)

        conn = FakeConnection()

        with self.assertRaises(RuntimeError):
            self.load(conn, reproject)

        self.assertEqual(self.committed_tile_steps(conn), ["10:30"])
        self.assertEqual(published(conn), set())

    def test_a_last_timestep_whose_tiles_fail_to_insert_leaves_no_row(self):
        inserts = []

        def rows(sql):
            if sql is raster_load._INSERT_TILES_SQL:
                inserts.append(sql)
                if len(inserts) == 2:
                    raise psycopg2.DataError("Could not open bytea with GDAL")
            return ()

        conn = FakeConnection(rows)

        with self.assertRaises(psycopg2.DataError):
            self.load(conn)

        self.assertEqual(self.committed_tile_steps(conn), ["10:30"])
        self.assertEqual(published(conn), set())


@unittest.skipUnless(os.environ.get("FLOOD_TEST_DSN"), "FLOOD_TEST_DSN unset")
class LoadRunTests(unittest.TestCase):
    """Runs against a real PostGIS with postgis_raster, the same database test_server.py uses."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.conn = psycopg2.connect(os.environ["FLOOD_TEST_DSN"])
        self.addCleanup(self.conn.close)
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SET TIME ZONE 'UTC';")
            cur.execute(create_flood_depth_raster_tables.SQL)
            cur.execute(create_flood_run_output_table.SQL)
            cur.execute("TRUNCATE flood_depth_raster_tile, flood_run_output;")

    def depth_dir(self, run: str, size: int) -> Path:
        path = self.root / run
        path.mkdir()
        write_depth_grid_tif(path / "depth_20260704_170000.tif", size)
        return path

    def tile_rows(self, run: str) -> list[tuple]:
        with self.conn, self.conn.cursor() as cur:
            cur.execute(
                "SELECT tile_x, tile_y, ST_Width(rast), ST_Height(rast), md5(ST_AsBinary(rast))"
                " FROM flood_depth_raster_tile WHERE run_ts = %s ORDER BY tile_y, tile_x;",
                (run,),
            )
            return cur.fetchall()

    def runs(self) -> list[str]:
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT DISTINCT run_ts FROM flood_depth_raster_tile ORDER BY run_ts;")
            return [row[0] for row in cur.fetchall()]

    def test_tiles_hold_the_reprojected_raster_at_their_positions(self):
        depth_dir = self.depth_dir("20260704T100000", 600)
        warped = self.root / "warped.tif"
        raster_load.reproject_to_4326(depth_dir / "depth_20260704_170000.tif", warped)
        warped_ds = gdal.Open(str(warped))
        expected = warped_ds.GetRasterBand(1).ReadAsArray()
        tiles_x = -(-expected.shape[1] // raster_load.TILE_SIZE)
        tiles_y = -(-expected.shape[0] // raster_load.TILE_SIZE)

        loaded = raster_load.load_run(self.conn, depth_dir, "20260704T100000", self.root / "work")

        self.assertEqual(len(loaded), 1)
        with self.conn, self.conn.cursor() as cur:
            cur.execute(
                "SELECT tile_x, tile_y, ST_DumpValues(rast, 1, false)"
                " FROM flood_depth_raster_tile WHERE run_ts = '20260704T100000';"
            )
            tiles = cur.fetchall()
        self.assertEqual(
            sorted((x, y) for x, y, _ in tiles),
            [(x, y) for x in range(tiles_x) for y in range(tiles_y)],
        )
        self.assertGreater(len(tiles), 1)
        size = raster_load.TILE_SIZE
        for x, y, values in tiles:
            np.testing.assert_array_equal(
                np.array(values, dtype=np.float32),
                expected[y * size:(y + 1) * size, x * size:(x + 1) * size],
                err_msg=f"tile ({x}, {y})",
            )

    def test_a_loaded_run_has_one_depth_raster_row_after_two_loads(self):
        depth_dir = self.depth_dir("20260704T100000", 4)

        raster_load.load_run(self.conn, depth_dir, "20260704T100000", self.root / "work")
        raster_load.load_run(self.conn, depth_dir, "20260704T100000", self.root / "work")

        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT run_ts, output FROM flood_run_output;")
            self.assertEqual(cur.fetchall(), [("20260704T100000", "depth_raster")])

    def test_loading_a_timestep_twice_gives_the_same_rows(self):
        depth_dir = self.depth_dir("20260704T100000", 600)
        raster_load.load_run(self.conn, depth_dir, "20260704T100000", self.root / "work")
        first = self.tile_rows("20260704T100000")

        raster_load.load_run(self.conn, depth_dir, "20260704T100000", self.root / "work")

        self.assertEqual(self.tile_rows("20260704T100000"), first)

    def test_prune_keeps_the_newest_runs(self):
        for run in ["20260701T000000", "20260702T000000", "20260703T000000", "20260704T000000"]:
            with mock.patch.dict(os.environ, {"FLOOD_RASTER_KEEP_RUNS": "10"}):
                raster_load.load_run(self.conn, self.depth_dir(run, 4), run, self.root / "work")

        with mock.patch.dict(os.environ, {"FLOOD_RASTER_KEEP_RUNS": "3"}):
            raster_load.load_run(self.conn, self.depth_dir("20260705T000000", 4), "20260705T000000", self.root / "work")

        self.assertEqual(self.runs(), ["20260703T000000", "20260704T000000", "20260705T000000"])

    def test_prune_never_deletes_the_run_being_loaded(self):
        for run in ["20260703T000000", "20260704T000000", "20260705T000000"]:
            raster_load.load_run(self.conn, self.depth_dir(run, 4), run, self.root / "work")

        with mock.patch.dict(os.environ, {"FLOOD_RASTER_KEEP_RUNS": "3"}):
            raster_load.load_run(self.conn, self.depth_dir("20260601T000000", 4), "20260601T000000", self.root / "work")

        self.assertEqual(
            self.runs(), ["20260601T000000", "20260703T000000", "20260704T000000", "20260705T000000"]
        )

    def test_prune_never_deletes_the_pinned_run(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(create_demo_pin_table.SQL)
            cur.execute("TRUNCATE demo_pin")
        for run in ["20260701T000000", "20260703T000000", "20260704T000000"]:
            raster_load.load_run(self.conn, self.depth_dir(run, 4), run, self.root / "work", keep_runs=10)
        with self.conn, self.conn.cursor() as cur:
            cur.execute("INSERT INTO demo_pin (run_ts, valid_time_utc, wet_edges) VALUES ('20260701T000000', '2026-07-01', 1)")

        raster_load.load_run(self.conn, self.depth_dir("20260705T000000", 4), "20260705T000000", self.root / "work", keep_runs=2)

        self.assertEqual(self.runs(), ["20260701T000000", "20260704T000000", "20260705T000000"])

    def test_keep_runs_argument_overrides_the_environment(self):
        for run in ["20260701T000000", "20260702T000000", "20260703T000000", "20260704T000000"]:
            raster_load.load_run(self.conn, self.depth_dir(run, 4), run, self.root / "work", keep_runs=10)

        with mock.patch.dict(os.environ, {"FLOOD_RASTER_KEEP_RUNS": "1"}):
            raster_load.load_run(
                self.conn, self.depth_dir("20260705T000000", 4), "20260705T000000", self.root / "work", keep_runs=1000
            )

        self.assertEqual(
            self.runs(),
            ["20260701T000000", "20260702T000000", "20260703T000000", "20260704T000000", "20260705T000000"],
        )

    def test_two_loads_under_one_run_name_keep_both_sets_of_timesteps(self):
        first, second = self.root / "event1", self.root / "event2"
        first.mkdir()
        second.mkdir()
        write_depth_grid_tif(first / "depth_20260704_170000.tif", 4)
        write_depth_grid_tif(second / "depth_20260704_190000.tif", 4)

        raster_load.load_run(self.conn, first, "20260704T170000", self.root / "work", keep_runs=1000)
        raster_load.load_run(self.conn, second, "20260704T170000", self.root / "work", keep_runs=1000)

        with self.conn, self.conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT valid_time_utc::text FROM flood_depth_raster_tile"
                " WHERE run_ts = '20260704T170000' ORDER BY 1;"
            )
            self.assertEqual([row[0] for row in cur.fetchall()], ["2026-07-04 10:00:00", "2026-07-04 12:00:00"])


if __name__ == "__main__":
    unittest.main()
