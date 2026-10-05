"""The shared fixture of US-043: one table file and its expected values, read by the Python reader here and by the
Java reader in java/time-aware-routing. Both copies live in the Java module's test resources, because the Docker
build of the module sees only that folder, and this test keeps them equal to what the generator writes."""

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import golden_fixture
from edge_depth_table import read_table

RESOURCES = golden_fixture.RESOURCES


@unittest.skipUnless(RESOURCES.is_dir(), "the Java module's test resources are not in this checkout")
class GoldenFixtureTest(unittest.TestCase):
    def test_the_files_in_the_java_module_are_what_the_generator_writes(self):
        table_bytes, expected = golden_fixture.build()

        self.assertEqual((RESOURCES / "golden.bin").read_bytes(), table_bytes)
        self.assertEqual(json.loads((RESOURCES / "golden.json").read_text()), expected)

    def test_the_python_reader_returns_every_expected_value(self):
        expected = json.loads((RESOURCES / "golden.json").read_text())

        table = read_table(RESOURCES / "golden.bin")

        header = table.header
        self.assertEqual(header.graph_hash, expected["graph_hash"])
        self.assertEqual(header.run_name, expected["run_name"])
        self.assertEqual(header.edge_count, expected["edge_count"])
        self.assertEqual(header.step_count, expected["step_count"])
        self.assertEqual([int(t.timestamp()) for t in header.step_times], expected["step_times_epoch"])
        for edge_id, row in enumerate(expected["depths_cm"]):
            self.assertEqual(table.edge_depths_cm(edge_id), tuple(row), f"edge {edge_id}")

    def test_the_fixture_has_the_edge_cases_a_reader_must_get_right(self):
        values = {v for row in golden_fixture.build()[1]["depths_cm"] for v in row}

        for needed in (0, 1, 255, 256, 257, 32767, 32768, 65535):
            self.assertIn(needed, values)

    def test_it_is_the_size_the_story_asks_for(self):
        _, expected = golden_fixture.build()

        self.assertEqual((expected["edge_count"], expected["step_count"]), (3000, 9))
        self.assertEqual(len(expected["depths_cm"]), 3000)

    def test_the_first_step_is_a_known_instant(self):
        _, expected = golden_fixture.build()

        self.assertEqual(
            datetime.fromtimestamp(expected["step_times_epoch"][0], timezone.utc),
            datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
