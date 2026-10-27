"""The freshness check of US-044: do the export folder, graph_edge, the tables and the live graph agree on the graph
hash? Pure files, no database."""

import json
import tempfile
import unittest
from pathlib import Path

import check_tables
from edge_depth_table import TableHeader, write_latest, write_table
from test_edge_depth_table import GOLDEN_HEADER, GOLDEN_ROWS

OLD = "1" * 64
NEW = "2" * 64


def add_table(table_dir, run, graph_hash, latest=False):
    name = f"{run}.bin"
    header = TableHeader(graph_hash, run, GOLDEN_HEADER.step_times, GOLDEN_HEADER.edge_count)
    write_table(Path(table_dir) / name, header, GOLDEN_ROWS)
    if latest:
        write_latest(table_dir, name)
    return name


def write_export(export_dir, graph_hash):
    Path(export_dir).mkdir(parents=True, exist_ok=True)
    (Path(export_dir) / "graph.json").write_text(
        json.dumps({"format_version": 1, "graph_hash": graph_hash, "edge_count": 3, "node_count": 4})
    )
    (Path(export_dir) / "edges.csv").write_text("edge_id,wkt\n")


class CheckTablesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tables = Path(self._tmp.name) / "tables"
        self.export = Path(self._tmp.name) / "export"
        self.tables.mkdir()

    def check(self, **kwargs):
        return check_tables.check(self.tables, self.export, **kwargs)

    def test_everything_on_one_graph_is_fresh(self):
        write_export(self.export, NEW)
        add_table(self.tables, "20261005T120000", NEW, latest=True)

        report = self.check(graph_edge_hash=NEW, live_graph_hash=NEW)

        self.assertFalse(report.stale)
        self.assertEqual(report.problems, ())

    def test_a_latest_table_for_the_old_graph_is_stale_and_both_hashes_are_named(self):
        write_export(self.export, NEW)
        add_table(self.tables, "20261005T120000", OLD, latest=True)

        report = self.check(live_graph_hash=NEW)

        self.assertTrue(report.stale)
        text = "\n".join(report.problems)
        self.assertIn(OLD, text)
        self.assertIn(NEW, text)
        self.assertIn("20261005T120000", text)

    def test_an_export_for_the_old_graph_is_reported_when_the_live_graph_is_new(self):
        write_export(self.export, OLD)
        add_table(self.tables, "20261005T120000", OLD, latest=True)

        report = self.check(live_graph_hash=NEW)

        self.assertTrue(report.stale)
        self.assertTrue(any("export" in p for p in report.problems))

    def test_without_a_live_hash_the_export_is_the_reference(self):
        write_export(self.export, NEW)
        add_table(self.tables, "20261005T120000", OLD, latest=True)

        self.assertTrue(self.check().stale)

    def test_graph_edge_behind_the_export_is_not_a_problem(self):
        """The next table build reloads graph_edge when the hash differs, so this heals itself."""
        write_export(self.export, NEW)
        add_table(self.tables, "20261005T120000", NEW, latest=True)

        report = self.check(graph_edge_hash=OLD, live_graph_hash=NEW)

        self.assertFalse(report.stale)
        self.assertEqual(report.problems, ())
        self.assertIn("reload", "\n".join(report.lines))

    def test_older_kept_tables_of_the_old_graph_are_not_a_problem(self):
        write_export(self.export, NEW)
        add_table(self.tables, "20261005T114500", OLD)
        add_table(self.tables, "20261005T120000", NEW, latest=True)

        report = self.check(live_graph_hash=NEW)

        self.assertFalse(report.stale)
        self.assertIn("20261005T114500", "\n".join(report.lines))

    def test_no_table_published_is_a_problem(self):
        write_export(self.export, NEW)

        report = self.check()

        self.assertTrue(report.problems)
        self.assertTrue(report.stale)

    def test_no_export_is_a_problem(self):
        add_table(self.tables, "20261005T120000", NEW, latest=True)

        report = self.check()

        self.assertTrue(any("export" in p for p in report.problems))

    def test_the_report_lists_every_hash_it_compared(self):
        write_export(self.export, NEW)
        add_table(self.tables, "20261005T120000", NEW, latest=True)

        text = "\n".join(self.check(graph_edge_hash=NEW, live_graph_hash=NEW).lines)

        for label in ("live graph", "export folder", "graph_edge", "latest table"):
            self.assertIn(label, text)


class MainTests(unittest.TestCase):
    def test_exit_code_is_one_for_a_stale_table_and_zero_for_a_fresh_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            tables, export = Path(tmp) / "t", Path(tmp) / "e"
            tables.mkdir()
            write_export(export, NEW)
            add_table(tables, "20261005T120000", NEW, latest=True)
            args = ["--table-dir", str(tables), "--export-dir", str(export), "--no-db"]

            self.assertEqual(check_tables.main(args + ["--graph-hash", NEW]), 0)
            self.assertEqual(check_tables.main(args + ["--graph-hash", OLD]), 1)


if __name__ == "__main__":
    unittest.main()
