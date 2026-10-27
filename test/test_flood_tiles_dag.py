"""Checks the flood_tiles DAG without Airflow installed, with the stand-ins of test_flood_mapping_dag_graph.py.

Run it as a file: python3 test/test_flood_tiles_dag.py
"""

import importlib.util
import os
import types
import unittest
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("dag_graph_fakes", ROOT / "test/test_flood_mapping_dag_graph.py")
fakes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fakes)

ANNOUNCED = fakes.FakeAsset("flood_depth_files")
ENV = {"MINIO_ENDPOINT": "http://minio:9000", "MINIO_ACCESS_KEY": "k", "MINIO_SECRET_KEY": "s"}


def event(run_ts, depth_dir):
    return types.SimpleNamespace(extra={"run_ts": run_ts, "depth_dir": depth_dir})


class FloodTilesGraphTests(unittest.TestCase):
    def setUp(self):
        self.dag = fakes.load_dag_module("dags/flood_tiles_dag.py").dag

    def test_dag_id(self):
        self.assertEqual(self.dag.dag_id, "flood_tiles")

    def test_runs_on_the_depth_files_event_with_one_task(self):
        self.assertEqual(self.dag.kwargs["schedule"], [ANNOUNCED])
        self.assertEqual(set(self.dag.tasks), {"9_build_flood_tiles"})
        self.assertEqual(self.dag.edges, set())
        self.assertEqual(self.dag.tasks["9_build_flood_tiles"].kwargs["inlets"], [ANNOUNCED])

    def test_keeps_the_retries_and_overlap_the_tile_task_had_in_the_core_dag(self):
        self.assertEqual(self.dag.kwargs["max_active_runs"], 2)
        self.assertEqual(self.dag.kwargs["default_args"]["retries"], 1)
        self.assertEqual(self.dag.kwargs["default_args"]["retry_delay"], timedelta(minutes=1))


class BuildFloodTilesTests(unittest.TestCase):
    def setUp(self):
        self.dag_module = fakes.load_dag_module("dags/flood_tiles_dag.py")
        self.publish = MagicMock()
        self.publish.publish_run.return_value = {"a": MagicMock(is_empty=False), "b": MagicMock(is_empty=True)}
        self.dag_module.publish = self.publish
        self.dag_module.DB_CONFIG = {}
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dirs = {}
        for run_ts in ("20260924T170639", "20260924T172139"):
            self.dirs[run_ts] = str(Path(self.tmp.name) / run_ts)
            os.mkdir(self.dirs[run_ts])

    def build(self, **kwargs):
        with patch.dict(os.environ, ENV), patch("builtins.print"):
            return self.dag_module.task_build_flood_tiles(**kwargs)

    def triggered_by(self, *run_ts):
        return {"triggering_asset_events": {ANNOUNCED: [event(value, self.dirs[value]) for value in run_ts]}}

    def test_a_triggering_event_builds_its_run_from_the_announced_folder(self):
        result = self.build(**self.triggered_by("20260924T170639"))

        self.assertEqual(len(result), 1)
        self.assertEqual(
            {key: result[0][key] for key in ("run_ts", "timesteps", "flooded_timesteps")},
            {"run_ts": "20260924T170639", "timesteps": 2, "flooded_timesteps": 1},
        )
        self.assertEqual(self.publish.publish_run.call_args.args[:2], (self.dirs["20260924T170639"], "20260924T170639"))
        self.assertEqual(
            self.publish.publish_run.call_args.kwargs,
            {
                "workers": 2,
                "db_conn": self.dag_module.psycopg2.connect.return_value,
                "tile_steps": 2,
                "keep_runs": 8,
                "cleanup_dirs": [
                    "/opt/airflow/data/mapping/results",
                    "/opt/airflow/data/mapping/output_depths",
                    "/opt/airflow/data/mapping/flood_extent_work",
                ],
                "cleanup_max_age_hours": 24,
            },
        )

    def test_events_folded_into_one_run_all_get_their_tiles_oldest_first(self):
        result = self.build(**self.triggered_by("20260924T172139", "20260924T170639"))

        self.assertEqual([built["run_ts"] for built in result], ["20260924T170639", "20260924T172139"])
        self.assertEqual(self.publish.publish_run.call_count, 2)

    def test_a_manual_run_builds_the_newest_announced_run(self):
        inlet_events = {ANNOUNCED: [event(run_ts, self.dirs[run_ts]) for run_ts in sorted(self.dirs)]}

        result = self.build(inlet_events=inlet_events)

        self.assertEqual([built["run_ts"] for built in result], ["20260924T172139"])

    def test_a_manual_run_picks_the_newest_run_whatever_the_event_order(self):
        newest_first = [event(run_ts, self.dirs[run_ts]) for run_ts in sorted(self.dirs, reverse=True)]

        result = self.build(inlet_events={ANNOUNCED: newest_first})

        self.assertEqual([built["run_ts"] for built in result], ["20260924T172139"])

    def test_an_event_without_a_run_fails_the_task(self):
        with self.assertRaises(ValueError):
            self.build(inlet_events={ANNOUNCED: []})

    def test_a_missing_depth_folder_fails_the_task_when_nothing_was_built(self):
        os.rmdir(self.dirs["20260924T170639"])

        with self.assertRaises(ValueError):
            self.build(**self.triggered_by("20260924T170639"))

    def test_a_folder_lost_mid_batch_does_not_stop_the_other_runs(self):
        os.rmdir(self.dirs["20260924T170639"])

        result = self.build(**self.triggered_by("20260924T170639", "20260924T172139"))

        self.assertEqual([built["run_ts"] for built in result], ["20260924T172139"])


if __name__ == "__main__":
    unittest.main()
