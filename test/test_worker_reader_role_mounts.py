"""The Airflow worker can run create_routing_reader_role.py with no manual copies (US-132).

    python3 -m pytest test/test_worker_reader_role_mounts.py

Reads compose.yml as text, since the repo's Python has no YAML parser. The worker takes its volumes from the
x-airflow-common anchor, so the test reads that block and checks the worker does not override it.
"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "database" / "create_routing_reader_role.py"
AIRFLOW_HOME = "/opt/airflow"

PARSER_MOUNT = (
    "./floodmap/graphhopper-flood-road/backend/core_contract.py",
    f"{AIRFLOW_HOME}/floodmap/graphhopper-flood-road/backend/core_contract.py",
    "ro",
)
PAGE_MOUNT = (
    "./artifacts/docs/concepts/core-output-contract.md",
    f"{AIRFLOW_HOME}/artifacts/docs/concepts/core-output-contract.md",
    "ro",
)


def block(lines: list[str], header: str, indent: int) -> list[str]:
    start = lines.index(header) + 1
    body = []
    for line in lines[start:]:
        if line.strip() and not line.lstrip().startswith("#") and len(line) - len(line.lstrip()) < indent:
            break
        body.append(line)
    return body


def volumes(body: list[str], indent: int) -> list[tuple[str, ...]]:
    key = " " * indent + "volumes:"
    start = body.index(key) + 1
    found = []
    for line in body[start:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" " * (indent + 2) + "- "):
            break
        found.append(tuple(line.strip()[2:].split(":")))
    return found


class WorkerReaderRoleMountsTests(unittest.TestCase):
    def setUp(self):
        lines = (ROOT / "compose.yml").read_text(encoding="utf-8").split("\n")
        worker = block(lines, "  airflow-worker:", 3)
        self.assertIn("    <<: *airflow-common", worker)
        self.assertNotIn("    volumes:", worker, "a worker override would drop the shared mounts")
        self.mounts = volumes(block(lines, "x-airflow-common: &airflow-common", 1), 2)

    def test_worker_mounts_the_parser_and_the_contract_page_read_only(self):
        self.assertIn(PARSER_MOUNT, self.mounts)
        self.assertIn(PAGE_MOUNT, self.mounts)

    def test_container_paths_are_where_the_script_looks_from_the_airflow_home(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("parents[2]", source)
        self.assertIn('REPO / "floodmap" / "graphhopper-flood-road" / "backend"', source)
        self.assertIn('REPO / "artifacts" / "docs" / "concepts" / "core-output-contract.md"', source)
        self.assertEqual(Path(AIRFLOW_HOME, "scripts", "database", SCRIPT.name).parents[2], Path(AIRFLOW_HOME))
        self.assertTrue(PARSER_MOUNT[1].startswith(f"{AIRFLOW_HOME}/floodmap/graphhopper-flood-road/backend/"))
        self.assertEqual(PAGE_MOUNT[1], f"{AIRFLOW_HOME}/artifacts/docs/concepts/core-output-contract.md")


if __name__ == "__main__":
    unittest.main()
