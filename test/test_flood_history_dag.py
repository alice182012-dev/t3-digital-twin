"""Checks the flood_history DAG without Airflow installed, with the stand-ins of test_flood_mapping_dag_graph.py.

Run it as a file: python3 test/test_flood_history_dag.py
"""

import importlib.util
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dag_graph_fakes", ROOT / "test/test_flood_mapping_dag_graph.py")
fakes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fakes)

EDGE_DEPTH_ROWS = fakes.FakeAsset("edge_depth")


def load_history_module():
    return fakes.load_dag_module("dags/flood_history_dag.py")


def event(run_ts):
    return types.SimpleNamespace(extra={"run_ts": run_ts})


class FloodHistoryGraphTests(unittest.TestCase):
    def setUp(self):
        self.dag = load_history_module().dag

    def test_dag_id(self):
        self.assertEqual(self.dag.dag_id, "flood_history")

    def test_holds_one_task_that_reads_the_asset_in_the_default_pool(self):
        task = self.dag.tasks["load_depth_history"]

        self.assertEqual(set(self.dag.tasks), {"load_depth_history"})
        self.assertEqual(task.kwargs["inlets"], [EDGE_DEPTH_ROWS])
        self.assertNotIn("pool", task.kwargs)

    def test_runs_on_the_asset_9c_emits(self):
        routing = fakes.load_dag_module("dags/routing_adapter_dag.py").dag

        self.assertEqual(self.dag.kwargs["schedule"], [EDGE_DEPTH_ROWS])
        self.assertEqual(routing.tasks["9c_build_edge_depth_table"].kwargs["outlets"], [EDGE_DEPTH_ROWS])


class LoadDepthHistoryTaskTests(unittest.TestCase):
    def setUp(self):
        self.dag_module = load_history_module()
        self.calls = []
        self.dag_module.create_timescale_tables = MagicMock(main=lambda: self.calls.append("schema"))
        self.dag_module.load_run = MagicMock(load=self.load)

    def load(self, run_ts):
        self.calls.append(run_ts)
        moment = datetime(2026, 9, 24, 9, 45, tzinfo=timezone.utc)
        return MagicMock(
            written=(moment,), skipped=(), rows=("row",) * 3, describe=lambda: f"Run {run_ts}: loaded"
        )

    def run_task(self, **context):
        with patch("builtins.print"):
            return self.dag_module.task_load_depth_history(**context)

    def test_ensures_the_schema_then_loads_the_run_of_the_event(self):
        result = self.run_task(triggering_asset_events={EDGE_DEPTH_ROWS: [event("20260924T164500")]})

        self.assertEqual(self.calls, ["schema", "20260924T164500"])
        self.assertEqual(
            result, [{"run_ts": "20260924T164500", "moments_written": 1, "moments_skipped": 0, "rows": 3}]
        )

    def test_folded_events_load_every_run_oldest_first(self):
        self.run_task(triggering_asset_events={EDGE_DEPTH_ROWS: [event("20260924T170000"), event("20260924T164500")]})

        self.assertEqual(self.calls, ["schema", "20260924T164500", "20260924T170000"])

    def test_a_manual_run_loads_the_newest_published_run(self):
        inlet_events = {EDGE_DEPTH_ROWS: [event("20260924T164500"), event("20260924T171500"), event("20260924T170000")]}

        self.run_task(triggering_asset_events={}, inlet_events=inlet_events)

        self.assertEqual(self.calls, ["schema", "20260924T171500"])

    def test_events_without_a_run_ts_fail_before_touching_the_database(self):
        with self.assertRaisesRegex(ValueError, "No edge_depth event carries a run_ts"):
            self.run_task(triggering_asset_events={EDGE_DEPTH_ROWS: [types.SimpleNamespace(extra={})]})

        self.assertEqual(self.calls, [])

    def test_a_failed_load_fails_the_task(self):
        self.dag_module.load_run = MagicMock(load=MagicMock(side_effect=ValueError("no flood_depth_raster_tile rows")))

        with self.assertRaises(ValueError):
            self.run_task(triggering_asset_events={EDGE_DEPTH_ROWS: [event("20260924T164500")]})


if __name__ == "__main__":
    unittest.main()
