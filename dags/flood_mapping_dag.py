from airflow import DAG
from airflow.exceptions import AirflowException, AirflowSkipException
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import BranchPythonOperator, PythonOperator
from datetime import datetime, timedelta, timezone
import functools
import sys
import os
import psycopg2

from core_assets import FLOOD_DEPTH_FILES, FLOOD_DEPTH_RASTER
from core_paths import BASE_PATH, DATA_PATH, DEPTH_ROOT_DIR, RESULT_DIR


SCRIPTS_PATH = os.path.join(BASE_PATH, "scripts")

sys.path.append(SCRIPTS_PATH)
# database/*.py import `db_config` as a top-level module (not `database.db_config`),
# so its directory needs to be importable directly too.
sys.path.append(os.path.join(SCRIPTS_PATH, "database"))
sys.path.append(os.path.join(SCRIPTS_PATH, "flood_extent"))

try:
    import archive_results
    import create_simulation
    import hotstart_policy
    import forecast_mode
    import standing_flood
    import stale_run
    import download_result
    import calculate_depth
    import netcdf_input
    import database.create_flood_extent_tables
    import database.create_flood_depth_raster_tables
    import database.create_graph_edge_table
    import database.create_edge_depth_tables
    import database.create_flood_run_output_table
    import database.create_demo_pin_table
    import database.create_forecast_mode_table
    import database.create_timescale_tables
    import flood_extent
    import raster_load
    from db_config import DB_CONFIG
except ImportError as e:
    print(f"❌ Lỗi Import: {e}")


STATE_FILE = os.path.join(BASE_PATH, "state", "flood_system_state.json")
INPUT_DEM = os.path.join(DATA_PATH, "inputs", "dem.tif")
INPUT_GRID = os.path.join(DATA_PATH, "inputs", "gridadmin.h5")
# 2b_archive_results copies results_3di.nc and a run record of every real-rain run here (compose.yml mounts
# ARCHIVE_HOST_PATH) before the 24-hour cleanup in the `flood_tiles` DAG deletes RESULT_DIR.
ARCHIVE_DIR = os.getenv("ARCHIVE_DIR", os.path.join(BASE_PATH, "archive"))
ARCHIVE_MIN_FREE_GB = float(os.getenv("ARCHIVE_MIN_FREE_GB", "50"))
# graph.json of the graph export names the graph hash that the run record carries.
EDGE_EXPORT_DIR = os.getenv("EDGE_EXPORT_DIR", os.path.join(DATA_PATH, "graph_export"))
# scripts/flood_extent/raster_load.py's own scratch space for the EPSG:4326-reprojected copy of
# each depth.tif; each file is deleted right after it loads, same posture as the flood_tiles work folder.
DEPTH_RASTER_WORK_DIR = os.path.join(DATA_PATH, "depth_raster_work")
RAIN_THRESHOLD_MM_HR = float(os.getenv("FLOOD_RAIN_THRESHOLD_MM_HR", "5"))
# Read at parse time so a bad value fails the DAG import with the variable named.
STALE_RUN_MINUTES = stale_run.limit_minutes(os.environ)
# The rain threshold only starts a simulation from a dry state. Once runs exist, the simulation continues until the
# newest standing_flood.STEADY_RUNS_TO_STOP runs of the edge depth table have stopped changing and no rain is forecast.
# Stopping an Airflow run does not stop its 3Di simulation, which keeps writing its timed saved
# states into the state file. After a stop and restart, choose_saved_state's 30-minute window can
# still find one of them and hotstart from a storm that kept growing. With this flag on, a run
# hotstarts only when the run of the previous slot is success or running.
COLD_START_AFTER_BREAK = os.getenv("FLOOD_COLD_START_AFTER_BREAK", "1").strip().lower() in ("1", "true", "yes")
# Keeps 0_check_forecast_rain and 1_trigger_simulation off the default pool, so a new run's
# rain check and 3Di trigger (I/O-bound: they wait on Tomorrow.io and 3Di, not local CPU) don't
# queue behind a previous run's CPU-heavy tasks for the worker's 2 Celery slots. Airflow 3
# forbids direct ORM/database access from code that runs at DAG-parse time, so this pool cannot
# be self-provisioned here; it's created once with `airflow pools set threedi_trigger 2 "..."`
# as a deploy step, the same way this repo's schema scripts are run once against the server.
POOL_THREEDI_TRIGGER = "threedi_trigger"
# 3_calculate_depth spawns MAX_WORKERS threedidepth subprocesses via multiprocessing.Pool
# (CPU-bound, not I/O-bound like the pool above). Two runs of this task at once would
# oversubscribe the box, so this one-slot pool exists to serialize it, not to prioritize it.
# Same out-of-band creation rule as POOL_THREEDI_TRIGGER: `airflow pools set depth_calc 1 "..."`.
POOL_DEPTH_CALC = "depth_calc"


def run_slot(kwargs):
    """The 15-minute slot this DAG run simulates. A manual run triggered without a logical date takes now."""
    return create_simulation.clock_slot(kwargs.get("logical_date") or datetime.now(timezone.utc))


def skip_stale_run(task):
    """Skips the task, and so its downstream tasks, when the run's slot is older than STALE_RUN_MINUTES. An unpause
    or a long queue revives runs of past slots, and their tasks would start real 3Di simulations."""

    @functools.wraps(task)
    def guarded(**kwargs):
        now = datetime.now(timezone.utc)
        slot = run_slot(kwargs)
        if stale_run.is_stale(slot, now, STALE_RUN_MINUTES):
            raise AirflowSkipException(stale_run.message(slot, now, STALE_RUN_MINUTES))
        return task(**kwargs)

    return guarded


def record_forecast_mode(kwargs, decision, standing, gate_open):
    """Writes the gate decision to forecast_mode for the backend. A failure here is printed and does not stop the gate,
    because a simulation that should run matters more than the banner."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            mode = forecast_mode.record_decision(
                conn, run_slot(kwargs), decision["max_intensity_mm_hr"], decision["threshold_mm_hr"], standing, gate_open
            )
        finally:
            conn.close()
        print(f"🚦 Forecast mode: {mode}")
    except Exception as error:
        print(f"❌ Could not write forecast_mode: {error}")


@skip_stale_run
def task_check_forecast_rain(**kwargs):
    """Choose the full pipeline when a forecast window from the run's slot reaches the rain threshold, or when
    an earlier run's flood still stands (standing_flood). Only a dry state skips the run."""
    ti = kwargs["ti"]
    intervals = create_simulation.get_rain_forecast(start=run_slot(kwargs))
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
        record_forecast_mode(kwargs, decision, standing=None, gate_open=True)
        return "1_trigger_simulation"

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        standing = standing_flood.read_standing_flood(conn, decision["max_intensity_mm_hr"])
    finally:
        conn.close()
    ti.xcom_push(key="standing_flood", value=standing)
    print(
        f"🌊 Standing flood: {standing['reason']}, {standing['steady_runs_in_a_row']} of "
        f"{standing['steady_runs_to_stop']} steady runs in a row, newest run {standing['newest_run_age_min']} min old"
    )
    record_forecast_mode(kwargs, decision, standing=standing["stands"], gate_open=standing["stands"])
    if standing["stands"]:
        return "1_trigger_simulation"
    print("✅ Dry state: skipping simulation, processing, and upload as a successful DAG run")
    return None


@skip_stale_run
def task_run_simulation(**kwargs):
    ti = kwargs["ti"]
    print("🚀 1. Trigger Simulation...")
    rain_intervals = ti.xcom_pull(task_ids="0_check_forecast_rain", key="rain_intervals")
    slot = run_slot(kwargs)
    hotstart = True
    if COLD_START_AFTER_BREAK:
        previous_slot = slot - timedelta(minutes=create_simulation.CYCLE_MINUTES)
        previous_runs = ti.get_dr_count(
            dag_id=kwargs["dag"].dag_id,
            logical_dates=[previous_slot],
            states=["success", "running"],
        )
        hotstart = hotstart_policy.should_hotstart(previous_runs)
        verdict = "hotstart allowed" if hotstart else "cold start forced"
        print(
            f"🔁 Chain check: {verdict}, {previous_runs} success or running run(s) "
            f"at previous slot {create_simulation.iso_utc(previous_slot)}"
        )
    sim_id, _ = create_simulation.run_forecast_process(
        state_file_path=STATE_FILE,
        rain_intervals=rain_intervals,
        slot_start=slot,
        hotstart=hotstart,
    )
    if not sim_id:
        # By the time this task runs, the rain gate (0_check_forecast_rain)
        # has already routed here specifically because it decided to run —
        # a legitimate dry-cycle skip never reaches this task at all (it
        # skips every downstream task instead). So a falsy sim_id
        # here always means a real 3Di failure, never a correct skip; raising
        # AirflowSkipException made that failure look identical to a
        # dry-cycle skip (both green) in the Airflow UI.
        raise AirflowException("❌ Simulation failed to trigger (see create_simulation logs for cause)")
    ti.xcom_push(key="sim_id", value=sim_id)
    # The same series run_forecast_process sent to 3Di, rebuilt from the same intervals and slot.
    rain_ingested = create_simulation.summarize_rain_values(
        create_simulation.build_rain_values(rain_intervals, start=slot), slot, create_simulation.rain_source()
    )
    ti.xcom_push(key="rain_ingested", value=rain_ingested)
    print(
        f"🌧️ Rain ingested: {rain_ingested['total_mm']:.2f} mm over {rain_ingested['interval_count']} points, "
        f"max {rain_ingested['max_mm_hr']:.2f} mm/h, source {rain_ingested['source']}"
    )


def task_download_result(**kwargs):
    ti = kwargs["ti"]
    sim_id = ti.xcom_pull(task_ids="1_trigger_simulation", key="sim_id")
    print(f"⬇️ 2. Download results for Sim {sim_id}...")
    # 3Di names every result file results_3di.nc, so each simulation gets its own folder: a run
    # that overlaps the previous one must not overwrite the file that run is still reading.
    saved_path = download_result.run_download(sim_id, output_dir=os.path.join(RESULT_DIR, str(sim_id)))
    if not saved_path:
        raise ValueError("❌ Download failed")
    ti.xcom_push(key="nc_path", value=saved_path)


def task_archive_results(**kwargs):
    ti = kwargs["ti"]
    rain_ingested = ti.xcom_pull(task_ids="1_trigger_simulation", key="rain_ingested")
    if not archive_results.is_real_rain(rain_ingested["source"]):
        print(f"🗃️ 2b. Skipping the archive: the rain source is {rain_ingested['source']}, not real rain")
        return
    sim_id = ti.xcom_pull(task_ids="1_trigger_simulation", key="sim_id")
    nc_path = ti.xcom_pull(task_ids="2_download_results", key="nc_path")
    record = archive_results.build_record(
        sim_id,
        create_simulation.iso_utc(run_slot(kwargs)),
        rain_ingested,
        os.getenv("MODEL_ID", "83022"),
        archive_results.read_graph_hash(EDGE_EXPORT_DIR),
    )
    print(f"🗃️ 2b. Archiving results of Sim {sim_id}...")
    archive_results.archive_run(
        sim_id=sim_id,
        nc_path=nc_path,
        archive_dir=ARCHIVE_DIR,
        record=record,
        floor_bytes=int(ARCHIVE_MIN_FREE_GB * 1024**3),
    )


def task_ensure_schema(**kwargs):
    print("🛠️ 0b. Ensuring PostGIS schema (extension, geom_4326, indexes, backfill)...")
    database.create_flood_extent_tables.main()
    database.create_flood_depth_raster_tables.main()
    database.create_graph_edge_table.main()
    database.create_edge_depth_tables.main()
    database.create_flood_run_output_table.main()
    database.create_demo_pin_table.main()
    database.create_forecast_mode_table.main()
    database.create_timescale_tables.main()


@skip_stale_run
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


@skip_stale_run
def task_publish_depth_files(**kwargs):
    """Tell the consumers that this run's depth folder is complete. Task 3 wrote it and task 2b has archived the
    results, so the age-based cleanup of `flood_tiles` cannot take a file the archive still needs."""
    depth_dir, run_ts = depth_run(kwargs["ti"])
    kwargs["outlet_events"][FLOOD_DEPTH_FILES].extra = {"run_ts": run_ts, "depth_dir": depth_dir}
    print(f"📨 3b. Depth files of run {run_ts} are ready: {depth_dir}")
    return {"run_ts": run_ts, "depth_dir": depth_dir}


def mark_forecast_mode_live(kwargs):
    """The run's first step is published, so its PENDING row becomes LIVE. A failure is printed and does not fail 9b."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        try:
            changed = forecast_mode.mark_live(conn, run_slot(kwargs))
        finally:
            conn.close()
        print("🚦 Forecast mode: LIVE" if changed else "🚦 Forecast mode: no PENDING row to move to LIVE")
    except Exception as error:
        print(f"❌ Could not move forecast_mode to LIVE: {error}")


@skip_stale_run
def task_load_depth_raster(**kwargs):
    """Loads every depth_*.tif of this run into flood_depth_raster_tile, reprojected to EPSG:4326, so
    GET /flood/points (Sprint 2) can answer an arbitrary-point depth query with ST_Value instead
    of reading the file from disk. Same run_ts as task 3b and the flood_tiles DAG, so both tables key off the (run,
    valid_time) pair the frontend already selects.

    On success it emits FLOOD_DEPTH_RASTER with the run_ts, which schedules routing_adapter_dag.py.
    """
    depth_dir, run_ts = depth_run(kwargs["ti"])

    print(f"🗺️ 9b. Loading depth rasters into PostGIS: {depth_dir} (run {run_ts})")
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        loaded = raster_load.load_run(conn, depth_dir, run_ts, DEPTH_RASTER_WORK_DIR)
    finally:
        conn.close()
    print(f"✅ Depth rasters loaded: {len(loaded)} timesteps")
    mark_forecast_mode_live(kwargs)
    kwargs["outlet_events"][FLOOD_DEPTH_RASTER].extra = {"run_ts": run_ts}
    return {"run_ts": run_ts, "timesteps": len(loaded)}


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
    schedule="*/15 * * * *",
    start_date=datetime(2026, 2, 5),
    catchup=False,
    # A run can take up to about 15 minutes, so the next slot's run may start while this one
    # finishes. Its first minutes only wait on 3Di, and every run writes to its own folders.
    max_active_runs=2,
    tags=["3di", "flood"],
) as dag:
    t0 = BranchPythonOperator(
        task_id="0_check_forecast_rain",
        python_callable=task_check_forecast_rain,
        pool=POOL_THREEDI_TRIGGER,
    )
    t1 = PythonOperator(
        task_id="1_trigger_simulation",
        python_callable=task_run_simulation,
        pool=POOL_THREEDI_TRIGGER,
    )
    t_ddl = PythonOperator(
        task_id="0b_ensure_schema", python_callable=task_ensure_schema
    )
    t2 = PythonOperator(
        task_id="2_download_results", python_callable=task_download_result
    )
    t2b = PythonOperator(task_id="2b_archive_results", python_callable=task_archive_results)
    # Ends when 2b ends, failed or not, so a full archive drive turns 2b red without stopping 3b_publish_depth_files, which starts the tile build.
    t2c = EmptyOperator(task_id="2c_archive_done", trigger_rule="all_done")
    t3 = PythonOperator(
        task_id="3_calculate_depth",
        python_callable=task_calculate_depth,
        pool=POOL_DEPTH_CALC,
    )
    t3b = PythonOperator(
        task_id="3b_publish_depth_files",
        python_callable=task_publish_depth_files,
        outlets=[FLOOD_DEPTH_FILES],
    )
    t9b = PythonOperator(
        task_id="9b_load_depth_raster",
        python_callable=task_load_depth_raster,
        outlets=[FLOOD_DEPTH_RASTER],
    )

    t0 >> t1 >> t2 >> t3
    t2 >> t2b >> t2c >> t3b
    t3 >> t3b
    t3 >> t9b
    t1 >> t_ddl
    t_ddl >> [t3b, t9b]
