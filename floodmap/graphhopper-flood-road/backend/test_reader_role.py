"""The backend's database connection can read the contract tables and write nothing (US-072).

    python test_reader_role.py

Live. Connects with db.DB_CONFIG, the connection the backend itself uses, and skips when
POSTGRES_PASSWORD is not set. Every statement runs in its own transaction and is rolled back.
It refuses to try a write when the role holds any write privilege on a contract table, so a run
with the writer's credentials fails before it touches a table.
"""

from __future__ import annotations

import os

from test_core_contract import CONTRACT_TABLES

OUTSIDE_THE_CONTRACT = "road_segment"
# Inside the model border, see .claude/CLAUDE.md.
LON, LAT = 105.75, 21.0


def _run(conn, sql: str, params: tuple = ()):
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall() if cur.description else None
    finally:
        conn.rollback()


def _refused(conn, sql: str) -> None:
    from psycopg2.errors import InsufficientPrivilege

    try:
        _run(conn, sql)
    except InsufficientPrivilege:
        return
    raise AssertionError(f"{sql!r} was not refused with a permission error")


def test_role_holds_no_write_privilege(conn) -> None:
    rows = _run(conn, "SELECT current_user, rolsuper FROM pg_roles WHERE rolname = current_user")
    user, superuser = rows[0]
    assert not superuser, f"{user} is a superuser"
    for table in sorted(CONTRACT_TABLES):
        rows = _run(
            conn,
            "SELECT has_table_privilege(current_user, %s, 'INSERT, UPDATE, DELETE, TRUNCATE')",
            (f"public.{table}",),
        )
        assert rows == [(False,)], f"{user} can write to {table}"


def test_select_works_on_each_contract_table(conn) -> None:
    for table in sorted(CONTRACT_TABLES):
        assert _run(conn, f"SELECT count(*) FROM (SELECT 1 FROM {table} LIMIT 1) t") is not None


def test_postgis_works(conn) -> None:
    rows = _run(
        conn,
        "SELECT ST_Value(rast, 1, ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), ST_SRID(rast))) "
        "FROM flood_depth_raster_tile LIMIT 1",
        (LON, LAT),
    )
    assert rows is not None
    for view in ("spatial_ref_sys", "geometry_columns", "raster_columns"):
        assert _run(conn, f"SELECT count(*) FROM {view}")[0][0] >= 0


def test_writes_are_refused(conn) -> None:
    for table in sorted(CONTRACT_TABLES):
        column = _run(
            conn,
            "SELECT attname FROM pg_attribute WHERE attrelid = to_regclass(%s) AND attnum = 1",
            (f"public.{table}",),
        )[0][0]
        _refused(conn, f"INSERT INTO {table} DEFAULT VALUES")
        _refused(conn, f"UPDATE {table} SET {column} = {column} WHERE false")
        _refused(conn, f"DELETE FROM {table} WHERE false")
        _refused(conn, f"TRUNCATE {table}")
    _refused(conn, "CREATE TABLE public.us072_probe (x integer)")


def test_a_table_outside_the_contract_is_refused(conn) -> None:
    _refused(conn, f"SELECT 1 FROM {OUTSIDE_THE_CONTRACT} LIMIT 1")


def main() -> int:
    if not os.environ.get("POSTGRES_PASSWORD"):
        print("skip: POSTGRES_PASSWORD is not set, so the reader role was not checked")
        return 0
    import psycopg2

    from db import DB_CONFIG

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        test_role_holds_no_write_privilege(conn)
        test_select_works_on_each_contract_table(conn)
        test_postgis_works(conn)
        test_writes_are_refused(conn)
        test_a_table_outside_the_contract_is_refused(conn)
    finally:
        conn.close()
    print(f"ok: {DB_CONFIG['user']} reads {len(CONTRACT_TABLES)} contract tables and writes nothing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
