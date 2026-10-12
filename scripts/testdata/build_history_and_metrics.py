"""Builds depth_history, history_moment, and flood_segment_metrics for every run in the test databases (US-127, D-039).

    python build_history_and_metrics.py   # inside the Airflow worker, after restore_snapshot.py

It reads the runs of `flood_road_file` in `minio_custom_test`, oldest first, and for each run loads the history into
`flood_metrics_test` with load_run.write_run and writes the metrics into `minio_custom_test` with extract_run. No raster
tile is needed, because a run's moments come from its forecast times. Then it compresses every chunk of depth_history
and prints the compression ratio. A second run gives the same rows, because each load replaces what it writes and
the chunks are decompressed first. It refuses a database whose name does not end in `_test`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg2

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
for folder in ("testdata", "database", "flood_history", "flood_metrics", "flood_roads"):
    sys.path.insert(0, str(SCRIPTS_DIR / folder))

import extract_run  # noqa: E402
import load_run  # noqa: E402
from db_config import DB_CONFIG, TIMESCALE_DB_CONFIG  # noqa: E402
from restore_snapshot import check_test_database  # noqa: E402

_RUN_TS_FORMAT = "YYYYMMDD\"T\"HH24MISS"

_DECOMPRESS_SQL = "SELECT decompress_chunk(c, if_compressed => true) FROM show_chunks('depth_history') c"
_COMPRESS_SQL = "SELECT compress_chunk(c, if_not_compressed => true) FROM show_chunks('depth_history') c"
_STATS_SQL = (
    "SELECT coalesce(sum(before_compression_total_bytes), 0), coalesce(sum(after_compression_total_bytes), 0) "
    "FROM chunk_compression_stats('depth_history')"
)


def run_names(conn) -> list[str]:
    """The runs of flood_road_file, oldest first, as the DAG names them."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT to_char(timestamp, '{_RUN_TS_FORMAT}') FROM flood_road_file ORDER BY timestamp")
        return [row[0] for row in cur.fetchall()]


def compression_ratio(timescale) -> tuple[int, int, float]:
    """Compresses every chunk of depth_history. Returns the bytes before, the bytes after, and their ratio."""
    with timescale.cursor() as cur:
        cur.execute(_COMPRESS_SQL)
        cur.execute(_STATS_SQL)
        before, after = (int(value) for value in cur.fetchone())
    timescale.commit()
    return before, after, before / after


def build(postgis_name: str, timescale_name: str) -> None:
    check_test_database(postgis_name, DB_CONFIG["database"])
    check_test_database(timescale_name, TIMESCALE_DB_CONFIG["database"])
    postgis = psycopg2.connect(**{**DB_CONFIG, "database": postgis_name})
    timescale = psycopg2.connect(**{**TIMESCALE_DB_CONFIG, "database": timescale_name})
    try:
        runs = run_names(postgis)
        with timescale.cursor() as cur:
            cur.execute(_DECOMPRESS_SQL)
        timescale.commit()
        for index, run_ts in enumerate(runs, start=1):
            result = load_run.write_run(timescale, load_run.read_run(postgis, run_ts))
            metrics = extract_run.extract_run(postgis, run_ts)
            print(f"[{index}/{len(runs)}] {result.describe()} {metrics} metric rows.", flush=True)
        with timescale.cursor() as cur:
            cur.execute("SELECT count(*) FROM depth_history")
            rows = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM history_moment")
            moments = cur.fetchone()[0]
        with postgis.cursor() as cur:
            cur.execute("SELECT count(*), count(DISTINCT run_ts) FROM flood_segment_metrics")
            metric_rows, metric_runs = cur.fetchone()
        before, after, ratio = compression_ratio(timescale)
    finally:
        postgis.close()
        timescale.close()
    print(f"depth_history: {rows} rows, history_moment: {moments} moments")
    print(f"flood_segment_metrics: {metric_rows} rows over {metric_runs} runs")
    print(f"compression of depth_history: {before} bytes before, {after} bytes after, ratio {ratio:.1f}")


def main() -> int:
    build(os.getenv("TEST_POSTGRES_DB", "minio_custom_test"), os.getenv("TEST_TIMESCALE_DB", "flood_metrics_test"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
