from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta, timezone
from pathlib import Path
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
    import flood_extent
    import publish
    import database.create_flood_extent_tables
    from db_config import DB_CONFIG
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

FLOOD_EXTENT_BUCKET = os.getenv("FLOOD_EXTENT_BUCKET", "flood-extent")
FLOOD_EXTENT_WORK_DIR = os.path.join(TEST_ROOT, "flood_extent_work")
# A generous keep_runs, not the production default: this test tree's run_ts values come from
# datetime.now() at trigger time, so they sort alongside real production runs in the same
# bucket. A small keep_runs here could prune a still-good production run out from under it.
TEST_KEEP_RUNS = 1000


def task_trigger_event1(**kwargs):
    ti = kwargs["ti"]
    print("🚀 1. Trigger Event 1 (20mm/h, 10:00-12:00 window, cold start -> saved state)...")

    # Guarantee a clean cold start on every manual run, regardless of any
    # saved-state id left over from a previous test run of this DAG.
    if os.path.exists(TEST_STATE_FILE):
        os.remove(TEST_STATE_FILE)

    event1_start = datetime.now(timezone.utc)
    rain_intervals = create_simulation.build_fixed_rain_intervals(
        EVENT1_RAIN_MM_HR, duration_hours=EVENT1_DURATION_HOURS, start_time=event1_start
    )
    sim_id, _ = create_simulation.run_forecast_process(
        state_file_path=TEST_STATE_FILE,
        rain_intervals=rain_intervals,
        use_saved_state=True,
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
    # Cascade: Event 2's rain window starts exactly when Event 1's ends.
    event2_start = event1_start + timedelta(hours=EVENT1_DURATION_HOURS)
    rain_intervals = create_simulation.build_fixed_rain_intervals(
        EVENT2_RAIN_MM_HR, duration_hours=EVENT2_DURATION_HOURS, start_time=event2_start
    )
    sim_id, _ = create_simulation.run_forecast_process(
        state_file_path=TEST_STATE_FILE,
        rain_intervals=rain_intervals,
        use_saved_state=True,
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
    print("🛠️ 0. Ensuring flood_extent_polygon schema exists...")
    database.create_flood_extent_tables.main()


def build_and_publish_tiles(depth_dir):
    """Shared by both events: publishes one event's depth tifs to the flood-extent bucket, the
    same code path production uses (dags/flood_mapping_dag.py's task 9), so a run of this DAG
    validates the CLI-subprocess calculate_depth rewrite through the whole downstream pipeline,
    not just calculate_depth in isolation."""
    depth_files = sorted(Path(depth_dir).glob("depth_*.tif"))
    if not depth_files:
        raise ValueError(f"❌ No depth_*.tif files in {depth_dir}")
    run_ts = flood_extent.stamp_key(depth_files[0])

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ["MINIO_ENDPOINT"],
        aws_access_key_id=os.environ["MINIO_ACCESS_KEY"],
        aws_secret_access_key=os.environ["MINIO_SECRET_KEY"],
    )
    db_conn = psycopg2.connect(**DB_CONFIG)
    try:
        results = publish.publish_run(
            depth_dir, run_ts, FLOOD_EXTENT_WORK_DIR, s3, FLOOD_EXTENT_BUCKET,
            db_conn=db_conn, keep_runs=TEST_KEEP_RUNS,
            cleanup_dirs=[os.path.join(TEST_ROOT, "output_depths"), FLOOD_EXTENT_WORK_DIR],
        )
    finally:
        db_conn.close()
    flooded = sum(1 for result in results.values() if not result.is_empty)
    print(f"✅ Published {run_ts}: {flooded}/{len(results)} timesteps have flooding")
    return {"run_ts": run_ts, "timesteps": len(results), "flooded_timesteps": flooded}


def task_build_tiles_event1(**kwargs):
    ti = kwargs["ti"]
    depth_dir = ti.xcom_pull(task_ids="3_calculate_depth_event1")
    print("🌊 3b. Publishing flood-extent tiles for Event 1...")
    return build_and_publish_tiles(depth_dir)


def task_build_tiles_event2(**kwargs):
    ti = kwargs["ti"]
    depth_dir = ti.xcom_pull(task_ids="6_calculate_depth_event2")
    print("🌊 6b. Publishing flood-extent tiles for Event 2...")
    return build_and_publish_tiles(depth_dir)


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
    description="Manual test: consecutive events (20mm/h then 5mm/h, 2h each) to observe the effect of 3Di saved-state hotstart. Depth analysis only, isolated test folders.",
    schedule=None,
    start_date=datetime(2026, 2, 5),
    catchup=False,
    max_active_runs=1,
    tags=["3di", "flood", "manual-test", "state-test"],
) as dag:

    t0 = PythonOperator(task_id="0_ensure_schema", python_callable=task_ensure_schema)
    t1 = PythonOperator(task_id="1_trigger_event1", python_callable=task_trigger_event1)
    t2 = PythonOperator(task_id="2_download_event1", python_callable=task_download_event1)
    t3 = PythonOperator(task_id="3_calculate_depth_event1", python_callable=task_calculate_depth_event1)
    t3b = PythonOperator(task_id="3b_build_tiles_event1", python_callable=task_build_tiles_event1)
    t4 = PythonOperator(task_id="4_trigger_event2", python_callable=task_trigger_event2)
    t5 = PythonOperator(task_id="5_download_event2", python_callable=task_download_event2)
    t6 = PythonOperator(task_id="6_calculate_depth_event2", python_callable=task_calculate_depth_event2)
    t6b = PythonOperator(task_id="6b_build_tiles_event2", python_callable=task_build_tiles_event2)

    # Event 2 is triggered as soon as Event 1's result is downloaded (it only
    # needs Event 1's saved state, not its depth calc). Depth calc for Event 2
    # waits for Event 1's depth calc to finish so the two heavy multiprocessing
    # jobs don't run concurrently.
    t0 >> t3b
    t0 >> t6b
    t1 >> t2
    t2 >> t3
    t3 >> t3b
    t2 >> t4 >> t5
    # t6 (event2's depth calc, also heavy multiprocessing) waits for t3b too, not just t3, so
    # it never overlaps event1's tile build either.
    [t3b, t5] >> t6
    t6 >> t6b
