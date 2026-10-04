"""Copy netcdf_values rows from storage-postgres into the timescaledb hypertable.

Reads the old wide netcdf_values on storage-postgres and writes the narrow
hypertable plus the mesh_elements dimension on timescaledb. The source
connection is opened read-only.

The unit of atomicity is one file_id. Its rows are deleted from the target and
recopied inside a single transaction that commits only at the end, so a crash
mid-file leaves that file_id either fully absent or fully present and a re-run
of a partially completed file_id converges. mesh_elements commits separately,
since adding an element is monotonic.

Usage:
    python backfill_netcdf_values.py --list
    python backfill_netcdf_values.py 241 242
"""

import argparse
import sys
import time

import psycopg2
from psycopg2.extras import execute_values

from db_config import DB_CONFIG, TIMESCALE_DB_CONFIG

MESH_ELEMENT_SQL = """
INSERT INTO mesh_elements (
    model_id,
    mesh_type,
    element_type,
    element_id,
    x,
    y
)
VALUES %s
ON CONFLICT (model_id, mesh_type, element_type, element_id) DO NOTHING;
"""

VALUE_SQL = """
INSERT INTO netcdf_values (
    file_id,
    element_id,
    variable_id,
    timestamp,
    value
)
VALUES %s;
"""


def read_variable_catalog(target):
    with target.cursor() as cur:
        cur.execute("SELECT id, variable_name FROM netcdf_variable_catalog;")
        return {variable_name: variable_id for variable_id, variable_name in cur.fetchall()}


def stream_batches(source, name, sql, params, batch_size):
    with source.cursor(name=name) as cur:
        cur.itersize = batch_size
        cur.execute(sql, params)

        batch = []
        for row in cur:
            batch.append(row)
            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch


def read_source_summary(source, file_id):
    with source.cursor() as cur:
        cur.execute(
            """
            SELECT count(*), min("timestamp" AT TIME ZONE 'UTC')
            FROM netcdf_values
            WHERE file_id = %s;
            """,
            (file_id,),
        )
        return cur.fetchone()


def read_model_id(source, file_id):
    with source.cursor() as cur:
        cur.execute("SELECT model_id FROM netcdf_files WHERE id = %s;", (file_id,))
        row = cur.fetchone()
        return row[0] if row else None


def warn_if_retention_drops(target, file_id, oldest):
    with target.cursor() as cur:
        cur.execute(
            """
            SELECT job_id, (config->>'drop_after')::interval
            FROM timescaledb_information.jobs
            WHERE proc_name = 'policy_retention' AND hypertable_name = 'netcdf_values';
            """
        )
        policy = cur.fetchone()

        if policy is None:
            return

        job_id, drop_after = policy
        cur.execute("SELECT now() - %s;", (drop_after,))
        cutoff = cur.fetchone()[0]

    if oldest >= cutoff:
        return

    print("")
    print("*" * 78)
    print(f"WARNING: file_id {file_id} is older than the netcdf_values retention window.")
    print(f"WARNING:   oldest timestamp to write : {oldest}")
    print(f"WARNING:   retention window          : {drop_after} (job {job_id})")
    print(f"WARNING:   chunks are dropped before : {cutoff}")
    print("WARNING: the retention job will drop these rows again. To suspend it:")
    print(f"WARNING:   SELECT alter_job({job_id}, scheduled => false);")
    print("*" * 78)
    print("")


def copy_mesh_elements(source, target, file_id, model_id, batch_size):
    sql = """
    SELECT DISTINCT mesh_type, element_type, element_id, x, y
    FROM netcdf_values
    WHERE file_id = %s;
    """

    written = 0
    with target.cursor() as cur:
        for batch in stream_batches(source, f"mesh_{file_id}", sql, (file_id,), batch_size):
            execute_values(
                cur,
                MESH_ELEMENT_SQL,
                [(model_id,) + row for row in batch],
            )
            written += len(batch)
    target.commit()

    print(f"  mesh_elements: {written} distinct elements offered", flush=True)


def copy_values(source, target, file_id, catalog, source_rows, batch_size):
    sql = """
    SELECT element_id, variable_name, "timestamp" AT TIME ZONE 'UTC', value
    FROM netcdf_values
    WHERE file_id = %s;
    """

    written = 0
    with target.cursor() as cur:
        cur.execute("DELETE FROM netcdf_values WHERE file_id = %s;", (file_id,))
        print(f"  cleared {cur.rowcount} existing target rows", flush=True)

        for batch in stream_batches(source, f"values_{file_id}", sql, (file_id,), batch_size):
            rows = []
            for element_id, variable_name, timestamp, value in batch:
                if variable_name not in catalog:
                    raise RuntimeError(
                        f"netcdf_variable_catalog has no row for {variable_name}. "
                        "Run scripts/database/create_timescale_tables.py to seed it."
                    )
                rows.append((file_id, element_id, catalog[variable_name], timestamp, value))

            execute_values(cur, VALUE_SQL, rows)
            written += len(rows)
            print(f"  values: {written}/{source_rows}", flush=True)

    target.commit()
    return written


def backfill_file(source, target, file_id, catalog, batch_size):
    started = time.monotonic()

    model_id = read_model_id(source, file_id)
    if model_id is None:
        print(f"file_id {file_id}: skipped, no netcdf_files row", flush=True)
        return 0

    source_rows, oldest = read_source_summary(source, file_id)
    if source_rows == 0:
        print(f"file_id {file_id}: skipped, no rows in the old netcdf_values", flush=True)
        return 0

    print(
        f"file_id {file_id}: {source_rows} source rows, model_id {model_id}, "
        f"oldest {oldest}",
        flush=True,
    )

    warn_if_retention_drops(target, file_id, oldest)

    copy_mesh_elements(source, target, file_id, model_id, batch_size)
    written = copy_values(source, target, file_id, catalog, source_rows, batch_size)

    # Release the source snapshot so a long run does not hold back vacuum of the
    # 56 GB old table. The session is read-only, so there is nothing to undo.
    source.rollback()

    print(
        f"file_id {file_id}: done, {written} rows written in "
        f"{time.monotonic() - started:.1f}s",
        flush=True,
    )
    return written


def list_files(source, target):
    with source.cursor() as cur:
        cur.execute(
            "SELECT file_id, count(*) FROM netcdf_values GROUP BY file_id ORDER BY file_id;"
        )
        source_counts = cur.fetchall()

    with target.cursor() as cur:
        cur.execute("SELECT file_id, count(*) FROM netcdf_values GROUP BY file_id;")
        target_counts = dict(cur.fetchall())

    print(f"{'file_id':>8} {'source_rows':>12} {'target_rows':>12}  state")
    for file_id, source_rows in source_counts:
        target_rows = target_counts.get(file_id, 0)
        if target_rows == source_rows:
            state = "complete"
        elif target_rows == 0:
            state = "absent"
        else:
            state = "partial"
        print(f"{file_id:>8} {source_rows:>12} {target_rows:>12}  {state}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file_ids", nargs="*", type=int, help="file_ids to copy")
    parser.add_argument(
        "--list",
        action="store_true",
        help="print every file_id in the old table with its row count and copy state",
    )
    parser.add_argument("--batch-size", type=int, default=50000)
    args = parser.parse_args(argv)

    if not args.list and not args.file_ids:
        parser.error("give at least one file_id, or --list")

    source = psycopg2.connect(**DB_CONFIG)
    source.set_session(readonly=True)
    target = psycopg2.connect(**TIMESCALE_DB_CONFIG)

    try:
        if args.list:
            list_files(source, target)
            return 0

        catalog = read_variable_catalog(target)
        started = time.monotonic()
        total = 0

        for file_id in args.file_ids:
            total += backfill_file(source, target, file_id, catalog, args.batch_size)

        print(
            f"TOTAL: {total} rows written across {len(args.file_ids)} file_ids in "
            f"{time.monotonic() - started:.1f}s",
            flush=True,
        )
        return 0
    finally:
        source.close()
        target.close()


if __name__ == "__main__":
    sys.exit(main())
