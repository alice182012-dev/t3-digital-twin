import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from osgeo import gdal, osr

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


if __name__ == "__main__":
    unittest.main()
