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
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TASKS = {
    "0_check_forecast_rain",
    "1_trigger_simulation",
    "0b_ensure_schema",
    "2_download_results",
    "2b_archive_results",
    "2c_archive_done",
    "3_calculate_depth",
    "3b_publish_depth_files",
    "9b_load_depth_raster",
}

EXPECTED_EDGES = {
    ("0_check_forecast_rain", "1_trigger_simulation"),
    ("1_trigger_simulation", "2_download_results"),
    ("2_download_results", "3_calculate_depth"),
    ("2_download_results", "2b_archive_results"),
    ("2b_archive_results", "2c_archive_done"),
    ("2c_archive_done", "3b_publish_depth_files"),
    ("3_calculate_depth", "3b_publish_depth_files"),
    ("3_calculate_depth", "9b_load_depth_raster"),
    ("1_trigger_simulation", "0b_ensure_schema"),
    ("0b_ensure_schema", "3b_publish_depth_files"),
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


class FakeAirflowSkipException(Exception):
    pass


def module(name, **attrs):
    fake = types.ModuleType(name)
    fake.__dict__.update(attrs)
    return fake


def load_dag_module(path="dags/flood_mapping_dag.py", environment=None):
    """The stale-run guard is off unless a test sets FLOOD_STALE_RUN_MINUTES, because the tests use fixed slots in the past."""
    environment = {"FLOOD_STALE_RUN_MINUTES": "0"} if environment is None else environment
    fakes = {
        "airflow": module("airflow", DAG=FakeDag),
        "airflow.sdk": module("airflow.sdk", Asset=FakeAsset),
        "airflow.exceptions": module(
            "airflow.exceptions", AirflowException=RuntimeError, AirflowSkipException=FakeAirflowSkipException
        ),
        "airflow.providers": module("airflow.providers"),
        "airflow.providers.standard": module("airflow.providers.standard"),
        "airflow.providers.standard.operators": module("airflow.providers.standard.operators"),
        "airflow.providers.standard.operators.empty": module(
            "airflow.providers.standard.operators.empty", EmptyOperator=FakeOperator
        ),
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
        with patch.dict(sys.modules, fakes), patch.dict(os.environ, environment), patch("builtins.print"):
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

    def gate(self, rain_should_run, max_mm_hr, standing):
        self.dag_module.create_simulation = MagicMock()
        self.dag_module.create_simulation.get_rain_forecast.return_value = [{"values": {}}]
        self.dag_module.create_simulation.evaluate_rain_gate.return_value = {
            "should_run": rain_should_run, "max_intensity_mm_hr": max_mm_hr, "threshold_mm_hr": 5.0, "interval_count": 8
        }
        self.dag_module.standing_flood = MagicMock()
        self.dag_module.standing_flood.read_standing_flood.return_value = standing
        self.dag_module.psycopg2 = MagicMock()
        self.dag_module.DB_CONFIG = {}
        with patch("builtins.print"):
            return self.dag_module.task_check_forecast_rain(ti=MagicMock())

    DRY = {"stands": False, "reason": "no_run", "dry_runs_in_a_row": 0, "dry_runs_to_stop": 5, "newest_run_age_min": None}
    WET = {"stands": True, "reason": "standing_flood", "dry_runs_in_a_row": 0, "dry_runs_to_stop": 5, "newest_run_age_min": 11.0}

    def test_a_dry_state_with_a_dry_forecast_skips_every_downstream_task(self):
        self.assertIsNone(self.gate(False, 0.4, self.DRY))

    def test_a_forecast_at_the_threshold_runs_without_reading_the_flood(self):
        self.assertEqual(self.gate(True, 5.2, self.DRY), "1_trigger_simulation")
        self.dag_module.standing_flood.read_standing_flood.assert_not_called()

    def test_a_standing_flood_keeps_the_simulation_going_under_the_threshold(self):
        self.assertEqual(self.gate(False, 3.6, self.WET), "1_trigger_simulation")
        self.dag_module.standing_flood.read_standing_flood.assert_called_once_with(
            self.dag_module.psycopg2.connect.return_value, 3.6, self.dag_module.DRY_DEPTH_M
        )

    def test_the_gate_records_its_decision_for_the_backend(self):
        self.dag_module.forecast_mode = MagicMock()
        self.gate(True, 5.2, self.DRY)
        self.gate(False, 3.6, self.WET)
        self.gate(False, 0.4, self.DRY)

        calls = self.dag_module.forecast_mode.record_decision.call_args_list
        self.assertEqual([call.args[2:] for call in calls], [(5.2, 5.0, None, True), (3.6, 5.0, True, True), (0.4, 5.0, False, False)])

    def test_a_failed_status_write_does_not_stop_the_gate(self):
        self.dag_module.forecast_mode = MagicMock()
        self.dag_module.forecast_mode.record_decision.side_effect = RuntimeError("database down")

        self.assertEqual(self.gate(True, 5.2, self.DRY), "1_trigger_simulation")

    def test_ensure_schema_creates_the_tables_its_downstream_tasks_write(self):
        database = MagicMock()
        self.dag_module.database = database

        with patch("builtins.print"):
            self.dag_module.task_ensure_schema()

        self.assertEqual(
            sorted(call[0] for call in database.mock_calls),
            [
                "create_demo_pin_table.main",
                "create_edge_depth_tables.main",
                "create_flood_depth_raster_tables.main",
                "create_flood_extent_tables.main",
                "create_flood_run_output_table.main",
                "create_forecast_mode_table.main",
                "create_graph_edge_table.main",
                "create_timescale_tables.main",
            ],
        )

    def test_no_core_task_waits_on_a_routing_task(self):
        """A DAG run takes its state from its leaf tasks. The leaves are core tasks only, so a routing failure
        cannot turn the run red and break the next slot's hotstart (hotstart_policy)."""
        leaves = {t for t in self.dag.tasks if not any(up == t for up, _ in self.dag.edges)}

        self.assertEqual(leaves, {"3b_publish_depth_files", "9b_load_depth_raster"})

    def test_no_task_ingests_the_netcdf_into_a_database(self):
        self.assertFalse(any("netcdf" in task_id for task_id in self.dag.tasks))
        self.assertFalse(hasattr(self.dag_module, "task_upload_netcdf_postgres"))

    def test_a_failed_archive_does_not_stop_the_tile_build(self):
        self.assertEqual(self.dag.tasks["2c_archive_done"].kwargs["trigger_rule"], "all_done")
        self.assertNotIn("trigger_rule", self.dag.tasks["3b_publish_depth_files"].kwargs)

    def test_the_tile_build_is_not_a_task_of_this_dag(self):
        self.assertNotIn("9_build_flood_tiles", self.dag.tasks)
        self.assertFalse(hasattr(self.dag_module, "task_build_flood_tiles"))

    def test_load_depth_raster_declares_the_published_asset(self):
        self.assertEqual(
            self.dag.tasks["9b_load_depth_raster"].kwargs["outlets"], [FakeAsset("flood_depth_raster_tile")]
        )
        self.assertEqual(
            self.dag.tasks["3b_publish_depth_files"].kwargs["outlets"], [FakeAsset("flood_depth_files")]
        )
        self.assertEqual(
            sorted(name for name, task in self.dag.tasks.items() if "outlets" in task.kwargs),
            ["3b_publish_depth_files", "9b_load_depth_raster"],
        )


class ArchiveTaskTests(unittest.TestCase):
    def setUp(self):
        self.dag_module = load_dag_module()
        spec = importlib.util.spec_from_file_location("archive_results", ROOT / "scripts/archive_results.py")
        self.dag_module.archive_results = importlib.util.module_from_spec(spec)
        # dataclasses looks the module up by name while it builds a class.
        sys.modules["archive_results"] = self.dag_module.archive_results
        self.addCleanup(sys.modules.pop, "archive_results", None)
        spec.loader.exec_module(self.dag_module.archive_results)
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.nc = Path(self.tmp.name) / "results" / "77" / "results_3di.nc"
        self.nc.parent.mkdir(parents=True)
        self.nc.write_bytes(b"nc")
        self.dag_module.ARCHIVE_DIR = str(Path(self.tmp.name) / "archive")
        # The free-space floor has its own tests in test_archive_results.py. Here it must not read the real disk.
        self.dag_module.ARCHIVE_MIN_FREE_GB = 0
        self.dag_module.EDGE_EXPORT_DIR = str(Path(self.tmp.name) / "no_export")
        self.dag_module.create_simulation = MagicMock()
        self.dag_module.create_simulation.iso_utc.return_value = "2026-10-09T06:00:00Z"
        self.dag_module.run_slot = MagicMock()

    def ti(self, source):
        values = {
            ("1_trigger_simulation", "rain_ingested"): {"source": source, "total_mm": 3.0},
            ("1_trigger_simulation", "sim_id"): 77,
            ("2_download_results", "nc_path"): str(self.nc),
        }
        ti = MagicMock()
        ti.xcom_pull.side_effect = lambda task_ids, key: values[(task_ids, key)]
        return ti

    def test_real_rain_archives_the_file_and_the_record(self):
        with patch("builtins.print"):
            self.dag_module.task_archive_results(ti=self.ti("tomorrow.io"))

        archived = Path(self.dag_module.ARCHIVE_DIR) / "77"
        self.assertEqual((archived / "results_3di.nc").read_bytes(), b"nc")
        self.assertIn('"run_timestamp": "2026-10-09T06:00:00Z"', (archived / "run_record.json").read_text())

    def test_test_rain_archives_nothing(self):
        with patch("builtins.print") as printed:
            self.dag_module.task_archive_results(ti=self.ti("fixed_test_rain"))

        self.assertFalse(Path(self.dag_module.ARCHIVE_DIR).exists())
        self.assertIn("Skipping the archive", printed.call_args[0][0])


class DepthRunTests(unittest.TestCase):
    """Tasks 3b and 9b name the run from the depth folder, not from an XCom of a removed task."""

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

    def load_depth_raster_with(self, forecast_mode):
        raster_load = MagicMock()
        raster_load.load_run.return_value = ["a"]
        self.dag_module.raster_load = raster_load
        self.dag_module.forecast_mode = forecast_mode
        self.dag_module.create_simulation = MagicMock()
        self.dag_module.DB_CONFIG = {}
        event = types.SimpleNamespace(extra={})
        with patch("builtins.print"):
            return self.dag_module.task_load_depth_raster(
                ti=self.ti, outlet_events={FakeAsset("flood_depth_raster_tile"): event}
            )

    def test_load_depth_raster_moves_the_forecast_mode_of_its_slot_to_live(self):
        forecast_mode = MagicMock()

        self.load_depth_raster_with(forecast_mode)

        forecast_mode.mark_live.assert_called_once()

    def test_a_failed_move_to_live_does_not_fail_the_task(self):
        forecast_mode = MagicMock()
        forecast_mode.mark_live.side_effect = RuntimeError("database down")

        self.assertEqual(self.load_depth_raster_with(forecast_mode)["timesteps"], 1)

    def test_publish_depth_files_announces_the_run_and_its_folder(self):
        event = types.SimpleNamespace(extra={})

        with patch("builtins.print"):
            result = self.dag_module.task_publish_depth_files(
                ti=self.ti, outlet_events={FakeAsset("flood_depth_files"): event}
            )

        expected = {"run_ts": "20260924T170639", "depth_dir": self.tmp.name}
        self.assertEqual(result, expected)
        self.assertEqual(event.extra, expected)

    def test_a_missing_depth_folder_fails_the_task(self):
        self.ti.xcom_pull.side_effect = lambda task_ids, key=None: None

        with self.assertRaises(ValueError):
            self.dag_module.task_load_depth_raster(ti=self.ti)


class StaleRunGuardTests(unittest.TestCase):
    NOW = datetime(2026, 10, 13, 6, 0, tzinfo=timezone.utc)
    TASKS = (
        "task_check_forecast_rain",
        "task_run_simulation",
        "task_calculate_depth",
        "task_publish_depth_files",
        "task_load_depth_raster",
    )

    def load(self, limit="120"):
        dag_module = load_dag_module(environment={"FLOOD_STALE_RUN_MINUTES": limit})
        self.work = {
            name: MagicMock()
            for name in ("create_simulation", "netcdf_input", "raster_load", "psycopg2", "forecast_mode", "standing_flood")
        }
        for name, mock in self.work.items():
            setattr(dag_module, name, mock)
        dag_module.run_slot = lambda kwargs: kwargs["logical_date"]
        dag_module.depth_run = MagicMock(side_effect=ValueError("work started"))
        fixed_now = self.NOW

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now

        dag_module.datetime = FixedDatetime
        return dag_module

    def call(self, dag_module, task_name, slot):
        kwargs = {"ti": MagicMock(), "logical_date": slot, "dag": MagicMock(), "outlet_events": MagicMock()}
        with patch("builtins.print"):
            return getattr(dag_module, task_name)(**kwargs)

    def test_a_three_hour_old_slot_skips_each_guarded_task_before_any_work(self):
        dag_module = self.load()
        slot = datetime(2026, 10, 13, 3, 0, tzinfo=timezone.utc)
        expected = (
            "Run slot 2026-10-13T03:00:00Z is 180 minutes old, over the limit of 120 minutes "
            "(FLOOD_STALE_RUN_MINUTES). Skipping so an old run does no work."
        )
        for task_name in self.TASKS:
            with self.subTest(task=task_name):
                with self.assertRaises(FakeAirflowSkipException) as raised:
                    self.call(dag_module, task_name, slot)
                self.assertEqual(str(raised.exception), expected)
        for name, mock in self.work.items():
            self.assertEqual(mock.mock_calls, [], name)
        dag_module.depth_run.assert_not_called()

    def test_a_twenty_minute_old_slot_runs_the_task(self):
        dag_module = self.load()
        slot = datetime(2026, 10, 13, 5, 40, tzinfo=timezone.utc)
        dag_module.create_simulation.get_rain_forecast.return_value = []

        with self.assertRaises(ValueError) as raised:
            self.call(dag_module, "task_check_forecast_rain", slot)

        self.assertIn("no rain forecast", str(raised.exception))
        dag_module.create_simulation.get_rain_forecast.assert_called_once()
        with self.assertRaises(ValueError) as raised:
            self.call(dag_module, "task_publish_depth_files", slot)
        self.assertEqual(str(raised.exception), "work started")

    def test_a_slot_exactly_at_the_limit_runs(self):
        dag_module = self.load()
        slot = datetime(2026, 10, 13, 4, 0, tzinfo=timezone.utc)

        with self.assertRaises(ValueError) as raised:
            self.call(dag_module, "task_publish_depth_files", slot)

        self.assertEqual(str(raised.exception), "work started")

    def test_the_limit_zero_never_skips(self):
        dag_module = self.load(limit="0")
        slot = datetime(2026, 10, 10, 3, 45, tzinfo=timezone.utc)

        with self.assertRaises(ValueError) as raised:
            self.call(dag_module, "task_publish_depth_files", slot)

        self.assertEqual(str(raised.exception), "work started")

    def test_an_invalid_limit_fails_the_import_and_names_the_variable(self):
        with self.assertRaises(ValueError) as raised:
            load_dag_module(environment={"FLOOD_STALE_RUN_MINUTES": "two hours"})

        self.assertEqual(
            str(raised.exception),
            "FLOOD_STALE_RUN_MINUTES must be a whole number of minutes, 0 or more, got 'two hours'",
        )

    def test_the_default_limit_is_two_hours(self):
        with patch.dict(os.environ):
            os.environ.pop("FLOOD_STALE_RUN_MINUTES", None)
            self.assertEqual(load_dag_module(environment={}).STALE_RUN_MINUTES, 120)

    def test_the_guarded_tasks_keep_their_names_for_airflow(self):
        dag_module = self.load()

        self.assertEqual([getattr(dag_module, name).__name__ for name in self.TASKS], list(self.TASKS))


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
