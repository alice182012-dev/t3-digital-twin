from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta, timezone
import sys
import os


BASE_PATH = "/opt/airflow"
SCRIPTS_PATH = os.path.join(BASE_PATH, "scripts")
DATA_PATH = os.path.join(BASE_PATH, "data/mapping")

sys.path.append(SCRIPTS_PATH)

try:
    import create_simulation
    import download_result
    import calculate_depth
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

    t1 = PythonOperator(task_id="1_trigger_event1", python_callable=task_trigger_event1)
    t2 = PythonOperator(task_id="2_download_event1", python_callable=task_download_event1)
    t3 = PythonOperator(task_id="3_calculate_depth_event1", python_callable=task_calculate_depth_event1)
    t4 = PythonOperator(task_id="4_trigger_event2", python_callable=task_trigger_event2)
    t5 = PythonOperator(task_id="5_download_event2", python_callable=task_download_event2)
    t6 = PythonOperator(task_id="6_calculate_depth_event2", python_callable=task_calculate_depth_event2)

    # Event 2 is triggered as soon as Event 1's result is downloaded (it only
    # needs Event 1's saved state, not its depth calc). Depth calc for Event 2
    # waits for Event 1's depth calc to finish so the two heavy multiprocessing
    # jobs don't run concurrently.
    t1 >> t2
    t2 >> t3
    t2 >> t4 >> t5
    [t3, t5] >> t6
