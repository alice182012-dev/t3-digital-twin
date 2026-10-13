"""The routing inputs of each run the core publishes.

`flood_mapping_full` emits FLOOD_DEPTH_RASTER from `9b_load_depth_raster`, and this DAG runs on that event. Its tasks
write only routing tables and files, so a failure here leaves the core run green, and the core's hotstart chain
(hotstart_policy) never sees it.
"""
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os
import psycopg2

from core_assets import EDGE_DEPTH_ROWS, FLOOD_DEPTH_RASTER


BASE_PATH = "/opt/airflow"
SCRIPTS_PATH = os.path.join(BASE_PATH, "scripts")
DATA_PATH = os.path.join(BASE_PATH, "data/mapping")

sys.path.append(SCRIPTS_PATH)
sys.path.append(os.path.join(SCRIPTS_PATH, "database"))
# edge_depth/*.py import each other as top-level modules.
sys.path.append(os.path.join(SCRIPTS_PATH, "edge_depth"))

try:
    import build_edge_depth
    import demo_pin
    import publish_edge_depth
    import run_output
    from db_config import DB_CONFIG
except ImportError as e:
    print(f"❌ Import error: {e}")


# 9c_build_edge_depth_table reads the export of the graph's edges (graph.json and edges.csv, written by
# java/time-aware-routing/export-edges.sh) from the first folder, writes <run>.bin into the second, then
# publishes it: `latest` points at it, and the newest EDGE_TABLE_KEEP_RUNS tables stay. The second folder is the
# Docker volume edge-depth-tables (compose.yml), which the routing readers mount read-only.
EDGE_EXPORT_DIR = os.getenv("EDGE_EXPORT_DIR", os.path.join(DATA_PATH, "graph_export"))
EDGE_TABLE_DIR = os.getenv("EDGE_TABLE_DIR", os.path.join(BASE_PATH, "edge_depth_tables"))
EDGE_TABLE_KEEP_RUNS = int(os.getenv("EDGE_TABLE_KEEP_RUNS", "8"))
# The runs of edge_depth that stay: those within this many hours before the newest run (US-118).
EDGE_DEPTH_KEEP_HOURS = int(os.getenv("EDGE_DEPTH_KEEP_HOURS", "24"))
# One slot, so routing holds at most one of the worker's Celery slots and the core's depth and tile tasks keep the
# rest. Airflow 3 forbids database access at
# DAG-parse time, so the pool is created once by hand (README, "Create the Airflow pools").
POOL_ROUTING = "routing_adapter"


def published_run_ts(kwargs):
    """The run this DAG run is for, from the `run_ts` in the extra of the FLOOD_DEPTH_RASTER event.

    An event-triggered run reads the events that triggered it. When the scheduler folds several events into one
    run, the newest run wins, the same rule as the `latest` pointer of the edge depth table. A manual run has no
    triggering event and reads the newest event 9b ever emitted instead. It does not read the newest run_ts in
    flood_depth_raster_tile, because 9b commits one timestep at a time and that run may still be loading.
    """
    triggering = kwargs.get("triggering_asset_events") or {}
    events = [event for asset_events in triggering.values() for event in asset_events]
    source = "triggering event"
    if not events:
        events = kwargs["inlet_events"][FLOOD_DEPTH_RASTER]
        source = "newest published event"
    runs = sorted({event.extra["run_ts"] for event in events if "run_ts" in (event.extra or {})})
    if not runs:
        raise ValueError(f"❌ No {FLOOD_DEPTH_RASTER.name} event carries a run_ts")
    if source == "triggering event" and len(runs) > 1:
        print(f"⏭️ Events folded into one run, building the newest only; skipped {runs[:-1]}")
    print(f"📨 Run {runs[-1]} from the {source}")
    return runs[-1]


def task_build_edge_depth_table(**kwargs):
    """Writes this run's edge depth table: the deepest flood sample along every GraphHopper edge, in
    centimetres, at every step, tagged with the graph hash (US-041), writes its wet edges to `edge_depth` with a
    registry row for the run (US-118), and publishes it (US-042): `latest`
    points at it, only forward, and the newest EDGE_TABLE_KEEP_RUNS tables stay. It reads the tiles task 9b
    loaded under the same run name, and the export of the graph's edges from EDGE_EXPORT_DIR.

    Its last write is the run's `edge_depth` row in flood_run_output, only when `latest` names this run's table.
    An older run that finishes after a newer one leaves `latest` alone, so its table is not the published one.

    On success it emits EDGE_DEPTH_ROWS with the run_ts, which schedules flood_history_dag.py. The `edge_depth` rows
    and the registry row are committed inside build_table, before the event, so flood_history never runs ahead of them."""
    ti = kwargs["ti"]
    run_ts = published_run_ts(kwargs)

    print(f"🧮 9c. Building the edge depth table for run {run_ts}: {EDGE_EXPORT_DIR} -> {EDGE_TABLE_DIR}")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        built = build_edge_depth.build_table(
            conn, run_ts, EDGE_EXPORT_DIR, EDGE_TABLE_DIR, keep_hours=EDGE_DEPTH_KEEP_HOURS
        )
        with conn, conn.cursor() as cur:
            pinned = demo_pin.kept_runs(cur, run_ts) - {run_ts}
    finally:
        conn.close()
    # A failure above or here leaves `latest` on the previous table: the pointer moves only inside publish_table.
    published = publish_edge_depth.publish_table(
        EDGE_TABLE_DIR, built.path.name, keep=EDGE_TABLE_KEEP_RUNS, also_keep={f"{run}.bin" for run in pinned}
    )
    report = {
        "run_ts": run_ts,
        "path": str(built.path),
        "graph_hash": built.graph_hash,
        "graph_loaded": built.graph_loaded,
        "edge_count": built.edge_count,
        "steps": built.step_count,
        "wet_edges": list(built.wet_edges),
        "sample_seconds": [round(seconds, 2) for seconds in built.sample_seconds],
        "bytes": built.size_bytes,
        "seconds": round(built.seconds, 2),
        "rows_written": built.rows_written,
        "rows_seconds": round(built.rows_seconds, 2),
        "runs_pruned": built.runs_pruned,
        "published": {
            "latest": published.latest,
            "previous": published.previous,
            "moved": published.moved,
            "removed": list(published.removed),
        },
    }
    ti.xcom_push(key="edge_depth_table", value=report)
    print(
        f"✅ Edge depth table: {built.edge_count} edges, {built.step_count} steps, {built.size_bytes} bytes, "
        f"wet edges per step {list(built.wet_edges)}, {built.seconds:.1f} s"
        + (", graph edges reloaded" if built.graph_loaded else "")
    )
    print(
        f"📌 latest -> {published.latest}"
        + ("" if published.moved else f" (unchanged: {built.path.name} is not newer)")
        + (f", removed {list(published.removed)}" if published.removed else "")
    )
    if published.latest == built.path.name:
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            with conn, conn.cursor() as cur:
                run_output.record(cur, run_ts, run_output.Output.EDGE_DEPTH)
        finally:
            conn.close()
    kwargs["outlet_events"][EDGE_DEPTH_ROWS].extra = {"run_ts": run_ts}
    return report


default_args = {
    "owner": "flood_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    "routing_adapter",
    default_args=default_args,
    description="Routing input (edge depth table and rows) for each run flood_mapping_full publishes",
    schedule=[FLOOD_DEPTH_RASTER],
    start_date=datetime(2026, 2, 5),
    catchup=False,
    tags=["routing", "flood"],
) as dag:
    t9c = PythonOperator(
        task_id="9c_build_edge_depth_table",
        python_callable=task_build_edge_depth_table,
        inlets=[FLOOD_DEPTH_RASTER],
        outlets=[EDGE_DEPTH_ROWS],
        pool=POOL_ROUTING,
    )
