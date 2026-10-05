"""Checks the flood_mapping_full task graph without Airflow installed.

The DAG file is imported with small stand-ins for the Airflow modules it uses. The stand-ins record
each task id and each `>>` edge, and the tests compare them with the intended graph.
"""

import importlib.util
import os
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TASKS = {
    "0_check_forecast_rain",
    "1_trigger_simulation",
    "0b_ensure_schema",
    "2_download_results",
    "3_calculate_depth",
    "3b_upload_netcdf_postgres",
    "9_build_flood_tiles",
    "9b_load_depth_raster",
    "9c_build_edge_depth_table",
    "edge_table_done",
    "load_road_segments",
    "flood_on_roads",
}

EXPECTED_EDGES = {
    ("0_check_forecast_rain", "1_trigger_simulation"),
    ("1_trigger_simulation", "2_download_results"),
    ("2_download_results", "3_calculate_depth"),
    ("3_calculate_depth", "9_build_flood_tiles"),
    ("3_calculate_depth", "9b_load_depth_raster"),
    ("2_download_results", "3b_upload_netcdf_postgres"),
    ("1_trigger_simulation", "0b_ensure_schema"),
    ("0b_ensure_schema", "3b_upload_netcdf_postgres"),
    ("0b_ensure_schema", "9_build_flood_tiles"),
    ("0b_ensure_schema", "9b_load_depth_raster"),
    ("9b_load_depth_raster", "flood_on_roads"),
    ("9b_load_depth_raster", "9c_build_edge_depth_table"),
    ("9c_build_edge_depth_table", "edge_table_done"),
    ("load_road_segments", "flood_on_roads"),
    ("0b_ensure_schema", "load_road_segments"),
    ("0b_ensure_schema", "flood_on_roads"),
}


class FakeDag:
    current = None

    def __init__(self, dag_id, **kwargs):
        self.dag_id = dag_id
        self.kwargs = kwargs
        self.tasks = {}
        self.edges = set()

    def __enter__(self):
        FakeDag.current = self
        return self

    def __exit__(self, *exc):
        FakeDag.current = None


class FakeOperator:
    def __init__(self, task_id, **kwargs):
        self.task_id = task_id
        self.kwargs = kwargs
        self.dag = FakeDag.current
        if task_id in self.dag.tasks:
            raise ValueError(f"duplicate task id {task_id}")
        self.dag.tasks[task_id] = self

    def __rshift__(self, other):
        for downstream in other if isinstance(other, list) else [other]:
            self.dag.edges.add((self.task_id, downstream.task_id))
        return other

    def __rrshift__(self, upstreams):
        for upstream in upstreams:
            self.dag.edges.add((upstream.task_id, self.task_id))
        return self


def module(name, **attrs):
    fake = types.ModuleType(name)
    fake.__dict__.update(attrs)
    return fake


def load_dag_module():
    fakes = {
        "airflow": module("airflow", DAG=FakeDag),
        "airflow.exceptions": module("airflow.exceptions", AirflowException=RuntimeError),
        "airflow.providers": module("airflow.providers"),
        "airflow.providers.standard": module("airflow.providers.standard"),
        "airflow.providers.standard.operators": module("airflow.providers.standard.operators"),
        "airflow.providers.standard.operators.python": module(
            "airflow.providers.standard.operators.python",
            BranchPythonOperator=FakeOperator,
            PythonOperator=FakeOperator,
        ),
        "boto3": module("boto3", client=MagicMock()),
        "psycopg2": module("psycopg2", connect=MagicMock()),
    }
    spec = importlib.util.spec_from_file_location("flood_mapping_dag_under_test", ROOT / "dags/flood_mapping_dag.py")
    dag_module = importlib.util.module_from_spec(spec)
    saved_path = list(sys.path)
    try:
        with patch.dict(sys.modules, fakes), patch("builtins.print"):
            spec.loader.exec_module(dag_module)
    finally:
        sys.path[:] = saved_path
    return dag_module


def load_flood_extent():
    spec = importlib.util.spec_from_file_location("flood_extent", ROOT / "scripts/flood_extent/flood_extent.py")
    flood_extent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(flood_extent)
    return flood_extent


class FloodMappingDagGraphTests(unittest.TestCase):
    def setUp(self):
        self.dag_module = load_dag_module()
        self.dag = self.dag_module.dag

    def test_dag_id(self):
        self.assertEqual(self.dag.dag_id, "flood_mapping_full")

    def test_task_ids_are_exactly_the_raster_first_set(self):
        self.assertEqual(set(self.dag.tasks), EXPECTED_TASKS)

    def test_edges_are_exactly_the_raster_first_set(self):
        self.assertEqual(self.dag.edges, EXPECTED_EDGES)

    def test_runs_on_the_quarter_hour_without_catchup(self):
        self.assertEqual(
            {key: self.dag.kwargs[key] for key in ("schedule", "catchup", "max_active_runs")},
            {"schedule": "*/15 * * * *", "catchup": False, "max_active_runs": 2},
        )

    def test_a_dry_forecast_skips_every_downstream_task(self):
        self.dag_module.create_simulation = MagicMock()
        self.dag_module.create_simulation.get_rain_forecast.return_value = [{"values": {}}]
        self.dag_module.create_simulation.evaluate_rain_gate.return_value = {
            "should_run": False, "max_intensity_mm_hr": 0.4, "threshold_mm_hr": 5.0, "interval_count": 8
        }

        with patch("builtins.print"):
            self.assertIsNone(self.dag_module.task_check_forecast_rain(ti=MagicMock()))

    def test_ensure_schema_creates_the_tables_its_downstream_tasks_write(self):
        database = MagicMock()
        self.dag_module.database = database

        with patch("builtins.print"):
            self.dag_module.task_ensure_schema()

        database.create_netcdf_tables.create_tables.assert_called_once_with()
        database.create_flood_road_tables.main.assert_called_once_with()
        database.create_flood_extent_tables.main.assert_called_once_with()
        database.create_flood_depth_raster_tables.main.assert_called_once_with()
        database.create_road_segment_table.main.assert_called_once_with()
        database.create_graph_edge_table.main.assert_called_once_with()

    def test_a_failed_edge_table_does_not_fail_the_run(self):
        """A DAG run takes its state from its leaf tasks. edge_table_done runs whatever happens to the
        edge table task, so a failure shows red on the task and the run stays green, which keeps the
        next slot's run allowed to hotstart (hotstart_policy)."""
        edge_table_done = self.dag.tasks["edge_table_done"]
        leaves = {t for t in self.dag.tasks if not any(up == t for up, _ in self.dag.edges)}

        self.assertEqual(edge_table_done.kwargs["trigger_rule"], "all_done")
        self.assertIn("edge_table_done", leaves)
        self.assertNotIn("9c_build_edge_depth_table", leaves)


class DepthRunTests(unittest.TestCase):
    """Tasks 9 and 9b name the run from the depth folder, not from an XCom of a removed task."""

    def setUp(self):
        self.dag_module = load_dag_module()
        self.dag_module.flood_extent = load_flood_extent()
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for name in ("depth_20260924_180639.tif", "depth_20260924_170639.tif"):
            (Path(self.tmp.name) / name).write_text("x")
        self.ti = MagicMock()
        self.ti.xcom_pull.side_effect = (
            lambda task_ids, key=None: self.tmp.name if (task_ids, key) == ("3_calculate_depth", None) else None
        )

    def test_load_depth_raster_uses_the_earliest_depth_file_as_run_ts(self):
        raster_load = MagicMock()
        raster_load.load_run.return_value = ["a", "b"]
        self.dag_module.raster_load = raster_load
        self.dag_module.DB_CONFIG = {}

        with patch("builtins.print"):
            result = self.dag_module.task_load_depth_raster(ti=self.ti)

        self.assertEqual(result, {"run_ts": "20260924T170639", "timesteps": 2})
        args = raster_load.load_run.call_args.args
        self.assertEqual(args[1:3], (self.tmp.name, "20260924T170639"))

    def test_build_flood_tiles_uses_the_earliest_depth_file_as_run_ts(self):
        publish = MagicMock()
        publish.publish_run.return_value = {
            "20260924T170639": MagicMock(is_empty=False),
            "20260924T180639": MagicMock(is_empty=True),
        }
        self.dag_module.publish = publish
        self.dag_module.DB_CONFIG = {}
        env = {"MINIO_ENDPOINT": "http://minio:9000", "MINIO_ACCESS_KEY": "k", "MINIO_SECRET_KEY": "s"}

        with patch.dict(os.environ, env), patch("builtins.print"):
            result = self.dag_module.task_build_flood_tiles(ti=self.ti)

        self.assertEqual(result, {"run_ts": "20260924T170639", "timesteps": 2, "flooded_timesteps": 1})
        self.assertEqual(publish.publish_run.call_args.args[:2], (self.tmp.name, "20260924T170639"))
        self.assertIn("/opt/airflow/data/mapping/results", publish.publish_run.call_args.kwargs["cleanup_dirs"])

    def test_flood_on_roads_computes_the_run_named_by_the_earliest_depth_file(self):
        flood_on_roads = MagicMock()
        flood_on_roads.compute.return_value = MagicMock(
            timesteps=(
                MagicMock(forecast_time=datetime(2026, 9, 24, 17, 6, 39), rows=3, wet_pieces=2),
                MagicMock(forecast_time=datetime(2026, 9, 24, 18, 6, 39), rows=3, wet_pieces=0),
            ),
            rows=6,
            target_table="flood_road_values",
            seconds=1.0,
        )
        self.dag_module.flood_on_roads = flood_on_roads
        self.dag_module.DB_CONFIG = {}

        with patch("builtins.print"):
            result = self.dag_module.task_flood_on_roads(ti=self.ti)

        self.assertEqual(result, {"run_ts": "20260924T170639", "timesteps": 2, "rows": 6})
        self.assertEqual(flood_on_roads.compute.call_args.args[1:], ("20260924T170639",))

    def test_build_edge_depth_table_builds_the_run_named_by_the_earliest_depth_file(self):
        build_edge_depth = MagicMock()
        build_edge_depth.build_table.return_value = MagicMock(
            path=Path("/opt/airflow/data/mapping/edge_depth/20260924T170639.bin"),
            graph_hash="a" * 64,
            graph_loaded=False,
            edge_count=67833,
            step_count=8,
            wet_edges=(10, 20, 30, 0, 0, 0, 0, 0),
            sample_seconds=(1.0,) * 8,
            size_bytes=1085368,
            seconds=12.5,
        )
        self.dag_module.build_edge_depth = build_edge_depth
        publish = self.dag_module.publish_edge_depth = MagicMock()
        publish.publish_table.return_value = MagicMock(
            latest="20260924T170639.bin", previous="20260924T165639.bin", moved=True, removed=("20260924T150639.bin",),
            kept=("20260924T170639.bin",),
        )
        self.dag_module.DB_CONFIG = {}

        with patch("builtins.print"):
            result = self.dag_module.task_build_edge_depth_table(ti=self.ti)

        args = build_edge_depth.build_table.call_args.args
        self.assertEqual(args[1], "20260924T170639")
        self.assertEqual(str(args[2]), "/opt/airflow/data/mapping/graph_export")
        self.assertEqual(str(args[3]), "/opt/airflow/edge_depth_tables")
        self.assertEqual(result["run_ts"], "20260924T170639")
        self.assertEqual((result["edge_count"], result["steps"], result["bytes"]), (67833, 8, 1085368))
        self.assertEqual(result["wet_edges"], [10, 20, 30, 0, 0, 0, 0, 0])
        self.assertEqual(result["seconds"], 12.5)
        self.assertEqual(
            result["published"],
            {"latest": "20260924T170639.bin", "previous": "20260924T165639.bin", "moved": True,
             "removed": ["20260924T150639.bin"]},
        )
        self.ti.xcom_push.assert_called_once_with(key="edge_depth_table", value=result)
        publish.publish_table.assert_called_once_with(
            "/opt/airflow/edge_depth_tables", "20260924T170639.bin", keep=3
        )

    def test_the_edge_table_folders_can_be_set_by_environment(self):
        env = {"EDGE_EXPORT_DIR": "/exports", "EDGE_TABLE_DIR": "/tables", "EDGE_TABLE_KEEP_RUNS": "5"}
        with patch.dict(os.environ, env):
            dag_module = load_dag_module()
        dag_module.flood_extent = self.dag_module.flood_extent
        dag_module.build_edge_depth = MagicMock()
        dag_module.publish_edge_depth = MagicMock()
        dag_module.publish_edge_depth.publish_table.return_value = MagicMock(removed=())
        dag_module.build_edge_depth.build_table.return_value = MagicMock(
            path=Path("/tables/x.bin"), graph_hash="a" * 64, graph_loaded=False, edge_count=1, step_count=1,
            wet_edges=(0,), sample_seconds=(0.1,), size_bytes=40, seconds=1.0,
        )
        dag_module.DB_CONFIG = {}

        with patch("builtins.print"):
            dag_module.task_build_edge_depth_table(ti=self.ti)

        args = dag_module.build_edge_depth.build_table.call_args.args
        self.assertEqual((str(args[2]), str(args[3])), ("/exports", "/tables"))
        self.assertEqual(dag_module.publish_edge_depth.publish_table.call_args.kwargs, {"keep": 5})

    def test_a_failed_build_publishes_nothing_so_latest_stays(self):
        self.dag_module.build_edge_depth = MagicMock()
        self.dag_module.build_edge_depth.build_table.side_effect = RuntimeError("no export")
        self.dag_module.publish_edge_depth = MagicMock()
        self.dag_module.DB_CONFIG = {}

        with patch("builtins.print"), self.assertRaises(RuntimeError):
            self.dag_module.task_build_edge_depth_table(ti=self.ti)

        self.dag_module.publish_edge_depth.publish_table.assert_not_called()
        self.ti.xcom_push.assert_not_called()

    def test_a_failed_publish_fails_the_task_and_reports_nothing(self):
        self.dag_module.build_edge_depth = MagicMock()
        self.dag_module.build_edge_depth.build_table.return_value = MagicMock(
            path=Path("/tables/x.bin"), graph_hash="a" * 64, graph_loaded=False, edge_count=1, step_count=1,
            wet_edges=(0,), sample_seconds=(0.1,), size_bytes=40, seconds=1.0,
        )
        self.dag_module.publish_edge_depth = MagicMock()
        self.dag_module.publish_edge_depth.publish_table.side_effect = ValueError("not a valid table")
        self.dag_module.DB_CONFIG = {}

        with patch("builtins.print"), self.assertRaises(ValueError):
            self.dag_module.task_build_edge_depth_table(ti=self.ti)

        self.ti.xcom_push.assert_not_called()

    def test_a_missing_depth_folder_fails_the_task(self):
        self.ti.xcom_pull.side_effect = lambda task_ids, key=None: None

        with self.assertRaises(ValueError):
            self.dag_module.task_load_depth_raster(ti=self.ti)


class DownloadResultTests(unittest.TestCase):
    def test_each_simulation_downloads_into_its_own_folder(self):
        dag_module = load_dag_module()
        dag_module.download_result = MagicMock()
        dag_module.download_result.run_download.side_effect = lambda sim_id, output_dir: f"{output_dir}/results_3di.nc"
        paths = []
        for sim_id in (101, 102):
            ti = MagicMock()
            ti.xcom_pull.return_value = sim_id
            with patch("builtins.print"):
                dag_module.task_download_result(ti=ti)
            paths.append(ti.xcom_push.call_args.kwargs["value"])

        self.assertEqual(
            paths,
            [
                "/opt/airflow/data/mapping/results/101/results_3di.nc",
                "/opt/airflow/data/mapping/results/102/results_3di.nc",
            ],
        )


class LoadRoadSegmentsTests(unittest.TestCase):
    def setUp(self):
        self.dag_module = load_dag_module()
        self.dag_module.DB_CONFIG = {}
        self.loader = MagicMock(DEFAULT_ROADS_PATH="/opt/airflow/data/mapping/inputs/toa-do-duong-hanoi.geojson")
        self.loader.load.return_value = MagicMock(inserted=0, updated=0, deleted=0, total=35652)
        self.dag_module.load_road_segments = self.loader

    def test_loads_the_production_roads_file_and_reports_the_counts(self):
        with patch.dict(os.environ), patch("builtins.print"):
            os.environ.pop("ROADS_GEOJSON_PATH", None)
            result = self.dag_module.task_load_road_segments()

        self.assertEqual(result, {"inserted": 0, "updated": 0, "deleted": 0, "total": 35652})
        self.assertEqual(
            self.loader.load.call_args.args[1], "/opt/airflow/data/mapping/inputs/toa-do-duong-hanoi.geojson"
        )

    def test_a_bad_roads_file_fails_the_task(self):
        self.loader.load.side_effect = ValueError("feature 0 has no properties['@id']")

        with patch("builtins.print"), self.assertRaises(ValueError):
            self.dag_module.task_load_road_segments()


if __name__ == "__main__":
    unittest.main()
