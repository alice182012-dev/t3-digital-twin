import os
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import publish
import flood_extent


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
