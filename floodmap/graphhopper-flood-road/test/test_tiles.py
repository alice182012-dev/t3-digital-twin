#!/usr/bin/env python3
"""Unit tests for backend/tiles.py.

Covers the pure surface: run/valid_time path resolution against a real
directory layout, the 404 miss cases, band coloring against the same
`depth_bands_m` table routing uses, and the tile cache's size bound. No
raster, no rio-tiler, no running server.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

_spec = importlib.util.spec_from_file_location("tiles", BACKEND / "tiles.py")
tiles = importlib.util.module_from_spec(_spec)
# @dataclass resolves its own module out of sys.modules, so register before exec.
sys.modules["tiles"] = tiles
_spec.loader.exec_module(tiles)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from flood_utils import depth_bands_m  # noqa: E402


class NormalizeStampTest(unittest.TestCase):
    def test_iso_with_colons(self):
        self.assertEqual(tiles.normalize_stamp("2026-08-09T16:42:00"), "20260809_164200")
        self.assertEqual(tiles.normalize_stamp("2026-08-09T17:12:00"), "20260809_171200")

    def test_compact_form_passes_through(self):
        self.assertEqual(tiles.normalize_stamp("20260809_164200"), "20260809_164200")

    def test_space_separated_iso(self):
        self.assertEqual(tiles.normalize_stamp("2026-08-09 16:42:00"), "20260809_164200")

    def test_rejects_traversal(self):
        for bad in ("../../etc/passwd", "..", "latest", "2026-08-09", "20260809_16420", ""):
            with self.assertRaises(tiles.TileNotFound):
                tiles.normalize_stamp(bad)


class ParseTilePathTest(unittest.TestCase):
    def test_iso_path_with_literal_colons(self):
        request = tiles.parse_tile_path("/tiles/2026-08-09T16:42:00/2026-08-09T17:12:00/13/6502/3607.png")
        self.assertEqual(request.run, "20260809_164200")
        self.assertEqual(request.valid_time, "20260809_171200")
        self.assertEqual((request.z, request.x, request.y), (13, 6502, 3607))

    def test_percent_encoded_colons(self):
        request = tiles.parse_tile_path("/tiles/2026-08-09T16%3A42%3A00/2026-08-09T17%3A12%3A00/13/6502/3607.png")
        self.assertEqual(request.run, "20260809_164200")
        self.assertEqual(request.valid_time, "20260809_171200")

    def test_non_tile_path_is_not_ours(self):
        self.assertIsNone(tiles.parse_tile_path("/flood/areas"))
        self.assertIsNone(tiles.parse_tile_path("/tiles/a/b/13/6502/3607.jpg"))

    def test_bad_stamp_in_tile_path_is_a_miss(self):
        with self.assertRaises(tiles.TileNotFound):
            tiles.parse_tile_path("/tiles/..%2F..%2Fetc/2026-08-09T17:12:00/13/6502/3607.png")


class ResolveTifTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        # The directory suffix is a separate end-of-window stamp, not
        # derivable from the run id. This is what forces the glob.
        run_dir = self.root / "depth_20260809_164200_181200"
        run_dir.mkdir()
        (run_dir / "depth_20260809_171200.tif").write_bytes(b"")
        self.addCleanup(self._tmp.cleanup)

    def test_hit_through_iso_stamps(self):
        found = tiles.resolve_tif("2026-08-09T16:42:00", "2026-08-09T17:12:00", root=self.root)
        self.assertEqual(found.name, "depth_20260809_171200.tif")
        self.assertEqual(found.parent.name, "depth_20260809_164200_181200")

    def test_unknown_run_raises(self):
        with self.assertRaises(tiles.TileNotFound):
            tiles.resolve_tif("2026-08-09T09:00:00", "2026-08-09T17:12:00", root=self.root)

    def test_known_run_unknown_valid_time_raises(self):
        with self.assertRaises(tiles.TileNotFound):
            tiles.resolve_tif("2026-08-09T16:42:00", "2026-08-09T23:59:00", root=self.root)


class ColorForDepthTest(unittest.TestCase):
    """Motorbike wades to 20cm, so the routing bands sit at 0.10 / 0.15 /
    0.20m. The tile legend has to land on exactly those edges."""

    def test_band_edges_match_flood_utils(self):
        edges = [band["band_min"] for band in depth_bands_m("motorbike")]
        self.assertEqual(edges, [0.20, 0.15000000000000002, 0.1])

    def test_below_shallowest_band_is_transparent(self):
        self.assertIsNone(tiles.color_for_depth(0.0))
        self.assertIsNone(tiles.color_for_depth(0.099))

    def test_each_band_gets_its_own_color(self):
        self.assertEqual(tiles.color_for_depth(0.10), (253, 187, 132))
        self.assertEqual(tiles.color_for_depth(0.14), (253, 187, 132))
        self.assertEqual(tiles.color_for_depth(0.16), (227, 74, 51))
        self.assertEqual(tiles.color_for_depth(0.20), (127, 0, 0))
        self.assertEqual(tiles.color_for_depth(0.706), (127, 0, 0))

    def test_car_bands_are_deeper_than_motorbike(self):
        # Car wades to 30cm, so 0.16m is impassable on a motorbike and
        # untouched for a car.
        self.assertEqual(tiles.color_for_depth(0.16, "car"), (253, 187, 132))
        self.assertIsNone(tiles.color_for_depth(0.14, "car"))


class TileCacheTest(unittest.TestCase):
    def test_evicts_least_recently_used_past_the_cap(self):
        cache = tiles.TileCache(max_entries=3, ttl_seconds=600)
        for index in range(3):
            cache.put(("k", index), b"png")
        cache.get(("k", 0))
        cache.put(("k", 3), b"png")
        self.assertEqual(len(cache), 3)
        self.assertIsNotNone(cache.get(("k", 0)))
        self.assertIsNone(cache.get(("k", 1)))
        self.assertIsNotNone(cache.get(("k", 3)))

    def test_size_stays_capped_under_a_long_pan(self):
        cache = tiles.TileCache(max_entries=10, ttl_seconds=600)
        for x in range(500):
            cache.put(("run", "vt", 13, x, 3607, "motorbike"), b"png")
        self.assertEqual(len(cache), 10)

    def test_expired_entry_is_a_miss(self):
        cache = tiles.TileCache(max_entries=10, ttl_seconds=0)
        cache.put(("k", 0), b"png")
        self.assertIsNone(cache.get(("k", 0)))


if __name__ == "__main__":
    unittest.main()
