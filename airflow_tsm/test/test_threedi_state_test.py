"""Local, real end-to-end test of the 3Di integration (threedi-api-client).

Mirrors airflow_tsm/dags/flood_forecast_state_test_dag.py's two-event
hotstart chain (20mm/h 2h event -> saved state -> 5mm/h 2h event hotstarted
from it), but runs outside Airflow using create_simulation.py /
download_result.py directly.

This creates two REAL simulations on 3Di and consumes real compute quota.

Usage (from repo root):
    python airflow_tsm/test/test_threedi_state_test.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.dirname(TEST_DIR)  # airflow_tsm/
SCRIPTS_PATH = os.path.join(BASE_PATH, "scripts")
REPO_ROOT = os.path.dirname(BASE_PATH)  # airflow_new/

sys.path.insert(0, SCRIPTS_PATH)
load_dotenv(os.path.join(REPO_ROOT, ".env"))

import create_simulation  # noqa: E402
import download_result  # noqa: E402

try:
    import calculate_depth  # noqa: E402
except ImportError as e:
    # Depth calc is unrelated to the 3Di client itself (it post-processes
    # already-downloaded files, no 3Di API calls) and pulls in a heavy geo
    # stack (fiona/rasterio/geopandas) that may not be installed in a local
    # dev env outside the Docker container. Skip it rather than block the
    # actual thing being tested: create -> hotstart -> download.
    print(f"⚠️ calculate_depth unavailable locally ({e}); depth calc steps will be skipped")
    calculate_depth = None

DATA_PATH = os.path.join(BASE_PATH, "data", "mapping")
INPUT_DEM = os.path.join(DATA_PATH, "inputs", "dem.tif")
INPUT_GRID = os.path.join(DATA_PATH, "inputs", "gridadmin.h5")

# Dedicated test tree, isolated from the production pipeline's state file /
# output dirs (those are used by flood_forecast_dag.py / flood_mapping_dag.py).
TEST_ROOT = os.path.join(BASE_PATH, "data", "mapping_state_test")
TEST_STATE_FILE = os.path.join(BASE_PATH, "state", "flood_state_test.json")

RESULT_DIR_EVENT1 = os.path.join(TEST_ROOT, "results", "event1_20mmhr")
RESULT_DIR_EVENT2 = os.path.join(TEST_ROOT, "results", "event2_5mmhr")
DEPTH_DIR_EVENT1 = os.path.join(TEST_ROOT, "output_depths", "event1_20mmhr")
DEPTH_DIR_EVENT2 = os.path.join(TEST_ROOT, "output_depths", "event2_5mmhr")

EVENT1_RAIN_MM_HR = 20
EVENT1_DURATION_HOURS = 2
EVENT2_RAIN_MM_HR = 5
EVENT2_DURATION_HOURS = 2


def run():
    for d in (RESULT_DIR_EVENT1, RESULT_DIR_EVENT2, DEPTH_DIR_EVENT1, DEPTH_DIR_EVENT2):
        os.makedirs(d, exist_ok=True)

    # Guarantee a clean cold start regardless of leftovers from a previous run.
    if os.path.exists(TEST_STATE_FILE):
        os.remove(TEST_STATE_FILE)

    # --- Event 1: cold start, 20mm/h, 2h -> registers a saved state ---
    print("\n=== [1/4] Trigger Event 1 (20mm/h, cold start -> saved state) ===")
    event1_start = datetime.now(timezone.utc)
    rain_intervals_1 = create_simulation.build_fixed_rain_intervals(
        EVENT1_RAIN_MM_HR, duration_hours=EVENT1_DURATION_HOURS, start_time=event1_start
    )
    sim_id_1, _ = create_simulation.run_forecast_process(
        state_file_path=TEST_STATE_FILE,
        rain_intervals=rain_intervals_1,
        use_saved_state=True,
    )
    if not sim_id_1:
        print("❌ Event 1 simulation was not triggered. Aborting.")
        return 1
    print(f"✅ Event 1 Simulation ID: {sim_id_1}")

    print("\n=== [2/4] Download + depth for Event 1 ===")
    nc_path_1 = download_result.run_download(sim_id_1, output_dir=RESULT_DIR_EVENT1)
    if not nc_path_1:
        print("❌ Download failed for Event 1. Aborting.")
        return 1
    print(f"✅ Event 1 NC: {nc_path_1}")
    if calculate_depth is not None:
        depth_dir_1 = calculate_depth.run_calculate_depth(
            grid_path=INPUT_GRID, nc_path=nc_path_1, dem_path=INPUT_DEM, output_dir=DEPTH_DIR_EVENT1
        )
        print(f"✅ Event 1 depth output: {depth_dir_1}")

    # --- Event 2: hotstart from Event 1's saved state, 5mm/h, 2h ---
    print("\n=== [3/4] Trigger Event 2 (5mm/h, hotstart from Event 1) ===")
    event2_start = event1_start + timedelta(hours=EVENT1_DURATION_HOURS)
    rain_intervals_2 = create_simulation.build_fixed_rain_intervals(
        EVENT2_RAIN_MM_HR, duration_hours=EVENT2_DURATION_HOURS, start_time=event2_start
    )
    sim_id_2, _ = create_simulation.run_forecast_process(
        state_file_path=TEST_STATE_FILE,
        rain_intervals=rain_intervals_2,
        use_saved_state=True,
    )
    if not sim_id_2:
        print("❌ Event 2 simulation was not triggered. Aborting.")
        return 1
    print(f"✅ Event 2 Simulation ID: {sim_id_2}")

    print("\n=== [4/4] Download + depth for Event 2 ===")
    nc_path_2 = download_result.run_download(sim_id_2, output_dir=RESULT_DIR_EVENT2)
    if not nc_path_2:
        print("❌ Download failed for Event 2. Aborting.")
        return 1
    print(f"✅ Event 2 NC: {nc_path_2}")
    if calculate_depth is not None:
        depth_dir_2 = calculate_depth.run_calculate_depth(
            grid_path=INPUT_GRID, nc_path=nc_path_2, dem_path=INPUT_DEM, output_dir=DEPTH_DIR_EVENT2
        )
        print(f"✅ Event 2 depth output: {depth_dir_2}")

    print("\n🎉 SUCCESS: both events ran end-to-end through the promoted (threedi-api-client) path.")
    print(f"   Event 1 sim={sim_id_1}  Event 2 sim={sim_id_2} (hotstarted from Event 1)")
    return 0


if __name__ == "__main__":
    sys.exit(run())
