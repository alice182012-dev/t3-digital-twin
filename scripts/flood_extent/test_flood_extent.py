import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import flood_extent


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
