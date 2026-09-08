#!/usr/bin/env python3
"""
D1 -- offline ingest of the 8-run forecast-cube fixture through the real
pipeline (extract_geojson_full -> merge_geojson -> mapping_geojson ->
geojson_to_pg), so PostGIS ends up populated by the same code paths
production uses, per the Phase 2 plan's Workstream D1.

Run against a local storage-postgres + minio (see compose.yml); point env
vars at them before running:

  POSTGRES_HOST=localhost POSTGRES_PORT=5433 \
  POSTGRES_DB=minio_custom POSTGRES_USER=minio_custom POSTGRES_PASSWORD=... \
  MINIO_ENDPOINT=http://localhost:9000 MINIO_ACCESS_KEY=... MINIO_SECRET_KEY=... \
  python3 scripts/run_d1_ingest.py
"""
import os
import re
import shutil
import sys
import tempfile

SCRIPTS_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.append(SCRIPTS_PATH)
sys.path.append(os.path.join(SCRIPTS_PATH, "database"))

import mapping.extract_geojson_full as extract_geojson_full
import mapping.merge_geojson as merge_geojson
import mapping.mapping_geojson as mapping_geojson
import mapping.upload_minio as upload_minio
import database.geojson_to_pg as geojson_to_pg
import database.create_geojson_tables as create_geojson_tables

REPO_ROOT = os.path.dirname(SCRIPTS_PATH)
GH_ROOT = os.path.join(os.path.dirname(REPO_ROOT), "grasshopper-routing")
RASTER_ROOT = os.path.join(GH_ROOT, "flood-timeseries")
ROADS_GEOJSON_PATH = os.path.join(GH_ROOT, "toa-do-duong-hanoi.geojson")

RUNDIR_RE = re.compile(r"depth_(\d{8})_(\d{6})_(\d{6})$")


def discover_run_dirs():
    dirs = []
    for name in sorted(os.listdir(RASTER_ROOT)):
        full = os.path.join(RASTER_ROOT, name)
        if os.path.isdir(full) and RUNDIR_RE.match(name):
            dirs.append(full)
    return dirs


def extract_geojson_sequential(input_dir, output_dir):
    """
    Local stand-in for extract_geojson_full.run_extract_geojson().

    That function forks a billiard.Pool per raster after GDAL/PROJ has
    already spun up threads in the parent -- fork()-after-threads is not
    safe on macOS and reliably segfaults there (Airflow's Linux workers
    don't hit this, so the production code is left as-is). Same per-file
    conversion logic (worker_tif_to_geojson), just run sequentially.
    """
    os.makedirs(output_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(input_dir) if f.endswith(".tif"))
    for f in files:
        in_path = os.path.join(input_dir, f)
        out_path = os.path.join(output_dir, f"{os.path.splitext(f)[0]}.geojson")
        result = extract_geojson_full.worker_tif_to_geojson((in_path, out_path))
        print(result)


def ingest_run(run_dir, workdir):
    run_name = os.path.basename(run_dir)
    print(f"\n=== {run_name} ===")

    geojson_dir = os.path.join(workdir, run_name, "geojson")
    final_dir = os.path.join(workdir, run_name, "final")
    os.makedirs(geojson_dir, exist_ok=True)
    os.makedirs(final_dir, exist_ok=True)

    # 1) depth_*.tif -> depth_*.geojson (pixel-box cells, EPSG:4326)
    extract_geojson_sequential(input_dir=run_dir, output_dir=geojson_dir)

    # 2) merge per-timestep geojsons into one wide table (col per valid time),
    #    upload the raw merged grid to MinIO under {run_ts}/flood_{run_ts}.geojson
    run_ts = merge_geojson.get_earliest_depth_timestamp(geojson_dir)
    if not run_ts:
        raise RuntimeError(f"no depth_*.geojson produced for {run_name}")

    merged_path = merge_geojson.run_merge(
        geojson_dir=geojson_dir,
        output_dir=final_dir,
        run_ts=run_ts,
    )
    if not merged_path:
        raise RuntimeError(f"merge failed for {run_name}")

    # 3) map merged flood cells onto road segments -> road_flood_timeseries geojson
    mapping_output_file = os.path.join(
        os.path.dirname(merged_path), "road_flood_timeseries_generated.geojson"
    )
    mapping_geojson.build_road_flood_timeseries_geojson(
        road_path=ROADS_GEOJSON_PATH,
        flood_path=merged_path,
        out_path=mapping_output_file,
    )

    # 4) upload road-mapped file to MinIO under {run_ts}/flood_road_{run_ts}.geojson
    result = upload_minio.run_upload(
        file_path=mapping_output_file,
        geojson_dir_to_clean=geojson_dir,
        delete_local_file_after_upload=True,
        run_ts=run_ts,
    )
    if not result:
        raise RuntimeError(f"minio upload failed for {run_name}")

    # 5) ingest into PostGIS -- same call task_upload_postgres makes in prod
    inserted = geojson_to_pg.upload_geojson_to_db(result["object_name"])
    print(f"-> {run_name}: run_ts={run_ts} inserted={inserted} rows")
    return {"run_name": run_name, "run_ts": run_ts, "object_name": result["object_name"], "inserted": inserted}


def main():
    print("Ensuring schema...")
    create_geojson_tables.main()

    run_dirs = discover_run_dirs()
    print(f"discovered {len(run_dirs)} run directories")

    workdir = tempfile.mkdtemp(prefix="d1_ingest_")
    results = []
    try:
        for run_dir in run_dirs:
            results.append(ingest_run(run_dir, workdir))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    print("\n=== summary ===")
    total = 0
    for r in results:
        print(f"  {r['run_name']}: {r['inserted']} rows -> {r['object_name']}")
        total += r["inserted"]
    print(f"total rows inserted: {total}")


if __name__ == "__main__":
    main()
