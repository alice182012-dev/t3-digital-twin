"""A reader role can read its own tables and nothing else, and write nothing (US-072, US-107).

    python test_reader_role.py
    POSTGRES_USER=analysis_reader POSTGRES_PASSWORD=... python test_reader_role.py

The live checks connect with db.DB_CONFIG, the connection the backend itself uses, and skip when
POSTGRES_PASSWORD is not set. The role's tables are its READER_ROLES entry, picked by READER_ROLE
or else by POSTGRES_USER. Every statement runs in its own transaction and is rolled back. It refuses
to try a write when the role holds any write privilege on one of its tables, so a run with the
writer's credentials fails before it touches a table. The offline test needs no database.
"""

from __future__ import annotations

import os

from test_core_contract import CONTRACT_TABLES, READER_ROLES

OUTSIDE_THE_CONTRACT = "flood_segment_metrics"
# Inside the model border, see .claude/CLAUDE.md.
LON, LAT = 105.75, 21.0


def tables_outside(role: str) -> list[str]:
    """The tables a read by role must be refused on."""
    return sorted((CONTRACT_TABLES - READER_ROLES[role]) | {OUTSIDE_THE_CONTRACT})


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


def check_role_holds_no_write_privilege(conn, tables: frozenset[str]) -> None:
    rows = _run(conn, "SELECT current_user, rolsuper FROM pg_roles WHERE rolname = current_user")
    user, superuser = rows[0]
    assert not superuser, f"{user} is a superuser"
    for table in sorted(tables):
        rows = _run(
            conn,
            "SELECT has_table_privilege(current_user, %s, 'INSERT, UPDATE, DELETE, TRUNCATE')",
            (f"public.{table}",),
        )
        assert rows == [(False,)], f"{user} can write to {table}"


def check_select_works_on_each_table(conn, tables: frozenset[str]) -> None:
    for table in sorted(tables):
        assert _run(conn, f"SELECT count(*) FROM (SELECT 1 FROM {table} LIMIT 1) t") is not None


def check_postgis_works(conn) -> None:
    rows = _run(
        conn,
        "SELECT ST_Value(rast, 1, ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 4326), ST_SRID(rast))) "
        "FROM flood_depth_raster_tile LIMIT 1",
        (LON, LAT),
    )
    assert rows is not None
    for view in ("spatial_ref_sys", "geometry_columns", "raster_columns"):
        assert _run(conn, f"SELECT count(*) FROM {view}")[0][0] >= 0


def check_writes_are_refused(conn, tables: frozenset[str]) -> None:
    for table in sorted(tables):
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


def check_reads_outside_the_role_are_refused(conn, role: str) -> None:
    for table in tables_outside(role):
        _refused(conn, f"SELECT 1 FROM {table} LIMIT 1")


def test_each_role_is_refused_the_tables_outside_its_list() -> None:
    assert tables_outside("routing_reader") == ["flood_segment_metrics"]
    assert tables_outside("analysis_reader") == [
        "demo_pin",
        "edge_depth",
        "edge_depth_run",
        "flood_segment_metrics",
        "forecast_mode",
        "graph_edge",
    ]


def main() -> int:
    test_each_role_is_refused_the_tables_outside_its_list()
    if not os.environ.get("POSTGRES_PASSWORD"):
        print("skip: POSTGRES_PASSWORD is not set, so the reader role was not checked")
        return 0
    import psycopg2

    from db import DB_CONFIG

    role = os.environ.get("READER_ROLE", DB_CONFIG["user"])
    if role not in READER_ROLES:
        raise AssertionError(f"{role} is not a reader role; set READER_ROLE to one of {sorted(READER_ROLES)}")
    tables = READER_ROLES[role]
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        check_role_holds_no_write_privilege(conn, tables)
        check_select_works_on_each_table(conn, tables)
        check_postgis_works(conn)
        check_writes_are_refused(conn, tables)
        check_reads_outside_the_role_are_refused(conn, role)
    finally:
        conn.close()
    print(
        f"ok: {DB_CONFIG['user']} reads the {len(tables)} tables of {role}, "
        f"is refused {', '.join(tables_outside(role))}, and writes nothing"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
