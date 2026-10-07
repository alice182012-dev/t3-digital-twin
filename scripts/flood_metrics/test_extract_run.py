import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from extract_run import FLOOD_UTILS_DIR, Segment, impassable_from_m, metric_rows, segments_from_rows
from metrics import DepthSeries, extract

REPO = Path(__file__).resolve().parents[2]
OWNER = REPO / "floodmap" / "graphhopper-flood-road" / "scripts" / "flood_utils.py"

T10 = datetime(2026, 9, 23, 10, 0)
T11 = datetime(2026, 9, 23, 11, 0)
T12 = datetime(2026, 9, 23, 12, 0)


class SegmentsFromRowsTests(unittest.TestCase):
    def test_groups_rows_into_one_series_per_segment_key(self):
        rows = [
            ("aaa", "Phố Huế", memoryview(b"\x01"), T10, 0.10),
            ("aaa", "Phố Huế", memoryview(b"\x01"), T11, 0.25),
            ("bbb", "Phố Huế", memoryview(b"\x02"), T10, 0.0),
        ]
        self.assertEqual(
            segments_from_rows(rows),
            [
                Segment("aaa", "Phố Huế", b"\x01", DepthSeries((T10, T11), (0.10, 0.25))),
                Segment("bbb", "Phố Huế", b"\x02", DepthSeries((T10,), (0.0,))),
            ],
        )

    def test_rejects_two_rows_for_one_segment_and_time(self):
        rows = [("aaa", "Phố Huế", b"\x01", T10, 0.1), ("aaa", "Phố Huế", b"\x01", T10, 0.2)]
        with self.assertRaises(ValueError):
            segments_from_rows(rows)

    def test_rejects_a_null_depth(self):
        with self.assertRaises(ValueError):
            segments_from_rows([("aaa", "Phố Huế", b"\x01", T10, None)])


class MetricRowsTests(unittest.TestCase):
    def test_one_row_per_vehicle_with_passability_columns(self):
        segment = Segment("aaa", "Phố Huế", b"\x01", DepthSeries((T10, T11, T12), (0.1, 0.25, 0.1)))
        thresholds = {"motorbike": 0.20, "car": 0.30}
        rows = metric_rows("20260923T100000", segment, extract(segment.series, thresholds), thresholds)

        shared = {
            "run_ts": "20260923T100000",
            "segment_key": "aaa",
            "road_name": "Phố Huế",
            "window_start": T10,
            "window_end": T12,
            "peak_time": T11,
            "peak_depth_m": 0.25,
            "time_to_peak": timedelta(hours=1),
            "peak_at_window_end": False,
            "recession_onset": T12,
            "forecast_depth_1h_m": 0.25,
            "forecast_depth_2h_m": 0.1,
            "geom_ewkb": b"\x01",
        }
        self.assertEqual(
            rows,
            [
                {
                    **shared,
                    "vehicle_type": "motorbike",
                    "impassable_from_m": 0.20,
                    "passability": "restored",
                    "closed_at": T11,
                    "pre_closure_time": T10,
                    "restored_at": T12,
                },
                {
                    **shared,
                    "vehicle_type": "car",
                    "impassable_from_m": 0.30,
                    "passability": "never_impassable",
                    "closed_at": None,
                    "pre_closure_time": None,
                    "restored_at": None,
                },
            ],
        )

    def test_still_closed_at_window_end_is_not_restored(self):
        segment = Segment("aaa", None, b"\x01", DepthSeries((T10, T11), (0.1, 0.5)))
        rows = metric_rows("r", segment, extract(segment.series, {"car": 0.3}), {"car": 0.3})
        self.assertEqual(
            (rows[0]["passability"], rows[0]["closed_at"], rows[0]["restored_at"]),
            ("not_restored", T11, None),
        )


class ImpassableFromTests(unittest.TestCase):
    def test_reads_the_hard_block_depth_routing_uses_for_every_vehicle(self):
        # flood_utils.VEHICLE_PROFILES' threshold_cm values, in metres.
        self.assertEqual(
            impassable_from_m(),
            {"motorbike": 0.20, "car": 0.30, "truck": 0.35, "foot": 0.40},
        )

    def test_reads_them_from_the_owner_module(self):
        impassable_from_m()
        self.assertIn("flood_utils", sys.modules, "impassable_from_m did not import flood_utils")
        self.assertEqual(Path(sys.modules["flood_utils"].__file__).resolve(), OWNER)

    def test_airflow_mounts_the_owner_where_the_extractor_looks(self):
        # The blocker airflow-cannot-import-flood-utils: ./scripts is /opt/airflow/scripts in the container,
        # so FLOOD_UTILS_DIR resolves under /opt/airflow and needs this mount, or the import fails there only.
        folder = OWNER.parent.relative_to(REPO).as_posix()
        compose = (REPO / "compose.yml").read_text(encoding="utf-8")
        self.assertIn(f"- ./{folder}:/opt/airflow/{folder}:ro", compose)
        self.assertEqual(FLOOD_UTILS_DIR.resolve(), OWNER.parent)


if __name__ == "__main__":
    unittest.main()
