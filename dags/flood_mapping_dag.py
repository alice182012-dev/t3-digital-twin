from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.providers.standard.operators.python import BranchPythonOperator, PythonOperator
from airflow.providers.standard.sensors.time_delta import TimeDeltaSensor
from datetime import datetime, timedelta
import sys
import os
import boto3
import psycopg2

sys.path.append(os.path.join("/opt/airflow", "plugins"))
from vn_timetable import VNContinuousTimetable


BASE_PATH = "/opt/airflow"
SCRIPTS_PATH = os.path.join(BASE_PATH, "scripts")
DATA_PATH = os.path.join(BASE_PATH, "data/mapping")

sys.path.append(SCRIPTS_PATH)
# database/*.py import `db_config` as a top-level module (not `database.db_config`),
# so its directory needs to be importable directly too.
sys.path.append(os.path.join(SCRIPTS_PATH, "database"))
sys.path.append(os.path.join(SCRIPTS_PATH, "flood_extent"))

try:
    import create_simulation
    import download_result
    import calculate_depth
    import netcdf_input
    import database.netcdf_to_pg
    import database.create_netcdf_tables
    import database.create_flood_road_tables
    import database.create_flood_extent_tables
    import database.create_flood_depth_raster_tables
    import database.create_road_segment_table
    import flood_extent
    import publish
    import raster_load
    from db_config import DB_CONFIG
    from roads import load_road_segments
    from flood_roads import flood_on_roads
except ImportError as e:
    print(f"❌ Lỗi Import: {e}")


STATE_FILE = os.path.join(BASE_PATH, "state", "flood_system_state.json")
INPUT_DEM = os.path.join(DATA_PATH, "inputs", "dem.tif")
INPUT_GRID = os.path.join(DATA_PATH, "inputs", "gridadmin.h5")
RESULT_DIR = os.path.join(DATA_PATH, "results")
DEPTH_ROOT_DIR = os.path.join(DATA_PATH, "output_depths")
# Vector tiles of the flood extent, one folder per run and timestep, served by the frontend at
# /flood-extent/<run>/<timestep>/{z}/{x}/{y}.pbf. compose.yml mounts this folder into it.
FLOOD_EXTENT_WORKERS = int(os.getenv("FLOOD_EXTENT_WORKERS", "2"))
FLOOD_EXTENT_KEEP_RUNS = int(os.getenv("FLOOD_EXTENT_KEEP_RUNS", "8"))
# scripts/flood_extent/publish.py's own scratch space, per timestep, deleted as each timestep's
# tiles finish uploading — never the final destination, just where the raster pipeline works.
FLOOD_EXTENT_WORK_DIR = os.path.join(DATA_PATH, "flood_extent_work")
FLOOD_EXTENT_BUCKET = os.getenv("FLOOD_EXTENT_BUCKET", "flood-extent")
FLOOD_EXTENT_CLEANUP_MAX_AGE_HOURS = int(os.getenv("FLOOD_EXTENT_CLEANUP_MAX_AGE_HOURS", "24"))
# scripts/flood_extent/raster_load.py's own scratch space for the EPSG:4326-reprojected copy of
# each depth.tif; each file is deleted right after it loads, same posture as FLOOD_EXTENT_WORK_DIR.
DEPTH_RASTER_WORK_DIR = os.path.join(DATA_PATH, "depth_raster_work")
RAIN_THRESHOLD_MM_HR = float(os.getenv("FLOOD_RAIN_THRESHOLD_MM_HR", "5"))
RAIN_CHECK_INTERVAL_SECONDS = int(os.getenv("FLOOD_RAIN_CHECK_INTERVAL_SECONDS", "900"))


def task_check_forecast_rain(**kwargs):
    """Choose the full pipeline only when any forecast window reaches 0.01 mm/h."""
    ti = kwargs["ti"]
    intervals = create_simulation.get_rain_forecast()
    if not intervals:
        raise ValueError("❌ Tomorrow.io returned no rain forecast; refusing to treat this as a dry cycle")

    decision = create_simulation.evaluate_rain_gate(intervals, RAIN_THRESHOLD_MM_HR)
    ti.xcom_push(key="rain_intervals", value=intervals)
    ti.xcom_push(key="rain_gate_decision", value=decision)
    print(
        "🌧️ Rain gate: "
        f"max={decision['max_intensity_mm_hr']:.2f} mm/h, "
        f"threshold={decision['threshold_mm_hr']:.2f} mm/h, "
        f"intervals={decision['interval_count']}"
    )
    if decision["should_run"]:
        return "1_trigger_simulation"
    print("✅ Dry cycle: skipping simulation, processing, and upload as a successful DAG run")
    return "wait_before_next_rain_check"


def task_run_simulation(**kwargs):
    ti = kwargs["ti"]
    print("🚀 1. Trigger Simulation...")
    rain_intervals = ti.xcom_pull(task_ids="0_check_forecast_rain", key="rain_intervals")
    sim_id, _ = create_simulation.run_forecast_process(
        state_file_path=STATE_FILE,
        rain_intervals=rain_intervals,
    )
    if not sim_id:
        # By the time this task runs, the rain gate (0_check_forecast_rain)
        # has already routed here specifically because it decided to run —
        # a legitimate dry-cycle skip never reaches this task at all (it
        # routes to wait_before_next_rain_check instead). So a falsy sim_id
        # here always means a real 3Di failure, never a correct skip; raising
        # AirflowSkipException made that failure look identical to a
        # dry-cycle skip (both green) in the Airflow UI.
        raise AirflowException("❌ Simulation failed to trigger (see create_simulation logs for cause)")
    ti.xcom_push(key="sim_id", value=sim_id)


def task_download_result(**kwargs):
    ti = kwargs["ti"]
    sim_id = ti.xcom_pull(task_ids="1_trigger_simulation", key="sim_id")
    print(f"⬇️ 2. Download results for Sim {sim_id}...")
    saved_path = download_result.run_download(sim_id, output_dir=RESULT_DIR)
    if not saved_path:
        raise ValueError("❌ Download failed")
    ti.xcom_push(key="nc_path", value=saved_path)


def task_ensure_schema(**kwargs):
    print("🛠️ 0b. Ensuring PostGIS schema (extension, geom_4326, indexes, backfill)...")
    database.create_flood_road_tables.main()
    database.create_flood_extent_tables.main()
    database.create_flood_depth_raster_tables.main()
    database.create_road_segment_table.main()
    database.create_netcdf_tables.create_tables()


def task_upload_netcdf_postgres(**kwargs):
    ti = kwargs["ti"]
    nc_path = ti.xcom_pull(task_ids="2_download_results", key="nc_path")

    if not nc_path or not os.path.exists(nc_path):
        raise ValueError(f"❌ Không tìm thấy NetCDF để ingest: {nc_path}")

    print(f"🗄️ 3b. Uploading NetCDF to Postgres: {nc_path}")

    database.netcdf_to_pg.upload_netcdf_to_database(nc_path)


def task_calculate_depth(**kwargs):
    """
    Task này sẽ trả về đường dẫn thư mục UUID vừa tạo.
    Ví dụ return: /opt/airflow/data/mapping/output_depths/a1b2c3d4
    """
    ti = kwargs["ti"]
    print("⚙️ 3. Calculating Depth...")

    output_uuid_dir = netcdf_input.calculate_depth_from_download(
        ti=ti,
        calculate_depth_fn=calculate_depth.run_calculate_depth,
        grid_path=INPUT_GRID,
        dem_path=INPUT_DEM,
        output_dir=DEPTH_ROOT_DIR,
        model_id=os.getenv("MODEL_ID"),
    )

    return output_uuid_dir


def depth_run(ti):
    """This run's depth folder from task 3, and the run name taken from its earliest depth file."""
    depth_dir = ti.xcom_pull(task_ids="3_calculate_depth")
    if not depth_dir or not os.path.isdir(str(depth_dir)):
        raise ValueError(f"❌ Depth directory is missing: {depth_dir}")
    return depth_dir, flood_extent.run_ts_for_depth_dir(depth_dir)


def task_build_flood_tiles(**kwargs):
    """Cut the map's flood-extent tiles from every depth raster of this run, publish them to
    MinIO, and write one PostGIS audit row per dissolved band polygon per timestep.

    Only uploaded tiles and DB rows are kept; publish_run deletes every local intermediate itself
    as each timestep finishes. The run name comes from the earliest depth file, the same one task
    9b uses, so the UI finds the tiles from the (run, valid_time) pair it already selects. Tiles go
    to MinIO, not a local folder, because the worker and the frontend run on separate hosts in
    production.
    """
    depth_dir, run_ts = depth_run(kwargs["ti"])

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
            keep_runs=FLOOD_EXTENT_KEEP_RUNS,
            cleanup_dirs=[DEPTH_ROOT_DIR, FLOOD_EXTENT_WORK_DIR],
            cleanup_max_age_hours=FLOOD_EXTENT_CLEANUP_MAX_AGE_HOURS,
        )
    finally:
        db_conn.close()
    flooded = sum(1 for result in results.values() if not result.is_empty)
    print(f"✅ Tiles done: {flooded}/{len(results)} timesteps have flooding")
    return {"run_ts": run_ts, "timesteps": len(results), "flooded_timesteps": flooded}


def task_load_depth_raster(**kwargs):
    """Loads every depth_*.tif of this run into flood_depth_raster_tile, reprojected to EPSG:4326, so
    GET /flood/points (Sprint 2) can answer an arbitrary-point depth query with ST_Value instead
    of reading the file from disk. Same run_ts as task 9, so both tables key off the (run,
    valid_time) pair the frontend already selects.
    """
    depth_dir, run_ts = depth_run(kwargs["ti"])

    print(f"🗺️ 9b. Loading depth rasters into PostGIS: {depth_dir} (run {run_ts})")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        loaded = raster_load.load_run(conn, depth_dir, run_ts, DEPTH_RASTER_WORK_DIR)
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


def task_flood_on_roads(**kwargs):
    """Writes this run's per-piece flood depth into flood_road_values, the table routing reads,
    from the tiles task 9b loaded under the same run name."""
    _, run_ts = depth_run(kwargs["ti"])

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
    "flood_mapping_full",
    default_args=default_args,
    description="Pipeline 3Di -> MinIO (Direct Path Passing)",
    schedule=VNContinuousTimetable(),
    start_date=datetime(2026, 2, 5),
    catchup=False,
    max_active_runs=1,
    tags=["3di", "flood"],
) as dag:
    t0 = BranchPythonOperator(
        task_id="0_check_forecast_rain",
        python_callable=task_check_forecast_rain,
    )
    wait_for_next_check = TimeDeltaSensor(
        task_id="wait_before_next_rain_check",
        delta=timedelta(seconds=RAIN_CHECK_INTERVAL_SECONDS),
        mode="reschedule",
    )
    t1 = PythonOperator(
        task_id="1_trigger_simulation", python_callable=task_run_simulation
    )
    t_ddl = PythonOperator(
        task_id="0b_ensure_schema", python_callable=task_ensure_schema
    )
    t2 = PythonOperator(
        task_id="2_download_results", python_callable=task_download_result
    )
    t3 = PythonOperator(
        task_id="3_calculate_depth", python_callable=task_calculate_depth
    )
    t3b = PythonOperator(
        task_id="3b_upload_netcdf_postgres", python_callable=task_upload_netcdf_postgres
    )
    t9 = PythonOperator(
        task_id="9_build_flood_tiles", python_callable=task_build_flood_tiles
    )
    t9b = PythonOperator(
        task_id="9b_load_depth_raster", python_callable=task_load_depth_raster
    )
    t_roads = PythonOperator(
        task_id="load_road_segments", python_callable=task_load_road_segments
    )
    t_flood_roads = PythonOperator(
        task_id="flood_on_roads", python_callable=task_flood_on_roads
    )

    t0 >> t1 >> t2 >> t3
    t3 >> t9
    t3 >> t9b
    t2 >> t3b
    t1 >> t_ddl
    t_ddl >> [t3b, t9, t9b]
    t_ddl >> [t_roads, t_flood_roads]
    t_roads >> t_flood_roads
    t9b >> t_flood_roads
    t0 >> wait_for_next_check
