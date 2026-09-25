#!/usr/bin/env python3
"""Publish one run's flood-extent tiles to MinIO and the PostGIS audit table.

`flood_extent.py`'s `Pipeline` still does the raster-to-tiles work for one timestep. This module
adds the two things a production, multi-host deployment needs on top of that: tiles land in a
shared MinIO bucket instead of a local folder (the Airflow worker and the frontend run on separate
hosts, so a bind mount can't carry tiles between them), and each dissolved band polygon is also
written to `flood_extent_polygon` as a queryable audit trail.

The S3 key layout mirrors the local-disk layout `flood_extent.build_run_tiles` used to write
directly (`runs/<run_ts>/<timestep_key>/{z}/{x}/{y}.pbf`, `timestep_key` from `stamp_key()`), on
purpose: the frontend's `floodExtentTilesUrl()` builds this same path from the `{run, valid_time}`
pair it already gets from Postgres (`FloodStore.ts`), so switching nginx from `try_files` to a
`proxy_pass` against MinIO needs no frontend change at all.

Library use (what the Airflow DAG does):

    publish_run(depth_dir, run_ts, work_dir, s3, bucket, db_conn=db_conn)
"""

import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import flood_extent

VIETNAM_UTC_OFFSET = timedelta(hours=7)


def valid_time_utc(filename):
    """depth_20260811_014000.tif -> the UTC instant it names (the filename is Vietnam time)."""
    match = flood_extent.DEPTH_FILE.match(Path(filename).name)
    if not match:
        raise flood_extent.FloodExtentError(f"Not a depth_<date>_<time>.tif file: {filename}")
    local = datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S")
    return (local - VIETNAM_UTC_OFFSET).replace(tzinfo=timezone.utc)


def upload_tiles(s3, bucket, tiles_dir, key_prefix):
    """Uploads every .pbf under `tiles_dir`, preserving its {z}/{x}/{y}.pbf layout under `key_prefix`."""
    for tile in Path(tiles_dir).rglob("*.pbf"):
        key = f"{key_prefix}/{tile.relative_to(tiles_dir).as_posix()}"
        s3.upload_file(str(tile), bucket, key, ExtraArgs={"ContentType": "application/x-protobuf"})


def write_step_rows(db_conn, run_ts, valid_time, result):
    """Upserts one `flood_extent_polygon` row per band in `result.polygons_4326`, then the step's
    `flood_extent_step` row, in one transaction: a reader never sees the step as published before
    its polygons. Called only after the step's tiles are uploaded. Safe to retry: each key
    replaces its own row instead of duplicating it."""
    if db_conn is None:
        return
    with db_conn.cursor() as cur:
        for code, wkb in result.polygons_4326.items():
            cur.execute(
                """
                INSERT INTO flood_extent_polygon (run_ts, valid_time_utc, dn_code, area_m2, geom)
                VALUES (%s, %s, %s, %s, ST_SetSRID(ST_GeomFromWKB(%s), 4326))
                ON CONFLICT (run_ts, valid_time_utc, dn_code)
                DO UPDATE SET area_m2 = EXCLUDED.area_m2, geom = EXCLUDED.geom
                """,
                (run_ts, valid_time, code, result.area_by_band[code], wkb),
            )
        cur.execute(
            """
            INSERT INTO flood_extent_step (run_ts, valid_time_utc, is_empty)
            VALUES (%s, %s, %s)
            ON CONFLICT (run_ts, valid_time_utc)
            DO UPDATE SET is_empty = EXCLUDED.is_empty, published_at = NOW()
            """,
            (run_ts, valid_time, result.is_empty),
        )
    db_conn.commit()


def publish_step(depth_file, run_ts, work_dir, s3, bucket, engine_options):
    """Builds and uploads one timestep. Runs in a worker thread, so it never touches `db_conn`
    (a psycopg2 connection isn't safe to use concurrently from multiple threads) — the caller
    writes polygon rows itself, sequentially, from the returned result."""
    timestep_key = flood_extent.stamp_key(depth_file)
    step_dir = Path(work_dir) / run_ts / timestep_key
    try:
        result = flood_extent.build_flood_extent(depth_file, step_dir, **engine_options)
        if not result.is_empty:
            upload_tiles(s3, bucket, step_dir, f"runs/{run_ts}/{timestep_key}")
        return timestep_key, result
    finally:
        shutil.rmtree(step_dir, ignore_errors=True)


def prune_bucket_runs(s3, bucket, keep_runs, always_keep):
    """Deletes every object under old `runs/<run>/` prefixes, keeping the newest `keep_runs`."""
    paginator = s3.get_paginator("list_objects_v2")
    prefixes = []
    for page in paginator.paginate(Bucket=bucket, Prefix="runs/", Delimiter="/"):
        prefixes += [p["Prefix"] for p in page.get("CommonPrefixes", [])]
    runs = sorted((p.removeprefix("runs/").rstrip("/") for p in prefixes), reverse=True)
    for old_run in runs[keep_runs:]:
        if old_run == always_keep:
            continue
        objects = [
            {"Key": obj["Key"]}
            for page in paginator.paginate(Bucket=bucket, Prefix=f"runs/{old_run}/")
            for obj in page.get("Contents", [])
        ]
        for i in range(0, len(objects), 1000):  # DeleteObjects caps at 1000 keys per call
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objects[i:i + 1000]})


def prune_step_rows(db_conn, keep_runs, always_keep):
    """Deletes the `flood_extent_step` rows of every run outside the newest `keep_runs`.

    The map lists steps across runs, so a step row whose tiles `prune_bucket_runs` deleted would
    point the map at a 404. A run with tiles also has step rows, so this never keeps fewer runs
    than the bucket does."""
    if db_conn is None:
        return
    with db_conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM flood_extent_step
            WHERE run_ts <> %(always_keep)s
              AND run_ts NOT IN (
                  SELECT DISTINCT run_ts FROM flood_extent_step ORDER BY run_ts DESC LIMIT %(keep_runs)s
              )
            """,
            {"keep_runs": keep_runs, "always_keep": always_keep},
        )
    db_conn.commit()


def cleanup_old_files(root_dirs, max_age_hours=24):
    """Deletes every top-level child of each root older than `max_age_hours`.

    A directory's age is its newest file's mtime, so a folder still being written by a run in
    progress is never mistaken for stale leftovers. Safe to call on a root that doesn't exist yet.
    """
    cutoff = time.time() - max_age_hours * 3600
    for root in root_dirs:
        root = Path(root)
        if not root.is_dir():
            continue
        for child in root.iterdir():
            newest = max((p.stat().st_mtime for p in child.rglob("*") if p.is_file()), default=child.stat().st_mtime) \
                if child.is_dir() else child.stat().st_mtime
            if newest < cutoff:
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink(missing_ok=True)


def publish_run(depth_dir, run_ts, work_dir, s3, bucket, *, workers=2, db_conn=None,
                 tile_steps=2, keep_runs=8, cleanup_dirs=(), cleanup_max_age_hours=24, **engine_options):
    """Builds the first `tile_steps` depth_*.tif files in `depth_dir`, by time, and publishes their
    tiles, polygon rows, and `flood_extent_step` rows.

    Only the first steps get tiles because the map only ever shows a run's earliest steps as now:
    by the time a later step comes due, a newer run has published it. The rest would cost tiling
    time inside the cycle for nothing.

    Fails loudly (raises) if any timestep fails, without deleting anything already published for
    the timesteps that succeeded — a missing tile 404s and the map treats it as empty, so partial
    per-timestep state is safe. Bucket pruning and the 24h local cleanup only run after every
    timestep in this run succeeds, so a partial failure never prunes still-good older runs.
    """
    depth_dir = Path(depth_dir)
    if not flood_extent.RUN_DIR.match(run_ts):
        raise flood_extent.FloodExtentError(f"run_ts must look like 20260811T014000, got {run_ts!r}")
    if tile_steps < 1:
        raise ValueError(f"tile_steps must be at least 1: {tile_steps}")
    depth_files = sorted(p for p in depth_dir.iterdir() if flood_extent.DEPTH_FILE.match(p.name))
    if not depth_files:
        raise flood_extent.FloodExtentError(f"No depth_*.tif files in {depth_dir}")
    depth_files = depth_files[:tile_steps]

    def build(depth_file):
        return publish_step(depth_file, run_ts, work_dir, s3, bucket, engine_options)

    results, failures = {}, []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for depth_file, future in [(p, pool.submit(build, p)) for p in depth_files]:
            try:
                key, result = future.result()
                results[key] = result
                write_step_rows(db_conn, run_ts, valid_time_utc(depth_file), result)
                print(f"{key}: {result.tile_count} tiles", flush=True)
            except Exception as error:
                if db_conn is not None:
                    db_conn.rollback()
                failures.append(f"{flood_extent.stamp_key(depth_file)}: {error}")
    if failures:
        raise flood_extent.FloodExtentError(
            f"{len(failures)}/{len(depth_files)} timesteps failed: " + "; ".join(failures)
        )

    prune_bucket_runs(s3, bucket, keep_runs, always_keep=run_ts)
    prune_step_rows(db_conn, keep_runs, always_keep=run_ts)
    cleanup_old_files(cleanup_dirs, cleanup_max_age_hours)
    return results
