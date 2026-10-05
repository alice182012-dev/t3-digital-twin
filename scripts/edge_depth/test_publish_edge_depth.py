"""Publishing and retention of edge depth tables (US-042). Pure files, no database."""

import multiprocessing
import os
import tempfile
import threading
import time
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

import publish_edge_depth
from edge_depth_table import (
    TableHeader,
    read_latest,
    read_latest_table,
    read_table,
    write_latest,
    write_table,
)
from publish_edge_depth import PublishError

EDGES = 5
STEPS = 2
BASE = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)


def run_name(index):
    """Run timestamps 15 minutes apart, in the format the DAG names runs with."""
    return (datetime(2026, 10, 5, 0, 0) + timedelta(minutes=15 * index)).strftime("%Y%m%dT%H%M%S")


def make_table(directory, index, graph_hash="a" * 64):
    """A valid table whose every depth is `index` centimetres, so a reader can tell tables apart."""
    name = run_name(index)
    header = TableHeader(
        graph_hash=graph_hash,
        run_name=name,
        step_times=tuple(BASE + timedelta(minutes=15 * s) for s in range(STEPS)),
        edge_count=EDGES,
    )
    write_table(Path(directory) / f"{name}.bin", header, [(index,) * STEPS for _ in range(EDGES)])
    return f"{name}.bin"


class PublishTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def names(self):
        return sorted(p.name for p in self.dir.iterdir())

    def latest(self):
        return read_latest(self.dir).name

    def test_the_first_publish_points_latest_at_the_table(self):
        name = make_table(self.dir, 1)

        result = publish_edge_depth.publish_table(self.dir, name)

        self.assertEqual(self.latest(), name)
        self.assertEqual((result.latest, result.previous, result.moved, result.removed), (name, None, True, ()))

    def test_a_newer_table_moves_the_pointer(self):
        first = make_table(self.dir, 1)
        second = make_table(self.dir, 2)
        publish_edge_depth.publish_table(self.dir, first)

        result = publish_edge_depth.publish_table(self.dir, second)

        self.assertEqual(self.latest(), second)
        self.assertEqual((result.previous, result.moved), (first, True))

    def test_an_older_table_that_finishes_last_does_not_move_the_pointer_back(self):
        older = make_table(self.dir, 1)
        newer = make_table(self.dir, 2)
        publish_edge_depth.publish_table(self.dir, newer)

        result = publish_edge_depth.publish_table(self.dir, older)

        self.assertEqual(self.latest(), newer)
        self.assertFalse(result.moved)
        self.assertEqual(result.latest, newer)

    def test_publishing_the_same_table_twice_changes_nothing(self):
        name = make_table(self.dir, 1)
        publish_edge_depth.publish_table(self.dir, name)

        result = publish_edge_depth.publish_table(self.dir, name)

        self.assertEqual((self.latest(), result.moved, result.removed), (name, False, ()))

    def test_the_fourth_table_removes_the_oldest(self):
        for index in (1, 2, 3):
            publish_edge_depth.publish_table(self.dir, make_table(self.dir, index))

        result = publish_edge_depth.publish_table(self.dir, make_table(self.dir, 4))

        self.assertEqual(result.removed, (f"{run_name(1)}.bin",))
        self.assertEqual(
            self.names(), sorted([f"{run_name(i)}.bin" for i in (2, 3, 4)] + ["latest"])
        )
        self.assertEqual(result.kept, tuple(f"{run_name(i)}.bin" for i in (4, 3, 2)))

    def test_keep_is_a_parameter(self):
        for index in (1, 2, 3):
            publish_edge_depth.publish_table(self.dir, make_table(self.dir, index), keep=1)

        self.assertEqual(self.names(), sorted([f"{run_name(3)}.bin", "latest"]))

    def test_keep_below_one_is_an_error(self):
        name = make_table(self.dir, 1)

        with self.assertRaises(ValueError):
            publish_edge_depth.publish_table(self.dir, name, keep=0)

    def test_the_table_the_pointer_names_is_never_removed(self):
        for index in (1, 2, 3, 4, 5):
            make_table(self.dir, index)
        write_latest(self.dir, f"{run_name(2)}.bin")  # a rollback to an older table

        result = publish_edge_depth.publish_table(self.dir, f"{run_name(1)}.bin")

        self.assertEqual(self.latest(), f"{run_name(2)}.bin")
        self.assertEqual(result.removed, (f"{run_name(1)}.bin",))
        self.assertEqual(
            self.names(), sorted([f"{run_name(i)}.bin" for i in (2, 3, 4, 5)] + ["latest"])
        )

    def test_a_truncated_table_is_refused_and_removed_and_the_pointer_stays(self):
        good = make_table(self.dir, 1)
        publish_edge_depth.publish_table(self.dir, good)
        bad = make_table(self.dir, 2)
        data = (self.dir / bad).read_bytes()
        (self.dir / bad).write_bytes(data[: len(data) - 7])

        with self.assertRaises(PublishError) as caught:
            publish_edge_depth.publish_table(self.dir, bad)

        self.assertIn(bad, str(caught.exception))
        self.assertEqual(self.latest(), good)
        self.assertEqual(self.names(), sorted([good, "latest"]))

    def test_a_missing_table_is_an_error_and_the_pointer_stays(self):
        good = make_table(self.dir, 1)
        publish_edge_depth.publish_table(self.dir, good)

        with self.assertRaises(PublishError):
            publish_edge_depth.publish_table(self.dir, f"{run_name(2)}.bin")

        self.assertEqual(self.latest(), good)

    def test_a_table_whose_header_names_another_run_is_refused(self):
        name = make_table(self.dir, 1)
        (self.dir / name).rename(self.dir / f"{run_name(2)}.bin")

        with self.assertRaises(PublishError) as caught:
            publish_edge_depth.publish_table(self.dir, f"{run_name(2)}.bin")

        self.assertIn("run", str(caught.exception))

    def test_only_run_named_files_are_tables(self):
        for bad in ("latest", "x.bin", "../20261005T000000.bin", "20261005T000000.txt", "20261005T000000"):
            with self.subTest(name=bad):
                with self.assertRaises(PublishError):
                    publish_edge_depth.publish_table(self.dir, bad)

    def test_other_files_in_the_folder_are_left_alone(self):
        (self.dir / "notes.txt").write_text("keep me")
        for index in (1, 2, 3, 4):
            publish_edge_depth.publish_table(self.dir, make_table(self.dir, index))

        self.assertIn("notes.txt", self.names())

    def test_a_garbage_pointer_counts_as_no_pointer(self):
        name = make_table(self.dir, 1)
        (self.dir / "latest").write_text("")

        result = publish_edge_depth.publish_table(self.dir, name)

        self.assertEqual((self.latest(), result.previous, result.moved), (name, None, True))

    def test_a_pointer_to_a_table_that_is_gone_counts_as_no_pointer(self):
        write_latest(self.dir, f"{run_name(9)}.bin")
        name = make_table(self.dir, 1)

        result = publish_edge_depth.publish_table(self.dir, name)

        self.assertEqual((self.latest(), result.moved), (name, True))

    def test_old_temporary_files_are_removed_and_new_ones_are_kept(self):
        name = make_table(self.dir, 1)
        old = self.dir / f".{run_name(0)}.123.tmp"
        old_pointer = self.dir / ".latest.1.2.tmp"
        fresh = self.dir / f".{run_name(0)}.456.tmp"
        for path in (old, old_pointer, fresh):
            path.write_bytes(b"x")
        two_hours_ago = time.time() - 7200
        os.utime(old, (two_hours_ago, two_hours_ago))
        os.utime(old_pointer, (two_hours_ago, two_hours_ago))

        publish_edge_depth.publish_table(self.dir, name)

        self.assertEqual(self.names(), sorted([name, "latest", fresh.name]))

    def test_two_overlapping_publishes_cannot_take_the_pointer_back(self):
        """Both publishes read the pointer before either writes it. Without a lock the older table can write last
        and take `latest` back. A pause between the read and the write forces that order."""
        original = publish_edge_depth._current

        def current_then_pause(table_dir):
            value = original(table_dir)
            time.sleep(0.02)
            return value

        for attempt in range(15):
            with self.subTest(attempt=attempt), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                older, newer = make_table(directory, 1), make_table(directory, 2)
                with mock.patch.object(publish_edge_depth, "_current", current_then_pause):
                    threads = [
                        threading.Thread(target=publish_edge_depth.publish_table, args=(directory, name))
                        for name in (newer, older)
                    ]
                    for t in threads:
                        t.start()
                    for t in threads:
                        t.join()

                self.assertEqual(read_latest(directory).name, newer)


class ReadLatestTableTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_reads_the_table_the_pointer_names(self):
        name = make_table(self.dir, 7)
        publish_edge_depth.publish_table(self.dir, name)

        table = read_latest_table(self.dir)

        self.assertEqual(table.edge_depths_cm(0), (7, 7))
        self.assertEqual(table.header.run_name, run_name(7))

    def test_reads_the_pointer_again_when_the_named_table_has_just_been_removed(self):
        first, second = make_table(self.dir, 1), make_table(self.dir, 2)
        write_latest(self.dir, first)
        (self.dir / first).unlink()
        calls = []

        def pointer_moves_after_the_first_read(directory):
            calls.append(1)
            if len(calls) == 2:
                write_latest(directory, second)
            return read_latest(directory)

        table = read_latest_table(self.dir, _read_pointer=pointer_moves_after_the_first_read)

        self.assertEqual(table.header.run_name, run_name(2))
        self.assertEqual(len(calls), 2)

    def test_a_missing_pointer_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            read_latest_table(self.dir)


def _poll(directory, stop, results):
    """The reader of a table, in its own process, as the Java and Python readers are. Every read must be a
    whole table whose every value equals its run's index, and whose header names the run of its file."""
    reads = failures = 0
    runs = set()
    while not stop.is_set():
        try:
            table = read_latest_table(Path(directory))
            index = table.edge_depths_cm(0)[0]
            ok = all(table.edge_depths_cm(e) == (index, index) for e in range(table.header.edge_count))
            ok = ok and table.header.run_name == run_name(index)
            runs.add(index)
            reads += 1
            failures += 0 if ok else 1
        except Exception:  # noqa: BLE001 - any failure of a read is a finding
            failures += 1
    results.put((reads, failures, sorted(runs)))


class ReaderPollingWhilePublishingTests(unittest.TestCase):
    def test_a_polling_reader_in_another_process_never_sees_a_partial_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            publish_edge_depth.publish_table(directory, make_table(directory, 0))
            context = multiprocessing.get_context("fork")
            stop, results = context.Event(), context.Queue()
            reader = context.Process(target=_poll, args=(str(directory), stop, results))
            reader.start()
            try:
                for index in range(1, 41):
                    publish_edge_depth.publish_table(directory, make_table(directory, index))
                time.sleep(0.2)
            finally:
                stop.set()
                reads, failures, runs = results.get(timeout=30)
                reader.join(timeout=30)

            self.assertEqual(failures, 0)
            self.assertGreater(reads, 50)
            self.assertGreater(len(runs), 1, "the reader must have seen the pointer move")
            self.assertEqual(read_table(read_latest(directory)).header.run_name, run_name(40))
            self.assertEqual(len([p for p in directory.iterdir() if p.suffix == ".bin"]), 3)


if __name__ == "__main__":
    unittest.main()
