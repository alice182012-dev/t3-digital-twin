"""The analysis service in compose.yml gets only its own variables (US-109).

    python3 -m pytest test/test_analysis_service_compose.py

Reads compose.yml as text, since the repo's Python has no YAML parser. A service is the block of non-comment lines
under a two-space key in `services:`, and its environment keys are the six-space keys under `    environment:`.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ALLOWED = {
    "HOST",
    "PORT",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "ANALYSIS_READER_USER",
    "ANALYSIS_READER_PASSWORD",
    "ANALYSIS_OWNER_USER",
    "ANALYSIS_OWNER_PASSWORD",
    "TIMESCALE_HOST",
    "TIMESCALE_PORT",
    "TIMESCALE_DB",
    "ANALYSIS_TIMESCALE_READER_USER",
    "ANALYSIS_TIMESCALE_READER_PASSWORD",
}
PASSWORDS = {"ANALYSIS_READER_PASSWORD", "ANALYSIS_OWNER_PASSWORD", "ANALYSIS_TIMESCALE_READER_PASSWORD"}


def service_block(compose: str, name: str) -> list[str]:
    lines = compose.split("\n")
    start = lines.index(f"  {name}:") + 1
    block = []
    for line in lines[start:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith("   "):
            break
        block.append(line)
    return block


def environment(block: list[str]) -> dict[str, str]:
    start = block.index("    environment:") + 1
    env = {}
    for line in block[start:]:
        match = re.match(r"^      ([A-Z_]+): (.*)$", line)
        if not match:
            break
        env[match.group(1)] = match.group(2)
    return env


class AnalysisServiceComposeTests(unittest.TestCase):
    def setUp(self):
        self.block = service_block((ROOT / "compose.yml").read_text(encoding="utf-8"), "analysis")

    def test_it_reads_no_env_file_and_not_the_airflow_anchor(self):
        text = "\n".join(self.block)
        self.assertNotIn("env_file", text)
        self.assertNotIn("airflow-common", text)

    def test_its_environment_keys_are_exactly_the_allowed_set(self):
        self.assertEqual(set(environment(self.block)), ALLOWED)

    def test_no_key_names_3di_or_tomorrow(self):
        for key in environment(self.block):
            self.assertNotIn("THREEDI", key)
            self.assertNotIn("TOMORROW", key)

    def test_each_password_is_required_with_no_fallback(self):
        env = environment(self.block)
        for key in PASSWORDS:
            self.assertEqual(env[key], f"${{{key}:?Set {key} in .env}}")

    def test_it_builds_from_its_own_folder_and_listens_on_localhost(self):
        text = "\n".join(self.block)
        self.assertIn("      context: ./analysis-service\n", text)
        self.assertIn('      - "127.0.0.1:${ANALYSIS_PORT:-8020}:8020"', text)


if __name__ == "__main__":
    unittest.main()
