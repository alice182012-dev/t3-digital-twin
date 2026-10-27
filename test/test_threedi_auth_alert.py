import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


import conftest  # noqa: F401  # unittest does not load conftest.py on its own

ROOT = Path(__file__).resolve().parents[1]


def load_create_simulation():
    requests = types.ModuleType("requests")
    fiona = types.ModuleType("fiona")
    fiona_vfs = types.ModuleType("fiona.vfs")
    fiona.vfs = fiona_vfs
    spec = importlib.util.spec_from_file_location(
        "test_create_simulation_auth_alert",
        ROOT / "scripts/create_simulation.py",
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(
        sys.modules,
        {"requests": requests, "fiona": fiona, "fiona.vfs": fiona_vfs},
    ):
        spec.loader.exec_module(module)
    return module


class ThreediAuthAlertTests(unittest.TestCase):
    def setUp(self):
        self.module = load_create_simulation()

    def _api_exception(self, status):
        return self.module.ApiException(status=status)

    def test_401_triggers_distinct_auth_expired_alert(self):
        with patch("builtins.print") as output:
            self.module._log_if_auth_expired(self._api_exception(401), "Tạo Sim")

        messages = [call.args[0] for call in output.call_args_list]
        self.assertTrue(any("auth-expired" in m and "will-not-self-resolve" in m for m in messages))

    def test_403_triggers_distinct_auth_expired_alert(self):
        with patch("builtins.print") as output:
            self.module._log_if_auth_expired(self._api_exception(403), "Start Simulation")

        messages = [call.args[0] for call in output.call_args_list]
        self.assertTrue(any("auth-expired" in m for m in messages))

    def test_non_auth_api_exception_does_not_fire_alert(self):
        with patch("builtins.print") as output:
            self.module._log_if_auth_expired(self._api_exception(500), "Tạo Sim")

        output.assert_not_called()

    def test_non_api_exception_does_not_fire_alert(self):
        with patch("builtins.print") as output:
            self.module._log_if_auth_expired(RuntimeError("boom"), "Tạo Sim")

        output.assert_not_called()


if __name__ == "__main__":
    unittest.main()
