"""Rebuilds the depth raster tiles of storm runs from their NetCDF files (US-126, D-039).

    python rebuild_tiles.py RUN_TS [RUN_TS ...]    # inside the Airflow worker, e.g. 20261010T041500

For each run it takes the NetCDF from the manifest of the test dataset, runs `calculate_depth` on it, and loads the
depth files with `raster_load.load_run`, the call of task `9b_load_depth_raster`. It writes to the database that
POSTGRES_DB names, so set POSTGRES_DB=minio_custom_test to rebuild into the test database. A run that already has its
8 steps is skipped, and a run with fewer is loaded again, because `load_run` replaces a step before it writes it.

The depth files go to a scratch folder and not to DEPTH_ROOT_DIR, which the age cleanup of `flood_tiles` sweeps, and the
folder of a run is deleted once its tiles are loaded. See artifacts/docs/concepts/test-dataset.md.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Mapping, Sequence

import psycopg2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "dags"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "database"))
sys.path.insert(0, str(ROOT / "scripts" / "flood_extent"))

from core_paths import BASE_PATH, DATA_PATH  # noqa: E402
from db_config import DB_CONFIG  # noqa: E402

STORM_DIR = Path(BASE_PATH) / "data/testdata/storm-2026-10-10"
SCRATCH_DIR = Path(DATA_PATH) / "testdata_rebuild"
STEPS_PER_RUN = 8


def plan_jobs(manifest: Mapping, run_ts_list: Sequence[str], storm_dir: Path) -> list[tuple[str, Path]]:
    """The (run_ts, NetCDF path) of each requested run, in the order requested without repeats.
    Raises when a run is not in the manifest."""
    nc_by_run = {entry["run_ts"]: entry["nc"] for entry in manifest["runs"]}
    unknown = [run_ts for run_ts in run_ts_list if run_ts not in nc_by_run]
    if unknown:
        raise ValueError(f"not in the manifest: {', '.join(unknown)}")
    return [(run_ts, storm_dir / nc_by_run[run_ts]) for run_ts in dict.fromkeys(run_ts_list)]


def loaded_steps(conn, run_ts: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT count(DISTINCT valid_time_utc) FROM flood_depth_raster_tile WHERE run_ts = %s", (run_ts,))
        return cur.fetchone()[0]


def run_count(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT count(DISTINCT run_ts) FROM flood_depth_raster_tile")
        return cur.fetchone()[0]


def rebuild(conn, jobs: Sequence[tuple[str, Path]]) -> None:
    # GDAL and the 3Di libraries exist only in the worker, so the import waits until a run needs them.
    import calculate_depth
    import raster_load

    for run_ts, nc_path in jobs:
        steps = loaded_steps(conn, run_ts)
        if steps == STEPS_PER_RUN:
            print(f"skip {run_ts}: {steps} steps are loaded")
            continue
        # load_run prunes to the newest keep_runs runs when it finishes. The runs of the storm are older than any
        # live run, so the default of 8 would delete the rebuilt runs. Keeping every run now in the table and every
        # run of this batch means a rebuild deletes nothing.
        keep_runs = max(run_count(conn) + len(jobs), 1)
        print(f"rebuild {run_ts} from {nc_path}")
        depth_dir = calculate_depth.run_calculate_depth(
            grid_path=str(Path(DATA_PATH) / "inputs" / "gridadmin.h5"),
            nc_path=str(nc_path),
            dem_path=str(Path(DATA_PATH) / "inputs" / "dem.tif"),
            output_dir=str(SCRATCH_DIR),
        )
        try:
            loaded = raster_load.load_run(conn, depth_dir, run_ts, SCRATCH_DIR / "reprojected", keep_runs=keep_runs)
        finally:
            shutil.rmtree(depth_dir, ignore_errors=True)
        print(f"loaded {run_ts}: {len(loaded)} steps")


def main(argv: Sequence[str]) -> int:
    if not argv:
        print("usage: rebuild_tiles.py RUN_TS [RUN_TS ...]", file=sys.stderr)
        return 2
    manifest = json.loads((STORM_DIR / "manifest.json").read_text())
    jobs = plan_jobs(manifest, argv, STORM_DIR)
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        rebuild(conn, jobs)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
