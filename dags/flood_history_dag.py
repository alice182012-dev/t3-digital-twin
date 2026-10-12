"""The per-piece depth history in TimescaleDB, one load per run (US-106, D-032).

`flood_on_roads` of `routing_adapter` emits FLOOD_ROAD_VALUES, and this DAG runs on that event. It copies the run's
rows of flood_road_values into depth_history and the run's moments into history_moment (scripts/flood_history/
load_run.py). prune_flood_road_values keeps the 24 hours before the newest run, so the run is still there when this
DAG reads it. A failure here touches neither the core run nor routing.
"""
from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os

from core_assets import FLOOD_ROAD_VALUES


SCRIPTS_PATH = os.path.join("/opt/airflow", "scripts")

sys.path.append(SCRIPTS_PATH)
sys.path.append(os.path.join(SCRIPTS_PATH, "database"))

try:
    import create_timescale_tables
    from flood_history import load_run
except ImportError as e:
    print(f"❌ Import error: {e}")


def published_runs(kwargs):
    """The runs this DAG run loads, from the `run_ts` in the extra of the FLOOD_ROAD_VALUES events, oldest first.

    Unlike routing_adapter_dag.published_run_ts, every run of folded events is loaded, not only the newest: routing
    needs only the newest run, but a run left out of the history leaves its early moments unknown. The load order does
    not change the result, since the later issued_at wins each moment. A manual run has no triggering event and loads
    the newest run flood_on_roads ever published.
    """
    triggering = kwargs.get("triggering_asset_events") or {}
    events = [event for asset_events in triggering.values() for event in asset_events]
    manual = not events
    if manual:
        events = kwargs["inlet_events"][FLOOD_ROAD_VALUES]
    runs = sorted({event.extra["run_ts"] for event in events if "run_ts" in (event.extra or {})})
    if not runs:
        raise ValueError(f"❌ No {FLOOD_ROAD_VALUES.name} event carries a run_ts")
    if manual:
        runs = runs[-1:]
    print(f"📨 Runs {runs} from the {'newest published event' if manual else 'triggering events'}")
    return runs


def task_load_depth_history(**kwargs):
    """Ensures the TimescaleDB schema, then loads each run of the events into depth_history and history_moment."""
    runs = published_runs(kwargs)

    print("🛠️ Ensuring the TimescaleDB schema")
    create_timescale_tables.main()
    loaded = []
    for run_ts in runs:
        print(f"🗄️ Loading run {run_ts} into depth_history")
        result = load_run.load(run_ts)
        print(f"✅ {result.describe()}")
        loaded.append(
            {
                "run_ts": run_ts,
                "moments_written": len(result.written),
                "moments_skipped": len(result.skipped),
                "rows": len(result.rows),
            }
        )
    return loaded


default_args = {
    "owner": "flood_team",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    "flood_history",
    default_args=default_args,
    description="Per-piece depth history in TimescaleDB for each run routing_adapter writes",
    schedule=[FLOOD_ROAD_VALUES],
    start_date=datetime(2026, 2, 5),
    catchup=False,
    tags=["flood", "history", "timescaledb"],
) as dag:
    PythonOperator(
        task_id="load_depth_history",
        python_callable=task_load_depth_history,
        inlets=[FLOOD_ROAD_VALUES],
    )
