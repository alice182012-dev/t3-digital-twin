"""Checks the flood_mapping_full task graph without Airflow installed.

The DAG file is imported with small stand-ins for the Airflow modules it uses. The stand-ins record
each task id and each `>>` edge, and the tests compare them with the intended graph.
test_routing_adapter_dag.py reuses load_dag_module for the routing DAG.
"""

import importlib.util
import os
import sys
import types
import unittest
from dataclasses import dataclass
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


@dataclass(frozen=True)
class FakeAsset:
    name: str


def module(name, **attrs):
    fake = types.ModuleType(name)
    fake.__dict__.update(attrs)
    return fake


def load_dag_module(path="dags/flood_mapping_dag.py"):
    fakes = {
        "airflow": module("airflow", DAG=FakeDag),
        "airflow.sdk": module("airflow.sdk", Asset=FakeAsset),
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
    spec = importlib.util.spec_from_file_location(f"{Path(path).stem}_under_test", ROOT / path)
    dag_module = importlib.util.module_from_spec(spec)
    saved_path = list(sys.path)
    try:
        # Airflow puts the DAGs folder on sys.path, which is how a DAG file imports core_assets.
        sys.path.append(str(ROOT / "dags"))
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

    def test_no_core_task_waits_on_a_routing_task(self):
        """A DAG run takes its state from its leaf tasks. The leaves are core tasks only, so a routing failure
        cannot turn the run red and break the next slot's hotstart (hotstart_policy)."""
        leaves = {t for t in self.dag.tasks if not any(up == t for up, _ in self.dag.edges)}

        self.assertEqual(leaves, {"3b_upload_netcdf_postgres", "9_build_flood_tiles", "9b_load_depth_raster"})

    def test_load_depth_raster_declares_the_published_asset(self):
        self.assertEqual(
            self.dag.tasks["9b_load_depth_raster"].kwargs["outlets"], [FakeAsset("flood_depth_raster_tile")]
        )
        self.assertEqual(
            [name for name, task in self.dag.tasks.items() if "outlets" in task.kwargs], ["9b_load_depth_raster"]
        )


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
        event = types.SimpleNamespace(extra={})

        with patch("builtins.print"):
            result = self.dag_module.task_load_depth_raster(
                ti=self.ti, outlet_events={FakeAsset("flood_depth_raster_tile"): event}
            )

        self.assertEqual(result, {"run_ts": "20260924T170639", "timesteps": 2})
        args = raster_load.load_run.call_args.args
        self.assertEqual(args[1:3], (self.tmp.name, "20260924T170639"))
        self.assertEqual(event.extra, {"run_ts": "20260924T170639"})

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


if __name__ == "__main__":
    unittest.main()
