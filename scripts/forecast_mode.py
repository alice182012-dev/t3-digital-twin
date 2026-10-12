"""The forecast mode of the flood map, written once per rain gate decision (US-111, D-030).

LIVE: the gate is open (rain above the threshold, or a flood stands) and a step of a run is published.
PENDING: the gate is open and no step has been published lately, so the simulation is still running.
DEMO: the gate is closed, so there is no flood to show.

Task 0_check_forecast_rain writes the row, and task 9b_load_depth_raster moves it from PENDING to LIVE once the run's
depth rasters are published. A step counts as published lately when flood_run_output holds a depth_raster row younger
than MAX_NEWEST_AGE, the age at which standing_flood ends a chain of runs.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from standing_flood import MAX_NEWEST_AGE

sys.path.insert(0, str(Path(__file__).resolve().parent / "database"))
import create_forecast_mode_table  # noqa: E402

LIVE, PENDING, DEMO = "LIVE", "PENDING", "DEMO"
# The rows of the last week stay, enough to see how the mode changed.
KEEP = "7 days"

_PUBLISHED_RECENTLY_SQL = """
SELECT EXISTS (
    SELECT 1 FROM flood_run_output
    WHERE output = 'depth_raster' AND published_at > LOCALTIMESTAMP - %(age)s::interval
)
"""

_UPSERT_SQL = """
INSERT INTO forecast_mode (slot, rain_peak_mm_hr, gate_mm_hr, standing_flood, mode)
VALUES (%(slot)s, %(rain_peak)s, %(gate)s, %(standing)s, %(mode)s)
ON CONFLICT (slot) DO UPDATE SET
    decided_at = NOW(), rain_peak_mm_hr = EXCLUDED.rain_peak_mm_hr, gate_mm_hr = EXCLUDED.gate_mm_hr,
    standing_flood = EXCLUDED.standing_flood, mode = EXCLUDED.mode
"""


def decide_mode(gate_open: bool, step_published_recently: bool) -> str:
    if not gate_open:
        return DEMO
    return LIVE if step_published_recently else PENDING


def slot_utc(slot: datetime) -> datetime:
    """The slot of a DAG run as the table keeps it: UTC without an offset."""
    return slot.astimezone(timezone.utc).replace(tzinfo=None)


def record_decision(conn, slot: datetime, rain_peak_mm_hr: float, gate_mm_hr: float, standing: bool | None, gate_open: bool) -> str:
    """Writes the decision of one run in one transaction and returns its mode. The table is created here too, because
    a dry state ends the run before 0b_ensure_schema."""
    with conn, conn.cursor() as cur:
        cur.execute(create_forecast_mode_table.SQL)
        cur.execute(_PUBLISHED_RECENTLY_SQL, {"age": MAX_NEWEST_AGE})
        mode = decide_mode(gate_open, cur.fetchone()[0])
        cur.execute(
            _UPSERT_SQL,
            {"slot": slot_utc(slot), "rain_peak": rain_peak_mm_hr, "gate": gate_mm_hr, "standing": standing, "mode": mode},
        )
        cur.execute("DELETE FROM forecast_mode WHERE slot < LOCALTIMESTAMP - %(keep)s::interval", {"keep": KEEP})
    return mode


def mark_live(conn, slot: datetime) -> bool:
    """Moves the run's PENDING row to LIVE. Returns whether it changed one."""
    with conn, conn.cursor() as cur:
        cur.execute("UPDATE forecast_mode SET mode = 'LIVE' WHERE slot = %s AND mode = 'PENDING'", (slot_utc(slot),))
        return cur.rowcount == 1
