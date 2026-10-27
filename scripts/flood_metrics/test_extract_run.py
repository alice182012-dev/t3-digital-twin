import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2

from extract_run import FLOOD_UTILS_DIR, Segment, extract_run, impassable_from_m, metric_rows, segments_from_rows
from metrics import DepthSeries, extract

REPO = Path(__file__).resolve().parents[2]
OWNER = REPO / "floodmap" / "graphhopper-flood-road" / "scripts" / "flood_utils.py"

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "database"))
import create_edge_depth_tables  # noqa: E402
import create_flood_metrics_tables  # noqa: E402
import create_graph_edge_table  # noqa: E402

DSN = os.getenv("EDGE_DEPTH_TEST_DSN")
SCHEMA = f"extract_run_test_{os.getpid()}"

T10 = datetime(2026, 9, 23, 10, 0)
T11 = datetime(2026, 9, 23, 11, 0)
T12 = datetime(2026, 9, 23, 12, 0)


UTC_10 = T10 - timedelta(hours=7)
UTC_11 = T11 - timedelta(hours=7)


class SegmentsFromRowsTests(unittest.TestCase):
    def test_one_series_per_edge_with_0_at_its_dry_steps_in_local_time(self):
        rows = [
            ("100:0", memoryview(b"\x01"), UTC_10, 10),
            ("100:0", memoryview(b"\x01"), UTC_11, 25),
            ("100:1", memoryview(b"\x02"), UTC_11, 40),
        ]
        self.assertEqual(
            segments_from_rows(rows, [UTC_11, UTC_10]),
            [
                Segment("100:0", b"\x01", DepthSeries((T10, T11), (0.10, 0.25))),
                Segment("100:1", b"\x02", DepthSeries((T10, T11), (0.0, 0.40))),
            ],
        )

    def test_a_run_with_no_wet_edge_has_no_segment(self):
        self.assertEqual(segments_from_rows([], [UTC_10, UTC_11]), [])

    def test_rejects_an_edge_that_is_not_in_graph_edge(self):
        with self.assertRaises(ValueError):
            segments_from_rows([("100:0", None, UTC_10, 10)], [UTC_10])

    def test_rejects_a_depth_at_a_time_the_run_does_not_cover(self):
        with self.assertRaises(ValueError):
            segments_from_rows([("100:0", b"\x01", UTC_11, 10)], [UTC_10])


class MetricRowsTests(unittest.TestCase):
    def test_one_row_per_vehicle_with_passability_columns(self):
        segment = Segment("100:0", b"\x01", DepthSeries((T10, T11, T12), (0.1, 0.25, 0.1)))
        thresholds = {"motorbike": 0.20, "car": 0.30}
        rows = metric_rows("20260923T100000", segment, extract(segment.series, thresholds), thresholds)

        shared = {
            "run_ts": "20260923T100000",
            "edge_key": "100:0",
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
        segment = Segment("100:0", b"\x01", DepthSeries((T10, T11), (0.1, 0.5)))
        rows = metric_rows("r", segment, extract(segment.series, {"car": 0.3}), {"car": 0.3})
        self.assertEqual(
            (rows[0]["passability"], rows[0]["closed_at"], rows[0]["restored_at"]),
            ("not_restored", T11, None),
        )


@unittest.skipUnless(DSN, "EDGE_DEPTH_TEST_DSN is not set")
class ExtractRunTests(unittest.TestCase):
    """Edge 100:0 is wet at both steps and crosses the car limit at the second. 100:1 is wet at the first only."""

    RUN = "20260923T170000"

    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg2.connect(DSN)
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {SCHEMA}")
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            for sql in (create_graph_edge_table.SQL, create_edge_depth_tables.SQL, create_flood_metrics_tables.SQL):
                cur.execute(sql)
            for edge_id, key in enumerate(["100:0", "100:1"]):
                cur.execute("INSERT INTO graph_edge (edge_id, edge_key, length_m, geom) "
                            "VALUES (%s, %s, 50, ST_GeomFromText('LINESTRING(105.72 21.0, 105.7205 21.0)', 4326))",
                            (edge_id, key))

    @classmethod
    def tearDownClass(cls):
        cls.conn.rollback()
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
        cls.conn.close()

    def setUp(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.execute("TRUNCATE edge_depth_run CASCADE")
            cur.execute("TRUNCATE flood_segment_metrics")

    def register(self, run, wet):
        """wet is (edge_key, utc step, depth_cm) rows. The run covers UTC_10 and UTC_11."""
        with self.conn, self.conn.cursor() as cur:
            cur.execute("INSERT INTO edge_depth_run (run_ts, graph_hash, valid_times) VALUES (%s, 'h', %s::timestamp[])",
                        (run, [UTC_10, UTC_11]))
            for key, step, cm in wet:
                cur.execute("INSERT INTO edge_depth VALUES (%s, %s, %s, %s)", (run, step, key, cm))

    def metrics(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT edge_key, vehicle_type, passability, peak_depth_m, window_start FROM flood_segment_metrics "
                        "ORDER BY edge_key, vehicle_type")
            return cur.fetchall()

    def test_every_wet_edge_gets_a_row_per_vehicle_in_local_time(self):
        self.register(self.RUN, [("100:0", UTC_10, 10), ("100:0", UTC_11, 33), ("100:1", UTC_10, 5)])

        written = extract_run(self.conn, self.RUN)

        rows = self.metrics()
        self.assertEqual(written, 8)
        self.assertEqual({row[0] for row in rows}, {"100:0", "100:1"})
        self.assertEqual(
            [row[1:4] for row in rows if row[0] == "100:0"],
            [("car", "not_restored", 0.33), ("foot", "never_impassable", 0.33),
             ("motorbike", "not_restored", 0.33), ("truck", "never_impassable", 0.33)],
        )
        self.assertEqual({row[4] for row in rows}, {T10})

    def test_a_run_with_no_wet_edge_writes_no_rows_and_does_not_raise(self):
        self.register(self.RUN, [])

        self.assertEqual(extract_run(self.conn, self.RUN), 0)
        self.assertEqual(self.metrics(), [])

    def test_a_run_the_registry_does_not_know_is_an_error(self):
        with self.assertRaises(ValueError):
            extract_run(self.conn, self.RUN)

    def test_a_rerun_replaces_the_edge_rows_and_keeps_the_piece_rows(self):
        self.register(self.RUN, [("100:0", UTC_10, 40)])
        with self.conn, self.conn.cursor() as cur:
            cur.execute("INSERT INTO flood_segment_metrics (run_ts, segment_key, vehicle_type, impassable_from_m, "
                        "window_start, window_end, passability, geom_4326) VALUES (%s, 'md5old', 'car', 0.3, %s, %s, "
                        "'never_impassable', ST_GeomFromText('POINT(105.72 21.0)', 4326))", (self.RUN, T10, T11))

        extract_run(self.conn, self.RUN)
        extract_run(self.conn, self.RUN)

        with self.conn.cursor() as cur:
            cur.execute("SELECT count(*) FILTER (WHERE edge_key IS NULL), count(*) FILTER (WHERE edge_key IS NOT NULL) "
                        "FROM flood_segment_metrics")
            self.assertEqual(cur.fetchone(), (1, 4))


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
