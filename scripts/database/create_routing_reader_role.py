"""Create one read-only role that a consumer app connects with (US-072, US-107).

    ROUTING_READER_PASSWORD=... python scripts/database/create_routing_reader_role.py routing_reader
    ANALYSIS_READER_PASSWORD=... python scripts/database/create_routing_reader_role.py analysis_reader

Connects with DB_CONFIG, the writer role, and needs CREATEROLE. The argument names a role under
"## Reader roles" in artifacts/docs/concepts/core-output-contract.md, or in the page that
CORE_CONTRACT_PAGE names. The role can read only the tables listed for it there. Its PostgreSQL name
is <ROLE>_USER (default: the role name) and its password is <ROLE>_PASSWORD. Rerun it after the role's
list changes.

PostGIS keeps working without a grant here. Its functions are executable by PUBLIC, and
spatial_ref_sys, geometry_columns and raster_columns are readable by PUBLIC.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "floodmap" / "graphhopper-flood-road" / "backend"))

from core_contract import parse_reader_roles  # noqa: E402
from roles import ensure_login_role, grant_statements  # noqa: E402


def reader_env(role: str) -> tuple[str, str]:
    """The variables that hold role's PostgreSQL name and its password."""
    prefix = role.upper()
    return f"{prefix}_USER", f"{prefix}_PASSWORD"


def page_path() -> Path:
    override = os.environ.get("CORE_CONTRACT_PAGE")
    if override:
        return Path(override)
    return REPO / "artifacts" / "docs" / "concepts" / "core-output-contract.md"


def main(argv: list[str]) -> int:
    roles = parse_reader_roles(page_path().read_text(encoding="utf-8"))
    if len(argv) != 2 or argv[1] not in roles:
        print(f"Usage: {Path(argv[0]).name} ROLE, where ROLE is one of {', '.join(sorted(roles))}.", file=sys.stderr)
        return 2
    role, tables = argv[1], roles[argv[1]]
    user_env, password_env = reader_env(role)
    user, password = os.environ.get(user_env, role), os.environ.get(password_env)
    if not password:
        print(f"Set {password_env} to the password {role} will use.", file=sys.stderr)
        return 1

    import psycopg2

    from db_config import DB_CONFIG

    statements = grant_statements(user, DB_CONFIG["database"], tables)

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn, conn.cursor() as cur:
            ensure_login_role(cur, user, password)
            for statement in statements:
                cur.execute(statement)
    finally:
        conn.close()

    print(f"Role {user} can read {', '.join(sorted(tables))}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
