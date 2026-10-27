"""The vehicle depth limits have one owner, VEHICLE_PROFILES in floodmap/graphhopper-flood-road/scripts/flood_utils.py.

    python3 scripts/test_vehicle_limit_owner.py
"""

from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A vehicle name next to its limit, as a dict entry, a map put, or a keyword argument.
LIMIT_LITERAL = re.compile(r"\b(motorbike|car|truck|foot)\b[\"']?\s*[:,=]\s*(20|30|35|40)\b")

SOURCE_SUFFIXES = {".py", ".java", ".ts", ".tsx", ".js", ".yml", ".yaml"}
SKIPPED_DIRS = {".git", ".claude", "node_modules", "dist", "build", "target", "artifacts", "marie-curie", "data"}

# Copies that cannot import Python, each pinned by its own test:
# config.yml's td_limit_cm by backend/test_time_aware_route.py ProfileLimitsTest,
# ScenarioReport.java by TimeAwareRouterTest against config.yml.
MIRRORS = {"java/time-aware-routing/src/main/java/com/graphhopper/timeaware/ScenarioReport.java"}


def is_test(path: Path) -> bool:
    name = path.name
    return name.startswith("test_") or name.endswith("Test.java") or ".test." in name or "/src/test/" in path.as_posix()


def files_with_limit_literals() -> set[str]:
    found = set()
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIPPED_DIRS]
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix not in SOURCE_SUFFIXES or is_test(path):
                continue
            if LIMIT_LITERAL.search(path.read_text(encoding="utf-8", errors="ignore")):
                found.add(path.relative_to(ROOT).as_posix())
    return found


class VehicleLimitOwnerTest(unittest.TestCase):
    def test_no_source_file_defines_the_limits_again(self):
        self.assertEqual(files_with_limit_literals(), MIRRORS)


if __name__ == "__main__":
    unittest.main()
