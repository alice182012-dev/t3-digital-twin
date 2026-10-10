"""Manual test: two consecutive synthetic rain events, run through the flood_mapping_full steps.

Event 1 is 20 mm/h for 2 h from a cold start at the current 15-minute slot, and it saves a 3Di
state at its end (SIMULATION_DURATION seconds), not at the one and two cycles production saves.
Event 2 is 5 mm/h for 2 h and starts at the slot where event 1 ends, so that state is valid at
exactly event 2's slot and event 2 hotstarts from it. Fixed synthetic rain replaces
flood_mapping_full's rain gate, so the DAG runs on a dry day. Trigger it by hand.

After each event's depth calculation, the DAG runs the same steps as flood_mapping_full: flood
tiles (task 9), the depth raster load (task 9b), and flood on roads. Only the first
FLOOD_EXTENT_TILE_STEPS (default 2) timesteps of each event get tiles, as in production; the
raster load and flood on roads cover every timestep. Both events publish under
ONE run name, event 1's earliest depth file stamp (decision D-007 in
artifacts/docs/decisions/decision-log.md), so event 1's tiled timesteps stay visible after event
2 publishes. The netcdf upload (task 3b of flood_mapping_full)
is left out on purpose: this DAG must not write synthetic simulations into the real netcdf tables.

What a run writes, where RUN_TS is event 1's earliest depth stamp (for example 20260925T101500,
logged by every publishing task and returned in its XCom):

- MinIO: the flood-extent tiles under runs/RUN_TS/ in the flood-extent bucket.
- flood_extent_polygon, flood_extent_step, and flood_depth_raster_tile: rows with run_ts = RUN_TS.
- flood_road_values: rows with timestamp = RUN_TS, written in place on purpose so routing shows
  the test event, plus one flood_road_file row named flood_on_roads_RUN_TS.
- road_segment: made to match the roads file, the same idempotent load production runs.

The run name is newer than the production runs, so the map, point depth, and routing show it
as the latest run until a newer production run replaces it. To remove a test run afterwards:

    DELETE FROM flood_road_values WHERE timestamp = to_timestamp('RUN_TS', 'YYYYMMDD"T"HH24MISS')::timestamp;
    DELETE FROM flood_road_file WHERE source_file = 'flood_on_roads_RUN_TS';
    DELETE FROM flood_extent_polygon WHERE run_ts = 'RUN_TS';
    DELETE FROM flood_extent_step WHERE run_ts = 'RUN_TS';
    DELETE FROM flood_depth_raster_tile WHERE run_ts = 'RUN_TS';

and delete the prefix runs/RUN_TS/ in the flood-extent bucket.
"""

from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta, timezone
import sys
import os
import boto3
import psycopg2


BASE_PATH = "/opt/airflow"
SCRIPTS_PATH = os.path.join(BASE_PATH, "scripts")
DATA_PATH = os.path.join(BASE_PATH, "data/mapping")

sys.path.append(SCRIPTS_PATH)
sys.path.append(os.path.join(SCRIPTS_PATH, "database"))
sys.path.append(os.path.join(SCRIPTS_PATH, "flood_extent"))

try:
    import create_simulation
    import download_result
    import calculate_depth
    import database.create_flood_road_tables
    import database.create_flood_extent_tables
    import database.create_flood_depth_raster_tables
    import database.create_road_segment_table
    import database.create_flood_run_output_table
    import flood_extent
    import publish
    import raster_load
    from db_config import DB_CONFIG
    from roads import load_road_segments
    from flood_roads import flood_on_roads
except ImportError as e:
    print(f"❌ Lỗi Import: {e}")


# Dedicated test tree, isolated from the production state file / output dirs
# used by flood_forecast_dag.py and flood_mapping_dag.py.
TEST_ROOT = os.path.join(BASE_PATH, "data/mapping_state_test")
TEST_STATE_FILE = os.path.join(BASE_PATH, "state", "flood_state_test.json")
INPUT_DEM = os.path.join(DATA_PATH, "inputs", "dem.tif")
INPUT_GRID = os.path.join(DATA_PATH, "inputs", "gridadmin.h5")

RESULT_DIR_EVENT1 = os.path.join(TEST_ROOT, "results", "event1_20mmhr")
RESULT_DIR_EVENT2 = os.path.join(TEST_ROOT, "results", "event2_5mmhr")
DEPTH_DIR_EVENT1 = os.path.join(TEST_ROOT, "output_depths", "event1_20mmhr")
DEPTH_DIR_EVENT2 = os.path.join(TEST_ROOT, "output_depths", "event2_5mmhr")

# Event 1: initial 2h event that creates the saved state.
EVENT1_RAIN_MM_HR = 20
EVENT1_DURATION_HOURS = 2

# Event 2: consecutive 2h event that hotstarts from Event 1's saved state.
EVENT2_RAIN_MM_HR = 5
EVENT2_DURATION_HOURS = 2

EVENT1_DEPTH_TASK = "3_calculate_depth_event1"
EVENT2_DEPTH_TASK = "6_calculate_depth_event2"

FLOOD_EXTENT_WORKERS = int(os.getenv("FLOOD_EXTENT_WORKERS", "2"))
FLOOD_EXTENT_TILE_STEPS = int(os.getenv("FLOOD_EXTENT_TILE_STEPS", "2"))
FLOOD_EXTENT_BUCKET = os.getenv("FLOOD_EXTENT_BUCKET", "flood-extent")
FLOOD_EXTENT_WORK_DIR = os.path.join(TEST_ROOT, "flood_extent_work")
DEPTH_RASTER_WORK_DIR = os.path.join(TEST_ROOT, "depth_raster_work")
# A generous keep_runs for both the bucket and flood_depth_raster_tile, not the production
# default: this test run's run_ts comes from its trigger time, so it sorts alongside real
# production runs. A small keep_runs here could prune a still-good production run.
TEST_KEEP_RUNS = 1000


def task_trigger_event1(**kwargs):
    ti = kwargs["ti"]
    print("🚀 1. Trigger Event 1 (20mm/h, 10:00-12:00 window, cold start -> saved state)...")

    # Guarantee a clean cold start on every manual run, regardless of any
    # saved-state id left over from a previous test run of this DAG.
    if os.path.exists(TEST_STATE_FILE):
        os.remove(TEST_STATE_FILE)

    event1_start = create_simulation.clock_slot(datetime.now(timezone.utc))
    rain_intervals = create_simulation.build_fixed_rain_intervals(
        EVENT1_RAIN_MM_HR, duration_hours=EVENT1_DURATION_HOURS, start_time=event1_start
    )
    sim_id, _ = create_simulation.run_forecast_process(
        state_file_path=TEST_STATE_FILE,
        rain_intervals=rain_intervals,
        use_saved_state=True,
        slot_start=event1_start,
        state_save_seconds=(create_simulation.SIMULATION_DURATION,),
    )
    if not sim_id:
        # This DAG uses fixed synthetic rain, not a rain gate — a falsy
        # sim_id here always means a real 3Di failure, never a legitimate
        # skip, so it should fail loudly rather than show as skipped.
        raise AirflowException("❌ Event 1 simulation failed to trigger (see create_simulation logs for cause)")
    ti.xcom_push(key="sim_id", value=sim_id)
    ti.xcom_push(key="event1_start", value=event1_start.isoformat())


def task_download_event1(**kwargs):
    ti = kwargs["ti"]
    sim_id = ti.xcom_pull(task_ids="1_trigger_event1", key="sim_id")
    print(f"⬇️ 2. Download results for Event 1 Sim {sim_id}...")
    saved_path = download_result.run_download(sim_id, output_dir=RESULT_DIR_EVENT1)
    if not saved_path:
        raise ValueError("❌ Download failed for Event 1")
    ti.xcom_push(key="nc_path", value=saved_path)


def task_calculate_depth_event1(**kwargs):
    ti = kwargs["ti"]
    nc_path = ti.xcom_pull(task_ids="2_download_event1", key="nc_path")

    print("⚙️ 3. Calculating Depth for Event 1...")

    output_dir = calculate_depth.run_calculate_depth(
        grid_path=INPUT_GRID,
        nc_path=nc_path,
        dem_path=INPUT_DEM,
        output_dir=DEPTH_DIR_EVENT1,
    )

    return output_dir


def task_trigger_event2(**kwargs):
    ti = kwargs["ti"]
    print("🚀 4. Trigger Event 2 (5mm/h, 12:00-14:00 window, hotstart from Event 1's saved state)...")

    event1_start = datetime.fromisoformat(
        ti.xcom_pull(task_ids="1_trigger_event1", key="event1_start")
    )
    # Event 2 starts where event 1's simulation ends, the valid time of event 1's saved state, so
    # the exact-match rule in create_simulation.choose_saved_state picks that state.
    event2_start = event1_start + timedelta(seconds=create_simulation.SIMULATION_DURATION)
    rain_intervals = create_simulation.build_fixed_rain_intervals(
        EVENT2_RAIN_MM_HR, duration_hours=EVENT2_DURATION_HOURS, start_time=event2_start
    )
    sim_id, _ = create_simulation.run_forecast_process(
        state_file_path=TEST_STATE_FILE,
        rain_intervals=rain_intervals,
        use_saved_state=True,
        slot_start=event2_start,
        state_save_seconds=(create_simulation.SIMULATION_DURATION,),
    )
    if not sim_id:
        raise AirflowException("❌ Event 2 simulation failed to trigger (see create_simulation logs for cause)")
    ti.xcom_push(key="sim_id", value=sim_id)


def task_download_event2(**kwargs):
    ti = kwargs["ti"]
    sim_id = ti.xcom_pull(task_ids="4_trigger_event2", key="sim_id")
    print(f"⬇️ 5. Download results for Event 2 Sim {sim_id}...")
    saved_path = download_result.run_download(sim_id, output_dir=RESULT_DIR_EVENT2)
    if not saved_path:
        raise ValueError("❌ Download failed for Event 2")
    ti.xcom_push(key="nc_path", value=saved_path)


def task_calculate_depth_event2(**kwargs):
    ti = kwargs["ti"]
    nc_path = ti.xcom_pull(task_ids="5_download_event2", key="nc_path")

    print("⚙️ 6. Calculating Depth for Event 2...")

    output_dir = calculate_depth.run_calculate_depth(
        grid_path=INPUT_GRID,
        nc_path=nc_path,
        dem_path=INPUT_DEM,
        output_dir=DEPTH_DIR_EVENT2,
    )

    return output_dir


def task_ensure_schema(**kwargs):
    print("🛠️ 0. Ensuring PostGIS schema (extension, geom_4326, indexes, backfill)...")
    database.create_flood_road_tables.main()
    database.create_flood_extent_tables.main()
    database.create_flood_depth_raster_tables.main()
    database.create_road_segment_table.main()
    database.create_flood_run_output_table.main()


def depth_stamps(depth_dir):
    return sorted(flood_extent.stamp_key(p) for p in os.listdir(depth_dir) if flood_extent.DEPTH_FILE.match(p))


def depth_run(ti, depth_task_id):
    """This event's depth folder, and the run name both events publish under: event 1's earliest
    depth file (D-007)."""
    depth_dir = ti.xcom_pull(task_ids=depth_task_id)
    event1_dir = ti.xcom_pull(task_ids=EVENT1_DEPTH_TASK)
    for path in (depth_dir, event1_dir):
        if not path or not os.path.isdir(str(path)):
            raise ValueError(f"❌ Depth directory is missing: {path}")
    run_ts = flood_extent.run_ts_for_depth_dir(event1_dir)
    # publish_run overwrites a timestep's tiles file by file and upserts its polygons band by
    # band, so a timestep both events wrote would keep leftovers of event 1. That only happens
    # when SIMULATION_DURATION is longer than event 1's rain window.
    if depth_dir != event1_dir and depth_stamps(depth_dir)[0] <= depth_stamps(event1_dir)[-1]:
        raise ValueError(f"❌ Event 2 has timesteps at or before Event 1's last one; they can't share run {run_ts}")
    return depth_dir, run_ts


def task_build_flood_tiles(depth_task_id, **kwargs):
    """Cut the map's flood-extent tiles from the first FLOOD_EXTENT_TILE_STEPS depth rasters of
    one event, publish them to MinIO under the shared run name, and write one PostGIS audit row
    per dissolved band polygon and one flood_extent_step row per timestep."""
    depth_dir, run_ts = depth_run(kwargs["ti"], depth_task_id)

    print(f"🌊 9. Publishing flood-extent tiles: {depth_dir} -> s3://{FLOOD_EXTENT_BUCKET}/runs/{run_ts}")
    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    )
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
            keep_runs=TEST_KEEP_RUNS,
            cleanup_dirs=[os.path.join(TEST_ROOT, "output_depths"), FLOOD_EXTENT_WORK_DIR],
        )
    finally:
        db_conn.close()
    flooded = sum(1 for result in results.values() if not result.is_empty)
    print(f"✅ Tiles done: {flooded}/{len(results)} timesteps have flooding")
    return {"run_ts": run_ts, "timesteps": len(results), "flooded_timesteps": flooded}


def task_load_depth_raster(depth_task_id, **kwargs):
    """Loads every depth_*.tif of one event into flood_depth_raster_tile under the shared run
    name, so GET /flood/points answers for both events' timesteps."""
    depth_dir, run_ts = depth_run(kwargs["ti"], depth_task_id)

    print(f"🗺️ 9b. Loading depth rasters into PostGIS: {depth_dir} (run {run_ts})")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        loaded = raster_load.load_run(conn, depth_dir, run_ts, DEPTH_RASTER_WORK_DIR, keep_runs=TEST_KEEP_RUNS)
    finally:
        conn.close()
    print(f"✅ Depth rasters loaded: {len(loaded)} timesteps")
    return {"run_ts": run_ts, "timesteps": len(loaded)}


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


def task_flood_on_roads(depth_task_id, **kwargs):
    """Writes the shared run's per-piece flood depth into flood_road_values, the table routing
    reads. compute() covers every timestep loaded for the run so far, so event 2's task also
    rewrites event 1's timesteps, which gives the same rows plus zeros for pieces only event 2
    wets."""
    _, run_ts = depth_run(kwargs["ti"], depth_task_id)

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
    "flood_forecast_consecutive_state_test",
    default_args=default_args,
    description="Manual test: consecutive events (20mm/h then 5mm/h, 2h each, the second hotstarted from the first's saved state) through the flood_mapping_full steps, published as one run the frontend shows.",
    schedule=None,
    start_date=datetime(2026, 2, 5),
    catchup=False,
    max_active_runs=1,
    tags=["3di", "flood", "manual-test", "state-test"],
) as dag:

    t0 = PythonOperator(task_id="0_ensure_schema", python_callable=task_ensure_schema)
    t_roads = PythonOperator(task_id="load_road_segments", python_callable=task_load_road_segments)
    t1 = PythonOperator(task_id="1_trigger_event1", python_callable=task_trigger_event1)
    t2 = PythonOperator(task_id="2_download_event1", python_callable=task_download_event1)
    t3 = PythonOperator(task_id=EVENT1_DEPTH_TASK, python_callable=task_calculate_depth_event1)
    event1 = {"depth_task_id": EVENT1_DEPTH_TASK}
    t3b = PythonOperator(task_id="3b_build_tiles_event1", python_callable=task_build_flood_tiles, op_kwargs=event1)
    t3c = PythonOperator(task_id="3c_load_depth_raster_event1", python_callable=task_load_depth_raster, op_kwargs=event1)
    t3d = PythonOperator(task_id="3d_flood_on_roads_event1", python_callable=task_flood_on_roads, op_kwargs=event1)
    t4 = PythonOperator(task_id="4_trigger_event2", python_callable=task_trigger_event2)
    t5 = PythonOperator(task_id="5_download_event2", python_callable=task_download_event2)
    t6 = PythonOperator(task_id=EVENT2_DEPTH_TASK, python_callable=task_calculate_depth_event2)
    event2 = {"depth_task_id": EVENT2_DEPTH_TASK}
    t6b = PythonOperator(task_id="6b_build_tiles_event2", python_callable=task_build_flood_tiles, op_kwargs=event2)
    t6c = PythonOperator(task_id="6c_load_depth_raster_event2", python_callable=task_load_depth_raster, op_kwargs=event2)
    t6d = PythonOperator(task_id="6d_flood_on_roads_event2", python_callable=task_flood_on_roads, op_kwargs=event2)

    t0 >> [t_roads, t3b, t3c, t3d, t6b, t6c, t6d]
    t_roads >> [t3d, t6d]

    # Event 2 is triggered as soon as Event 1's result is downloaded (it only
    # needs Event 1's saved state, not its depth calc).
    t1 >> t2 >> t3
    t2 >> t4 >> t5
    t3 >> [t3b, t3c]
    t3c >> t3d
    # Event 2's depth calc (heavy multiprocessing) waits for event 1's tile build and raster load
    # too, so it never overlaps either of them.
    [t3b, t3c, t5] >> t6
    t6 >> [t6b, t6c]
    t6c >> t6d
