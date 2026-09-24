"""Compares flood_on_roads.py's rows for one run with the GeoJSON chain's old rows for that run.

Usage: python compare_with_old.py RUN_TS OLD_CSV [--table flood_road_values_shadow] [--dsn DSN]

OLD_CSV holds the old flood_road_values rows of the run, with columns road_name, forecast_time,
depth, and wkt (the sliver's EPSG:4326 geometry). Each old row is a sliver of a road cut by one
flood cell and carries that cell's depth. Each sliver is assigned to the road_segment piece nearest
its midpoint, and a piece counts as impassable under the old pipeline when any of its slivers
reaches the vehicle's limit, which is how flood_areas.py treats the old rows. The run's tiles must
be in flood_depth_raster_tile, because the report also reads the raster along each old sliver. The
report prints Markdown tables to stdout.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from psycopg2 import sql

import flood_on_roads

SCRIPTS_DIR = Path(__file__).resolve().parents[1]

# A sliver lies on its way and a piece is a substring of the same way, so their distance is float
# noise from the 3405 round trip in load_road_segments.py. Anything farther is reported unmatched.
MATCH_TOLERANCE_M = 1.0

_LOAD_OLD_SQL = """
CREATE TEMP TABLE old_rows (road_name TEXT, forecast_time TIMESTAMP, depth DOUBLE PRECISION, wkt TEXT)
ON COMMIT DROP
"""

_MATCH_SQL = """
CREATE TEMP TABLE old_sliver ON COMMIT DROP AS
SELECT row_number() OVER () AS id, g AS geom,
       o.forecast_time, o.depth, ST_Length(ST_Transform(g, 3405)) AS length_m,
       CASE WHEN ST_Distance(ST_Transform(m.geom, 3405), ST_Transform(mid, 3405)) <= %(tol)s
            THEN m.segment_id END AS segment_id
FROM old_rows o
CROSS JOIN LATERAL ST_GeomFromText(o.wkt, 4326) AS g
CROSS JOIN LATERAL ST_LineInterpolatePoint(g, 0.5) AS mid
LEFT JOIN LATERAL (
    SELECT r.segment_id, r.geom FROM road_segment r ORDER BY r.geom <-> mid LIMIT 1
) m ON true
"""

# The old depth is one pixel of the flood cell the sliver crosses, which can lie off the road. This
# reads the same run's tiles at 1 m steps along each wet sliver itself, so a disagreement can be
# traced to the old sampling or to the new rows.
_SLIVER_RASTER_SQL = """
ALTER TABLE old_sliver ADD COLUMN on_sliver_max DOUBLE PRECISION;
UPDATE old_sliver s SET on_sliver_max = x.on_sliver_max
FROM (
    SELECT s.id, max(coalesce(v.depth, 0)) AS on_sliver_max
    FROM old_sliver s
    CROSS JOIN LATERAL generate_series(0, greatest(1, ceil(s.length_m))::int - 1) AS i
    CROSS JOIN LATERAL ST_LineInterpolatePoint(s.geom, (i + 0.5) / greatest(1, ceil(s.length_m))) AS pt
    LEFT JOIN LATERAL (
        SELECT max(ST_Value(t.rast, pt)) AS depth
        FROM flood_depth_raster_tile t
        WHERE t.run_ts = %(run_ts)s AND t.valid_time_utc = s.forecast_time - %(offset)s
          AND ST_Intersects(ST_ConvexHull(t.rast), pt)
    ) v ON true
    WHERE s.depth > 0
    GROUP BY s.id
) x
WHERE x.id = s.id;
UPDATE old_sliver SET on_sliver_max = 0 WHERE on_sliver_max IS NULL;
"""

_NEW_SQL = """
CREATE TEMP TABLE new_piece ON COMMIT DROP AS
SELECT segment_id, forecast_time, depth, depth_max FROM {table} WHERE timestamp = %(timestamp)s
"""

_COVERAGE_SQL = """
WITH wet_old AS (SELECT * FROM old_sliver WHERE depth > 0),
old_pieces AS (SELECT DISTINCT forecast_time, segment_id FROM old_sliver WHERE segment_id IS NOT NULL)
SELECT t.forecast_time,
       (SELECT count(*) FROM old_sliver o WHERE o.forecast_time = t.forecast_time),
       (SELECT count(*) FROM wet_old o WHERE o.forecast_time = t.forecast_time),
       (SELECT count(*) FROM wet_old o WHERE o.forecast_time = t.forecast_time AND o.on_sliver_max = 0),
       (SELECT count(*) FROM wet_old o WHERE o.forecast_time = t.forecast_time AND o.segment_id IS NULL),
       (SELECT count(*) FROM wet_old o JOIN new_piece n USING (forecast_time, segment_id)
        WHERE o.forecast_time = t.forecast_time),
       (SELECT count(*) FROM wet_old o JOIN new_piece n USING (forecast_time, segment_id)
        WHERE o.forecast_time = t.forecast_time AND n.depth_max > 0),
       (SELECT count(*) FROM new_piece n WHERE n.forecast_time = t.forecast_time),
       (SELECT count(*) FROM new_piece n WHERE n.forecast_time = t.forecast_time AND n.depth_max > 0),
       (SELECT count(*) FROM new_piece n WHERE n.forecast_time = t.forecast_time AND n.depth_max > 0
          AND NOT EXISTS (SELECT 1 FROM old_pieces p
                          WHERE p.forecast_time = n.forecast_time AND p.segment_id = n.segment_id))
FROM (SELECT DISTINCT forecast_time FROM old_sliver UNION SELECT DISTINCT forecast_time FROM new_piece) t
ORDER BY 1
"""

_DEPTH_SQL = """
SELECT o.forecast_time,
       count(*),
       avg(o.depth), avg(n.depth), avg(n.depth_max),
       avg(abs(o.depth - n.depth)), avg(abs(o.depth - n.depth_max)),
       count(*) FILTER (WHERE o.depth > n.depth_max + 0.005),
       corr(o.depth, n.depth), corr(o.depth, n.depth_max)
FROM old_sliver o JOIN new_piece n USING (forecast_time, segment_id)
WHERE o.depth > 0
GROUP BY 1 ORDER BY 1
"""

_PIECE_SQL = """
WITH old_piece AS (
    SELECT forecast_time, segment_id, max(depth) AS old_max, max(on_sliver_max) AS on_sliver_max
    FROM old_sliver WHERE segment_id IS NOT NULL GROUP BY 1, 2
)
SELECT forecast_time, segment_id, coalesce(o.old_max, 0), coalesce(o.on_sliver_max, 0),
       coalesce(n.depth, 0), coalesce(n.depth_max, 0)
FROM old_piece o FULL JOIN new_piece n USING (forecast_time, segment_id)
"""


@dataclass
class Confusion:
    both: int = 0
    danger: int = 0
    danger_off_sliver: int = 0
    new_only: int = 0
    neither: int = 0

    def add(self, old_impassable: bool, new_impassable: bool, on_sliver_impassable: bool) -> None:
        if old_impassable and new_impassable:
            self.both += 1
        elif old_impassable:
            self.danger += 1
            self.danger_off_sliver += not on_sliver_impassable
        elif new_impassable:
            self.new_only += 1
        else:
            self.neither += 1


def vehicle_limits() -> dict[str, float]:
    """The limits routing uses, read the way flood_metrics reads them, not copied."""
    sys.path.insert(0, str(SCRIPTS_DIR / "flood_metrics"))
    from extract_run import impassable_from_m

    return impassable_from_m()


def compare(conn, run_ts: str, old_csv: Path, table: str) -> dict:
    timestamp = flood_on_roads.run_timestamp(run_ts)
    with conn, conn.cursor() as cur:
        cur.execute(_LOAD_OLD_SQL)
        with open(old_csv, encoding="utf-8") as f:
            cur.copy_expert("COPY old_rows FROM STDIN WITH (FORMAT csv, HEADER true)", f)
        cur.execute(_MATCH_SQL, {"tol": MATCH_TOLERANCE_M})
        cur.execute(_SLIVER_RASTER_SQL, {"run_ts": run_ts, "offset": flood_on_roads.VIETNAM_UTC_OFFSET})
        cur.execute(sql.SQL(_NEW_SQL).format(table=sql.Identifier(table)), {"timestamp": timestamp})
        cur.execute(_COVERAGE_SQL)
        coverage = cur.fetchall()
        cur.execute(_DEPTH_SQL)
        depth = cur.fetchall()
        cur.execute(_PIECE_SQL)
        pieces = cur.fetchall()
        cur.execute(
            "SELECT percentile_cont(ARRAY[0.1, 0.5, 0.9]) WITHIN GROUP (ORDER BY length_m) FROM old_sliver"
        )
        sliver_lengths = cur.fetchone()[0]

    limits = vehicle_limits()
    confusion: dict[tuple, Confusion] = {}
    for forecast_time, _segment_id, old_max, on_sliver_max, mean, deepest in pieces:
        for vehicle, limit in limits.items():
            for measure, new_value in (("mean", mean), ("max", deepest)):
                for key in ((forecast_time, vehicle, measure), ("all", vehicle, measure)):
                    confusion.setdefault(key, Confusion()).add(
                        old_max >= limit, new_value >= limit, on_sliver_max >= limit
                    )
    return {
        "coverage": coverage,
        "depth": depth,
        "confusion": confusion,
        "limits": limits,
        "sliver_lengths": sliver_lengths,
    }


def _fmt(value, digits=3):
    return "n/a" if value is None else f"{value:.{digits}f}"


def report(run_ts: str, result: dict) -> str:
    lines = [f"## Run {run_ts}", ""]
    p10, p50, p90 = result["sliver_lengths"]
    lines += [
        f"Old sliver length: 10th percentile {p10:.1f} m, median {p50:.1f} m, 90th percentile {p90:.1f} m.",
        "",
        "### Coverage",
        "",
        "| Forecast time | Old rows | Old wet slivers | Wet, raster dry on sliver | Wet, no piece | "
        "Wet, piece has new row | "
        "Wet, piece wet in new | New rows | New wet rows | New wet, no old sliver |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in result["coverage"]:
        lines.append(f"| {row[0]:%Y-%m-%d %H:%M:%S} | " + " | ".join(str(v) for v in row[1:]) + " |")
    lines += [
        "",
        "### Depth agreement (old wet sliver against its piece)",
        "",
        "| Forecast time | Pairs | Old mean | New mean | New max mean | Abs diff to mean | "
        "Abs diff to max | Old above max | Corr mean | Corr max |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in result["depth"]:
        lines.append(
            f"| {row[0]:%Y-%m-%d %H:%M:%S} | {row[1]} | "
            + " | ".join(_fmt(v) for v in row[2:7])
            + f" | {row[7]} | {_fmt(row[8])} | {_fmt(row[9])} |"
        )
    lines += [
        "",
        "### Impassable per piece: old against new",
        "",
        "Columns count pieces. **Old imp, new pass** is the dangerous cell: the old rows closed the piece "
        "and the new rows would route through it. **Of which raster below limit on old slivers** counts "
        "the dangerous pieces where the raster, read along the old slivers themselves, stays under the "
        "limit: the old depth came from a pixel off the road.",
        "",
        "| Forecast time | Vehicle (limit m) | New measure | Both imp | **Old imp, new pass** | "
        "Of which raster below limit on old slivers | Old pass, new imp | Both pass |",
        "|---|---|---|---|---|---|---|---|",
    ]
    limits = result["limits"]
    keys = sorted(result["confusion"], key=lambda k: (k[0] == "all", str(k[0]), list(limits).index(k[1]), k[2] != "mean"))
    for key in keys:
        c = result["confusion"][key]
        when = "all timesteps" if key[0] == "all" else f"{key[0]:%Y-%m-%d %H:%M:%S}"
        lines.append(
            f"| {when} | {key[1]} ({limits[key[1]]:.2f}) | {key[2]} | {c.both} | **{c.danger}** | "
            f"{c.danger_off_sliver} | {c.new_only} | {c.neither} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_ts")
    parser.add_argument("old_csv", type=Path)
    parser.add_argument("--table", default="flood_road_values_shadow")
    parser.add_argument("--dsn", help="libpq connection string; defaults to db_config.DB_CONFIG")
    args = parser.parse_args(argv)

    if args.dsn:
        conn = psycopg2.connect(args.dsn)
    else:
        sys.path.insert(0, str(SCRIPTS_DIR / "database"))
        from db_config import DB_CONFIG

        conn = psycopg2.connect(**DB_CONFIG)
    try:
        print(report(args.run_ts, compare(conn, args.run_ts, args.old_csv, args.table)))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
