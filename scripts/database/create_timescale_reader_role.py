"""Create the read-only role the analysis service connects to timescaledb with (US-109).

    ANALYSIS_TIMESCALE_READER_PASSWORD=... python scripts/database/create_timescale_reader_role.py

Connects with TIMESCALE_DB_CONFIG, the writer role, and needs CREATEROLE. The role's name is
ANALYSIS_TIMESCALE_READER_USER (default analysis_timescale_reader) and its password is
ANALYSIS_TIMESCALE_READER_PASSWORD. It can read depth_history and history_moment, the tables of US-106, and nothing
else in schema public. TimescaleDB passes a grant on a hypertable on to its chunks. A rerun changes nothing.
"""

from __future__ import annotations

import os
import sys

from roles import ensure_login_role, grant_statements

TABLES = frozenset({"depth_history", "history_moment"})


def statements(role: str, database: str) -> list[str]:
    return grant_statements(role, database, TABLES)


def apply(conn, role: str, password: str) -> None:
    with conn, conn.cursor() as cur:
        ensure_login_role(cur, role, password)
        for statement in statements(role, conn.info.dbname):
            cur.execute(statement)


def main() -> int:
    role = os.environ.get("ANALYSIS_TIMESCALE_READER_USER", "analysis_timescale_reader")
    password = os.environ.get("ANALYSIS_TIMESCALE_READER_PASSWORD")
    if not password:
        print(f"Set ANALYSIS_TIMESCALE_READER_PASSWORD to the password {role} will use.", file=sys.stderr)
        return 1

    import psycopg2

    from db_config import TIMESCALE_DB_CONFIG

    conn = psycopg2.connect(**TIMESCALE_DB_CONFIG)
    try:
        apply(conn, role, password)
    finally:
        conn.close()

    print(f"Role {role} can read {', '.join(sorted(TABLES))}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
