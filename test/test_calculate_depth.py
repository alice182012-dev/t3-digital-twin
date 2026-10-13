import importlib.util
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import numpy as np

import conftest  # noqa: F401  # unittest does not load conftest.py on its own

ROOT = Path(__file__).resolve().parents[1]

try:
    from osgeo import gdal
except ImportError:
    gdal = None


def load_calculate_depth():
    fiona = types.ModuleType("fiona")
    fiona.vfs = types.ModuleType("fiona.vfs")
    gridresultadmin = types.ModuleType("threedigrid.admin.gridresultadmin")
    gridresultadmin.GridH5ResultAdmin = MagicMock()
    stubs = {
        "billiard": types.ModuleType("billiard"),
        "fiona": fiona,
        "fiona.vfs": fiona.vfs,
        "threedigrid": types.ModuleType("threedigrid"),
        "threedigrid.admin": types.ModuleType("threedigrid.admin"),
        "threedigrid.admin.gridresultadmin": gridresultadmin,
    }
    if gdal is None:
        osgeo = types.ModuleType("osgeo")
        osgeo.gdal = MagicMock()
        stubs["osgeo"] = osgeo
    spec = importlib.util.spec_from_file_location(
        "test_calculate_depth_module", ROOT / "scripts/calculate_depth.py"
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


calculate_depth = load_calculate_depth()


class RoundToMinuteTest(unittest.TestCase):
    def test_rounds_half_up_to_the_nearest_minute(self):
        cases = [
            (datetime(2026, 9, 26, 10, 15, 2), datetime(2026, 9, 26, 10, 15)),
            (datetime(2026, 9, 26, 10, 14, 59), datetime(2026, 9, 26, 10, 15)),
            (datetime(2026, 9, 26, 10, 15, 29), datetime(2026, 9, 26, 10, 15)),
            (datetime(2026, 9, 26, 10, 15, 30), datetime(2026, 9, 26, 10, 16)),
            (datetime(2026, 9, 26, 23, 59, 45), datetime(2026, 9, 27, 0, 0)),
        ]
        for given, expected in cases:
            with self.subTest(given=given):
                self.assertEqual(calculate_depth.round_to_minute(given), expected)


@unittest.skipIf(gdal is None, "osgeo.gdal is not installed")
class GetTimeFromTifTest(unittest.TestCase):
    def write_depth_tif(self, path, description):
        ds = gdal.GetDriverByName("GTiff").Create(str(path), 4, 4, 1, gdal.GDT_Float32)
        ds.SetGeoTransform((0, 1, 0, 0, 0, -1))
        band = ds.GetRasterBand(1)
        band.WriteArray(np.full((4, 4), 0.5, dtype=np.float32))
        band.SetNoDataValue(-9999)
        band.SetDescription(description)
        ds.FlushCache()
        ds = None

    def test_names_and_describes_a_drifted_step_on_the_whole_minute_in_vietnam_time(self):
        with TemporaryDirectory() as tmp:
            tif = Path(tmp) / "temp_0001.tif"
            self.write_depth_tif(tif, "waterdepth 2026-09-26 01:15:02")

            stamp = calculate_depth.get_time_from_tif_and_clean(str(tif))

            ds = gdal.Open(str(tif))
            description = ds.GetRasterBand(1).GetDescription()
            ds = None
        self.assertEqual(stamp, "20260926_081500")
        self.assertEqual(description, "waterdepth 2026-09-26 08:15:00")


if __name__ == "__main__":
    unittest.main()
