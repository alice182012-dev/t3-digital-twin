"""What the role scripts share: a login role with a password, and SELECT on exactly some tables in schema public.

create_routing_reader_role.py (US-072, US-107), create_analysis_schema.py and create_timescale_reader_role.py
(US-109) use it.
"""

from __future__ import annotations

import re

_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


def quote(name: str) -> str:
    if not _IDENTIFIER.match(name):
        raise ValueError(f"{name!r} is not a plain lowercase identifier")
    return f'"{name}"'


def grant_statements(role: str, database: str, tables: frozenset[str]) -> list[str]:
    """The statements that leave role with SELECT on exactly tables in schema public."""
    r = quote(role)
    return [
        f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {r}",
        f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {r}",
        f"REVOKE CREATE ON SCHEMA public FROM {r}",
        f"GRANT CONNECT ON DATABASE {quote(database)} TO {r}",
        f"GRANT USAGE ON SCHEMA public TO {r}",
        *(f"GRANT SELECT ON public.{quote(table)} TO {r}" for table in sorted(tables)),
    ]


def ensure_login_role(cur, user: str, password: str) -> None:
    """Creates user when it is missing, then sets its attributes and password, so a rerun converges."""
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (user,))
    if cur.fetchone() is None:
        cur.execute(f"CREATE ROLE {quote(user)}")
    cur.execute(
        f"ALTER ROLE {quote(user)} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %s",
        (password,),
    )
