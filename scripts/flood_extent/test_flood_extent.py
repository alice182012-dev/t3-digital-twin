import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from osgeo import ogr, osr

import flood_extent


def square(x, y, size):
    return f"POLYGON(({x} {y},{x + size} {y},{x + size} {y + size},{x} {y + size},{x} {y}))"


class DissolveTests(unittest.TestCase):
    # Band 10 has no polygons, so the merge must not take its schema from an empty part.
    POLYGONS = [
        (0, square(0, 0, 50)),
        (20, square(0, 0, 10)),
        (20, square(5, 5, 10)),
        (30, square(100, 0, 10)),
        (30, square(200, 0, 10)),
        (30, square(204, 4, 2)),
        (600, square(300, 0, 20)),
    ]

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pipeline = flood_extent.Pipeline("depth.tif", "tiles", 1, 8, 20, 10, 16)
        self.pipeline.bind(self.tmp.name)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(32648)
        dataset = ogr.GetDriverByName("GPKG").CreateDataSource(str(self.pipeline.poly))
        layer = dataset.CreateLayer("poly", srs=srs, geom_type=ogr.wkbPolygon)
        layer.CreateField(ogr.FieldDefn("DN", ogr.OFTInteger))
        for code, wkt in self.POLYGONS:
            feature = ogr.Feature(layer.GetLayerDefn())
            feature.SetField("DN", code)
            feature.SetGeometry(ogr.CreateGeometryFromWkt(wkt))
            layer.CreateFeature(feature)
        dataset = None

    def read(self, path):
        dataset = ogr.Open(str(path))
        self.assertEqual(dataset.GetLayerCount(), 1)
        layer = dataset.GetLayer()
        rows = [(f.GetField("DN"), round(f.GetGeometryRef().GetArea(), 6)) for f in layer]
        return layer.GetName(), layer.GetSpatialRef().GetAuthorityCode(None), rows

    def test_unions_each_band_like_the_single_group_by_query(self):
        reference = Path(self.tmp.name) / "reference.gpkg"
        flood_extent.Pipeline.run(
            "ogr2ogr", "-q", "-f", "GPKG", reference, self.pipeline.poly, "-dialect", "SQLite",
            "-sql", "SELECT DN, ST_Union(geom) AS geom FROM poly WHERE DN > 0 GROUP BY DN",
            "-nln", "dissolved")

        self.pipeline.dissolve()

        expected = ("dissolved", "32648", [(20, 175.0), (30, 200.0), (600, 400.0)])
        self.assertEqual(self.read(reference), expected)
        self.assertEqual(self.read(self.pipeline.dissolved), expected)

    def test_a_failing_band_raises_flood_extent_error(self):
        self.pipeline.poly.unlink()

        with self.assertRaisesRegex(flood_extent.FloodExtentError, r"^ogr2ogr -q failed \(1\): "):
            self.pipeline.dissolve()


class RunTsForDepthDirTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def touch(self, *names):
        for name in names:
            (self.root / name).write_text("x")

    def test_names_the_run_after_the_earliest_depth_file(self):
        self.touch(
            "depth_20260924_180639.tif",
            "depth_20260924_170639.tif",
            "depth_20260924_174639.tif",
            "depth_20260101_000000.tif.aux.xml",
            "depth_summary.csv",
        )

        self.assertEqual(flood_extent.run_ts_for_depth_dir(self.root), "20260924T170639")

    def test_accepts_the_folder_as_a_string(self):
        self.touch("depth_20260811_014000.tif")

        self.assertEqual(flood_extent.run_ts_for_depth_dir(str(self.root)), "20260811T014000")

    def test_rejects_a_folder_with_no_depth_file(self):
        self.touch("depth_20260101_000000.tif.aux.xml")

        with self.assertRaises(flood_extent.FloodExtentError):
            flood_extent.run_ts_for_depth_dir(self.root)


if __name__ == "__main__":
    unittest.main()
