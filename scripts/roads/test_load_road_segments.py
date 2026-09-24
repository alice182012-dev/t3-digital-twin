"""Runs against a real PostGIS. Set ROAD_SEGMENT_TEST_DSN (for example
"host=/tmp port=55433 dbname=roadtest user=postgres"); each run works in its own schema and drops
it afterwards."""

import json
import os
import sys
import unittest
from functools import cache
from pathlib import Path
from tempfile import TemporaryDirectory

import psycopg2
from osgeo import osr

import load_road_segments
from load_road_segments import LoadResult, RoadSegmentError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "database"))
from create_road_segment_table import SQL as CREATE_TABLE_SQL  # noqa: E402

DSN = os.getenv("ROAD_SEGMENT_TEST_DSN")
SCHEMA = f"road_segment_test_{os.getpid()}"
ORIGIN = (583000.0, 2327000.0)


@cache
def to_4326():
    osr.UseExceptions()
    src, dst = osr.SpatialReference(), osr.SpatialReference()
    src.ImportFromEPSG(3405)
    dst.ImportFromEPSG(4326)
    for srs in (src, dst):
        srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    return osr.CoordinateTransformation(src, dst)


def line(*offsets_m):
    """A LineString through the given (east, north) offsets in metres from ORIGIN in EPSG:3405,
    written in lon/lat as the real roads file is."""
    coords = []
    for dx, dy in offsets_m:
        lon, lat, _ = to_4326().TransformPoint(ORIGIN[0] + dx, ORIGIN[1] + dy)
        coords.append([lon, lat])
    return {"type": "LineString", "coordinates": coords}


def feature(way_id, geometry, name="Phố Test", highway="residential"):
    props = {"highway": highway, "name": name}
    if way_id is not None:
        props["@id"] = way_id
    return {"type": "Feature", "id": way_id, "properties": props, "geometry": geometry}


@unittest.skipUnless(DSN, "ROAD_SEGMENT_TEST_DSN is not set")
class LoadRoadSegmentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conn = psycopg2.connect(DSN)
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA {SCHEMA}")
            cur.execute(f"SET search_path TO {SCHEMA}, public")
            cur.execute(CREATE_TABLE_SQL)

    @classmethod
    def tearDownClass(cls):
        with cls.conn, cls.conn.cursor() as cur:
            cur.execute(f"DROP SCHEMA {SCHEMA} CASCADE")
        cls.conn.close()

    def setUp(self):
        with self.conn, self.conn.cursor() as cur:
            cur.execute("TRUNCATE road_segment")
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write_roads(self, *features):
        path = Path(self.tmp.name) / f"roads_{len(list(Path(self.tmp.name).iterdir()))}.geojson"
        path.write_text(json.dumps({"type": "FeatureCollection", "features": list(features)}))
        return path

    def load(self, *features):
        return load_road_segments.load(self.conn, self.write_roads(*features), max_piece=50.0)

    def rows(self):
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT segment_id, way_id, piece_index, road_name, highway, round(length_m::numeric, 3),
                       round(ST_X(ST_StartPoint(ST_Transform(geom, 3405)))::numeric - {ORIGIN[0]}, 2),
                       round(ST_Y(ST_StartPoint(ST_Transform(geom, 3405)))::numeric - {ORIGIN[1]}, 2)
                FROM road_segment ORDER BY way_id, piece_index
                """
            )
            return [
                (sid, way, idx, name, hwy, float(length), float(x), float(y))
                for sid, way, idx, name, hwy, length, x, y in cur.fetchall()
            ]

    def test_short_way_is_one_piece(self):
        result = self.load(feature("way/1", line((0, 0), (30, 0))))

        self.assertEqual(result, LoadResult(inserted=1, updated=0, deleted=0, total=1))
        self.assertEqual(
            self.rows(), [("way/1#0", "way/1", 0, "Phố Test", "residential", 30.0, 0.0, 0.0)]
        )

    def test_long_way_splits_into_equal_ordered_pieces(self):
        self.load(feature("way/2", line((0, 0), (120, 0))))

        self.assertEqual(
            self.rows(),
            [
                ("way/2#0", "way/2", 0, "Phố Test", "residential", 40.0, 0.0, 0.0),
                ("way/2#1", "way/2", 1, "Phố Test", "residential", 40.0, 40.0, 0.0),
                ("way/2#2", "way/2", 2, "Phố Test", "residential", 40.0, 80.0, 0.0),
            ],
        )

    def test_exact_multiple_gets_no_empty_last_piece(self):
        self.load(
            feature("way/3", line((0, 0), (100, 0))),
            feature("way/7", line((0, 0), (100.0001, 0))),
        )

        self.assertEqual(
            [(sid, length) for sid, *_, length, _x, _y in self.rows()],
            [("way/3#0", 50.0), ("way/3#1", 50.0), ("way/7#0", 50.0), ("way/7#1", 50.0)],
        )

    def test_split_follows_metric_length_not_vertices(self):
        self.load(feature("way/4", line((0, 0), (10, 0), (10, 90))))

        self.assertEqual(
            [(sid, length, x, y) for sid, *_, length, x, y in self.rows()],
            [("way/4#0", 50.0, 0.0, 0.0), ("way/4#1", 50.0, 10.0, 40.0)],
        )

    def test_second_load_of_same_file_changes_nothing(self):
        roads = self.write_roads(
            feature("way/1", line((0, 0), (30, 0))),
            feature("way/2", line((0, 0), (120, 0)), name=None),
        )
        first = load_road_segments.load(self.conn, roads, max_piece=50.0)
        before = self.rows()

        second = load_road_segments.load(self.conn, roads, max_piece=50.0)

        self.assertEqual(first, LoadResult(inserted=4, updated=0, deleted=0, total=4))
        self.assertEqual(second, LoadResult(inserted=0, updated=0, deleted=0, total=4))
        self.assertEqual(self.rows(), before)

    def test_reload_removes_dropped_ways_and_surplus_pieces(self):
        self.load(
            feature("way/1", line((0, 0), (30, 0))),
            feature("way/2", line((0, 0), (120, 0))),
        )

        result = self.load(feature("way/2", line((0, 0), (80, 0)), highway="primary"))

        self.assertEqual(result, LoadResult(inserted=0, updated=2, deleted=2, total=2))
        self.assertEqual(
            [(sid, hwy, length) for sid, _w, _i, _n, hwy, length, _x, _y in self.rows()],
            [("way/2#0", "primary", 40.0), ("way/2#1", "primary", 40.0)],
        )

    def test_bad_features_raise_and_write_nothing(self):
        self.load(feature("way/1", line((0, 0), (30, 0))))
        polygon = {"type": "Polygon", "coordinates": [line((0, 0), (10, 0), (10, 10), (0, 0))["coordinates"]]}
        cases = {
            "no @id": [feature(None, line((0, 0), (30, 0)))],
            "not a LineString": [feature("way/5", polygon)],
            "repeated @id": [
                feature("way/6", line((0, 0), (30, 0))),
                feature("way/6", line((0, 0), (40, 0))),
            ],
        }
        for label, features in cases.items():
            with self.subTest(label):
                with self.assertRaises(RoadSegmentError):
                    self.load(*features)
                self.assertEqual([row[0] for row in self.rows()], ["way/1#0"])


if __name__ == "__main__":
    unittest.main()
