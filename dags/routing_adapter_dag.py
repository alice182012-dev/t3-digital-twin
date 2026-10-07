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

from core_assets import FLOOD_DEPTH_RASTER


BASE_PATH = "/opt/airflow"
SCRIPTS_PATH = os.path.join(BASE_PATH, "scripts")
DATA_PATH = os.path.join(BASE_PATH, "data/mapping")

sys.path.append(SCRIPTS_PATH)
sys.path.append(os.path.join(SCRIPTS_PATH, "database"))
# edge_depth/*.py import each other as top-level modules.
sys.path.append(os.path.join(SCRIPTS_PATH, "edge_depth"))

try:
    import build_edge_depth
    import publish_edge_depth
    from db_config import DB_CONFIG
    from roads import load_road_segments
    from flood_roads import flood_on_roads
except ImportError as e:
    print(f"❌ Import error: {e}")


# 9c_build_edge_depth_table reads the export of the graph's edges (graph.json and edges.csv, written by
# java/time-aware-routing/export-edges.sh) from the first folder, writes <run>.bin into the second, then
# publishes it: `latest` points at it, and the newest EDGE_TABLE_KEEP_RUNS tables stay. The second folder is the
# Docker volume edge-depth-tables (compose.yml), which the routing readers mount read-only.
EDGE_EXPORT_DIR = os.getenv("EDGE_EXPORT_DIR", os.path.join(DATA_PATH, "graph_export"))
EDGE_TABLE_DIR = os.getenv("EDGE_TABLE_DIR", os.path.join(BASE_PATH, "edge_depth_tables"))
EDGE_TABLE_KEEP_RUNS = int(os.getenv("EDGE_TABLE_KEEP_RUNS", "3"))
# One slot, so routing holds at most one of the worker's Celery slots and the core's depth and tile tasks keep the
# rest. It also keeps two routing runs from writing road_segment at once. Airflow 3 forbids database access at
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
    centimetres, at every step, tagged with the graph hash (US-041), and publishes it (US-042): `latest`
    points at it, only forward, and the newest EDGE_TABLE_KEEP_RUNS tables stay. It reads the tiles task 9b
    loaded under the same run name, and the export of the graph's edges from EDGE_EXPORT_DIR."""
    ti = kwargs["ti"]
    run_ts = published_run_ts(kwargs)

    print(f"🧮 9c. Building the edge depth table for run {run_ts}: {EDGE_EXPORT_DIR} -> {EDGE_TABLE_DIR}")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        built = build_edge_depth.build_table(conn, run_ts, EDGE_EXPORT_DIR, EDGE_TABLE_DIR)
    finally:
        conn.close()
    # A failure above or here leaves `latest` on the previous table: the pointer moves only inside publish_table.
    published = publish_edge_depth.publish_table(EDGE_TABLE_DIR, built.path.name, keep=EDGE_TABLE_KEEP_RUNS)
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
    return report


def task_load_road_segments(**kwargs):
    """Makes road_segment match the roads file. A file that has not changed reports zero changes;
    a bad file raises before anything is written."""
    roads_path = os.getenv("ROADS_GEOJSON_PATH", load_road_segments.DEFAULT_ROADS_PATH)
    print(f"🛣️ Loading road pieces into road_segment: {roads_path}")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        result = load_road_segments.load(conn, roads_path)
    finally:
        conn.close()
    print(
        f"✅ road_segment: {result.inserted} inserted, {result.updated} updated, "
        f"{result.deleted} deleted, {result.total} rows total"
    )
    if result.updated or result.deleted:
        # See artifacts/docs/concepts/road-segment-table.md, "Limits of the id".
        print("⚠️ Existing segment_id values now describe different road; older per-piece results no longer line up")
    return {
        "inserted": result.inserted,
        "updated": result.updated,
        "deleted": result.deleted,
        "total": result.total,
    }


def task_flood_on_roads(**kwargs):
    """Writes this run's per-piece flood depth into flood_road_values, the table routing reads,
    from the tiles task 9b loaded under the same run name."""
    run_ts = published_run_ts(kwargs)

    print(f"🌊 Computing flood on roads for run {run_ts}")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        result = flood_on_roads.compute(conn, run_ts)
    finally:
        conn.close()
    for step in result.timesteps:
        print(f"   {step.forecast_time:%Y-%m-%d %H:%M:%S}: {step.rows} rows, {step.wet_pieces} wet pieces")
    print(f"✅ {result.rows} rows written to {result.target_table} in {result.seconds:.1f} s")
    return {"run_ts": run_ts, "timesteps": len(result.timesteps), "rows": result.rows}


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
    description="Routing inputs (road pieces, flood on roads, edge depth table) for each run flood_mapping_full publishes",
    schedule=[FLOOD_DEPTH_RASTER],
    start_date=datetime(2026, 2, 5),
    catchup=False,
    tags=["routing", "flood"],
) as dag:
    t_roads = PythonOperator(
        task_id="load_road_segments", python_callable=task_load_road_segments, pool=POOL_ROUTING
    )
    t_flood_roads = PythonOperator(
        task_id="flood_on_roads",
        python_callable=task_flood_on_roads,
        inlets=[FLOOD_DEPTH_RASTER],
        pool=POOL_ROUTING,
    )
    t9c = PythonOperator(
        task_id="9c_build_edge_depth_table",
        python_callable=task_build_edge_depth_table,
        inlets=[FLOOD_DEPTH_RASTER],
        pool=POOL_ROUTING,
        # Takes the pool's one slot before the road tasks: 9c must end within 5 minutes of 3_calculate_depth
        # (US-045), and the road tasks have no limit.
        priority_weight=10,
    )

    t_roads >> t_flood_roads
