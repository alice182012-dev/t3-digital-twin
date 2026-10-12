"""Runs against a real PostGIS with postgis_raster. Set FLOOD_ROADS_TEST_DSN (for example
"host=/tmp port=55433 dbname=flowtest user=postgres"); each run works in its own schema and drops
it afterwards.

The synthetic tiles are 10 by 10 pixels of 0.00001 degrees in EPSG:4326, like raster_load's tiles
with fewer pixels. Each test piece runs along one pixel row and declares a length_m equal to its
pixel count, so its 1 m samples land on pixel centres and the expected depths are exact."""

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

import psycopg2

import flood_on_roads
from flood_on_roads import FloodOnRoadsError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "database"))
import create_flood_depth_raster_tables  # noqa: E402
import create_flood_road_tables  # noqa: E402
import create_flood_run_output_table  # noqa: E402
import create_road_segment_table  # noqa: E402
from test_run_output import FakeConnection, published  # noqa: E402

DSN = os.getenv("FLOOD_ROADS_TEST_DSN")
SCHEMA = f"flood_roads_test_{os.getpid()}"

RUN = "20260924T164803"
T1_UTC = datetime(2026, 9, 24, 9, 48, 3)
T2_UTC = datetime(2026, 9, 24, 10, 18, 9)
RUN_LOCAL = datetime(2026, 9, 24, 16, 48, 3)
T1_LOCAL = datetime(2026, 9, 24, 16, 48, 3)
T2_LOCAL = datetime(2026, 9, 24, 17, 18, 9)

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
    return f"LINESTRING({ULX + col_from * PX} {lat}, {ULX + col_to * PX} {lat})"


@unittest.skipUnless(DSN, "FLOOD_ROADS_TEST_DSN is not set")
class FloodOnRoadsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg2.connect(DSN)
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {SCHEMA}")
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.execute(create_flood_road_tables.SQL)
            cur.execute(create_road_segment_table.SQL)
            cur.execute(create_flood_depth_raster_tables.SQL)
            cur.execute(create_flood_run_output_table.SQL)

    @classmethod
    def tearDownClass(cls):
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
        cls.conn.close()

    def setUp(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(
                "TRUNCATE road_segment, flood_depth_raster_tile, flood_road_values, flood_road_file, flood_run_output"
            )
            # Qualified: search_path falls through to public, where a real shadow table may live.
            cur.execute(f"DROP TABLE IF EXISTS {SCHEMA}.flood_road_values_shadow")

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

    def add_piece(self, segment_id, wkt, length_m, road_name="Phố Test"):
        way_id, piece = segment_id.split("#")
        with self.conn, self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO road_segment VALUES (%s, %s, %s, %s, 'residential', %s, ST_GeomFromText(%s, 4326))",
                (segment_id, way_id, int(piece), road_name, length_m, wkt),
            )

    def rows(self, table="flood_road_values"):
        with self.conn.cursor() as cur:
            cur.execute(
                f"""SELECT segment_id, timestamp, forecast_time, depth, road_name,
                           ST_AsText(geom_4326), geom->>'type'
                    FROM {table} ORDER BY segment_id, forecast_time"""
            )
            return cur.fetchall()

    def depths(self, table="flood_road_values"):
        """This task's rows only; rows seeded as the old pipeline's have no segment_id."""
        return {
            (seg, ft): round(depth, 5)
            for seg, _, ft, depth, *_ in self.rows(table)
            if seg is not None
        }

    def standard_run(self):
        """Tile (0,0) and tile (1,0) sit side by side. Row 1 of tile (0,0) has a 2-pixel stretch at
        0.6 m; row 3 is 0.2 m in tile (0,0) and 0.4 m in tile (1,0); row 8 is 0.5 m at T1 only.
        Tile (2,0) is wet at T1 and wholly dry at T2, so T2 samples nothing in it. way/6 stops short
        of tile (1,0)'s edge, since touching that wet hull would make T2 sample it anyway."""
        t1_left = {(1, 2): 0.6, (1, 3): 0.6, **{(3, c): 0.2 for c in range(TILE)}}
        t1_left.update({(8, c): 0.5 for c in range(TILE)})
        right = {(3, c): 0.4 for c in range(TILE)}
        self.add_tile(T1_UTC, 0, 0, t1_left)
        self.add_tile(T1_UTC, 1, 0, right)
        t2_left = {k: v for k, v in t1_left.items() if k[0] != 8}
        self.add_tile(T2_UTC, 0, 0, t2_left)
        self.add_tile(T2_UTC, 1, 0, right)
        self.add_tile(T1_UTC, 2, 0, {(4, c): 0.3 for c in range(TILE)})
        self.add_tile(T2_UTC, 2, 0, {})
        self.add_tile(T1_UTC, 5, 5, {})
        self.add_tile(T2_UTC, 5, 5, {})

        self.add_piece("way/1#0", row_line(1, 0, 10), 10.0)
        self.add_piece("way/2#0", row_line(3, 5, 15), 10.0)
        self.add_piece("way/3#0", row_line(6, 0, 10), 10.0)
        self.add_piece("way/4#0", row_line(58, 50, 60), 10.0)
        self.add_piece("way/5#0", row_line(8, 0, 10), 10.0, road_name=None)
        self.add_piece("way/6#0", row_line(4, 22, 28), 6.0)

    def test_depth_is_the_deepest_sample_even_on_a_short_stretch(self):
        self.standard_run()
        flood_on_roads.compute(self.conn, RUN)
        self.assertEqual(self.depths()[("way/1#0", T1_LOCAL)], 0.6)

    def test_piece_across_two_tiles_reads_both(self):
        """way/7 is deepest in the left tile and way/8 in the right one, so each value proves one
        tile was matched to the piece's samples."""
        self.add_tile(T1_UTC, 0, 0, {(0, 9): 0.45, (2, 9): 0.15})
        self.add_tile(T1_UTC, 1, 0, {(0, 0): 0.15, (2, 0): 0.45})
        self.add_piece("way/7#0", row_line(0, 5, 15), 10.0)
        self.add_piece("way/8#0", row_line(2, 5, 15), 10.0)
        flood_on_roads.compute(self.conn, RUN)
        self.assertEqual(
            self.depths(), {("way/7#0", T1_LOCAL): 0.45, ("way/8#0", T1_LOCAL): 0.45}
        )

    def test_dry_pieces_get_no_rows(self):
        self.standard_run()
        flood_on_roads.compute(self.conn, RUN)
        self.assertEqual({seg for seg, _ in self.depths()}, {"way/1#0", "way/2#0", "way/5#0", "way/6#0"})

    def test_piece_wet_at_one_timestep_gets_a_zero_row_at_the_other(self):
        self.standard_run()
        flood_on_roads.compute(self.conn, RUN)
        depths = self.depths()
        self.assertEqual(depths[("way/5#0", T1_LOCAL)], 0.5)
        self.assertEqual(depths[("way/5#0", T2_LOCAL)], 0.0)
        self.assertEqual(depths[("way/6#0", T1_LOCAL)], 0.3)
        self.assertEqual(depths[("way/6#0", T2_LOCAL)], 0.0)

    def test_timestamps_are_local_run_and_forecast_times(self):
        self.standard_run()
        result = flood_on_roads.compute(self.conn, RUN)
        rows = self.rows()
        self.assertEqual({row[1] for row in rows}, {RUN_LOCAL})
        self.assertEqual({row[2] for row in rows}, {T1_LOCAL, T2_LOCAL})
        self.assertEqual(
            [(t.forecast_time, t.rows, t.wet_pieces) for t in result.timesteps],
            [(T1_LOCAL, 4, 4), (T2_LOCAL, 4, 2)],
        )

    def test_row_carries_road_name_segment_and_geometry(self):
        self.standard_run()
        flood_on_roads.compute(self.conn, RUN)
        by_segment = {row[0]: row for row in self.rows()}
        self.assertEqual(by_segment["way/1#0"][4], "Phố Test")
        self.assertEqual(by_segment["way/5#0"][4], "way/5")
        self.assertEqual(by_segment["way/1#0"][5], row_line(1, 0, 10).replace(", ", ","))
        self.assertEqual(by_segment["way/1#0"][6], "LineString")

    def test_rerun_converges_and_replaces_only_this_runs_timesteps(self):
        self.standard_run()
        with self.conn, self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO flood_road_file (timestamp, source_file) VALUES (%s, 'old.geojson') RETURNING id",
                (RUN_LOCAL,),
            )
            file_id = cur.fetchone()[0]
            for timestamp, forecast_time, name in (
                (RUN_LOCAL, T1_LOCAL, "old sliver, same run and time"),
                (datetime(2026, 9, 24, 16, 18, 0), T1_LOCAL, "older run"),
                (RUN_LOCAL, datetime(2026, 9, 24, 19, 0, 0), "time this run has no tiles for"),
            ):
                cur.execute(
                    """INSERT INTO flood_road_values (file_id, timestamp, road_name, forecast_time, depth)
                       VALUES (%s, %s, %s, %s, 0.9)""",
                    (file_id, timestamp, name, forecast_time),
                )

        flood_on_roads.compute(self.conn, RUN)
        first = self.depths()
        flood_on_roads.compute(self.conn, RUN)

        self.assertEqual(self.depths(), first)
        self.assertEqual(len(first), 8)
        with self.conn.cursor() as cur:
            cur.execute("SELECT road_name FROM flood_road_values WHERE segment_id IS NULL ORDER BY 1")
            self.assertEqual(
                [row[0] for row in cur.fetchall()], ["older run", "time this run has no tiles for"]
            )
            cur.execute("SELECT feature_count FROM flood_road_file WHERE source_file = %s", (f"flood_on_roads_{RUN}",))
            self.assertEqual(cur.fetchall(), [(4,)])

    def test_a_rerun_keeps_one_road_values_row(self):
        self.standard_run()
        flood_on_roads.compute(self.conn, RUN)
        flood_on_roads.compute(self.conn, RUN)

        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT run_ts, output FROM flood_run_output")
            self.assertEqual(cur.fetchall(), [(RUN, "road_values")])

    def test_shadow_target_leaves_flood_road_values_alone(self):
        self.standard_run()
        flood_on_roads.create_shadow_table(self.conn, "flood_road_values_shadow")
        result = flood_on_roads.compute(self.conn, RUN, target_table="flood_road_values_shadow")

        self.assertEqual(self.rows(), [])
        self.assertEqual(len(self.rows("flood_road_values_shadow")), 8)
        self.assertEqual(result.target_table, "flood_road_values_shadow")
        self.assertEqual(result.rows, 8)

    def registry(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("SELECT source_file, feature_count, forecast_times FROM flood_road_file ORDER BY id")
            return cur.fetchall()

    def test_a_dry_run_registers_its_forecast_times_and_writes_no_rows(self):
        self.add_tile(T1_UTC, 0, 0, {})
        self.add_tile(T2_UTC, 0, 0, {})
        self.add_piece("way/1#0", row_line(1, 0, 10), 10.0)
        flood_on_roads.compute(self.conn, RUN)
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.registry(), [(f"flood_on_roads_{RUN}", 0, [T1_LOCAL, T2_LOCAL])])

    def test_a_wet_run_registers_its_forecast_times(self):
        self.standard_run()
        flood_on_roads.compute(self.conn, RUN)
        self.assertEqual(self.registry(), [(f"flood_on_roads_{RUN}", 4, [T1_LOCAL, T2_LOCAL])])

    def test_a_rerun_keeps_the_registered_forecast_times(self):
        self.standard_run()
        flood_on_roads.compute(self.conn, RUN)
        flood_on_roads.compute(self.conn, RUN)
        self.assertEqual(self.registry(), [(f"flood_on_roads_{RUN}", 4, [T1_LOCAL, T2_LOCAL])])

    def test_table_script_run_twice_backfills_a_registered_runs_forecast_times(self):
        """A run registered before forecast_times existed gets its times from its value rows; a run
        without rows keeps NULL, and a second run of the script changes nothing."""
        with self.conn, self.conn.cursor() as cur:
            cur.execute("ALTER TABLE flood_road_file DROP COLUMN forecast_times")
            cur.execute(
                "INSERT INTO flood_road_file (timestamp, source_file) VALUES (%s, 'old run') RETURNING id",
                (RUN_LOCAL,),
            )
            file_id = cur.fetchone()[0]
            cur.execute("INSERT INTO flood_road_file (timestamp, source_file) VALUES (%s, 'no rows')", (RUN_LOCAL,))
            for forecast_time in (T2_LOCAL, T1_LOCAL, T2_LOCAL):
                cur.execute(
                    "INSERT INTO flood_road_values (file_id, timestamp, forecast_time, depth) VALUES (%s, %s, %s, 0.3)",
                    (file_id, RUN_LOCAL, forecast_time),
                )
            cur.execute(create_flood_road_tables.SQL)
            cur.execute(create_flood_road_tables.SQL)
        self.assertEqual(self.registry(), [("old run", None, [T1_LOCAL, T2_LOCAL]), ("no rows", None, None)])

    def test_run_without_tiles_raises_and_writes_nothing(self):
        self.add_piece("way/1#0", row_line(1, 0, 10), 10.0)
        with self.assertRaises(FloodOnRoadsError):
            flood_on_roads.compute(self.conn, RUN)
        self.assertEqual(self.rows(), [])


class RoadValuesRunOutputTests(unittest.TestCase):
    """The road_values row of flood_run_output commits in the transaction of the run's rows, and only then."""

    def connection(self, fail_insert=False):
        def rows(sql):
            if sql is flood_on_roads._TIMESTEPS_SQL:
                return [(T1_UTC,)]
            if sql is flood_on_roads._REGISTER_SQL:
                return [(7,)]
            if isinstance(sql, str) and "count(DISTINCT segment_id)" in sql:
                return [(3,)]
            if fail_insert and not isinstance(sql, str) and "INSERT INTO" in repr(sql):
                raise psycopg2.errors.DiskFull("could not extend file")
            return ()

        return FakeConnection(rows)

    def test_a_computed_run_records_its_road_values_row(self):
        conn = self.connection()

        result = flood_on_roads.compute(conn, RUN)

        self.assertEqual(result.rows, 3)
        self.assertEqual(published(conn), {(RUN, "road_values")})

    def test_a_failed_insert_of_the_rows_leaves_no_row(self):
        conn = self.connection(fail_insert=True)

        with self.assertRaises(psycopg2.errors.DiskFull):
            flood_on_roads.compute(conn, RUN)

        self.assertEqual(conn.committed, [])

    def test_a_shadow_target_records_no_row(self):
        conn = self.connection()

        flood_on_roads.compute(conn, RUN, target_table="flood_road_values_shadow")

        written = [repr(sql) for sql, _ in conn.committed if not isinstance(sql, str)]
        self.assertEqual(len([text for text in written if "flood_road_values_shadow" in text]), 2)
        self.assertEqual(published(conn), set())


if __name__ == "__main__":
    unittest.main()
