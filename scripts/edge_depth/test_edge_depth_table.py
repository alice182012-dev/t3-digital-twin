import struct
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from edge_depth_table import (
    TableFormatError,
    TableHeader,
    read_latest,
    read_table,
    write_latest,
    write_table,
)

T0 = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)

GOLDEN_HEADER = TableHeader(
    graph_hash="abc",
    run_name="r1",
    step_times=(T0, T0 + timedelta(minutes=15)),
    edge_count=2,
)
GOLDEN_ROWS = [[0, 1], [256, 65535]]
GOLDEN_BYTES = bytes.fromhex(
    "45444744"  # magic "EDGD"
    "0100"  # version 1
    "0200"  # 2 steps
    "02000000"  # 2 edges
    "0300"  # graph hash length 3
    "0200"  # run name length 2
    "616263"  # "abc"
    "7231"  # "r1"
    "80a2bd6a00000000"  # 2026-10-01T00:00:00Z
    "04a6bd6a00000000"  # 2026-10-01T00:15:00Z
    "00000100"  # edge 0: 0 cm, 1 cm
    "0001ffff"  # edge 1: 256 cm, 65535 cm
)


def nine_steps(start=T0):
    return tuple(start + timedelta(minutes=15 * i) for i in range(9))


def fixture_rows(edge_count, step_count):
    return [[(edge * 7 + step * 13) % 65536 for step in range(step_count)] for edge in range(edge_count)]


class EdgeDepthTableTest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.dir = Path(self._dir.name)
        self.path = self.dir / "table.bin"

    def write_golden(self):
        write_table(self.path, GOLDEN_HEADER, GOLDEN_ROWS)

    def test_a_few_thousand_edges_and_nine_steps_read_back_exactly(self):
        header = TableHeader("graph-hash-1", "20260930T020000", nine_steps(), edge_count=3000)
        rows = fixture_rows(3000, 9)
        write_table(self.path, header, rows)

        table = read_table(self.path)

        self.assertEqual(table.header, header)
        for edge in range(3000):
            self.assertEqual(table.edge_depths_cm(edge), tuple(rows[edge]))
            for step in range(9):
                self.assertEqual(table.depth_cm(edge, step), rows[edge][step])

    def test_writer_produces_the_documented_bytes(self):
        self.write_golden()

        self.assertEqual(self.path.read_bytes(), GOLDEN_BYTES)

    def test_reader_reads_the_documented_bytes(self):
        self.path.write_bytes(GOLDEN_BYTES)

        table = read_table(self.path)

        self.assertEqual(table.header, GOLDEN_HEADER)
        self.assertEqual([list(table.edge_depths_cm(e)) for e in range(2)], GOLDEN_ROWS)

    def test_non_ascii_text_in_the_header_survives(self):
        header = TableHeader("băm-đồ-thị", "chạy-1", (T0,), edge_count=1)
        write_table(self.path, header, [[5]])

        self.assertEqual(read_table(self.path).header, header)

    def test_reader_refuses_a_wrong_magic(self):
        self.path.write_bytes(b"NOPE" + GOLDEN_BYTES[4:])

        with self.assertRaisesRegex(TableFormatError, "magic"):
            read_table(self.path)

    def test_reader_refuses_a_wrong_version(self):
        self.path.write_bytes(GOLDEN_BYTES[:4] + struct.pack("<H", 2) + GOLDEN_BYTES[6:])

        with self.assertRaisesRegex(TableFormatError, "version 2"):
            read_table(self.path)

    def test_reader_refuses_a_truncated_body(self):
        self.path.write_bytes(GOLDEN_BYTES[:-1])

        with self.assertRaisesRegex(TableFormatError, "body"):
            read_table(self.path)

    def test_reader_refuses_a_body_with_extra_bytes(self):
        self.path.write_bytes(GOLDEN_BYTES + b"\x00\x00")

        with self.assertRaisesRegex(TableFormatError, "body"):
            read_table(self.path)

    def test_reader_refuses_a_truncated_header(self):
        for cut in (3, 10, 20):
            with self.subTest(cut=cut):
                self.path.write_bytes(GOLDEN_BYTES[:cut])
                with self.assertRaisesRegex(TableFormatError, "header"):
                    read_table(self.path)

    def test_reader_refuses_an_empty_file(self):
        self.path.write_bytes(b"")

        with self.assertRaises(TableFormatError):
            read_table(self.path)

    def test_writer_refuses_a_row_with_the_wrong_step_count(self):
        with self.assertRaisesRegex(ValueError, "edge 1.*1 depths.*2 steps"):
            write_table(self.path, GOLDEN_HEADER, [[0, 1], [5]])

    def test_writer_refuses_too_few_rows(self):
        with self.assertRaisesRegex(ValueError, "1 rows.*2 edges"):
            write_table(self.path, GOLDEN_HEADER, [[0, 1]])

    def test_writer_refuses_too_many_rows(self):
        with self.assertRaisesRegex(ValueError, "more than 2 rows"):
            write_table(self.path, GOLDEN_HEADER, [[0, 1], [0, 1], [0, 1]])

    def test_writer_refuses_a_depth_outside_unsigned_16_bits(self):
        for bad in (-1, 65536):
            with self.subTest(depth=bad):
                with self.assertRaisesRegex(ValueError, "edge 0"):
                    write_table(self.path, GOLDEN_HEADER, [[bad, 0], [0, 0]])

    def test_header_refuses_naive_step_times(self):
        with self.assertRaisesRegex(ValueError, "timezone"):
            TableHeader("h", "r", (datetime(2026, 10, 1),), edge_count=1)

    def test_header_refuses_unordered_step_times(self):
        with self.assertRaisesRegex(ValueError, "increasing"):
            TableHeader("h", "r", (T0 + timedelta(minutes=15), T0), edge_count=1)

    def test_header_refuses_no_steps(self):
        with self.assertRaisesRegex(ValueError, "at least one step"):
            TableHeader("h", "r", (), edge_count=1)

    def test_header_normalizes_step_times_to_utc(self):
        plus_seven = timezone(timedelta(hours=7))
        header = TableHeader("h", "r", (T0.astimezone(plus_seven),), edge_count=1)

        self.assertEqual(header.step_times[0].utcoffset(), timedelta(0))
        self.assertEqual(header.step_times[0], T0)

    def test_depth_lookup_refuses_an_edge_or_step_out_of_range(self):
        self.write_golden()
        table = read_table(self.path)

        for edge, step in ((2, 0), (-1, 0), (0, 2), (0, -1)):
            with self.subTest(edge=edge, step=step):
                with self.assertRaises(IndexError):
                    table.depth_cm(edge, step)
        with self.assertRaises(IndexError):
            table.edge_depths_cm(2)

    def test_zero_edges_is_a_valid_table(self):
        header = TableHeader("h", "r", (T0,), edge_count=0)
        write_table(self.path, header, [])

        table = read_table(self.path)

        self.assertEqual(table.header.edge_count, 0)
        with self.assertRaises(IndexError):
            table.depth_cm(0, 0)


class LatestPointerTest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        self.dir = Path(self._dir.name)

    def test_pointer_names_the_current_table(self):
        write_table(self.dir / "20260930T020000.bin", GOLDEN_HEADER, GOLDEN_ROWS)
        write_latest(self.dir, "20260930T020000.bin")

        self.assertEqual((self.dir / "latest").read_text(), "20260930T020000.bin\n")
        self.assertEqual(read_latest(self.dir), self.dir / "20260930T020000.bin")

    def test_pointer_moves_to_a_newer_table(self):
        write_latest(self.dir, "a.bin")
        write_latest(self.dir, "b.bin")

        self.assertEqual(read_latest(self.dir), self.dir / "b.bin")

    def test_reading_a_missing_pointer_fails_clearly(self):
        with self.assertRaises(FileNotFoundError):
            read_latest(self.dir)

    def test_pointer_refuses_a_name_that_leaves_the_directory(self):
        for bad in ("../x.bin", "sub/x.bin", "", "latest"):
            with self.subTest(name=bad):
                with self.assertRaises(ValueError):
                    write_latest(self.dir, bad)

    def test_reading_a_pointer_that_names_a_path_fails(self):
        (self.dir / "latest").write_text("../escape.bin\n")

        with self.assertRaises(ValueError):
            read_latest(self.dir)


if __name__ == "__main__":
    unittest.main()
