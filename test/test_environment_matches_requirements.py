import re
import unittest
from importlib import metadata
from pathlib import Path

import conftest

ROOT = Path(__file__).resolve().parents[1]


class EnvironmentMatchesRequirements(unittest.TestCase):
    def test_installed_threedi_client_matches_pin(self):
        text = (ROOT / "requirements.txt").read_text()
        pinned = re.search(r"^threedi-api-client==(\S+)", text, re.MULTILINE).group(1)
        installed = metadata.version("threedi-api-client")
        if installed != pinned:
            self.skipTest(
                f"installed threedi-api-client {installed} differs from pinned {pinned}: "
                "tests ran with stand-ins, the full check runs in the worker"
            )
        self.assertEqual([], conftest.STAND_INS)
