from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os
import time
import boto3
import psycopg2

from core_assets import FLOOD_DEPTH_FILES
from core_paths import BASE_PATH, DATA_PATH, DEPTH_ROOT_DIR, RESULT_DIR


SCRIPTS_PATH = os.path.join(BASE_PATH, "scripts")

sys.path.append(SCRIPTS_PATH)
# database/*.py import `db_config` as a top-level module (not `database.db_config`),
# so its directory needs to be importable directly too.
sys.path.append(os.path.join(SCRIPTS_PATH, "database"))
sys.path.append(os.path.join(SCRIPTS_PATH, "flood_extent"))

try:
    import publish
    from db_config import DB_CONFIG
except ImportError as e:
    print(f"❌ Lỗi Import: {e}")


# Vector tiles of the flood extent, one folder per run and timestep, served by the frontend at
# /flood-extent/<run>/<timestep>/{z}/{x}/{y}.pbf.
FLOOD_EXTENT_WORKERS = int(os.getenv("FLOOD_EXTENT_WORKERS", "2"))
FLOOD_EXTENT_KEEP_RUNS = int(os.getenv("FLOOD_EXTENT_KEEP_RUNS", "8"))
FLOOD_EXTENT_TILE_STEPS = int(os.getenv("FLOOD_EXTENT_TILE_STEPS", "2"))
# scripts/flood_extent/publish.py's own scratch space, per timestep, deleted as each timestep's
# tiles finish uploading — never the final destination, just where the raster pipeline works.
FLOOD_EXTENT_WORK_DIR = os.path.join(DATA_PATH, "flood_extent_work")
FLOOD_EXTENT_BUCKET = os.getenv("FLOOD_EXTENT_BUCKET", "flood-extent")
FLOOD_EXTENT_CLEANUP_MAX_AGE_HOURS = int(os.getenv("FLOOD_EXTENT_CLEANUP_MAX_AGE_HOURS", "24"))


def announced_depth_runs(kwargs):
    """The (run_ts, depth_dir) pairs this DAG run builds tiles for, oldest first.

    An event-triggered run reads the events that triggered it. When the scheduler folds several events into one
    run, every run in them gets its tiles, because the map lists each run. A manual run has no triggering event and
    builds the newest run that was announced, by `run_ts`, which does not depend on the order of the events.
    """
    triggering = kwargs.get("triggering_asset_events") or {}
    events = [event for asset_events in triggering.values() for event in asset_events]
    manual = not events
    if manual:
        events = list(kwargs["inlet_events"][FLOOD_DEPTH_FILES])
    runs = {
        event.extra["run_ts"]: event.extra["depth_dir"]
        for event in events
        if "run_ts" in (event.extra or {}) and "depth_dir" in event.extra
    }
    if not runs:
        raise ValueError(f"❌ No {FLOOD_DEPTH_FILES.name} event carries the run to build")
    ordered = sorted(runs.items())
    return ordered[-1:] if manual else ordered


def task_build_flood_tiles(**kwargs):
    """Cut the map's flood-extent tiles from the first FLOOD_EXTENT_TILE_STEPS depth rasters of
    each announced run, publish them to MinIO, and write one PostGIS audit row per dissolved band
    polygon and one flood_extent_step row per timestep.

    Only uploaded tiles and DB rows are kept; publish_run deletes every local intermediate itself
    as each timestep finishes, and deletes RESULT_DIR and DEPTH_ROOT_DIR files older than
    FLOOD_EXTENT_CLEANUP_MAX_AGE_HOURS. The run name comes from the event of flood_mapping_full, the
    same name task 9b uses, so the UI finds the tiles from the (run, valid_time) pair it already
    selects. Tiles go to MinIO, not a local folder, because the worker and the frontend run on
    separate hosts in production.

    Each run reports the seconds the tile build took.
    """
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    )
    built = []
    for run_ts, depth_dir in announced_depth_runs(kwargs):
        if not os.path.isdir(depth_dir):
            # An earlier run of this batch can age-clean this folder, so one lost run must not sink the others.
            print(f"⚠️ Depth directory is missing, skipping run {run_ts}: {depth_dir}")
            continue
        started = time.monotonic()
        print(f"🌊 9. Publishing flood-extent tiles: {depth_dir} -> s3://{FLOOD_EXTENT_BUCKET}/runs/{run_ts}")
        db_conn = psycopg2.connect(**DB_CONFIG)
        try:
            results = publish.publish_run(
                depth_dir,
                run_ts,
                FLOOD_EXTENT_WORK_DIR,
                s3,
                FLOOD_EXTENT_BUCKET,
                workers=FLOOD_EXTENT_WORKERS,
                db_conn=db_conn,
                tile_steps=FLOOD_EXTENT_TILE_STEPS,
                keep_runs=FLOOD_EXTENT_KEEP_RUNS,
                cleanup_dirs=[RESULT_DIR, DEPTH_ROOT_DIR, FLOOD_EXTENT_WORK_DIR],
                cleanup_max_age_hours=FLOOD_EXTENT_CLEANUP_MAX_AGE_HOURS,
            )
        finally:
            db_conn.close()
        build_s = time.monotonic() - started
        flooded = sum(1 for result in results.values() if not result.is_empty)
        print(f"✅ Tiles of {run_ts} done: {flooded}/{len(results)} timesteps have flooding ({build_s:.1f} s)")
        built.append(
            {
                "run_ts": run_ts,
                "timesteps": len(results),
                "flooded_timesteps": flooded,
                "build_seconds": round(build_s, 1),
            }
        )
    if not built:
        raise ValueError("❌ No announced depth directory exists, so no tiles were built")
    return built


default_args = {
    "owner": "flood_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    "flood_tiles",
    default_args=default_args,
    description="Flood-extent vector tiles for the map, for each run flood_mapping_full announces",
    schedule=[FLOOD_DEPTH_FILES],
    start_date=datetime(2026, 2, 5),
    catchup=False,
    # Same limit the tile task had inside flood_mapping_full, where two runs could overlap.
    max_active_runs=2,
    tags=["flood", "visualization"],
) as dag:
    PythonOperator(
        task_id="9_build_flood_tiles",
        python_callable=task_build_flood_tiles,
        inlets=[FLOOD_DEPTH_FILES],
    )
