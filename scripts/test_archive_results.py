import json
import tempfile
import unittest
from collections import namedtuple
from pathlib import Path

import archive_results as ar

Usage = namedtuple("Usage", "total used free")
GB = 1024**3


def make_nc(tmp: Path, sim_id=77, payload=b"netcdf-bytes") -> Path:
    folder = tmp / "results" / str(sim_id)
    folder.mkdir(parents=True)
    path = folder / "results_3di.nc"
    path.write_bytes(payload)
    return path


RAIN = {"source": "tomorrow.io", "total_mm": 12.5, "interval_count": 9, "max_mm_hr": 7.2}


class RecordTests(unittest.TestCase):
    def test_a_record_holds_the_five_fields_of_the_story(self):
        record = ar.build_record(77, "2026-10-09T06:00:00Z", RAIN, "83022", "abc")

        self.assertEqual(
            record,
            {"sim_id": 77, "run_timestamp": "2026-10-09T06:00:00Z", "rain_input": RAIN, "model_id": "83022", "graph_hash": "abc"},
        )

    def test_the_graph_hash_comes_from_graph_json_and_is_none_without_the_export(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(ar.read_graph_hash(d))
            (Path(d) / "graph.json").write_text(json.dumps({"graph_hash": "8c13"}))
            self.assertEqual(ar.read_graph_hash(d), "8c13")


class RainModeTests(unittest.TestCase):
    def test_only_tomorrow_io_counts_as_real_rain(self):
        self.assertTrue(ar.is_real_rain("tomorrow.io"))
        self.assertFalse(ar.is_real_rain("fixed_test_rain"))
        self.assertFalse(ar.is_real_rain("replay:storm.csv"))


class ArchiveRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.nc = make_nc(self.tmp)
        self.archive = self.tmp / "archive"
        self.record = ar.build_record(77, "2026-10-09T06:00:00Z", RAIN, "83022", "abc")

    def run_archive(self, free_gb=500, floor_gb=50, nc=None):
        return ar.archive_run(
            sim_id=77, nc_path=nc or self.nc, archive_dir=self.archive, record=self.record,
            floor_bytes=floor_gb * GB, disk_usage=lambda _: Usage(1000 * GB, 0, free_gb * GB),
        )

    def test_the_file_and_the_record_land_under_the_sim_id(self):
        result = self.run_archive()

        self.assertEqual((self.archive / "77" / "results_3di.nc").read_bytes(), b"netcdf-bytes")
        self.assertEqual(json.loads((self.archive / "77" / "run_record.json").read_text())["sim_id"], 77)
        self.assertEqual(result.free_bytes, 500 * GB)

    def test_the_record_carries_the_size_and_checksum_of_the_copy(self):
        self.run_archive()

        record = json.loads((self.archive / "77" / "run_record.json").read_text())
        self.assertEqual(record["bytes"], len(b"netcdf-bytes"))
        self.assertEqual(len(record["sha256"]), 64)

    def test_a_second_run_gives_the_same_archive(self):
        self.run_archive()
        first = sorted(p.name for p in (self.archive / "77").iterdir())
        self.run_archive()

        self.assertEqual(sorted(p.name for p in (self.archive / "77").iterdir()), first)

    def test_no_temporary_file_stays_behind(self):
        self.run_archive()

        self.assertEqual(sorted(p.name for p in (self.archive / "77").iterdir()), ["results_3di.nc", "run_record.json"])

    def test_free_space_below_the_floor_fails_after_the_copy(self):
        with self.assertRaisesRegex(ar.ArchiveError, "49.0 GB free"):
            self.run_archive(free_gb=49, floor_gb=50)

        self.assertTrue((self.archive / "77" / "results_3di.nc").exists())

    def test_a_missing_result_file_fails(self):
        with self.assertRaisesRegex(ar.ArchiveError, "results_3di.nc"):
            self.run_archive(nc=self.tmp / "gone.nc")


if __name__ == "__main__":
    unittest.main()
