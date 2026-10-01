import os
import stat
import tempfile
import unittest

from depth_inputs import localize_input


class LocalizeInputTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.src_dir = os.path.join(self._tmp.name, "mount")
        self.cache_dir = os.path.join(self._tmp.name, "cache")
        os.makedirs(self.src_dir)
        self.src = os.path.join(self.src_dir, "dem.tif")
        with open(self.src, "wb") as f:
            f.write(b"dem-bytes-v1")
        os.utime(self.src, (1_700_000_000, 1_700_000_000))

    def tearDown(self):
        os.chmod(self.src_dir, stat.S_IRWXU)
        if os.path.isdir(self.cache_dir):
            os.chmod(self.cache_dir, stat.S_IRWXU)
        self._tmp.cleanup()

    def test_first_call_copies_into_cache_dir(self):
        local = localize_input(self.src, self.cache_dir)
        self.assertEqual(local, os.path.join(self.cache_dir, "dem.tif"))
        with open(local, "rb") as f:
            self.assertEqual(f.read(), b"dem-bytes-v1")
        self.assertEqual(int(os.stat(local).st_mtime), 1_700_000_000)
        self.assertEqual(os.listdir(self.cache_dir), ["dem.tif"])

    def test_unchanged_source_reuses_the_existing_copy(self):
        first = localize_input(self.src, self.cache_dir)
        inode = os.stat(first).st_ino
        second = localize_input(self.src, self.cache_dir)
        self.assertEqual(second, first)
        self.assertEqual(os.stat(second).st_ino, inode)

    def test_source_with_a_different_size_refreshes_the_copy(self):
        localize_input(self.src, self.cache_dir)
        with open(self.src, "wb") as f:
            f.write(b"dem-bytes-version-2")
        os.utime(self.src, (1_700_000_000, 1_700_000_000))
        local = localize_input(self.src, self.cache_dir)
        with open(local, "rb") as f:
            self.assertEqual(f.read(), b"dem-bytes-version-2")

    def test_source_with_a_different_mtime_refreshes_the_copy(self):
        localize_input(self.src, self.cache_dir)
        with open(self.src, "wb") as f:
            f.write(b"dem-bytes-v2")
        os.utime(self.src, (1_700_000_060, 1_700_000_060))
        local = localize_input(self.src, self.cache_dir)
        with open(local, "rb") as f:
            self.assertEqual(f.read(), b"dem-bytes-v2")
        self.assertEqual(int(os.stat(local).st_mtime), 1_700_000_060)

    def test_unwritable_cache_dir_returns_the_source(self):
        os.makedirs(self.cache_dir)
        os.chmod(self.cache_dir, stat.S_IRUSR | stat.S_IXUSR)
        self.assertEqual(localize_input(self.src, self.cache_dir), self.src)
        self.assertEqual(os.listdir(self.cache_dir), [])

    def test_missing_source_returns_the_source(self):
        missing = os.path.join(self.src_dir, "results_3di.nc")
        self.assertEqual(localize_input(missing, self.cache_dir), missing)


if __name__ == "__main__":
    unittest.main()
