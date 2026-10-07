"""Create the read-only role the routing backend connects with (US-072).

    ROUTING_READER_PASSWORD=... python scripts/database/create_routing_reader_role.py

Connects with DB_CONFIG, the writer role, and needs CREATEROLE. The role is named by
ROUTING_READER_USER (default routing_reader) and gets the password in ROUTING_READER_PASSWORD.
It can read only the tables that artifacts/docs/concepts/core-output-contract.md lists, or the page
that CORE_CONTRACT_PAGE names. Rerun it after the contract page changes.

PostGIS keeps working without a grant here. Its functions are executable by PUBLIC, and
spatial_ref_sys, geometry_columns and raster_columns are readable by PUBLIC.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "floodmap" / "graphhopper-flood-road" / "backend"))

from core_contract import contract_tables  # noqa: E402

DEFAULT_ROLE = "routing_reader"
_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


def _quote(name: str) -> str:
    if not _IDENTIFIER.match(name):
        raise ValueError(f"{name!r} is not a plain lowercase identifier")
    return f'"{name}"'


def grant_statements(role: str, database: str, tables: frozenset[str]) -> list[str]:
    """The statements that leave role with SELECT on exactly tables in schema public."""
    r = _quote(role)
    return [
        f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {r}",
        f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {r}",
        f"REVOKE CREATE ON SCHEMA public FROM {r}",
        f"GRANT CONNECT ON DATABASE {_quote(database)} TO {r}",
        f"GRANT USAGE ON SCHEMA public TO {r}",
        *(f"GRANT SELECT ON public.{_quote(table)} TO {r}" for table in sorted(tables)),
    ]


def page_path() -> Path:
    override = os.environ.get("CORE_CONTRACT_PAGE")
    if override:
        return Path(override)
    return REPO / "artifacts" / "docs" / "concepts" / "core-output-contract.md"


def main() -> int:
    import psycopg2

    from db_config import DB_CONFIG

    role = os.environ.get("ROUTING_READER_USER", DEFAULT_ROLE)
    password = os.environ.get("ROUTING_READER_PASSWORD")
    if not password:
        print("Set ROUTING_READER_PASSWORD to the password the backend will use.", file=sys.stderr)
        return 1
    tables = contract_tables(page_path().read_text(encoding="utf-8"))
    if not tables:
        print(f"{page_path()} lists no contract table.", file=sys.stderr)
        return 1
    statements = grant_statements(role, DB_CONFIG["database"], tables)

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
            if cur.fetchone() is None:
                cur.execute(f"CREATE ROLE {_quote(role)}")
            cur.execute(
                f"ALTER ROLE {_quote(role)} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOREPLICATION NOBYPASSRLS PASSWORD %s",
                (password,),
            )
            for statement in statements:
                cur.execute(statement)
    finally:
        conn.close()

    print(f"Role {role} can read {', '.join(sorted(tables))}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
