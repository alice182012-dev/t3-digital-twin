"""Run/timestep listing for the map's flood layer, backed by `flood_extent_polygon` and
`flood_extent_step`.

Both tables are written by scripts/flood_extent/publish.py per (run_ts, valid_time_utc), a
separate table and pipeline from flood_areas.py's `flood_road_values`, which the routing engine
reads instead. See artifacts/raw/T3-Digital-Twin_Architecture.md section 4.2 for why the split is intentional: this
module backs GET /flood/runs and GET /flood/timesteps (map display only), never routing.

`list_timesteps` reads `flood_extent_step`, not `flood_extent_polygon`: a step row exists only
once the step's tiles and polygons are fully published, and a dry step has a step row but no
polygon rows. Runs on the 15-minute cycle overlap, so the default listing takes each valid time
from the newest run that published it instead of following one run.

`run_ts` is already the MinIO tile folder name (e.g. "20260922T133131"), lexically
sortable because it's a fixed-width YYYYMMDDTHHMMSS string, so `max(run_ts)` is the newest run.
`valid_time_utc` is stored as UTC but the tile folder names are keyed by the Vietnam-local
depth-file timestamp (scripts/flood_extent/publish.py's `valid_time_utc()` runs that conversion
in reverse), so `list_timesteps` converts back to local time here; otherwise the `valid_time`
it returns wouldn't match the tile URL the frontend builds from it (floodmap-maps'
floodExtentTiles.ts:tileFolderKey).
"""
from __future__ import annotations

from datetime import timedelta, timezone

VIETNAM_TZ = timezone(timedelta(hours=7))


def list_runs(conn) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT run_ts FROM flood_extent_polygon ORDER BY run_ts DESC;")
        return [row[0] for row in cur.fetchall()]


def latest_run(conn) -> str | None:
    """The newest flood-extent run, or None when the table is empty."""
    with conn.cursor() as cur:
        cur.execute("SELECT max(run_ts) FROM flood_extent_polygon;")
        row = cur.fetchone()
    return row[0] if row and row[0] is not None else None


def list_timesteps(conn, run: str | None = None) -> list[dict[str, str]]:
    """Published valid times, ascending, each paired with the run whose tile to show.

    run=None or "latest" pairs each valid time with the newest run that published it. An
    explicit run lists only that run's steps. Dry steps stay in the list: a dry step is a real
    "no flooding at this time", not a gap to fill from an older run.
    """
    with conn.cursor() as cur:
        if run and run != "latest":
            cur.execute(
                "SELECT valid_time_utc, run_ts FROM flood_extent_step WHERE run_ts = %(run)s ORDER BY valid_time_utc;",
                {"run": run},
            )
        else:
            cur.execute(
                "SELECT valid_time_utc, max(run_ts) FROM flood_extent_step GROUP BY valid_time_utc ORDER BY valid_time_utc;"
            )
        rows = cur.fetchall()
    return [
        {"valid_time": valid_time.replace(tzinfo=timezone.utc).astimezone(VIETNAM_TZ).isoformat(), "run": run_ts}
        for valid_time, run_ts in rows
    ]
