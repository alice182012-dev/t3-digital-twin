"""Checks the routing_adapter DAG without Airflow installed, with the stand-ins of test_flood_mapping_dag_graph.py.

Run it as a file: python3 test/test_routing_adapter_dag.py
"""

import importlib.util
import os
import sys
import types
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dag_graph_fakes", ROOT / "test/test_flood_mapping_dag_graph.py")
fakes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fakes)

sys.path.insert(0, str(ROOT / "scripts/database"))
import run_output  # noqa: E402
from test_run_output import FakeConnection, published  # noqa: E402

PUBLISHED = fakes.FakeAsset("flood_depth_raster_tile")
ROAD_VALUES = fakes.FakeAsset("flood_road_values")


def load_routing_module():
    return fakes.load_dag_module("dags/routing_adapter_dag.py")


def event(run_ts):
    return types.SimpleNamespace(extra={"run_ts": run_ts})


def triggered_by(*run_ts):
    return {PUBLISHED: [event(value) for value in run_ts]}


class RoutingAdapterGraphTests(unittest.TestCase):
    def setUp(self):
        self.dag = load_routing_module().dag

    def test_dag_id(self):
        self.assertEqual(self.dag.dag_id, "routing_adapter")

    def test_holds_exactly_the_four_routing_tasks(self):
        self.assertEqual(
            set(self.dag.tasks),
            {"load_road_segments", "flood_on_roads", "prune_flood_road_values", "9c_build_edge_depth_table"},
        )

    def test_the_road_tasks_run_in_order_and_9c_waits_for_nothing(self):
        self.assertEqual(
            self.dag.edges,
            {("load_road_segments", "flood_on_roads"), ("flood_on_roads", "prune_flood_road_values")},
        )

    def test_runs_on_the_asset_9b_emits(self):
        self.assertEqual(self.dag.kwargs["schedule"], [PUBLISHED])

    def test_the_core_dag_emits_the_asset_this_dag_runs_on(self):
        core = fakes.load_dag_module().dag

        self.assertEqual(core.tasks["9b_load_depth_raster"].kwargs["outlets"], self.dag.kwargs["schedule"])

    def test_the_core_dag_holds_none_of_the_routing_tasks(self):
        core = fakes.load_dag_module().dag

        self.assertEqual(set(core.tasks) & set(self.dag.tasks), set())

    def test_every_task_runs_in_the_routing_pool(self):
        self.assertEqual({task.kwargs["pool"] for task in self.dag.tasks.values()}, {"routing_adapter"})

    def test_9c_takes_the_pool_slot_before_the_road_tasks(self):
        weights = {name: task.kwargs.get("priority_weight", 1) for name, task in self.dag.tasks.items()}

        self.assertEqual(
            weights,
            {"load_road_segments": 1, "flood_on_roads": 1, "prune_flood_road_values": 1, "9c_build_edge_depth_table": 10},
        )

    def test_the_tasks_that_need_a_run_read_the_published_asset(self):
        inlets = {name: task.kwargs.get("inlets") for name, task in self.dag.tasks.items()}

        self.assertEqual(
            inlets,
            {
                "load_road_segments": None,
                "flood_on_roads": [PUBLISHED],
                "prune_flood_road_values": None,
                "9c_build_edge_depth_table": [PUBLISHED],
            },
        )


class PublishedRunTests(unittest.TestCase):
    def setUp(self):
        self.dag_module = load_routing_module()

    def run_ts(self, **context):
        with patch("builtins.print"):
            return self.dag_module.published_run_ts(context)

    def test_a_triggered_run_takes_the_run_ts_of_its_event(self):
        self.assertEqual(self.run_ts(triggering_asset_events=triggered_by("20261007T150000")), "20261007T150000")

    def test_folded_events_build_the_newest_run(self):
        context = triggered_by("20261007T151500", "20261007T150000")

        self.assertEqual(self.run_ts(triggering_asset_events=context), "20261007T151500")

    def test_a_manual_run_takes_the_newest_event_9b_emitted(self):
        inlet_events = {PUBLISHED: [event("20261007T143000"), event("20261007T150000"), event("20261007T144500")]}

        self.assertEqual(self.run_ts(triggering_asset_events={}, inlet_events=inlet_events), "20261007T150000")

    def test_events_without_a_run_ts_fail_the_task(self):
        empty = {PUBLISHED: [types.SimpleNamespace(extra={})]}

        with self.assertRaises(ValueError):
            self.run_ts(triggering_asset_events=empty)

    def test_no_event_at_all_fails_the_task(self):
        with self.assertRaises(ValueError):
            self.run_ts(triggering_asset_events={}, inlet_events={PUBLISHED: []})


class RoutingTaskTests(unittest.TestCase):
    """The task bodies moved from flood_mapping_dag.py. Only the source of run_ts changed."""

    def setUp(self):
        self.dag_module = load_routing_module()
        self.dag_module.DB_CONFIG = {}
        self.dag_module.run_output = run_output
        self.ti = MagicMock()
        self.context = {"ti": self.ti, "triggering_asset_events": triggered_by("20260924T170639")}

    def test_flood_on_roads_computes_the_run_of_the_event_and_publishes_it(self):
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

        outlet_events = {ROAD_VALUES: types.SimpleNamespace(extra=None)}

        with patch("builtins.print"):
            result = self.dag_module.task_flood_on_roads(**self.context, outlet_events=outlet_events)

        self.assertEqual(result, {"run_ts": "20260924T170639", "timesteps": 2, "rows": 6})
        self.assertEqual(flood_on_roads.compute.call_args.args[1:], ("20260924T170639",))
        self.assertEqual(outlet_events[ROAD_VALUES].extra, {"run_ts": "20260924T170639"})

    def built_table(self, path="/opt/airflow/edge_depth_tables/20260924T170639.bin"):
        return MagicMock(
            path=Path(path), graph_hash="a" * 64, graph_loaded=False, edge_count=67833, step_count=8,
            wet_edges=(10, 20, 30, 0, 0, 0, 0, 0), sample_seconds=(1.0,) * 8, size_bytes=1085368, seconds=12.5,
        )

    def test_build_edge_depth_table_builds_and_publishes_the_run_of_the_event(self):
        build_edge_depth = self.dag_module.build_edge_depth = MagicMock()
        build_edge_depth.build_table.return_value = self.built_table()
        publish = self.dag_module.publish_edge_depth = MagicMock()
        publish.publish_table.return_value = MagicMock(
            latest="20260924T170639.bin", previous="20260924T165639.bin", moved=True, removed=("20260924T150639.bin",),
        )

        with patch("builtins.print"):
            result = self.dag_module.task_build_edge_depth_table(**self.context)

        args = build_edge_depth.build_table.call_args.args
        self.assertEqual(args[1:], ("20260924T170639", "/opt/airflow/data/mapping/graph_export", "/opt/airflow/edge_depth_tables"))
        self.assertEqual(result["run_ts"], "20260924T170639")
        self.assertEqual((result["edge_count"], result["steps"], result["bytes"]), (67833, 8, 1085368))
        self.assertEqual(result["wet_edges"], [10, 20, 30, 0, 0, 0, 0, 0])
        self.assertEqual(
            result["published"],
            {"latest": "20260924T170639.bin", "previous": "20260924T165639.bin", "moved": True,
             "removed": ["20260924T150639.bin"]},
        )
        self.ti.xcom_push.assert_called_once_with(key="edge_depth_table", value=result)
        publish.publish_table.assert_called_once_with("/opt/airflow/edge_depth_tables", "20260924T170639.bin", keep=8)

    def test_the_edge_table_folders_can_be_set_by_environment(self):
        env = {"EDGE_EXPORT_DIR": "/exports", "EDGE_TABLE_DIR": "/tables", "EDGE_TABLE_KEEP_RUNS": "5"}
        with patch.dict(os.environ, env):
            dag_module = load_routing_module()
        dag_module.DB_CONFIG = {}
        dag_module.build_edge_depth = MagicMock()
        dag_module.build_edge_depth.build_table.return_value = self.built_table("/tables/x.bin")
        dag_module.publish_edge_depth = MagicMock()
        dag_module.publish_edge_depth.publish_table.return_value = MagicMock(removed=())

        with patch("builtins.print"):
            dag_module.task_build_edge_depth_table(**self.context)

        args = dag_module.build_edge_depth.build_table.call_args.args
        self.assertEqual(args[2:], ("/exports", "/tables"))
        self.assertEqual(dag_module.publish_edge_depth.publish_table.call_args.kwargs, {"keep": 5})

    def test_compose_defaults_the_edge_table_count_to_the_dag_default(self):
        compose = (ROOT / "compose.yml").read_text(encoding="utf-8")
        self.assertIn("EDGE_TABLE_KEEP_RUNS: ${EDGE_TABLE_KEEP_RUNS:-8}", compose)

    def test_a_failed_build_publishes_nothing_so_latest_stays(self):
        self.dag_module.build_edge_depth = MagicMock()
        self.dag_module.build_edge_depth.build_table.side_effect = RuntimeError("no export")
        self.dag_module.publish_edge_depth = MagicMock()

        with patch("builtins.print"), self.assertRaises(RuntimeError):
            self.dag_module.task_build_edge_depth_table(**self.context)

        self.dag_module.publish_edge_depth.publish_table.assert_not_called()
        self.ti.xcom_push.assert_not_called()

    def test_a_failed_publish_fails_the_task_and_reports_nothing(self):
        self.dag_module.build_edge_depth = MagicMock()
        self.dag_module.build_edge_depth.build_table.return_value = self.built_table("/tables/x.bin")
        self.dag_module.publish_edge_depth = MagicMock()
        self.dag_module.publish_edge_depth.publish_table.side_effect = ValueError("not a valid table")

        with patch("builtins.print"), self.assertRaises(ValueError):
            self.dag_module.task_build_edge_depth_table(**self.context)

        self.ti.xcom_push.assert_not_called()

    def build_and_publish(self, conn, latest="20260924T170639.bin", publish_error=None):
        self.dag_module.build_edge_depth = MagicMock()
        self.dag_module.build_edge_depth.build_table.return_value = self.built_table()
        self.dag_module.publish_edge_depth = MagicMock()
        self.dag_module.publish_edge_depth.publish_table.return_value = MagicMock(
            latest=latest, previous="20260924T165639.bin", moved=latest == "20260924T170639.bin", removed=(),
        )
        self.dag_module.publish_edge_depth.publish_table.side_effect = publish_error
        self.dag_module.psycopg2 = types.SimpleNamespace(connect=lambda **config: conn)
        with patch("builtins.print"):
            self.dag_module.task_build_edge_depth_table(**self.context)

    def test_a_published_table_records_its_edge_depth_row(self):
        conn = FakeConnection()

        self.build_and_publish(conn)

        self.assertEqual(published(conn), {("20260924T170639", "edge_depth")})

    def test_an_older_table_that_latest_does_not_name_records_no_row(self):
        conn = FakeConnection()

        self.build_and_publish(conn, latest="20260924T171639.bin")

        self.assertEqual(self.ti.xcom_push.call_args.kwargs["value"]["published"]["moved"], False)
        self.assertEqual(published(conn), set())

    def test_a_failed_publish_records_no_row(self):
        conn = FakeConnection()

        with self.assertRaises(ValueError):
            self.build_and_publish(conn, publish_error=ValueError("not a valid table"))

        self.assertEqual(published(conn), set())

    def pruned(self, **fields):
        result = dict(
            newest_run=datetime(2026, 10, 9, 16, 0), cutoff=datetime(2026, 10, 8, 16, 0),
            runs_deleted=2, rows_deleted=70000, runs_kept=97,
        )
        result.update(fields)
        return MagicMock(**result)

    def test_prune_keeps_24_hours_by_default_and_reports_what_it_deleted(self):
        prune = self.dag_module.prune_flood_road_values = MagicMock()
        prune.prune.return_value = self.pruned()

        with patch("builtins.print"):
            result = self.dag_module.task_prune_flood_road_values(**self.context)

        self.assertEqual(prune.prune.call_args.args[1:], (24,))
        self.assertEqual(
            result,
            {"newest_run": "2026-10-09T16:00:00", "cutoff": "2026-10-08T16:00:00", "runs_deleted": 2,
             "rows_deleted": 70000, "runs_kept": 97},
        )

    def test_prune_of_an_empty_table_reports_zero(self):
        prune = self.dag_module.prune_flood_road_values = MagicMock()
        prune.prune.return_value = self.pruned(newest_run=None, cutoff=None, runs_deleted=0, rows_deleted=0, runs_kept=0)

        with patch("builtins.print"):
            result = self.dag_module.task_prune_flood_road_values(**self.context)

        self.assertEqual(
            result, {"newest_run": None, "cutoff": None, "runs_deleted": 0, "rows_deleted": 0, "runs_kept": 0}
        )

    def test_the_prune_window_can_be_set_by_environment(self):
        with patch.dict(os.environ, {"FLOOD_ROAD_VALUES_KEEP_HOURS": "6"}):
            dag_module = load_routing_module()
        dag_module.DB_CONFIG = {}
        dag_module.prune_flood_road_values = MagicMock()
        dag_module.prune_flood_road_values.prune.return_value = self.pruned()

        with patch("builtins.print"):
            dag_module.task_prune_flood_road_values(**self.context)

        self.assertEqual(dag_module.prune_flood_road_values.prune.call_args.args[1:], (6,))

    def test_a_prune_window_that_is_not_a_positive_integer_fails_the_task_and_deletes_nothing(self):
        for value in ("0", "-3", "1.5", "abc", ""):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"FLOOD_ROAD_VALUES_KEEP_HOURS": value}):
                    dag_module = load_routing_module()
                dag_module.DB_CONFIG = {}
                dag_module.prune_flood_road_values = MagicMock()

                with patch("builtins.print"), self.assertRaisesRegex(ValueError, "FLOOD_ROAD_VALUES_KEEP_HOURS"):
                    dag_module.task_prune_flood_road_values(**self.context)

                dag_module.prune_flood_road_values.prune.assert_not_called()

    def test_load_road_segments_loads_the_production_roads_file(self):
        loader = self.dag_module.load_road_segments = MagicMock(
            DEFAULT_ROADS_PATH="/opt/airflow/data/mapping/inputs/toa-do-duong-hanoi.geojson"
        )
        loader.load.return_value = MagicMock(inserted=0, updated=0, deleted=0, total=35652)

        with patch.dict(os.environ), patch("builtins.print"):
            os.environ.pop("ROADS_GEOJSON_PATH", None)
            result = self.dag_module.task_load_road_segments(**self.context)

        self.assertEqual(result, {"inserted": 0, "updated": 0, "deleted": 0, "total": 35652})
        self.assertEqual(loader.load.call_args.args[1], "/opt/airflow/data/mapping/inputs/toa-do-duong-hanoi.geojson")

    def test_a_bad_roads_file_fails_the_task(self):
        self.dag_module.load_road_segments = MagicMock(DEFAULT_ROADS_PATH="/x.geojson")
        self.dag_module.load_road_segments.load.side_effect = ValueError("feature 0 has no properties['@id']")

        with patch("builtins.print"), self.assertRaises(ValueError):
            self.dag_module.task_load_road_segments(**self.context)


if __name__ == "__main__":
    unittest.main()
