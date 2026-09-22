"""Run/timestep listing for the map's flood layer, backed by `flood_extent_polygon`.

`flood_extent_polygon` is written by scripts/flood_extent/publish.py per (run_ts,
valid_time_utc) — a separate table and pipeline from flood_areas.py's
`flood_road_values`, which the routing engine reads instead. See
artifacts/SW Architecture.md #8 for why the split is intentional: this module backs
GET /flood/runs and GET /flood/timesteps (map display only), never routing.

`run_ts` is already the MinIO tile folder name (e.g. "20260922T133131"), lexically
sortable because it's a fixed-width YYYYMMDDTHHMMSS string. `valid_time_utc` is
stored as UTC but the tile folder names on disk are keyed by the Vietnam-local
depth-file timestamp (scripts/flood_extent/publish.py's `valid_time_utc()` runs
that conversion in reverse), so `list_timesteps` converts back to local time here —
otherwise the `valid_time` this returns wouldn't match the tile URL the frontend
builds from it (floodmap-maps' floodExtentTiles.ts:tileFolderKey).
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
    """Valid times for exactly ONE run, ascending, each paired with that `run`.

    Every dict carries the same `run` (FloodStore.ts invariant I2: a single ordered
    forecast series). run=None or "latest" resolves to latest_run(conn); an empty
    table yields [].
    """
    resolved = run if run and run != "latest" else latest_run(conn)
    if resolved is None:
        return []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT valid_time_utc FROM flood_extent_polygon WHERE run_ts = %(run)s ORDER BY valid_time_utc;",
            {"run": resolved},
        )
        rows = cur.fetchall()
    return [
        {"valid_time": row[0].replace(tzinfo=timezone.utc).astimezone(VIETNAM_TZ).isoformat(), "run": resolved}
        for row in rows
    ]
