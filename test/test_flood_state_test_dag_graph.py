"""Checks the flood_forecast_consecutive_state_test task graph without Airflow installed.

The DAG file is imported with small stand-ins for the Airflow modules it uses, the same way
test_flood_mapping_dag_graph.py checks flood_mapping_full. Run it as a file:
python3 test/test_flood_state_test_dag_graph.py
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
    "0_ensure_schema",
    "load_road_segments",
    "1_trigger_event1",
    "2_download_event1",
    "3_calculate_depth_event1",
    "3b_build_tiles_event1",
    "3c_load_depth_raster_event1",
    "3d_flood_on_roads_event1",
    "4_trigger_event2",
    "5_download_event2",
    "6_calculate_depth_event2",
    "6b_build_tiles_event2",
    "6c_load_depth_raster_event2",
    "6d_flood_on_roads_event2",
}

EXPECTED_EDGES = {
    ("0_ensure_schema", "load_road_segments"),
    ("0_ensure_schema", "3b_build_tiles_event1"),
    ("0_ensure_schema", "3c_load_depth_raster_event1"),
    ("0_ensure_schema", "3d_flood_on_roads_event1"),
    ("0_ensure_schema", "6b_build_tiles_event2"),
    ("0_ensure_schema", "6c_load_depth_raster_event2"),
    ("0_ensure_schema", "6d_flood_on_roads_event2"),
    ("load_road_segments", "3d_flood_on_roads_event1"),
    ("load_road_segments", "6d_flood_on_roads_event2"),
    ("1_trigger_event1", "2_download_event1"),
    ("2_download_event1", "3_calculate_depth_event1"),
    ("2_download_event1", "4_trigger_event2"),
    ("4_trigger_event2", "5_download_event2"),
    ("3_calculate_depth_event1", "3b_build_tiles_event1"),
    ("3_calculate_depth_event1", "3c_load_depth_raster_event1"),
    ("3c_load_depth_raster_event1", "3d_flood_on_roads_event1"),
    ("3b_build_tiles_event1", "6_calculate_depth_event2"),
    ("3c_load_depth_raster_event1", "6_calculate_depth_event2"),
    ("5_download_event2", "6_calculate_depth_event2"),
    ("6_calculate_depth_event2", "6b_build_tiles_event2"),
    ("6_calculate_depth_event2", "6c_load_depth_raster_event2"),
    ("6c_load_depth_raster_event2", "6d_flood_on_roads_event2"),
}


class FakeDag:
    current = None

    def __init__(self, dag_id, **kwargs):
        self.dag_id = dag_id
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
            "airflow.providers.standard.operators.python", PythonOperator=FakeOperator
        ),
        "boto3": module("boto3", client=MagicMock()),
        "psycopg2": module("psycopg2", connect=MagicMock()),
    }
    spec = importlib.util.spec_from_file_location(
        "flood_state_test_dag_under_test", ROOT / "dags/flood_forecast_state_test_dag.py"
    )
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


class StateTestDagGraphTests(unittest.TestCase):
    def setUp(self):
        self.dag_module = load_dag_module()
        self.dag = self.dag_module.dag

    def test_dag_id(self):
        self.assertEqual(self.dag.dag_id, "flood_forecast_consecutive_state_test")

    def test_task_ids_are_exactly_the_two_event_set(self):
        self.assertEqual(set(self.dag.tasks), EXPECTED_TASKS)

    def test_edges_are_exactly_the_two_event_set(self):
        self.assertEqual(self.dag.edges, EXPECTED_EDGES)

    def test_no_task_writes_the_netcdf_tables(self):
        self.assertFalse(any("netcdf" in task_id for task_id in self.dag.tasks))
        self.assertFalse(hasattr(self.dag_module, "task_upload_netcdf_postgres"))

    def test_each_event_task_reads_its_own_depth_folder(self):
        for task_id, depth_task in [
            ("3b_build_tiles_event1", "3_calculate_depth_event1"),
            ("3c_load_depth_raster_event1", "3_calculate_depth_event1"),
            ("3d_flood_on_roads_event1", "3_calculate_depth_event1"),
            ("6b_build_tiles_event2", "6_calculate_depth_event2"),
            ("6c_load_depth_raster_event2", "6_calculate_depth_event2"),
            ("6d_flood_on_roads_event2", "6_calculate_depth_event2"),
        ]:
            self.assertEqual(self.dag.tasks[task_id].kwargs["op_kwargs"], {"depth_task_id": depth_task}, task_id)

    def test_ensure_schema_creates_what_production_creates(self):
        database = MagicMock()
        self.dag_module.database = database

        with patch("builtins.print"):
            self.dag_module.task_ensure_schema()

        database.create_flood_road_tables.main.assert_called_once_with()
        database.create_flood_extent_tables.main.assert_called_once_with()
        database.create_flood_depth_raster_tables.main.assert_called_once_with()
        database.create_road_segment_table.main.assert_called_once_with()
        database.create_flood_run_output_table.main.assert_called_once_with()


class SharedRunNameTests(unittest.TestCase):
    """Both events publish under event 1's earliest depth stamp (D-007), each from its own folder."""

    EVENT1_FILES = ("depth_20260925_101500.tif", "depth_20260925_121500.tif")
    EVENT2_FILES = ("depth_20260925_123000.tif", "depth_20260925_141500.tif")

    def setUp(self):
        self.dag_module = load_dag_module()
        self.dag_module.flood_extent = load_flood_extent()
        self.dag_module.DB_CONFIG = {}
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dirs = {
            "3_calculate_depth_event1": self.depth_dir("event1", self.EVENT1_FILES),
            "6_calculate_depth_event2": self.depth_dir("event2", self.EVENT2_FILES),
        }
        self.ti = MagicMock()
        self.ti.xcom_pull.side_effect = lambda task_ids, key=None: self.dirs.get(task_ids) if key is None else None

    def depth_dir(self, name, files):
        path = Path(self.tmp.name) / name
        path.mkdir()
        for file in files:
            (path / file).write_text("x")
        return str(path)

    def run_task(self, function, depth_task_id):
        env = {"MINIO_ENDPOINT": "http://minio:9000", "MINIO_ACCESS_KEY": "k", "MINIO_SECRET_KEY": "s"}
        with patch.dict(os.environ, env), patch("builtins.print"):
            return function(depth_task_id, ti=self.ti)

    def test_both_events_build_tiles_under_event_1s_run_name(self):
        publish = MagicMock()
        publish.publish_run.return_value = {"a": MagicMock(is_empty=False), "b": MagicMock(is_empty=True)}
        self.dag_module.publish = publish

        for depth_task in self.dirs:
            result = self.run_task(self.dag_module.task_build_flood_tiles, depth_task)
            self.assertEqual(result, {"run_ts": "20260925T101500", "timesteps": 2, "flooded_timesteps": 1})
            self.assertEqual(publish.publish_run.call_args.args[:2], (self.dirs[depth_task], "20260925T101500"))
            self.assertEqual(publish.publish_run.call_args.kwargs["keep_runs"], 1000)

    def test_both_events_load_rasters_under_event_1s_run_name_without_pruning(self):
        raster_load = MagicMock()
        raster_load.load_run.return_value = ["a", "b"]
        self.dag_module.raster_load = raster_load

        for depth_task in self.dirs:
            result = self.run_task(self.dag_module.task_load_depth_raster, depth_task)
            self.assertEqual(result, {"run_ts": "20260925T101500", "timesteps": 2})
            self.assertEqual(raster_load.load_run.call_args.args[1:3], (self.dirs[depth_task], "20260925T101500"))
            self.assertEqual(raster_load.load_run.call_args.kwargs["keep_runs"], 1000)

    def test_both_events_compute_flood_on_roads_for_event_1s_run_name(self):
        flood_on_roads = MagicMock()
        flood_on_roads.compute.return_value = MagicMock(
            timesteps=(MagicMock(forecast_time=datetime(2026, 9, 25, 10, 15), rows=3, wet_pieces=2),),
            rows=3,
            target_table="flood_road_values",
            seconds=1.0,
        )
        self.dag_module.flood_on_roads = flood_on_roads

        for depth_task in self.dirs:
            result = self.run_task(self.dag_module.task_flood_on_roads, depth_task)
            self.assertEqual(result, {"run_ts": "20260925T101500", "timesteps": 1, "rows": 3})
            self.assertEqual(flood_on_roads.compute.call_args.args[1:], ("20260925T101500",))

    def test_event_2_timesteps_overlapping_event_1_fail_before_publishing(self):
        self.dirs["6_calculate_depth_event2"] = self.depth_dir(
            "event2_overlap", ("depth_20260925_121500.tif", "depth_20260925_141500.tif")
        )
        publish = MagicMock()
        self.dag_module.publish = publish

        with self.assertRaises(ValueError):
            self.run_task(self.dag_module.task_build_flood_tiles, "6_calculate_depth_event2")
        publish.publish_run.assert_not_called()

    def test_a_missing_event_1_folder_fails_event_2s_task(self):
        del self.dirs["3_calculate_depth_event1"]

        with self.assertRaises(ValueError):
            self.run_task(self.dag_module.task_load_depth_raster, "6_calculate_depth_event2")


if __name__ == "__main__":
    unittest.main()
