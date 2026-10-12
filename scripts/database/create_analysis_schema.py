"""Create schema `analysis` in storage-postgres and the role that owns it, the analysis service's only write target (US-109).

    ANALYSIS_OWNER_PASSWORD=... python scripts/database/create_analysis_schema.py

Connects with DB_CONFIG, the writer role, and needs CREATEROLE. The role's name is ANALYSIS_OWNER_USER (default
analysis_owner) and its password is ANALYSIS_OWNER_PASSWORD. The role can write nothing in schema public. A rerun
changes nothing.
"""

from __future__ import annotations

import os
import sys

from roles import ensure_login_role, quote

SCHEMA = "analysis"


def statements(owner: str, database: str) -> list[str]:
    """The statements that leave owner owning schema analysis, with no right on schema public or its tables."""
    o, s = quote(owner), quote(SCHEMA)
    return [
        f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {o}",
        f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {o}",
        f"REVOKE ALL ON SCHEMA public FROM {o}",
        f"GRANT CONNECT ON DATABASE {quote(database)} TO {o}",
        f"CREATE SCHEMA IF NOT EXISTS {s} AUTHORIZATION {o}",
        f"ALTER SCHEMA {s} OWNER TO {o}",
        # An unqualified CREATE TABLE lands in analysis, and PostGIS types in public still resolve.
        f"ALTER ROLE {o} SET search_path TO {s}, public",
    ]


def apply(conn, owner: str, password: str) -> None:
    with conn, conn.cursor() as cur:
        ensure_login_role(cur, owner, password)
        for statement in statements(owner, conn.info.dbname):
            cur.execute(statement)


def main() -> int:
    owner = os.environ.get("ANALYSIS_OWNER_USER", "analysis_owner")
    password = os.environ.get("ANALYSIS_OWNER_PASSWORD")
    if not password:
        print(f"Set ANALYSIS_OWNER_PASSWORD to the password {owner} will use.", file=sys.stderr)
        return 1

    import psycopg2

    from db_config import DB_CONFIG

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        apply(conn, owner, password)
    finally:
        conn.close()

    print(f"Role {owner} owns schema {SCHEMA}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
