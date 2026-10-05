"""Runs against a real PostGIS with postgis_raster. Set EDGE_DEPTH_TEST_DSN (for example
"host=/tmp/pgtest port=55433 dbname=flowtest user=postgres"); the tests work in their own schema and
drop it afterwards.

The synthetic tiles are 10 by 10 pixels of 0.00001 degrees in EPSG:4326, like raster_load's tiles with
fewer pixels. Each test edge runs along one pixel row and declares a length close to its pixel count in
metres (the table task takes the length from the geometry, about 1.1 m per pixel), so its samples land
on pixel centres and the expected depths are exact."""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

import build_edge_depth
import edge_depth_table
import graph_edges
import spot_check
from build_edge_depth import EdgeDepthBuildError
from test_graph_edges import write_export

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "database"))
import create_flood_depth_raster_tables  # noqa: E402
import create_graph_edge_table  # noqa: E402

DSN = os.getenv("EDGE_DEPTH_TEST_DSN")
SCHEMA = f"edge_depth_test_{os.getpid()}"

RUN = "20260924T164803"
T1_UTC = datetime(2026, 9, 24, 9, 48, 3)
T2_UTC = datetime(2026, 9, 24, 10, 18, 9)

PX = 0.00001
TILE = 10
ULX, ULY = 105.8, 21.0


def tile_values(wet):
    """A TILE x TILE grid, 0 (nodata) except {(row, col): depth}."""
    return [[wet.get((r, c), 0.0) for c in range(TILE)] for r in range(TILE)]


def row_line(row, col_from, col_to):
    """A LineString along pixel row `row` from the left edge of col_from to the left edge of col_to,
    in the global pixel grid that starts at (ULX, ULY)."""
    lat = ULY - (row + 0.5) * PX
    return f"LINESTRING ({ULX + col_from * PX:.7f} {lat:.7f}, {ULX + col_to * PX:.7f} {lat:.7f})"


# Edge ids run from 0 without gaps, as in a real export.
STANDARD_EDGES = [
    (0, row_line(1, 0, 10)),    # 2 pixels at 0.6 m, deepest sample 0.6 m at both steps
    (1, row_line(3, 5, 15)),    # 0.2 m in tile (0,0), 0.4 m in tile (1,0): deepest 0.4 m
    (2, row_line(6, 0, 10)),    # dry
    (3, row_line(58, 50, 60)),  # far from every tile
    (4, row_line(8, 0, 10)),    # 0.5 m at the first step only
]


class DepthCmTests(unittest.TestCase):
    def test_rounds_to_the_nearest_centimetre(self):
        self.assertEqual(build_edge_depth.depth_cm(0.2), 20)
        self.assertEqual(build_edge_depth.depth_cm(0.204), 20)
        self.assertEqual(build_edge_depth.depth_cm(0.206), 21)

    def test_dry_and_tiny_depths_are_zero(self):
        self.assertEqual(build_edge_depth.depth_cm(0.0), 0)
        self.assertEqual(build_edge_depth.depth_cm(0.004), 0)

    def test_a_depth_above_what_uint16_holds_is_capped(self):
        self.assertEqual(build_edge_depth.depth_cm(700.0), 0xFFFF)


@unittest.skipUnless(DSN, "EDGE_DEPTH_TEST_DSN is not set")
class BuildEdgeDepthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg2.connect(DSN)
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {SCHEMA}")
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.execute(create_flood_depth_raster_tables.SQL)
            cur.execute(create_graph_edge_table.SQL)

    @classmethod
    def tearDownClass(cls):
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
        cls.conn.close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.export_dir = Path(self.tmp.name) / "export"
        self.out_dir = Path(self.tmp.name) / "tables"
        with self.conn, self.conn.cursor() as cur:
            cur.execute("TRUNCATE flood_depth_raster_tile, graph_edge, graph_edge_export")

    def add_tile(self, valid_time_utc, tile_x, tile_y, wet):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO flood_depth_raster_tile (run_ts, valid_time_utc, tile_x, tile_y, rast)
                SELECT %(run)s, %(t)s, %(x)s, %(y)s,
                       ST_SetValues(
                           ST_AddBand(
                               ST_MakeEmptyRaster(%(n)s, %(n)s, %(ulx)s, %(uly)s, %(px)s, -%(px)s, 0, 0, 4326),
                               '32BF'::text, 0, 0),
                           1, 1, 1, %(values)s::double precision[][])
                """,
                {
                    "run": RUN,
                    "t": valid_time_utc,
                    "x": tile_x,
                    "y": tile_y,
                    "n": TILE,
                    "ulx": ULX + tile_x * TILE * PX,
                    "uly": ULY - tile_y * TILE * PX,
                    "px": PX,
                    "values": tile_values(wet),
                },
            )

    def standard_run(self):
        """Tile (0,0) and tile (1,0) sit side by side. Row 1 of tile (0,0) has a 2-pixel stretch at
        0.6 m; row 3 is 0.2 m in tile (0,0) and 0.4 m in tile (1,0); row 8 is 0.5 m at T1 only."""
        t1_left = {(1, 2): 0.6, (1, 3): 0.6, **{(3, c): 0.2 for c in range(TILE)}}
        t1_left.update({(8, c): 0.5 for c in range(TILE)})
        right = {(3, c): 0.4 for c in range(TILE)}
        self.add_tile(T1_UTC, 0, 0, t1_left)
        self.add_tile(T1_UTC, 1, 0, right)
        t2_left = {k: v for k, v in t1_left.items() if k[0] != 8}
        self.add_tile(T2_UTC, 0, 0, t2_left)
        self.add_tile(T2_UTC, 1, 0, right)

    def build(self, edges=STANDARD_EDGES, graph_hash="a" * 64):
        write_export(self.export_dir, edges=edges, graph_hash=graph_hash)
        return build_edge_depth.build_table(self.conn, RUN, self.export_dir, self.out_dir)

    def read(self, result):
        return edge_depth_table.read_table(result.path)

    def test_each_edge_gets_its_deepest_sample_in_centimetres_at_each_step(self):
        self.standard_run()

        table = self.read(self.build())

        self.assertEqual(table.edge_depths_cm(0), (60, 60))
        self.assertEqual(table.edge_depths_cm(1), (40, 40))
        self.assertEqual(table.edge_depths_cm(2), (0, 0))
        self.assertEqual(table.edge_depths_cm(4), (50, 0))

    def test_an_edge_outside_the_model_reads_zero(self):
        self.standard_run()

        table = self.read(self.build())

        self.assertEqual(table.edge_depths_cm(3), (0, 0))

    def test_the_header_holds_the_hash_the_run_the_steps_and_the_edge_count(self):
        self.standard_run()

        header = self.read(self.build(graph_hash="f" * 64)).header

        self.assertEqual(header.graph_hash, "f" * 64)
        self.assertEqual(header.run_name, RUN)
        self.assertEqual(header.edge_count, 5)
        self.assertEqual(
            header.step_times,
            (T1_UTC.replace(tzinfo=timezone.utc), T2_UTC.replace(tzinfo=timezone.utc)),
        )

    def test_the_file_is_named_after_the_run(self):
        self.standard_run()

        result = self.build()

        self.assertEqual(result.path, self.out_dir / f"{RUN}.bin")
        self.assertEqual(sorted(p.name for p in self.out_dir.iterdir()), [f"{RUN}.bin"])

    def test_the_report_has_the_size_the_counts_and_the_durations(self):
        self.standard_run()

        result = self.build()

        self.assertEqual(result.size_bytes, result.path.stat().st_size)
        self.assertEqual((result.edge_count, result.step_count), (5, 2))
        self.assertEqual(result.wet_edges, (3, 2))
        self.assertEqual(len(result.sample_seconds), 2)
        self.assertGreater(result.seconds, 0)
        self.assertEqual(result.graph_hash, "a" * 64)
        self.assertEqual(result.run_ts, RUN)

    def test_the_first_build_loads_the_export_and_a_second_does_not(self):
        self.standard_run()

        first = self.build()
        second = self.build()

        self.assertTrue(first.graph_loaded)
        self.assertFalse(second.graph_loaded)

    def test_a_new_export_replaces_the_edges_and_the_values(self):
        self.standard_run()
        self.build(graph_hash="a" * 64)
        # In the new graph edge 2 runs where edge 0 did.
        moved = [STANDARD_EDGES[0], STANDARD_EDGES[1], (2, STANDARD_EDGES[0][1]), *STANDARD_EDGES[3:]]
        other = Path(self.tmp.name) / "export2"
        write_export(other, edges=moved, graph_hash="b" * 64)

        result = build_edge_depth.build_table(self.conn, RUN, other, self.out_dir)
        table = self.read(result)

        self.assertTrue(result.graph_loaded)
        self.assertEqual(table.header.graph_hash, "b" * 64)
        self.assertEqual(table.edge_depths_cm(2), (60, 60))

    def test_a_run_with_no_tiles_is_an_error_and_writes_nothing(self):
        with self.assertRaises(EdgeDepthBuildError) as caught:
            self.build()

        self.assertIn(RUN, str(caught.exception))
        self.assertFalse(self.out_dir.exists() and any(self.out_dir.iterdir()))

    def test_a_missing_export_is_an_error_and_writes_nothing(self):
        self.standard_run()

        with self.assertRaises(graph_edges.GraphExportError):
            build_edge_depth.build_table(self.conn, RUN, Path(self.tmp.name) / "none", self.out_dir)

        self.assertFalse(self.out_dir.exists() and any(self.out_dir.iterdir()))

    def test_a_failed_build_keeps_the_previous_file(self):
        self.standard_run()
        first = self.build()
        before = first.path.read_bytes()
        with self.conn, self.conn.cursor() as cur:
            cur.execute("DELETE FROM flood_depth_raster_tile")

        with self.assertRaises(EdgeDepthBuildError):
            self.build()

        self.assertEqual(first.path.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.out_dir.iterdir()), [f"{RUN}.bin"])

    def test_building_twice_gives_the_same_bytes(self):
        self.standard_run()

        first = self.build().path.read_bytes()
        second = self.build().path.read_bytes()

        self.assertEqual(first, second)

    # The spot check of US-041: table values against a direct ST_Value reading at the same sample points.

    def test_the_spot_check_finds_no_difference_on_a_correct_table(self):
        self.standard_run()
        result = self.build()

        check = spot_check.spot_check(self.conn, result.path, count=5)

        self.assertEqual(len(check.rows), 5 * 2)
        self.assertEqual(check.mismatches, ())

    def test_the_spot_check_reads_the_same_value_directly(self):
        self.standard_run()
        result = self.build()

        check = spot_check.spot_check(self.conn, result.path, count=5)

        by_key = {(row.edge_id, row.step): (row.table_cm, row.direct_cm) for row in check.rows}
        self.assertEqual(by_key[(0, 0)], (60, 60))
        self.assertEqual(by_key[(1, 1)], (40, 40))
        self.assertEqual(by_key[(4, 0)], (50, 50))
        self.assertEqual(by_key[(4, 1)], (0, 0))
        self.assertEqual(by_key[(3, 0)], (0, 0))

    def test_the_spot_check_reports_a_wrong_table_value(self):
        self.standard_run()
        result = self.build()
        table = edge_depth_table.read_table(result.path)
        rows = [list(table.edge_depths_cm(e)) for e in range(table.header.edge_count)]
        rows[1][0] = 99  # the table says 99 cm where the raster says 40
        edge_depth_table.write_table(result.path, table.header, rows)

        check = spot_check.spot_check(self.conn, result.path, count=5)

        self.assertEqual([(m.edge_id, m.step, m.table_cm, m.direct_cm) for m in check.mismatches], [(1, 0, 99, 40)])

    def test_the_spot_check_picks_wet_and_dry_edges_the_same_way_each_time(self):
        self.standard_run()
        result = self.build()

        first = spot_check.spot_check(self.conn, result.path, count=3, seed=7)
        second = spot_check.spot_check(self.conn, result.path, count=3, seed=7)

        self.assertEqual(first.rows, second.rows)
        picked = {row.edge_id for row in first.rows}
        self.assertEqual(len(picked), 3)
        self.assertTrue(any(row.table_cm > 0 for row in first.rows), "it must include a wet edge")
        self.assertTrue(any(row.table_cm == 0 for row in first.rows), "it must include a dry edge")

    def test_the_spot_check_needs_a_table_for_the_loaded_graph(self):
        self.standard_run()
        result = self.build()
        with self.conn, self.conn.cursor() as cur:
            cur.execute("UPDATE graph_edge_export SET graph_hash = %s", ("9" * 64,))

        with self.assertRaises(spot_check.SpotCheckError) as caught:
            spot_check.spot_check(self.conn, result.path, count=5)

        self.assertIn("hash", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
