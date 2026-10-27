"""Checks an edge depth table against the raster tiles, for a handful of edges.

Usage: python spot_check.py TABLE_FILE [--count 20] [--seed 0]

For each picked edge and each step it compares the table's value with a direct reading: ST_Value at
the same sample points that build_edge_depth.py uses (the midpoint of every metre along the edge),
deepest sample, in whole centimetres. build_edge_depth.py finds the pixel of a sample by grid
arithmetic, and this reads it with ST_Value, so the two share no code for the lookup. It is the
acceptance check of US-041. Exit code 1 means at least one value differs.

The picks are half wet edges and half dry ones, chosen with a seeded generator, so a run is repeatable
and covers both the depths and the zeros.
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg2

import build_edge_depth
import edge_depth_table
import graph_edges

SCRIPTS_DIR = Path(__file__).resolve().parents[1]


class SpotCheckError(ValueError):
    pass


@dataclass(frozen=True)
class SpotRow:
    edge_id: int
    step: int
    table_cm: int
    direct_cm: int


@dataclass(frozen=True)
class SpotCheck:
    rows: tuple[SpotRow, ...]

    @property
    def mismatches(self) -> tuple[SpotRow, ...]:
        return tuple(row for row in self.rows if row.table_cm != row.direct_cm)


_DIRECT_SQL = """
SELECT coalesce(max(ST_Value(t.rast, 1, p.pt)), 0)
FROM graph_edge e
CROSS JOIN LATERAL (SELECT greatest(1, ceil(e.length_m / %(step)s))::int AS n) q
CROSS JOIN LATERAL generate_series(0, q.n - 1) AS i
CROSS JOIN LATERAL (SELECT ST_LineInterpolatePoint(e.geom, (i + 0.5) / q.n) AS pt) p
JOIN flood_depth_raster_tile t
  ON t.run_ts = %(run_ts)s AND t.valid_time_utc = %(valid_time_utc)s
 AND ST_Intersects(ST_ConvexHull(t.rast), p.pt)
WHERE e.edge_id = %(edge_id)s
"""


def pick_edges(table: edge_depth_table.EdgeDepthTable, count: int, seed: int) -> list[int]:
    """Half wet edges (any step above 0) and half dry ones, then ordered by id."""
    wet, dry = [], []
    for edge_id in range(table.header.edge_count):
        (wet if any(table.edge_depths_cm(edge_id)) else dry).append(edge_id)
    rng = random.Random(seed)
    want_wet = min(len(wet), (count + 1) // 2)
    picked = rng.sample(wet, want_wet)
    picked += rng.sample(dry, min(len(dry), count - len(picked)))
    if len(picked) < count:  # too few dry edges: fill up with wet ones
        rest = [e for e in wet if e not in set(picked)]
        picked += rng.sample(rest, min(len(rest), count - len(picked)))
    return sorted(picked)


def spot_check(conn, table_path, count: int = 20, seed: int = 0) -> SpotCheck:
    table = edge_depth_table.read_table(Path(table_path))
    header = table.header
    held = graph_edges.loaded_hash(conn)
    if held != header.graph_hash:
        raise SpotCheckError(
            f"the table is for graph hash {header.graph_hash}, but graph_edge holds {held}; "
            "the check would compare against different edges"
        )
    rows = []
    for edge_id in pick_edges(table, count, seed):
        for step, step_time in enumerate(header.step_times):
            with conn, conn.cursor() as cur:
                cur.execute(
                    _DIRECT_SQL,
                    {
                        "run_ts": header.run_name,
                        "valid_time_utc": step_time.replace(tzinfo=None),
                        "edge_id": edge_id,
                        "step": build_edge_depth.SAMPLE_STEP_M,
                    },
                )
                direct = build_edge_depth.depth_cm(cur.fetchone()[0])
            rows.append(SpotRow(edge_id, step, table.depth_cm(edge_id, step), direct))
    return SpotCheck(tuple(rows))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("table_file")
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(SCRIPTS_DIR / "database"))
    from db_config import DB_CONFIG

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        check = spot_check(conn, args.table_file, args.count, args.seed)
    finally:
        conn.close()

    print("edge_id step table_cm direct_cm")
    for row in check.rows:
        flag = "" if row.table_cm == row.direct_cm else "  DIFFERENT"
        print(f"{row.edge_id:7d} {row.step:4d} {row.table_cm:8d} {row.direct_cm:9d}{flag}")
    edges = len({row.edge_id for row in check.rows})
    if check.mismatches:
        print(f"FAIL: {len(check.mismatches)} of {len(check.rows)} values differ ({edges} edges)")
        return 1
    print(f"PASS: {len(check.rows)} values equal a direct ST_Value reading ({edges} edges)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
