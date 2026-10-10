"""Reads the column tables and the reader roles of artifacts/docs/concepts/core-output-contract.md.

Each table under a heading whose header row is `| Column | Type | Nullable |` describes the table
the heading names. Type is PostgreSQL's format_type() text, Nullable is `yes` or `no`.
"""

from __future__ import annotations

import re
from typing import NamedTuple

HEADER = ("Column", "Type", "Nullable")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SEPARATOR = re.compile(r"^\|[\s:|-]+\|$")
_NULLABLE = {"yes": True, "no": False}


class Column(NamedTuple):
    name: str
    type: str
    nullable: bool


def _cells(line: str) -> list[str]:
    return [cell.strip().strip("`").strip() for cell in line.strip().strip("|").split("|")]


def parse_contract(markdown_text: str) -> dict[str, list[Column]]:
    """Table name to its columns in page order. Raises ValueError on a malformed contract table."""
    tables: dict[str, list[Column]] = {}
    heading: str | None = None
    current: list[Column] | None = None
    for number, raw in enumerate(markdown_text.splitlines(), start=1):
        line = raw.strip()
        if current is not None:
            if _SEPARATOR.match(line):
                continue
            if line.startswith("|"):
                cells = _cells(line)
                if len(cells) != 3:
                    raise ValueError(f"line {number}: a row of table {heading} needs 3 cells, got {len(cells)}")
                name, type_, nullable = cells
                if nullable not in _NULLABLE:
                    raise ValueError(f"line {number}: {heading}.{name} has Nullable {nullable!r}, expected yes or no")
                current.append(Column(name, type_, _NULLABLE[nullable]))
                continue
            current = None
        match = _HEADING.match(line)
        if match:
            heading = match.group(2)
        elif line.startswith("|") and tuple(_cells(line)) == HEADER:
            if heading is None:
                raise ValueError(f"line {number}: a column table needs a heading that names its table")
            if heading in tables:
                raise ValueError(f"line {number}: table {heading} is described twice")
            current = tables[heading] = []
    return tables


def contract_tables(markdown_text: str) -> frozenset[str]:
    """The names of the tables the contract describes."""
    return frozenset(parse_contract(markdown_text))


_TABLE_BULLET = re.compile(r"^- `([^`]+)`$")


def parse_reader_roles(markdown_text: str) -> dict[str, frozenset[str]]:
    """Role name to the tables it may read, from the `### <role>` headings and their `` - `table` ``
    bullets under `## Reader roles`. Raises ValueError on a repeated role, a role with no table, or
    a table the contract does not describe."""
    described = contract_tables(markdown_text)
    roles: dict[str, set[str]] = {}
    in_section = False
    role: str | None = None
    for number, raw in enumerate(markdown_text.splitlines(), start=1):
        line = raw.strip()
        heading = _HEADING.match(line)
        if heading:
            level, title = len(heading.group(1)), heading.group(2)
            if level <= 2:
                in_section = level == 2 and title == "Reader roles"
                role = None
            elif in_section and level == 3:
                if title in roles:
                    raise ValueError(f"line {number}: role {title} is listed twice")
                role = title
                roles[role] = set()
            continue
        bullet = _TABLE_BULLET.match(line) if in_section else None
        if not bullet:
            continue
        table = bullet.group(1)
        if role is None:
            raise ValueError(f"line {number}: table {table} needs a role heading before it")
        if table not in described:
            raise ValueError(f"line {number}: role {role} lists {table}, which the contract does not describe")
        roles[role].add(table)
    empty = sorted(name for name, tables in roles.items() if not tables)
    if empty:
        raise ValueError(f"role {empty[0]} lists no table")
    return {name: frozenset(tables) for name, tables in roles.items()}


class Keys(NamedTuple):
    primary: tuple[str, ...]
    unique: tuple[tuple[str, ...], ...]


_KEY_BULLET = re.compile(r"^- \*\*(Primary key|Unique) columns\.\*\*\s*(.+)$")


def parse_keys(markdown_text: str) -> dict[str, Keys]:
    """Table name to its primary key and unique constraints, from the `Primary key columns` and
    `Unique columns` bullets under each table heading. Raises ValueError on a repeated primary key."""
    primary: dict[str, tuple[str, ...]] = {}
    unique: dict[str, list[tuple[str, ...]]] = {}
    heading: str | None = None
    for number, raw in enumerate(markdown_text.splitlines(), start=1):
        line = raw.strip()
        match = _HEADING.match(line)
        if match:
            heading = match.group(2)
            continue
        bullet = _KEY_BULLET.match(line)
        if not bullet:
            continue
        if heading is None:
            raise ValueError(f"line {number}: a key bullet needs a heading that names its table")
        columns = tuple(re.findall(r"`([^`]+)`", bullet.group(2)))
        if not columns:
            raise ValueError(f"line {number}: {heading} has a key bullet with no column in code font")
        if bullet.group(1) == "Primary key":
            if heading in primary:
                raise ValueError(f"line {number}: table {heading} has two primary keys")
            primary[heading] = columns
        else:
            unique.setdefault(heading, []).append(columns)
    return {name: Keys(cols, tuple(unique.get(name, ()))) for name, cols in primary.items()}
