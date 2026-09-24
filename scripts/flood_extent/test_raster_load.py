import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import numpy as np
import psycopg2
from osgeo import gdal, osr

import create_flood_depth_raster_tables
import raster_load

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
            cur.execute("TRUNCATE flood_depth_raster_tile;")

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


if __name__ == "__main__":
    unittest.main()
