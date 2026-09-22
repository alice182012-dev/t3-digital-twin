from airflow import DAG
from airflow.exceptions import AirflowException
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta, timezone
import sys
import os


BASE_PATH = "/opt/airflow"
SCRIPTS_PATH = os.path.join(BASE_PATH, "scripts")
DATA_PATH = os.path.join(BASE_PATH, "data")

sys.path.append(SCRIPTS_PATH)

try:
    import create_simulation
    import download_result
    import calculate_depth
except ImportError as e:
    print(f"❌ Lỗi Import: {e}")


# Grid/DEM fixtures are shared, read-only inputs — reusing them is safe and
# avoids re-uploading them for a single-event smoke test.
INPUT_GRID = os.path.join(DATA_PATH, "inputs", "gridadmin.h5")
INPUT_DEM = os.path.join(DATA_PATH, "inputs", "dem.tif")

# Everything this DAG writes lives under its own tree, isolated from
# production state/output (flood_mapping_dag.py, flood_forecast_dag.py) and
# from flood_forecast_state_test_dag.py's hotstart test tree, so a run here
# never collides with or gets cleaned up alongside either.
TEST_STATE_FILE = os.path.join(BASE_PATH, "state", "flood_state_cli_test.json")
RESULT_DIR = os.path.join(DATA_PATH, "results_cli_test")
OUTPUT_DIR = os.path.join(DATA_PATH, "output_depths_cli_test")

RAIN_MM_HR = 20
RAIN_DURATION_HOURS = 2


def task_trigger_simulation(**kwargs):
    ti = kwargs["ti"]
    print("🚀 1. Trigger single 3Di simulation (20mm/h, 2h, fixed synthetic rain)...")

    rain_intervals = create_simulation.build_fixed_rain_intervals(
        RAIN_MM_HR, duration_hours=RAIN_DURATION_HOURS, start_time=datetime.now(timezone.utc)
    )
    sim_id, _ = create_simulation.run_forecast_process(
        state_file_path=TEST_STATE_FILE,
        rain_intervals=rain_intervals,
        # Always cold start: this DAG validates calculate_depth end to end on
        # a single event, not the hotstart path (flood_forecast_state_test_dag.py
        # covers that).
        use_saved_state=False,
    )
    if not sim_id:
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


def task_calculate_depth(**kwargs):
    ti = kwargs["ti"]
    nc_path = ti.xcom_pull(task_ids="2_download_result", key="nc_path")

    print("⚙️ 3. Calculating depth (calculate_depth.py manual test, real simulation output)...")

    output_dir = calculate_depth.run_calculate_depth(
        grid_path=INPUT_GRID,
        nc_path=nc_path,
        dem_path=INPUT_DEM,
        output_dir=OUTPUT_DIR,
    )

    print(f"🎉 Depth output written to: {output_dir}")
    return output_dir


default_args = {
    "owner": "flood_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    "calculate_depth_manual_test",
    default_args=default_args,
    description=(
        "Manual test: trigger a single real 3Di simulation (fixed synthetic "
        "rain, cold start), download it, then run "
        "calculate_depth.run_calculate_depth against the result. For "
        "validating the calculate_depth CLI-subprocess rewrite end to end, "
        "isolated from every other DAG's state and output."
    ),
    schedule=None,
    start_date=datetime(2026, 2, 5),
    catchup=False,
    max_active_runs=1,
    tags=["3di", "flood", "manual-test", "calculate-depth"],
) as dag:
    t1 = PythonOperator(task_id="1_trigger_simulation", python_callable=task_trigger_simulation)
    t2 = PythonOperator(task_id="2_download_result", python_callable=task_download_result)
    t3 = PythonOperator(task_id="3_calculate_depth", python_callable=task_calculate_depth)

    t1 >> t2 >> t3
