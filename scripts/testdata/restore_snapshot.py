"""Restores the snapshot of the storm test dataset into two test databases (US-125, D-039).

    python restore_snapshot.py            # inside the Airflow worker, where the data folder is mounted

It creates `minio_custom_test` in `storage-postgres` and `flood_metrics_test` in `timescaledb` when they do not exist,
runs the DDL of scripts/database/ against them, and loads each CSV of `snapshot/` in the order of the foreign keys.
A run empties the restored tables first and loads them in one transaction, so a second run gives the same rows and a
failed run leaves the previous rows. The script refuses to load a database whose name does not end in `_test`, and it
reads the row counts of the production tables before and after, so a restore that touched them is reported.

The names come from TEST_POSTGRES_DB and TEST_TIMESCALE_DB. Pipeline code under test runs with POSTGRES_DB and
TIMESCALE_DB set to those names. See artifacts/docs/concepts/test-dataset.md.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import psycopg2
from psycopg2 import sql

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "database"))

import create_edge_depth_tables  # noqa: E402
import create_flood_depth_raster_tables  # noqa: E402
import create_flood_extent_tables  # noqa: E402
import create_flood_metrics_tables  # noqa: E402
import create_flood_road_tables  # noqa: E402
import create_flood_run_output_table  # noqa: E402
import create_graph_edge_table  # noqa: E402
import create_road_segment_table  # noqa: E402
import create_timescale_tables  # noqa: E402
from db_config import DB_CONFIG, TIMESCALE_DB_CONFIG  # noqa: E402

DEFAULT_SNAPSHOT_DIR = "/opt/airflow/data/testdata/storm-2026-10-10/snapshot"
TEST_SUFFIX = "_test"

POSTGIS_DDL = (
    create_flood_road_tables.SQL,
    create_flood_extent_tables.SQL,
    create_flood_depth_raster_tables.SQL,
    create_road_segment_table.SQL,
    create_graph_edge_table.SQL,
    create_flood_metrics_tables.SQL,
    create_flood_run_output_table.SQL,
    create_edge_depth_tables.SQL,
)

# A table comes after the tables it references. flood_road_values.file_id references flood_road_file.id.
RESTORE_ORDER = (
    "graph_edge_export",
    "graph_edge",
    "road_segment",
    "flood_road_file",
    "flood_road_values",
    "flood_extent_step",
    "flood_extent_polygon",
    "flood_segment_metrics",
)

_HASH_CHUNK = 1 << 20


@dataclass(frozen=True)
class SnapshotFile:
    table: str
    path: Path
    columns: tuple[str, ...]
    rows: int
    sha256: str


def check_test_database(name: str, production: str) -> None:
    """Raises unless `name` is a test database that differs from the production one."""
    if not name.endswith(TEST_SUFFIX):
        raise ValueError(f"{name!r} does not end in {TEST_SUFFIX!r}, so it is not a test database")
    if name == production:
        raise ValueError(f"{name!r} is the production database")


def read_manifest(snapshot_dir: Path) -> list[SnapshotFile]:
    """The files to load, in RESTORE_ORDER. Raises when the manifest lacks a table of the order or holds another."""
    manifest = json.loads((snapshot_dir / "MANIFEST.json").read_text())
    by_table = {
        entry["table"]: SnapshotFile(
            entry["table"],
            snapshot_dir.parent / entry["file"],
            tuple(entry["columns"]),
            entry["rows"],
            entry["sha256"],
        )
        for entry in manifest["tables"]
    }
    if set(by_table) != set(RESTORE_ORDER):
        raise ValueError(f"the manifest holds {sorted(by_table)}, the restore order expects {sorted(RESTORE_ORDER)}")
    return [by_table[table] for table in RESTORE_ORDER]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_files(files: Iterable[SnapshotFile]) -> None:
    for file in files:
        if sha256_of(file.path) != file.sha256:
            raise ValueError(f"{file.path} does not match the checksum in the manifest")


def table_counts(conn, tables: Sequence[str]) -> dict[str, int]:
    counts = {}
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table)))
            counts[table] = cur.fetchone()[0]
    return counts


def ensure_database(admin_config: dict, name: str, production: str) -> None:
    """Creates the database `name` when it does not exist. Connects to the production database for the CREATE."""
    check_test_database(name, production)
    conn = psycopg2.connect(**admin_config)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,))
            if cur.fetchone() is None:
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    finally:
        conn.close()


def create_schema(conn, ddl: Iterable[str]) -> None:
    with conn.cursor() as cur:
        for statement in ddl:
            cur.execute(statement)
    conn.commit()


def load_snapshot(conn, files: Sequence[SnapshotFile]) -> dict[str, int]:
    """Empties the tables of `files` and loads each CSV, in one transaction. Returns the row count of each table."""
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL("TRUNCATE {}").format(sql.SQL(", ").join(sql.Identifier(file.table) for file in files))
        )
        for file in files:
            columns = sql.SQL(", ").join(sql.Identifier(column) for column in file.columns)
            statement = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true)").format(
                sql.Identifier(file.table), columns
            )
            with gzip.open(file.path, "rt", encoding="utf-8", newline="") as stream:
                cur.copy_expert(statement, stream, size=_HASH_CHUNK)
            if "id" in file.columns:
                cur.execute(
                    sql.SQL(
                        "SELECT setval(pg_get_serial_sequence(%s, 'id'), max(id)) FROM {} HAVING count(*) > 0"
                    ).format(sql.Identifier(file.table)),
                    (file.table,),
                )
    conn.commit()
    return table_counts(conn, [file.table for file in files])


def check_counts(files: Sequence[SnapshotFile], counts: dict[str, int]) -> list[str]:
    return [
        f"{file.table}: {counts[file.table]} rows, the manifest has {file.rows}"
        for file in files
        if counts[file.table] != file.rows
    ]


def restore(snapshot_dir: Path, postgis_name: str, timescale_name: str) -> int:
    postgis_production, timescale_production = DB_CONFIG["database"], TIMESCALE_DB_CONFIG["database"]
    check_test_database(postgis_name, postgis_production)
    check_test_database(timescale_name, timescale_production)

    files = read_manifest(snapshot_dir)
    tables = [file.table for file in files]
    print(f"Verifying {len(files)} files against the manifest")
    verify_files(files)

    with psycopg2.connect(**DB_CONFIG) as production:
        before = table_counts(production, tables)

    ensure_database(DB_CONFIG, postgis_name, postgis_production)
    ensure_database(TIMESCALE_DB_CONFIG, timescale_name, timescale_production)

    test_config = {**DB_CONFIG, "database": postgis_name}
    conn = psycopg2.connect(**test_config)
    try:
        create_schema(conn, POSTGIS_DDL)
        counts = load_snapshot(conn, files)
        with conn.cursor() as cur:
            cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            size = cur.fetchone()[0]
    finally:
        conn.close()
    print(f"{postgis_name}: {size}")
    for table in tables:
        print(f"  {table}: {counts[table]}")

    timescale = psycopg2.connect(**{**TIMESCALE_DB_CONFIG, "database": timescale_name})
    try:
        create_schema(timescale, [create_timescale_tables.SQL])
    finally:
        timescale.close()
    print(f"{timescale_name}: schema ready")

    with psycopg2.connect(**DB_CONFIG) as production:
        after = table_counts(production, tables)

    problems = check_counts(files, counts)
    if before != after:
        problems.append(f"the production counts changed: {before} then {after}")
    for problem in problems:
        print(f"ERROR {problem}", file=sys.stderr)
    if not problems:
        print("ok: every table has the manifest's row count, and the production counts did not change")
    return 1 if problems else 0


def main() -> int:
    snapshot_dir = Path(os.getenv("TESTDATA_SNAPSHOT_DIR", DEFAULT_SNAPSHOT_DIR))
    return restore(
        snapshot_dir,
        os.getenv("TEST_POSTGRES_DB", "minio_custom_test"),
        os.getenv("TEST_TIMESCALE_DB", "flood_metrics_test"),
    )


if __name__ == "__main__":
    raise SystemExit(main())
