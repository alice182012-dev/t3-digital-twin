"""Checks that create_simulation.py starts each 3Di run on its 15-minute slot.

The threedi_api_client modules are stand-ins, so this runs without the client installed:
python3 test/test_create_simulation_cycle.py
"""

import importlib.util
import os
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]


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


if __name__ == "__main__":
    unittest.main()
