"""Builds one run's edge depth table: the flood depth of every GraphHopper edge at every step of the run.

Usage: python build_edge_depth.py RUN_TS --export-dir DIR --out-dir DIR   (RUN_TS as the DAG names it, for
example 20260924T164803)

Inputs are the export of the graph's edges (graph_edges.py) and flood_depth_raster_tile
(scripts/flood_extent/raster_load.py). Each edge is sampled at the midpoint of every metre along it, and
the value is the deepest sample, in centimetres. This is the statistic of the retired per-piece sampler (decision D-006 in
artifacts/docs/decisions/decision-log.md, replaced by this table in D-038). An edge that touches no wet pixel, or lies outside the tiles, reads 0.

The file is <out-dir>/<RUN_TS>.bin in the format of edge_depth_table.py, tagged with the graph hash of the
export. It is written under a temporary name and renamed, so an interrupted build leaves no partial file and
keeps the previous one. The latest pointer and the retention of old tables belong to US-042.

The same pass also writes the wet edges to the database (edge_depth_rows.py, US-118), before it writes the file, so
a database failure leaves no file and the previous table stays published. That needs an export of format 3, whose
edge_key names each edge across a re-import of the same OSM file.
The design is in artifacts/archive/plans/edge-depth-table-airflow-task.md.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import time
from array import array
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path

import psycopg2

import edge_depth_rows
import edge_depth_table
import graph_edges

SCRIPTS_DIR = Path(__file__).resolve().parents[1]

SAMPLE_STEP_M = 1.0
# One sampling step takes about 5 s on an idle database. A step that runs past this is a bad plan or a
# starved database, and it is cancelled so it cannot hold the database for the runs behind it (on 2026-10-05
# one step ran over 770 s). The build fails, the core run stays green (9c runs in routing_adapter), and the
# previous table stays published.
DEFAULT_STEP_TIMEOUT_S = 120.0
_MAX_CM = 0xFFFF


class EdgeDepthBuildError(ValueError):
    pass


@dataclass(frozen=True)
class BuildResult:
    run_ts: str
    path: Path
    graph_hash: str
    graph_loaded: bool
    edge_count: int
    step_count: int
    wet_edges: tuple[int, ...]
    sample_seconds: tuple[float, ...]
    size_bytes: int
    seconds: float
    rows_written: int
    rows_seconds: float
    runs_pruned: int


def depth_cm(depth_m: float) -> int:
    """Metres to whole centimetres, rounded to the nearest, capped at what the format's uint16 holds."""
    return min(_MAX_CM, math.floor(depth_m * 100 + 0.5))


_TIMESTEPS_SQL = """
SELECT DISTINCT valid_time_utc FROM flood_depth_raster_tile WHERE run_ts = %(run_ts)s ORDER BY 1
"""

# Each sample is matched to its pixel by grid
# arithmetic and an equality join on the wet pixels, so every tile is unpacked once. Only edges
# touching a tile with a wet pixel are sampled, and only edges with a wet sample are returned.
_SAMPLE_SQL = """
WITH tiles AS MATERIALIZED (
    SELECT tile_x, tile_y, rast,
           ST_UpperLeftX(rast) AS tile_ulx, ST_UpperLeftY(rast) AS tile_uly
    FROM flood_depth_raster_tile
    WHERE run_ts = %(run_ts)s AND valid_time_utc = %(valid_time_utc)s
), grid AS MATERIALIZED (
    SELECT min(tile_ulx) AS ulx, max(tile_uly) AS uly,
           min(ST_ScaleX(rast)) AS sx, min(ST_ScaleY(rast)) AS sy
    FROM tiles
), wet_pixels AS MATERIALIZED (
    SELECT t.tile_x, t.tile_y,
           round((t.tile_ulx - g.ulx) / g.sx)::int + p.x - 1 AS gx,
           round((t.tile_uly - g.uly) / g.sy)::int + p.y - 1 AS gy,
           p.val AS depth
    FROM tiles t CROSS JOIN grid g
    CROSS JOIN LATERAL ST_PixelAsCentroids(t.rast, 1, true) p
    WHERE p.val > 0
), wet_tiles AS (
    SELECT DISTINCT tile_x, tile_y FROM wet_pixels
), candidates AS (
    SELECT DISTINCT e.edge_id, e.geom, e.length_m
    FROM tiles t
    JOIN wet_tiles USING (tile_x, tile_y)
    JOIN graph_edge e ON ST_Intersects(e.geom, ST_ConvexHull(t.rast))
), samples AS (
    SELECT c.edge_id,
           floor((ST_X(pt) - g.ulx) / g.sx)::int AS gx,
           floor((ST_Y(pt) - g.uly) / g.sy)::int AS gy
    FROM (SELECT *, greatest(1, ceil(length_m / %(step)s))::int AS n FROM candidates) c
    CROSS JOIN LATERAL generate_series(0, c.n - 1) AS i
    CROSS JOIN LATERAL ST_LineInterpolatePoint(c.geom, (i + 0.5) / c.n) AS pt
    CROSS JOIN grid g
)
SELECT s.edge_id, max(w.depth)
FROM samples s JOIN wet_pixels w USING (gx, gy)
GROUP BY s.edge_id
"""


_KEYS_SQL = "SELECT edge_id, edge_key FROM graph_edge WHERE edge_id = ANY(%s)"


def build_table(
    conn,
    run_ts: str,
    export_dir,
    out_dir,
    step_timeout_s: float = DEFAULT_STEP_TIMEOUT_S,
    keep_hours: int = edge_depth_rows.DEFAULT_KEEP_HOURS,
) -> BuildResult:
    """Builds <out_dir>/<run_ts>.bin from the run's raster tiles and the export in export_dir, and writes the
    run's wet edges to edge_depth, keeping the runs of the last `keep_hours` before the newest.

    Raises GraphExportError when the export is missing or inconsistent, and EdgeDepthBuildError when the
    run has no tiles or the export has no edge keys. None of them writes a file or a row."""
    started = time.monotonic()
    export = graph_edges.read_export(export_dir)
    if export.format_version < graph_edges.EDGE_KEY_FORMAT_VERSION:
        raise EdgeDepthBuildError(
            f"the export in {export_dir} has format_version {export.format_version}, and edge_depth needs "
            f"{graph_edges.EDGE_KEY_FORMAT_VERSION} for its edge_key. Write a new export from a graph with osm_way_id "
            "(artifacts/docs/concepts/graph-reimport-procedure.md)"
        )
    with conn, conn.cursor() as cur:
        cur.execute(_TIMESTEPS_SQL, {"run_ts": run_ts})
        valid_times = [row[0] for row in cur.fetchall()]
    if not valid_times:
        raise EdgeDepthBuildError(f"no flood_depth_raster_tile rows for run {run_ts}")

    graph_loaded = graph_edges.load_graph_edges(conn, export)

    # The tiles of a run are loaded minutes before this task. Autovacuum has not seen them yet, and a plan
    # made on stale statistics can pick a nested loop over the unpacked pixels.
    with conn, conn.cursor() as cur:
        cur.execute("ANALYZE flood_depth_raster_tile")

    steps = len(valid_times)
    depths = array("H", bytes(2 * export.edge_count * steps))
    wet_edges = []
    wet_cells = []
    sample_seconds = []
    for step, valid_time in enumerate(valid_times):
        step_started = time.monotonic()
        wet = 0
        try:
            with conn, conn.cursor() as cur:
                cur.execute("SELECT set_config('statement_timeout', %s, true)", (f"{max(1, int(step_timeout_s * 1000))}ms",))
                cur.execute(_SAMPLE_SQL, {"run_ts": run_ts, "valid_time_utc": valid_time, "step": SAMPLE_STEP_M})
                for edge_id, depth in cur.fetchall():
                    cm = depth_cm(depth)
                    if cm > 0:
                        depths[edge_id * steps + step] = cm
                        wet_cells.append((edge_id, valid_time, cm))
                        wet += 1
        except psycopg2.errors.QueryCanceled as e:
            raise EdgeDepthBuildError(
                f"step {step + 1} of {steps} ({valid_time}) ran past {step_timeout_s:g} s and was cancelled"
            ) from e
        wet_edges.append(wet)
        sample_seconds.append(time.monotonic() - step_started)

    rows_started = time.monotonic()
    write = edge_depth_rows.write_run(
        conn, run_ts, export.graph_hash, valid_times, _keyed(conn, wet_cells), keep_hours
    )
    rows_seconds = time.monotonic() - rows_started

    header = edge_depth_table.TableHeader(
        graph_hash=export.graph_hash,
        run_name=run_ts,
        step_times=tuple(v.replace(tzinfo=timezone.utc) for v in valid_times),
        edge_count=export.edge_count,
    )
    path = _write(Path(out_dir), run_ts, header, depths, steps)
    return BuildResult(
        run_ts=run_ts,
        path=path,
        graph_hash=export.graph_hash,
        graph_loaded=graph_loaded,
        edge_count=export.edge_count,
        step_count=steps,
        wet_edges=tuple(wet_edges),
        sample_seconds=tuple(sample_seconds),
        size_bytes=path.stat().st_size,
        seconds=time.monotonic() - started,
        rows_written=write.rows,
        rows_seconds=rows_seconds,
        runs_pruned=write.runs_pruned,
    )


def _keyed(conn, wet_cells) -> list[edge_depth_rows.WetEdge]:
    """The wet (edge id, time, cm) cells with the edge_key of graph_edge in place of the edge id."""
    edge_ids = sorted({edge_id for edge_id, _, _ in wet_cells})
    with conn, conn.cursor() as cur:
        cur.execute(_KEYS_SQL, (edge_ids,))
        keys = dict(cur.fetchall())
    missing = [edge_id for edge_id in edge_ids if not keys.get(edge_id)]
    if missing:
        raise EdgeDepthBuildError(
            f"graph_edge has no edge_key for {len(missing)} wet edges, for example edge {missing[0]}"
        )
    return [edge_depth_rows.WetEdge(valid_time, keys[edge_id], cm) for edge_id, valid_time, cm in wet_cells]


def _write(out_dir: Path, run_ts: str, header, depths: array, steps: int) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / f"{run_ts}.bin"
    # A name of its own, so two overlapping builds of one run cannot write into each other's file.
    temporary = out_dir / f".{run_ts}.{os.getpid()}.tmp"
    try:
        rows = (tuple(depths[e * steps:(e + 1) * steps]) for e in range(header.edge_count))
        edge_depth_table.write_table(temporary, header, rows)
        os.replace(temporary, final)
    finally:
        temporary.unlink(missing_ok=True)
    return final


def main(argv: list[str] | None = None) -> BuildResult:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_ts")
    parser.add_argument("--export-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--publish", action="store_true", help="also point `latest` at the table and apply retention")
    parser.add_argument("--keep", type=int, default=3)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(SCRIPTS_DIR / "database"))
    from db_config import DB_CONFIG

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        result = build_table(conn, args.run_ts, args.export_dir, args.out_dir)
    finally:
        conn.close()

    if args.publish:
        import publish_edge_depth

        published = publish_edge_depth.publish_table(args.out_dir, result.path.name, keep=args.keep)
        print(
            f"latest -> {published.latest}" + ("" if published.moved else " (unchanged)")
            + (f", removed {list(published.removed)}" if published.removed else "")
        )

    for index, (wet, seconds) in enumerate(zip(result.wet_edges, result.sample_seconds)):
        print(f"step {index}: {wet} wet edges, sampled in {seconds:.1f} s")
    print(
        f"{result.path} written: {result.edge_count} edges, {result.step_count} steps, "
        f"{result.size_bytes} bytes, graph {result.graph_hash[:12]}, in {result.seconds:.1f} s."
    )
    return result


if __name__ == "__main__":
    main()
