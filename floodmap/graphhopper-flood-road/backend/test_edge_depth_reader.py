"""Tests for edge_depth_reader.py, the backend's own reader of the edge depth table (US-053), on the shared golden fixture
that the Python and Java readers are tested on (java/time-aware-routing/src/test/resources/edge-depth):

    python test_edge_depth_reader.py
"""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import edge_depth_reader as reader

FIXTURE = Path(__file__).resolve().parents[3] / "java" / "time-aware-routing" / "src" / "test" / "resources" / "edge-depth"


@unittest.skipUnless((FIXTURE / "golden.bin").exists(), "the golden fixture is not in this build context")
class GoldenFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden = (FIXTURE / "golden.bin").read_bytes()
        cls.expected = json.loads((FIXTURE / "golden.json").read_text(encoding="utf-8"))

    def write(self, directory, name, data):
        path = Path(directory) / name
        path.write_bytes(data)
        return path

    def test_the_header_is_the_one_the_writer_wrote(self):
        with tempfile.TemporaryDirectory() as tmp:
            table = reader.read_table(self.write(tmp, "t.bin", self.golden))
        self.assertEqual(table.graph_hash, self.expected["graph_hash"])
        self.assertEqual(table.run_name, self.expected["run_name"])
        self.assertEqual(table.edge_count, self.expected["edge_count"])
        self.assertEqual(table.step_count, self.expected["step_count"])
        self.assertEqual(table.step_times, tuple(datetime.fromtimestamp(t, timezone.utc) for t in self.expected["step_times_epoch"]))

    def test_every_edge_and_step_returns_the_value_of_the_other_readers(self):
        with tempfile.TemporaryDirectory() as tmp:
            table = reader.read_table(self.write(tmp, "t.bin", self.golden))
        checked = 0
        for edge, row in enumerate(self.expected["depths_cm"]):
            for step, value in enumerate(row):
                self.assertEqual(table.depth_cm(edge, step), value, f"edge {edge} step {step}")
                checked += 1
        self.assertEqual(checked, 3000 * 9)

    def test_values_above_the_signed_range_are_not_negative(self):
        with tempfile.TemporaryDirectory() as tmp:
            table = reader.read_table(self.write(tmp, "t.bin", self.golden))
        self.assertEqual(table.depth_cm(1, 0), 65535)

    def test_an_edge_or_step_outside_the_table_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            table = reader.read_table(self.write(tmp, "t.bin", self.golden))
        for edge, step in ((3000, 0), (-1, 0), (0, 9), (0, -1)):
            with self.assertRaises(IndexError):
                table.depth_cm(edge, step)

    def damaged(self, mutate, contains):
        data = bytearray(self.golden)
        data = mutate(data)
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write(tmp, "bad.bin", bytes(data))
            with self.assertRaises(reader.TableFormatError) as caught:
                reader.read_table(path)
        self.assertIn(contains, str(caught.exception))

    def test_a_wrong_magic(self):
        def mutate(d):
            d[0] = ord("X")
            return d
        self.damaged(mutate, "magic")

    def test_a_wrong_version(self):
        def mutate(d):
            d[4] = 2
            return d
        self.damaged(mutate, "version 2")

    def test_a_file_shorter_than_the_fixed_header(self):
        self.damaged(lambda d: d[:10], "header is cut off")

    def test_a_header_cut_off_in_the_hash(self):
        self.damaged(lambda d: d[: 16 + 20], "header is cut off")

    def test_a_body_one_byte_short_or_long(self):
        self.damaged(lambda d: d[:-1], "body")
        self.damaged(lambda d: d + b"\0", "body")

    def test_step_times_that_do_not_increase(self):
        def mutate(d):
            at = 16 + 64 + 15
            d[at + 8 : at + 16] = d[at : at + 8]
            return d
        self.damaged(mutate, "increase")

    def test_text_that_is_not_utf8(self):
        def mutate(d):
            d[16] = 0xFF
            return d
        self.damaged(mutate, "UTF-8")

    def test_a_table_with_no_steps(self):
        def mutate(d):
            d[6] = d[7] = 0
            return d
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(reader.TableFormatError):
                reader.read_table(self.write(tmp, "bad.bin", bytes(mutate(bytearray(self.golden)))))


@unittest.skipUnless((FIXTURE / "golden.bin").exists(), "the golden fixture is not in this build context")
class LatestAndGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.golden = (FIXTURE / "golden.bin").read_bytes()

    def tearDown(self):
        self.tmp.cleanup()

    def publish(self, name):
        (self.dir / name).write_bytes(self.golden)
        (self.dir / "latest").write_text(name + "\n", encoding="utf-8")

    def test_the_table_that_latest_names_is_read(self):
        self.publish("20261001T000000.bin")
        self.assertEqual(reader.read_latest(self.dir).run_name, "20261001T000000")

    def test_an_unchanged_file_is_read_once_and_a_replaced_file_is_read_again(self):
        self.publish("20261001T000000.bin")
        first = reader.read_latest(self.dir)
        self.assertIs(reader.read_latest(self.dir), first)
        # A new table under a new name, as a publish writes it.
        self.publish("20261001T001500.bin")
        self.assertIsNot(reader.read_latest(self.dir), first)

    def test_a_table_file_that_changes_in_place_is_read_again(self):
        self.publish("20261001T000000.bin")
        first = reader.read_latest(self.dir)
        (self.dir / "20261001T000000.bin").write_bytes(self.golden + b"")  # same size, new mtime
        import os, time
        os.utime(self.dir / "20261001T000000.bin", ns=(time.time_ns() + 5_000_000_000, time.time_ns() + 5_000_000_000))
        self.assertIsNot(reader.read_latest(self.dir), first)

    def test_no_pointer_is_a_missing_table_error_that_names_the_folder(self):
        with self.assertRaises(reader.TableUnavailable) as caught:
            reader.read_latest(self.dir)
        self.assertIn(str(self.dir), str(caught.exception))

    def test_a_pointer_to_a_missing_file_is_unavailable(self):
        (self.dir / "latest").write_text("20261001T000000.bin\n", encoding="utf-8")
        with self.assertRaises(reader.TableUnavailable):
            reader.read_latest(self.dir)

    def test_a_damaged_table_is_unavailable_and_says_why(self):
        (self.dir / "20261001T000000.bin").write_bytes(self.golden[:-1])
        (self.dir / "latest").write_text("20261001T000000.bin\n", encoding="utf-8")
        with self.assertRaises(reader.TableUnavailable) as caught:
            reader.read_latest(self.dir)
        self.assertIn("body", str(caught.exception))

    def test_a_pointer_that_climbs_out_of_the_folder_is_refused(self):
        (self.dir / "latest").write_text("../x.bin\n", encoding="utf-8")
        with self.assertRaises(reader.TableUnavailable):
            reader.read_latest(self.dir)

    def test_a_table_for_the_loaded_graph_passes_the_guard(self):
        self.publish("20261001T000000.bin")
        table = reader.read_latest(self.dir)
        self.assertIs(reader.require_graph_hash(table, table.graph_hash), table)

    def test_a_table_for_another_graph_is_refused_and_both_hashes_are_named(self):
        self.publish("20261001T000000.bin")
        table = reader.read_latest(self.dir)
        with self.assertRaises(reader.TableUnavailable) as caught:
            reader.require_graph_hash(table, "f" * 64)
        message = str(caught.exception)
        self.assertIn(table.graph_hash, message)
        self.assertIn("f" * 64, message)
        self.assertIn("graph-reimport-procedure", message)


if __name__ == "__main__":
    unittest.main()
