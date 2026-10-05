"""Runs against a real PostGIS. Set EDGE_DEPTH_TEST_DSN (for example
"host=/tmp/pgtest port=55433 dbname=flowtest user=postgres"); the tests work in their own schema and
drop it afterwards. The pure checks of read_export and iter_edges need no database."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import psycopg2

import graph_edges
from graph_edges import GraphExportError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "database"))
import create_graph_edge_table  # noqa: E402

DSN = os.getenv("EDGE_DEPTH_TEST_DSN")
SCHEMA = f"graph_edges_test_{os.getpid()}"

# Three edges near Hanoi. Edge 1 runs 0.001 degrees of latitude, about 111 m.
EDGES = [
    (0, "LINESTRING (105.8000000 21.0000000, 105.8010000 21.0000000)"),
    (1, "LINESTRING (105.8000000 21.0000000, 105.8000000 21.0010000)"),
    (2, "LINESTRING (105.8010000 21.0000000, 105.8015000 21.0005000, 105.8020000 21.0010000)"),
]


def write_export(directory, edges=EDGES, graph_hash="a" * 64, edge_count=None, **overrides):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    meta = {
        "format_version": 1,
        "graph_hash": graph_hash,
        "edge_count": len(edges) if edge_count is None else edge_count,
        "node_count": 4,
        "graphhopper_commit": "d7dc1b069d2d091c7cfdc007d99d1765c82e618d",
    }
    meta.update(overrides)
    (directory / "graph.json").write_text(json.dumps(meta, indent=2) + "\n")
    lines = ["edge_id,wkt"] + [f'{edge_id},"{wkt}"' for edge_id, wkt in edges]
    (directory / "edges.csv").write_text("\n".join(lines) + "\n")
    return directory


class ReadExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_reads_the_hash_and_counts(self):
        write_export(self.dir, graph_hash="b" * 64)

        export = graph_edges.read_export(self.dir)

        self.assertEqual((export.graph_hash, export.edge_count, export.node_count), ("b" * 64, 3, 4))

    def test_a_missing_folder_names_the_folder_and_the_script(self):
        with self.assertRaises(GraphExportError) as caught:
            graph_edges.read_export(self.dir / "none")

        self.assertIn(str(self.dir / "none"), str(caught.exception))
        self.assertIn("export-edges.sh", str(caught.exception))

    def test_a_missing_edges_file_is_an_error(self):
        write_export(self.dir)
        (self.dir / "edges.csv").unlink()

        with self.assertRaises(GraphExportError):
            graph_edges.read_export(self.dir)

    def test_a_wrong_format_version_is_an_error(self):
        write_export(self.dir, format_version=2)

        with self.assertRaises(GraphExportError) as caught:
            graph_edges.read_export(self.dir)

        self.assertIn("format_version", str(caught.exception))

    def test_a_missing_key_is_an_error(self):
        write_export(self.dir)
        meta = json.loads((self.dir / "graph.json").read_text())
        del meta["graph_hash"]
        (self.dir / "graph.json").write_text(json.dumps(meta))

        with self.assertRaises(GraphExportError) as caught:
            graph_edges.read_export(self.dir)

        self.assertIn("graph_hash", str(caught.exception))


class IterEdgesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_yields_each_edge_id_with_its_geometry_in_order(self):
        write_export(self.dir)

        rows = list(graph_edges.iter_edges(graph_edges.read_export(self.dir)))

        self.assertEqual(rows, EDGES)

    def test_fewer_rows_than_edge_count_is_an_error(self):
        write_export(self.dir, edge_count=4)

        with self.assertRaises(GraphExportError) as caught:
            list(graph_edges.iter_edges(graph_edges.read_export(self.dir)))

        self.assertIn("3 rows", str(caught.exception))

    def test_more_rows_than_edge_count_is_an_error(self):
        write_export(self.dir, edge_count=2)

        with self.assertRaises(GraphExportError):
            list(graph_edges.iter_edges(graph_edges.read_export(self.dir)))

    def test_ids_must_run_from_zero_without_gaps(self):
        write_export(self.dir, edges=[EDGES[0], EDGES[2]])

        with self.assertRaises(GraphExportError) as caught:
            list(graph_edges.iter_edges(graph_edges.read_export(self.dir)))

        self.assertIn("edge_id 2", str(caught.exception))


@unittest.skipUnless(DSN, "EDGE_DEPTH_TEST_DSN is not set")
class LoadGraphEdgesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg2.connect(DSN)
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {SCHEMA}")
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.execute(create_graph_edge_table.SQL)

    @classmethod
    def tearDownClass(cls):
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
        cls.conn.close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        with self.conn, self.conn.cursor() as cur:
            cur.execute("TRUNCATE graph_edge, graph_edge_export")

    def edges(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT edge_id, ST_AsText(geom), length_m FROM graph_edge ORDER BY edge_id")
            return cur.fetchall()

    def test_the_first_load_fills_the_table_and_records_the_hash(self):
        export = graph_edges.read_export(write_export(self.dir, graph_hash="c" * 64))

        loaded = graph_edges.load_graph_edges(self.conn, export)

        self.assertTrue(loaded)
        self.assertEqual([row[0] for row in self.edges()], [0, 1, 2])
        self.assertEqual(graph_edges.loaded_hash(self.conn), "c" * 64)

    def test_length_is_in_metres(self):
        graph_edges.load_graph_edges(self.conn, graph_edges.read_export(write_export(self.dir)))

        lengths = {edge_id: length for edge_id, _, length in self.edges()}

        # 0.001 degrees of latitude is 110.6 m, and of longitude at 21 degrees north is about 103.4 m.
        self.assertAlmostEqual(lengths[1], 110.6, delta=1.0)
        self.assertAlmostEqual(lengths[0], 103.8, delta=1.5)

    def test_the_same_hash_is_not_loaded_again(self):
        export = graph_edges.read_export(write_export(self.dir))
        graph_edges.load_graph_edges(self.conn, export)
        with self.conn, self.conn.cursor() as cur:
            cur.execute("DELETE FROM graph_edge WHERE edge_id = 2")

        loaded = graph_edges.load_graph_edges(self.conn, export)

        self.assertFalse(loaded)
        self.assertEqual([row[0] for row in self.edges()], [0, 1])

    def test_a_new_hash_replaces_every_edge(self):
        graph_edges.load_graph_edges(self.conn, graph_edges.read_export(write_export(self.dir, graph_hash="1" * 64)))
        other = Path(self.tmp.name) / "other"
        write_export(other, edges=EDGES[:2], graph_hash="2" * 64)

        loaded = graph_edges.load_graph_edges(self.conn, graph_edges.read_export(other))

        self.assertTrue(loaded)
        self.assertEqual([row[0] for row in self.edges()], [0, 1])
        self.assertEqual(graph_edges.loaded_hash(self.conn), "2" * 64)

    def test_a_bad_geometry_leaves_the_old_graph_in_place(self):
        graph_edges.load_graph_edges(self.conn, graph_edges.read_export(write_export(self.dir, graph_hash="1" * 64)))
        bad = Path(self.tmp.name) / "bad"
        write_export(bad, edges=[EDGES[0], (1, "NOT A LINE")], graph_hash="2" * 64)

        with self.assertRaises(Exception):
            graph_edges.load_graph_edges(self.conn, graph_edges.read_export(bad))
        self.conn.rollback()

        self.assertEqual([row[0] for row in self.edges()], [0, 1, 2])
        self.assertEqual(graph_edges.loaded_hash(self.conn), "1" * 64)

    def test_a_broken_export_is_refused_before_the_database_is_touched(self):
        graph_edges.load_graph_edges(self.conn, graph_edges.read_export(write_export(self.dir, graph_hash="1" * 64)))
        broken = Path(self.tmp.name) / "broken"
        write_export(broken, edge_count=9, graph_hash="2" * 64)

        with self.assertRaises(GraphExportError):
            graph_edges.load_graph_edges(self.conn, graph_edges.read_export(broken))

        self.assertEqual(graph_edges.loaded_hash(self.conn), "1" * 64)
        self.assertEqual(len(self.edges()), 3)


if __name__ == "__main__":
    unittest.main()
