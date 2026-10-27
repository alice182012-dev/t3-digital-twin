"""Checks that create_simulation.py starts each 3Di run on its 15-minute slot.

The threedi_api_client modules are stand-ins, so this runs without the client installed:
python3 test/test_create_simulation_cycle.py
"""

import importlib.util
import json
import os
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))  # create_simulation.py imports rain_replay as a top-level module


class Model:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeApi:
    """Records every 3Di call. Saved-state ids count up from 501."""

    def __init__(self, initial_saved_states=(), fail_attach=False):
        self.calls = []
        self.initial_saved_states = list(initial_saved_states)
        self.fail_attach = fail_attach
        self.next_saved_state_id = 501

    def simulations_from_template(self, from_template):
        self.calls.append(("from_template", from_template))
        return Model(id=42)

    def simulations_events_rain_timeseries_create(self, sim_id, rain):
        self.calls.append(("rain", rain))

    def simulations_initial_saved_state_list(self, simulation_pk):
        self.calls.append(("initial_list", simulation_pk))
        return Model(count=len(self.initial_saved_states), results=[Model(id=i) for i in self.initial_saved_states])

    def simulations_initial_saved_state_delete(self, id, simulation_pk):
        self.calls.append(("initial_delete", id))

    def simulations_initial_saved_state_create(self, simulation_pk, data):
        self.calls.append(("initial_create", data))
        if self.fail_attach:
            raise RuntimeError("saved state expired")

    def simulations_create_saved_states_timed_create(self, sim_id, timed):
        self.calls.append(("timed_state", timed))
        saved = Model(id=self.next_saved_state_id)
        self.next_saved_state_id += 1
        return saved

    def simulations_actions_create(self, sim_id, action):
        self.calls.append(("action", action.name))

    def simulations_status_list(self, sim_id):
        return Model(name="finished")

    def of(self, kind):
        return [value for name, value in self.calls if name == kind]


def load_create_simulation(api=None):
    openapi = types.ModuleType("threedi_api_client.openapi")
    for name in ("Action", "FromTemplate", "TimedSavedState", "TimeseriesRain"):
        setattr(openapi, name, type(name, (Model,), {}))
    openapi.ApiException = type("ApiException", (Exception,), {})
    fakes = {
        "threedi_api_client": types.ModuleType("threedi_api_client"),
        "threedi_api_client.openapi": openapi,
        "threedi_client": types.ModuleType("threedi_client"),
        "requests": types.ModuleType("requests"),
    }
    fakes["threedi_client"].get_client = lambda: api
    fakes["requests"].get = MagicMock()
    spec = importlib.util.spec_from_file_location("create_simulation_under_test", ROOT / "scripts/create_simulation.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, fakes), patch.dict(os.environ, {"SIMULATION_DURATION": "7200"}):
        spec.loader.exec_module(module)
    return module


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def rain_at(*start_times):
    return [{"startTime": value, "values": {"precipitationIntensity": 3.6}} for value in start_times]


class ClockSlotTests(unittest.TestCase):
    def test_floors_to_the_quarter_hour(self):
        module = load_create_simulation()

        self.assertEqual(module.clock_slot(utc(2026, 9, 26, 10, 14, 59)), utc(2026, 9, 26, 10, 0))
        self.assertEqual(module.clock_slot(utc(2026, 9, 26, 10, 15, 0)), utc(2026, 9, 26, 10, 15))
        self.assertEqual(module.clock_slot(utc(2026, 9, 26, 10, 29, 59, 999999)), utc(2026, 9, 26, 10, 15))


class RainValuesTests(unittest.TestCase):
    def test_offsets_are_relative_to_the_slot_and_clamped_at_zero(self):
        module = load_create_simulation()
        intervals = rain_at("2026-09-26T10:10:00Z", "2026-09-26T10:15:00Z", "2026-09-26T10:30:00Z")

        values = module.build_rain_values(intervals, start=utc(2026, 9, 26, 10, 15))

        self.assertEqual([item[0] for item in values], [0, 0, 900])

    def test_without_a_start_offsets_are_relative_to_the_first_interval(self):
        module = load_create_simulation()

        values = module.build_rain_values(rain_at("2026-09-26T10:10:00Z", "2026-09-26T10:25:00Z"))

        self.assertEqual([item[0] for item in values], [0, 900])


class RunStartTests(unittest.TestCase):
    def run_forecast(self, api, state_file, **kwargs):
        module = load_create_simulation(api)
        with patch("builtins.print"):
            return module.run_forecast_process(state_file, **kwargs)

    def test_simulation_starts_at_the_given_slot(self):
        api = FakeApi()
        with patch.dict(os.environ, {"FLOOD_TEST_RAIN_MM_HR": ""}):
            self.run_forecast(
                api, "/nonexistent/state.json", rain_intervals=rain_at("2026-09-26T10:15:00Z", "2026-09-26T10:30:00Z"),
                use_saved_state=False, slot_start=utc(2026, 9, 26, 10, 15),
            )

        (from_template,) = api.of("from_template")
        self.assertEqual(from_template.start_datetime, "2026-09-26T10:15:00Z")
        self.assertEqual([item[0] for item in api.of("rain")[0].values], [0, 900])

    def test_without_a_slot_the_first_rain_interval_picks_it(self):
        api = FakeApi()
        self.run_forecast(
            api, "/nonexistent/state.json", rain_intervals=rain_at("2026-09-26T10:22:00Z", "2026-09-26T10:37:00Z"),
            use_saved_state=False,
        )

        self.assertEqual(api.of("from_template")[0].start_datetime, "2026-09-26T10:15:00Z")
        self.assertEqual([item[0] for item in api.of("rain")[0].values], [420, 1320])

    def test_test_rain_is_built_from_the_slot(self):
        module = load_create_simulation()

        with patch.dict(os.environ, {"FLOOD_TEST_RAIN_MM_HR": "6"}), patch("builtins.print"):
            intervals = module.get_rain_forecast(start=utc(2026, 9, 26, 10, 15))

        self.assertEqual(intervals[0]["startTime"], "2026-09-26T10:15:00Z")
        self.assertEqual(len(intervals), 9)


class SavedStateTests(unittest.TestCase):
    SLOT = utc(2026, 9, 26, 10, 15)
    RAIN = rain_at("2026-09-26T10:15:00Z", "2026-09-26T10:30:00Z")

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state_file = os.path.join(self.tmp.name, "state", "flood_system_state.json")

    def write_state_file(self, content):
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        with open(self.state_file, "w") as f:
            json.dump(content, f)

    def read_state_file(self):
        with open(self.state_file) as f:
            return json.load(f)["states"]

    def run_slot(self, api, **kwargs):
        module = load_create_simulation(api)
        with patch("builtins.print"):
            return module.run_forecast_process(self.state_file, rain_intervals=self.RAIN, slot_start=self.SLOT, **kwargs)

    def test_saves_states_at_one_and_two_cycles_and_records_their_valid_times(self):
        api = FakeApi()

        sim_id, states = self.run_slot(api)

        self.assertEqual(sim_id, 42)
        self.assertEqual([timed.time for timed in api.of("timed_state")], [900, 1800])
        expected = [
            {"id": 501, "valid_at": "2026-09-26T10:30:00Z"},
            {"id": 502, "valid_at": "2026-09-26T10:45:00Z"},
        ]
        self.assertEqual(states, expected)
        self.assertEqual(self.read_state_file(), expected)

    def test_hotstart_attaches_the_state_valid_at_the_slot(self):
        self.write_state_file({"states": [
            {"id": 7, "valid_at": "2026-09-26T10:15:00Z"},
            {"id": 8, "valid_at": "2026-09-26T10:30:00Z"},
            {"id": 6, "valid_at": "2026-09-26T10:00:00Z"},
        ]})
        api = FakeApi(initial_saved_states=[3])

        self.run_slot(api)

        self.assertFalse(api.of("from_template")[0].clone_initials)
        self.assertEqual(api.of("initial_delete"), [3])
        self.assertEqual(api.of("initial_create"), [{"saved_state": 7}])
        self.assertEqual(
            [name for name, _ in api.calls if name in ("initial_create", "action")], ["initial_create", "action"]
        )

    def test_without_an_exact_state_it_takes_the_newest_up_to_two_cycles_old(self):
        self.write_state_file({"states": [
            {"id": 5, "valid_at": "2026-09-26T09:45:00Z"},
            {"id": 4, "valid_at": "2026-09-26T09:30:00Z"},
        ]})
        api = FakeApi()

        self.run_slot(api)

        self.assertEqual(api.of("initial_create"), [{"saved_state": 5}])

    def test_a_state_older_than_two_cycles_is_a_cold_start(self):
        self.write_state_file({"states": [{"id": 5, "valid_at": "2026-09-26T09:44:59Z"}]})
        api = FakeApi()

        self.run_slot(api)

        self.assertTrue(api.of("from_template")[0].clone_initials)
        self.assertEqual(api.of("initial_list") + api.of("initial_create"), [])

    def test_the_old_state_file_format_is_a_cold_start(self):
        self.write_state_file({"last_saved_state_id": 99, "updated_at": "2026-09-25 10:00:00"})
        api = FakeApi()

        sim_id, _ = self.run_slot(api)

        self.assertEqual(sim_id, 42)
        self.assertTrue(api.of("from_template")[0].clone_initials)
        self.assertEqual(api.of("initial_create"), [])
        self.assertEqual([s["id"] for s in self.read_state_file()], [501, 502])

    def test_a_failed_attach_fails_the_run_instead_of_cold_starting(self):
        self.write_state_file({"states": [{"id": 7, "valid_at": "2026-09-26T10:15:00Z"}]})
        api = FakeApi(fail_attach=True)

        self.assertEqual(self.run_slot(api), (None, None))
        self.assertEqual(api.of("action"), [])

    def test_new_states_merge_with_earlier_ones_from_an_overlapping_run(self):
        self.write_state_file({"states": [
            {"id": 8, "valid_at": "2026-09-26T11:00:00Z"},
            {"id": 7, "valid_at": "2026-09-26T10:45:00Z"},
        ]})

        self.run_slot(FakeApi())

        self.assertEqual(self.read_state_file(), [
            {"id": 501, "valid_at": "2026-09-26T10:30:00Z"},
            {"id": 502, "valid_at": "2026-09-26T10:45:00Z"},
            {"id": 8, "valid_at": "2026-09-26T11:00:00Z"},
        ])

    def test_cold_run_without_saved_state_registers_nothing(self):
        api = FakeApi()

        self.assertEqual(self.run_slot(api, use_saved_state=False), (42, []))
        self.assertEqual(api.of("timed_state"), [])
        self.assertFalse(os.path.exists(self.state_file))


class FakeTi:
    def __init__(self):
        self.xcom = {}
        self.task_id = None

    def xcom_push(self, key, value):
        self.xcom[(self.task_id, key)] = value

    def xcom_pull(self, task_ids, key=None):
        return self.xcom.get((task_ids, key))

    def get_dr_count(self, **kwargs):
        return 1  # the previous slot has a success or running run, so the cold-start check allows a hotstart


def load_test_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"test/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FloodMappingDagSlotTests(unittest.TestCase):
    def test_forecast_and_simulation_use_the_logical_date_slot(self):
        dag_module = load_test_module("test_flood_mapping_dag_graph").load_dag_module()
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        api = FakeApi()
        dag_module.create_simulation = load_create_simulation(api)
        dag_module.hotstart_policy = importlib.import_module("hotstart_policy")
        dag_module.STATE_FILE = os.path.join(tmp.name, "flood_system_state.json")
        ti = FakeTi()
        logical_date = utc(2026, 9, 26, 10, 29, 10)

        with patch.dict(os.environ, {"FLOOD_TEST_RAIN_MM_HR": "6"}), patch("builtins.print"):
            ti.task_id = "0_check_forecast_rain"
            self.assertEqual(dag_module.task_check_forecast_rain(ti=ti, logical_date=logical_date), "1_trigger_simulation")
            ti.task_id = "1_trigger_simulation"
            dag_module.task_run_simulation(ti=ti, logical_date=logical_date, dag=types.SimpleNamespace(dag_id="flood_mapping_full"))

        self.assertEqual(ti.xcom[("0_check_forecast_rain", "rain_intervals")][0]["startTime"], "2026-09-26T10:15:00Z")
        self.assertEqual(api.of("from_template")[0].start_datetime, "2026-09-26T10:15:00Z")
        self.assertEqual(api.of("rain")[0].values[0][0], 0)


class SummarizeRainValuesTests(unittest.TestCase):
    """summarize_rain_values reads the [offset_seconds, m/s] list that is sent to 3Di."""

    SLOT = utc(2026, 9, 26, 10, 15)

    def setUp(self):
        self.module = load_create_simulation()

    def test_reports_count_offsets_peak_and_total(self):
        # 0 mm/h rising to 3.6 mm/h over one hour is a triangle of 1.8 mm.
        summary = self.module.summarize_rain_values([[0, 0.0], [3600, 1e-6]], self.SLOT, "tomorrow.io")

        self.assertEqual(
            summary,
            {
                "slot": "2026-09-26T10:15:00Z",
                "source": "tomorrow.io",
                "interval_count": 2,
                "first_offset_s": 0,
                "last_offset_s": 3600,
                "max_mm_hr": 3.6,
                "total_mm": 1.8,
            },
        )

    def test_constant_rain_totals_intensity_times_duration(self):
        values = [[offset, 6 / 3_600_000] for offset in range(0, 7201, 900)]

        summary = self.module.summarize_rain_values(values, self.SLOT, "fixed_test_rain")

        self.assertEqual((summary["interval_count"], summary["max_mm_hr"], summary["total_mm"]), (9, 6.0, 12.0))

    def test_an_empty_list_reports_no_rain(self):
        summary = self.module.summarize_rain_values([], self.SLOT, "tomorrow.io")

        self.assertEqual(
            (summary["interval_count"], summary["first_offset_s"], summary["last_offset_s"], summary["total_mm"]),
            (0, None, None, 0.0),
        )

    def test_source_names_the_branch_get_rain_forecast_takes(self):
        env = {"FLOOD_TEST_RAIN_CSV": "", "FLOOD_TEST_RAIN_START": "", "FLOOD_TEST_RAIN_MM_HR": ""}
        with patch.dict(os.environ, env):
            self.assertEqual(self.module.rain_source(), "tomorrow.io")
        with patch.dict(os.environ, {**env, "FLOOD_TEST_RAIN_MM_HR": "6"}):
            self.assertEqual(self.module.rain_source(), "fixed_test_rain")
        with patch.dict(
            os.environ,
            {**env, "FLOOD_TEST_RAIN_CSV": "/data/rain/hanoi-2025-10-05.csv", "FLOOD_TEST_RAIN_START": "2026-10-02T09:00:00Z"},
        ):
            self.assertEqual(self.module.rain_source(), "replay:hanoi-2025-10-05.csv")


class RainIngestedXcomTests(unittest.TestCase):
    """1_trigger_simulation pushes rain_ingested next to sim_id, built from the series sent to 3Di."""

    LOGICAL_DATE = utc(2026, 9, 26, 10, 29, 10)

    def run_dag(self, api, rain_mm_hr="6"):
        dag_module = load_test_module("test_flood_mapping_dag_graph").load_dag_module()
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        dag_module.create_simulation = load_create_simulation(api)
        dag_module.hotstart_policy = importlib.import_module("hotstart_policy")
        dag_module.STATE_FILE = os.path.join(tmp.name, "flood_system_state.json")
        ti = self.ti = FakeTi()
        env = {"FLOOD_TEST_RAIN_MM_HR": rain_mm_hr, "FLOOD_TEST_RAIN_CSV": "", "FLOOD_TEST_RAIN_START": ""}
        with patch.dict(os.environ, env), patch("builtins.print"):
            ti.task_id = "0_check_forecast_rain"
            dag_module.task_check_forecast_rain(ti=ti, logical_date=self.LOGICAL_DATE)
            ti.task_id = "1_trigger_simulation"
            dag_module.task_run_simulation(
                ti=ti, logical_date=self.LOGICAL_DATE, dag=types.SimpleNamespace(dag_id="flood_mapping_full")
            )
        return ti

    def test_pushes_the_summary_of_the_series_sent_to_3di(self):
        api = FakeApi()

        self.run_dag(api)

        ti = self.ti
        sent = api.of("rain")[0].values
        summary = ti.xcom[("1_trigger_simulation", "rain_ingested")]
        self.assertEqual(ti.xcom[("1_trigger_simulation", "sim_id")], 42)
        self.assertEqual(summary["interval_count"], len(sent))
        self.assertEqual((summary["first_offset_s"], summary["last_offset_s"]), (sent[0][0], sent[-1][0]))
        self.assertEqual(
            (summary["slot"], summary["source"], summary["max_mm_hr"], summary["total_mm"]),
            ("2026-09-26T10:15:00Z", "fixed_test_rain", 6.0, 12.0),
        )

    def test_a_failed_trigger_pushes_no_summary(self):
        class FailingApi(FakeApi):
            def simulations_from_template(self, from_template):
                raise RuntimeError("3Di refused the simulation")

        with self.assertRaises(Exception):
            self.run_dag(FailingApi())

        self.assertIn(("0_check_forecast_rain", "rain_intervals"), self.ti.xcom)
        self.assertNotIn(("1_trigger_simulation", "rain_ingested"), self.ti.xcom)


class StateTestDagChainTests(unittest.TestCase):
    """flood_forecast_consecutive_state_test: event 2 hotstarts from event 1's end state."""

    def test_event2_starts_at_event1_end_state_and_attaches_it(self):
        dag_module = load_test_module("test_flood_state_test_dag_graph").load_dag_module()

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 9, 26, 10, 22, 30, tzinfo=timezone.utc)

        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        api = FakeApi()
        dag_module.create_simulation = load_create_simulation(api)
        dag_module.datetime = FixedDatetime
        dag_module.TEST_STATE_FILE = os.path.join(tmp.name, "flood_state_test.json")
        ti = FakeTi()

        with patch("builtins.print"):
            ti.task_id = "1_trigger_event1"
            dag_module.task_trigger_event1(ti=ti)
            ti.task_id = "4_trigger_event2"
            dag_module.task_trigger_event2(ti=ti)

        self.assertEqual(
            [t.start_datetime for t in api.of("from_template")], ["2026-09-26T10:15:00Z", "2026-09-26T12:15:00Z"]
        )
        self.assertEqual([t.clone_initials for t in api.of("from_template")], [True, False])
        self.assertEqual([t.time for t in api.of("timed_state")], [7200, 7200])
        self.assertEqual(api.of("initial_create"), [{"saved_state": 501}])


if __name__ == "__main__":
    unittest.main()
