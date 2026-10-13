"""Runs the database test suites on the Mac against the project's own servers (US-128, D-039).

    python3 scripts/testdata/run_db_tests.py [--only FOLDER] [--dry-run]

It opens an SSH tunnel to the server, creates one fresh scratch database in `storage-postgres` and one in
`timescaledb` (names end in `_test`), points FLOOD_TEST_DSN, EDGE_DEPTH_TEST_DSN and FLOOD_TEST_TIMESCALE_DSN at them,
runs each suite folder with pytest, prints one table of counts, and drops the scratch databases. Many suites create and
drop tables in `public`, so they never touch `minio_custom_test` or `flood_metrics_test`. The script counts the rows of
the restored tables of those two databases before and after, and exits 1 when a suite fails or errors or a count differs.

The user and the password are read from the worker container at run time and live in memory only.
RESTORE_TEST_DSN stays unset: test_restore_snapshot.py needs the snapshot folder, which exists only in the worker.
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence
from urllib.parse import quote

import psycopg2
from psycopg2 import sql

sys.path.insert(0, str(Path(__file__).resolve().parent))

from restore_snapshot import RESTORE_ORDER, check_test_database  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]

SSH_TARGET = "tecotec@100.67.84.55"
REMOTE_POSTGIS_PORT = 5433
REMOTE_TIMESCALE_PORT = 5434
DOCKER = ("docker", "--context=remote-server")
WORKER = "airflow_new-airflow-worker-1"
WORKER_VARIABLES = (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "TIMESCALE_USER",
    "TIMESCALE_PASSWORD",
    "TIMESCALE_DB",
)

DATASET_POSTGIS_DB = os.getenv("TEST_POSTGRES_DB", "minio_custom_test")
DATASET_TIMESCALE_DB = os.getenv("TEST_TIMESCALE_DB", "flood_metrics_test")

SUITES = {
    "scripts/backend_soak": ("scripts/backend_soak",),
    "scripts/database": ("scripts/database",),
    "scripts/edge_depth": ("scripts/edge_depth",),
    "scripts/flood_extent": ("scripts/flood_extent",),
    "scripts/flood_history": ("scripts/flood_history",),
    "scripts/flood_metrics": ("scripts/flood_metrics",),
    "scripts/testdata": ("scripts/testdata",),
    "scripts": ("scripts/test_*.py",),
    "floodmap/graphhopper-flood-road/backend": ("floodmap/graphhopper-flood-road/backend",),
    "analysis-service": ("analysis-service",),
    "test": ("test",),
}

TUNNEL_WAIT_SECONDS = 20
TAIL_LINES = 15


@dataclass(frozen=True)
class Counts:
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0

    @property
    def broken(self) -> bool:
        return self.failed > 0 or self.errors > 0


def scratch_names(token: str) -> tuple[str, str]:
    """The names of the scratch databases in storage-postgres and in timescaledb."""
    return f"us128_{token}_pg_test", f"us128_{token}_ts_test"


def check_scratch_name(name: str, admin_db: str, dataset_dbs: Sequence[str]) -> None:
    """Raises unless `name` may be created and dropped: it ends in `_test` and is neither the database the script
    connects through nor a dataset database."""
    check_test_database(name, admin_db)
    if name in dataset_dbs:
        raise ValueError(f"{name!r} is a dataset database")


def build_dsn(user: str, password: str, host: str, port: int, database: str) -> str:
    return f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}/{database}"


_SUMMARY_PART = re.compile(r"(\d+) (passed|failed|errors?|skipped)")
_SUMMARY_LINE = re.compile(r"\d+ (passed|failed|errors?|skipped|deselected|xfailed|xpassed|warnings?).* in [\d.]+s")
_PYTEST_OK_EXIT_CODES = (0, 1, 5)


def parse_summary(output: str) -> Counts | None:
    """The counts of pytest's last summary line, or None when the output has none."""
    for line in reversed(output.splitlines()):
        if _SUMMARY_LINE.search(line):
            found = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
            for number, word in _SUMMARY_PART.findall(line):
                found[word.rstrip("s") if word.startswith("error") else word] += int(number)
            return Counts(found["passed"], found["failed"], found["error"], found["skipped"])
    return None


def summarize(returncode: int, output: str) -> Counts:
    """The counts of one pytest run. A run that gave no summary, or that exited with a code pytest reserves for a
    crash or a usage error, counts as one error, so it cannot pass unseen."""
    counts = parse_summary(output)
    if counts is None:
        counts = Counts(errors=1) if returncode != 5 else Counts()
    if returncode not in _PYTEST_OK_EXIT_CODES and not counts.broken:
        counts = Counts(counts.passed, counts.failed, counts.errors + 1, counts.skipped)
    return counts


DatasetCounts = Mapping[str, Mapping[str, "int | None"]]


def compare_counts(before: DatasetCounts, after: DatasetCounts) -> list[str]:
    """One line per table whose count differs. Empty when the dataset is unchanged."""
    differences = []
    for database in before:
        for table, count in before[database].items():
            if after[database][table] != count:
                differences.append(f"{database}.{table}: {count} before, {after[database][table]} after")
    return differences


def format_suite_table(results: Sequence[tuple[str, Counts]]) -> str:
    rows = [("folder", "passed", "failed", "errors", "skipped")]
    rows += [(name, *(str(n) for n in (c.passed, c.failed, c.errors, c.skipped))) for name, c in results]
    rows.append(
        (
            "total",
            *(str(sum(getattr(c, field) for _, c in results)) for field in ("passed", "failed", "errors", "skipped")),
        )
    )
    widths = [max(len(row[i]) for row in rows) for i in range(5)]
    lines = ["  ".join(cell.ljust(width) if i == 0 else cell.rjust(width) for i, (cell, width) in enumerate(zip(row, widths))) for row in rows]
    lines.insert(1, "  ".join("-" * width for width in widths))
    lines.insert(-1, lines[1])
    return "\n".join(lines)


def format_dataset_counts(before: DatasetCounts, after: DatasetCounts) -> str:
    rows = [("table", "before", "after")]
    for database in before:
        for table, count in before[database].items():
            rows.append((f"{database}.{table}", _cell(count), _cell(after[database][table])))
    width = max(len(row[0]) for row in rows)
    return "\n".join(f"{table.ljust(width)}  {b:>12}  {a:>12}" for table, b, a in rows)


def _cell(count: int | None) -> str:
    return "absent" if count is None else str(count)


def scrub(text: str, secrets_: Sequence[str]) -> str:
    for secret in secrets_:
        if secret:
            text = text.replace(secret, "***").replace(quote(secret, safe=""), "***")
    return text


def tunnel_command(local_postgis: int, local_timescale: int) -> list[str]:
    return [
        "ssh",
        "-N",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "BatchMode=yes",
        "-L", f"{local_postgis}:127.0.0.1:{REMOTE_POSTGIS_PORT}",
        "-L", f"{local_timescale}:127.0.0.1:{REMOTE_TIMESCALE_PORT}",
        SSH_TARGET,
    ]


def credentials_command() -> list[str]:
    return [*DOCKER, "exec", WORKER, "printenv", *WORKER_VARIABLES]


def suite_paths(name: str) -> list[str]:
    """The pytest arguments of a suite. The top-level scripts suite lists its own files, not its subfolders."""
    paths = []
    for pattern in SUITES[name]:
        if "*" in pattern:
            paths += sorted(str(p.relative_to(REPO_ROOT)) for p in REPO_ROOT.glob(pattern))
        else:
            paths.append(pattern)
    return paths


def pytest_command(name: str) -> list[str]:
    return [sys.executable, "-m", "pytest", "-q", *suite_paths(name)]


def selected_suites(only: str | None) -> list[str]:
    return [only] if only else list(SUITES)


def dry_run_plan(token: str, only: str | None) -> str:
    pg, ts = scratch_names(token)
    lines = [
        "Dry run. Nothing connects.",
        f"scratch PostGIS database:      {pg} (extensions postgis, postgis_raster)",
        f"scratch TimescaleDB database:  {ts} (extension timescaledb)",
        f"dataset databases (counted, never written): {DATASET_POSTGIS_DB}, {DATASET_TIMESCALE_DB}",
        f"counted tables: {', '.join(RESTORE_ORDER)}",
        f"credentials: {' '.join(credentials_command())}",
        f"tunnel: {' '.join(tunnel_command(0, 0))}",
        "  (the local ports 0 stand for two free ports chosen at run time)",
        "env: FLOOD_TEST_DSN and EDGE_DEPTH_TEST_DSN -> scratch PostGIS, FLOOD_TEST_TIMESCALE_DSN -> scratch TimescaleDB",
        "RESTORE_TEST_DSN stays unset, so the restore test skips (it needs the snapshot folder of the worker)",
        "suites:",
    ]
    lines += [f"  {name}: {' '.join(pytest_command(name))}" for name in selected_suites(only)]
    return "\n".join(lines)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_port(port: int, tunnel: subprocess.Popen) -> None:
    deadline = time.monotonic() + TUNNEL_WAIT_SECONDS
    while time.monotonic() < deadline:
        if tunnel.poll() is not None:
            raise RuntimeError(f"the SSH tunnel exited with code {tunnel.returncode}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.3)
    raise RuntimeError(f"port {port} did not accept a connection within {TUNNEL_WAIT_SECONDS} s")


def read_worker_environment() -> dict[str, str]:
    result = subprocess.run(credentials_command(), capture_output=True, text=True)
    values = result.stdout.splitlines()
    if result.returncode != 0 or len(values) != len(WORKER_VARIABLES):
        raise RuntimeError(f"could not read {', '.join(WORKER_VARIABLES)} from {WORKER}: {result.stderr.strip()}")
    return dict(zip(WORKER_VARIABLES, values))


def connect(user: str, password: str, port: int, database: str):
    return psycopg2.connect(build_dsn(user, password, "127.0.0.1", port, database))


def count_dataset(user: str, password: str, port: int, database: str) -> dict[str, int | None]:
    """The row count of each RESTORE_ORDER table, None for a table the database lacks. Read-only."""
    conn = connect(user, password, port, database)
    conn.set_session(readonly=True)
    try:
        counts: dict[str, int | None] = {}
        with conn.cursor() as cur:
            for table in RESTORE_ORDER:
                cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
                if cur.fetchone()[0] is None:
                    counts[table] = None
                    continue
                cur.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table)))
                counts[table] = cur.fetchone()[0]
        return counts
    finally:
        conn.close()


def create_scratch(user: str, password: str, port: int, admin_db: str, name: str, extensions: Sequence[str]) -> None:
    conn = connect(user, password, port, admin_db)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    finally:
        conn.close()
    conn = connect(user, password, port, name)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for extension in extensions:
                cur.execute(sql.SQL("CREATE EXTENSION IF NOT EXISTS {}").format(sql.Identifier(extension)))
    finally:
        conn.close()


def drop_scratch(user: str, password: str, port: int, admin_db: str, name: str) -> None:
    conn = connect(user, password, port, admin_db)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                (name,),
            )
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name)))
    finally:
        conn.close()


def run_suite(name: str, env: Mapping[str, str], secrets_: Sequence[str]) -> Counts:
    result = subprocess.run(pytest_command(name), cwd=REPO_ROOT, env=dict(env), capture_output=True, text=True)
    output = result.stdout + result.stderr
    counts = summarize(result.returncode, output)
    if counts.broken:
        tail = "\n".join(output.splitlines()[-TAIL_LINES:])
        print(f"--- tail of {name} ---\n{scrub(tail, secrets_)}\n", flush=True)
    return counts


def _raise_interrupt(signum, frame):
    raise KeyboardInterrupt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--only", choices=list(SUITES), help="run one suite folder")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and connect to nothing")
    args = parser.parse_args(argv)

    token = secrets.token_hex(4)
    if args.dry_run:
        print(dry_run_plan(token, args.only))
        return 0

    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, _raise_interrupt)

    tunnel = None
    created: list[tuple[int, str, str]] = []
    worker_env: dict[str, str] = {}
    exit_code = 1
    try:
        worker_env = read_worker_environment()
        pg_user, pg_password = worker_env["POSTGRES_USER"], worker_env["POSTGRES_PASSWORD"]
        ts_user, ts_password = worker_env["TIMESCALE_USER"], worker_env["TIMESCALE_PASSWORD"]
        pg_admin, ts_admin = worker_env["POSTGRES_DB"], worker_env["TIMESCALE_DB"]
        pg_name, ts_name = scratch_names(token)
        for name, admin in ((pg_name, pg_admin), (ts_name, ts_admin)):
            check_scratch_name(name, admin, (DATASET_POSTGIS_DB, DATASET_TIMESCALE_DB))

        pg_port, ts_port = free_port(), free_port()
        tunnel = subprocess.Popen(tunnel_command(pg_port, ts_port))
        wait_for_port(pg_port, tunnel)
        wait_for_port(ts_port, tunnel)

        def dataset_counts() -> dict:
            return {
                DATASET_POSTGIS_DB: count_dataset(pg_user, pg_password, pg_port, DATASET_POSTGIS_DB),
                DATASET_TIMESCALE_DB: count_dataset(ts_user, ts_password, ts_port, DATASET_TIMESCALE_DB),
            }

        before = dataset_counts()

        created.append((pg_port, pg_name, "pg"))
        create_scratch(pg_user, pg_password, pg_port, pg_admin, pg_name, ("postgis", "postgis_raster"))
        created.append((ts_port, ts_name, "ts"))
        create_scratch(ts_user, ts_password, ts_port, ts_admin, ts_name, ("timescaledb",))

        pg_dsn = build_dsn(pg_user, pg_password, "127.0.0.1", pg_port, pg_name)
        ts_dsn = build_dsn(ts_user, ts_password, "127.0.0.1", ts_port, ts_name)
        env = {k: v for k, v in os.environ.items() if k != "RESTORE_TEST_DSN"}
        env.update(FLOOD_TEST_DSN=pg_dsn, EDGE_DEPTH_TEST_DSN=pg_dsn, FLOOD_TEST_TIMESCALE_DSN=ts_dsn)
        secrets_ = (pg_password, ts_password)

        results = []
        for name in selected_suites(args.only):
            print(f"running {name}", flush=True)
            results.append((name, run_suite(name, env, secrets_)))

        after = dataset_counts()
        differences = compare_counts(before, after)

        print()
        print(format_suite_table(results))
        print("\nRESTORE_TEST_DSN is unset: test_restore_snapshot.py stays skipped, it needs the snapshot folder of the worker.")
        print("\nDataset row counts (restored tables only):")
        print(format_dataset_counts(before, after))
        print("\nDataset unchanged." if not differences else "\nDATASET CHANGED:\n" + "\n".join(differences))
        exit_code = 1 if differences or any(c.broken for _, c in results) else 0
    except Exception as error:
        print(f"error: {scrub(str(error), [worker_env.get(k, '') for k in ('POSTGRES_PASSWORD', 'TIMESCALE_PASSWORD')])}", file=sys.stderr)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        for port, name, kind in created:
            user, password, admin = (
                (worker_env["POSTGRES_USER"], worker_env["POSTGRES_PASSWORD"], worker_env["POSTGRES_DB"])
                if kind == "pg"
                else (worker_env["TIMESCALE_USER"], worker_env["TIMESCALE_PASSWORD"], worker_env["TIMESCALE_DB"])
            )
            try:
                drop_scratch(user, password, port, admin, name)
                print(f"dropped {name}")
            except Exception as error:
                print(f"could not drop {name}, drop it by hand: {scrub(str(error), [password])}", file=sys.stderr)
                exit_code = 1
        if tunnel is not None:
            tunnel.terminate()
            tunnel.wait()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
