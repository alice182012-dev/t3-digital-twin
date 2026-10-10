"""The core output contract page against the parser, and against the live schema.

    python test_core_contract.py

The offline tests need no database and no psycopg2. The page test reads
artifacts/docs/concepts/core-output-contract.md, or CORE_CONTRACT_PAGE when set, and skips when the
page is absent (the backend image holds only backend/ and scripts/). The live test runs when
POSTGRES_PASSWORD is set and connects with db.DB_CONFIG.
"""

from __future__ import annotations

import os
from pathlib import Path

from core_contract import Column, Keys, contract_tables, parse_contract, parse_keys, parse_reader_roles

CONTRACT_TABLES = {
    "flood_depth_raster_tile",
    "flood_extent_polygon",
    "flood_extent_step",
    "flood_road_values",
    "graph_edge",
}

READER_ROLES = {
    "routing_reader": frozenset(CONTRACT_TABLES),
    "analysis_reader": frozenset(
        {"flood_depth_raster_tile", "flood_extent_polygon", "flood_extent_step", "flood_road_values"}
    ),
}

_LIVE_COLUMNS_SQL = """
SELECT a.attname, format_type(a.atttypid, a.atttypmod), NOT a.attnotnull
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
WHERE c.oid = to_regclass(%s) AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY a.attnum
"""

_LIVE_KEYS_SQL = """
SELECT c.contype, array_agg(a.attname::text ORDER BY k.ord)
FROM pg_constraint c
CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS k(attnum, ord)
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = k.attnum
WHERE c.conrelid = to_regclass(%s) AND c.contype IN ('p', 'u')
GROUP BY c.oid, c.contype
"""

SAMPLE = """# Sample

Prose with a | pipe | in it.

## Tables

### first_table

One row is one thing.

| Column | Type | Nullable |
| ------ | ---- | -------- |
| `id` | `bigint` | no |
| `geom` | `geometry(Geometry,4326)` | yes |

- **Key.** `id`.
- **Primary key columns.** `id`.
- **Unique columns.** `run_ts`, `valid_time_utc`.

### second_table

| Column | Type | Nullable |
|---|---|---|
| valid_time_utc | timestamp without time zone | no |

## Retention

| Output | Kept | Set by |
| ------ | ---- | ------ |
| `first_table` | Newest 8 runs | `publish.py` |

## Reader roles

Prose about every role.

- **Password.** `<ROLE>_PASSWORD` in `.env`.

### reader_one

- `first_table`
- `second_table`

### reader_two

The second reader.

- `second_table`

## After

- `first_table`
"""


def page_path() -> Path | None:
    override = os.environ.get("CORE_CONTRACT_PAGE")
    if override:
        return Path(override)
    parents = Path(__file__).resolve().parents
    if len(parents) < 4:
        return None
    return parents[3] / "artifacts" / "docs" / "concepts" / "core-output-contract.md"


def diff_columns(table: str, expected: list[Column], actual: list[Column]) -> list[str]:
    if not actual:
        return [f"{table}: not found in the database"]
    found = {c.name: c for c in actual}
    wanted = {c.name: c for c in expected}
    lines = [f"{table}.{c.name}: in the contract, not in the database" for c in expected if c.name not in found]
    lines += [f"{table}.{c.name}: in the database, not in the contract" for c in actual if c.name not in wanted]
    for c in expected:
        live = found.get(c.name)
        if live is None:
            continue
        if live.type != c.type:
            lines.append(f"{table}.{c.name}: type {c.type!r} in the contract, {live.type!r} in the database")
        if live.nullable != c.nullable:
            lines.append(
                f"{table}.{c.name}: nullable {'yes' if c.nullable else 'no'} in the contract, "
                f"{'yes' if live.nullable else 'no'} in the database"
            )
    contract_order = [c.name for c in expected if c.name in found]
    live_order = [c.name for c in actual if c.name in wanted]
    if contract_order != live_order:
        lines.append(f"{table}: column order {contract_order} in the contract, {live_order} in the database")
    return lines


def diff_keys(table: str, expected: Keys | None, primary: tuple[str, ...], unique: set[tuple[str, ...]]) -> list[str]:
    if expected is None:
        return [f"{table}: the contract lists no primary key"]
    lines = []
    if expected.primary != primary:
        lines.append(f"{table}: primary key {list(expected.primary)} in the contract, {list(primary)} in the database")
    for cols in sorted(set(expected.unique) - unique):
        lines.append(f"{table}: unique {list(cols)} in the contract, not in the database")
    for cols in sorted(unique - set(expected.unique)):
        lines.append(f"{table}: unique {list(cols)} in the database, not in the contract")
    return lines


def test_parses_keys() -> None:
    assert parse_keys(SAMPLE) == {"first_table": Keys(("id",), (("run_ts", "valid_time_utc"),))}


def test_rejects_two_primary_keys() -> None:
    text = "### t\n\n- **Primary key columns.** `a`.\n- **Primary key columns.** `b`.\n"
    try:
        parse_keys(text)
    except ValueError as error:
        assert "table t has two primary keys" in str(error), error
    else:
        raise AssertionError("two primary keys on one table must be rejected")


def test_diff_keys_names_the_table() -> None:
    expected = Keys(("run_ts", "id"), (("a", "b"), ("c",)))
    assert diff_keys("t", expected, ("id",), {("a", "b"), ("d",)}) == [
        "t: primary key ['run_ts', 'id'] in the contract, ['id'] in the database",
        "t: unique ['c'] in the contract, not in the database",
        "t: unique ['d'] in the database, not in the contract",
    ]
    assert diff_keys("t", expected, ("run_ts", "id"), {("a", "b"), ("c",)}) == []
    assert diff_keys("t", None, ("id",), set()) == ["t: the contract lists no primary key"]


def test_parses_each_column_table_in_page_order() -> None:
    assert parse_contract(SAMPLE) == {
        "first_table": [
            Column("id", "bigint", False),
            Column("geom", "geometry(Geometry,4326)", True),
        ],
        "second_table": [Column("valid_time_utc", "timestamp without time zone", False)],
    }
    assert contract_tables(SAMPLE) == frozenset({"first_table", "second_table"})


def test_rejects_a_nullable_that_is_not_yes_or_no() -> None:
    text = "### t\n\n| Column | Type | Nullable |\n| - | - | - |\n| `b` | `text` | maybe |\n"
    try:
        parse_contract(text)
    except ValueError as error:
        assert "t.b has Nullable 'maybe'" in str(error), error
    else:
        raise AssertionError("a Nullable of 'maybe' must be rejected")


def test_rejects_a_table_described_twice() -> None:
    table = "| Column | Type | Nullable |\n| - | - | - |\n| `a` | `text` | no |\n"
    try:
        parse_contract(f"### t\n\n{table}\n### t\n\n{table}")
    except ValueError as error:
        assert "table t is described twice" in str(error), error
    else:
        raise AssertionError("a second description of one table must be rejected")


def test_diff_names_the_table_and_the_column() -> None:
    contract = [Column("id", "bigint", False), Column("run_ts", "text", False), Column("depth", "double precision", True)]
    live = [Column("run_ts", "text", True), Column("id", "integer", False), Column("extra", "jsonb", True)]
    assert diff_columns("t", contract, live) == [
        "t.depth: in the contract, not in the database",
        "t.extra: in the database, not in the contract",
        "t.id: type 'bigint' in the contract, 'integer' in the database",
        "t.run_ts: nullable no in the contract, yes in the database",
        "t: column order ['id', 'run_ts'] in the contract, ['run_ts', 'id'] in the database",
    ]
    assert diff_columns("t", contract, contract) == []
    assert diff_columns("gone", contract, []) == ["gone: not found in the database"]


def test_parses_each_reader_role_and_its_tables() -> None:
    assert parse_reader_roles(SAMPLE) == {
        "reader_one": frozenset({"first_table", "second_table"}),
        "reader_two": frozenset({"second_table"}),
    }
    assert parse_reader_roles("# No roles here\n") == {}


def _reader_roles_error(roles_section: str) -> str:
    try:
        parse_reader_roles(SAMPLE.replace("## After", roles_section + "\n## After"))
    except ValueError as error:
        return str(error)
    raise AssertionError(f"{roles_section!r} was accepted")


def test_rejects_a_role_with_no_table() -> None:
    assert _reader_roles_error("### reader_three\n\nNo tables.\n") == "role reader_three lists no table"


def test_rejects_a_table_the_contract_does_not_describe() -> None:
    assert _reader_roles_error("### reader_three\n\n- `road_segment`\n") == (
        "line 51: role reader_three lists road_segment, which the contract does not describe"
    )


def test_rejects_a_role_listed_twice() -> None:
    assert _reader_roles_error("### reader_one\n\n- `first_table`\n") == "line 49: role reader_one is listed twice"


def test_rejects_a_table_before_any_role() -> None:
    text = "### t\n\n| Column | Type | Nullable |\n| - | - | - |\n| `a` | `text` | no |\n\n## Reader roles\n\n- `t`\n"
    try:
        parse_reader_roles(text)
    except ValueError as error:
        assert str(error) == "line 9: table t needs a role heading before it", error
    else:
        raise AssertionError("a table bullet before any role heading must be rejected")


def test_page_describes_the_five_contract_tables() -> None:
    path = page_path()
    if path is None or not path.is_file():
        print(f"skip: contract page not found at {path}")
        return
    tables = parse_contract(path.read_text(encoding="utf-8"))
    missing = CONTRACT_TABLES - set(tables)
    assert not missing, f"the page does not describe {sorted(missing)}"
    empty = sorted(name for name in CONTRACT_TABLES if not tables[name])
    assert not empty, f"the page lists no columns for {empty}"
    keys = parse_keys(path.read_text(encoding="utf-8"))
    no_key = sorted(CONTRACT_TABLES - set(keys))
    assert not no_key, f"the page lists no primary key for {no_key}"
    assert parse_reader_roles(path.read_text(encoding="utf-8")) == READER_ROLES


def test_page_matches_the_live_schema() -> None:
    if not os.environ.get("POSTGRES_PASSWORD"):
        print("skip: POSTGRES_PASSWORD is not set, so the live schema check did not run")
        return
    path = page_path()
    if path is None or not path.is_file():
        raise AssertionError(f"the live check needs the contract page, not found at {path}; set CORE_CONTRACT_PAGE")
    import psycopg2

    from db import DB_CONFIG

    tables = parse_contract(path.read_text(encoding="utf-8"))
    keys = parse_keys(path.read_text(encoding="utf-8"))
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        lines = []
        with conn.cursor() as cur:
            for table in sorted(CONTRACT_TABLES):
                cur.execute(_LIVE_COLUMNS_SQL, (table,))
                live = [Column(name, type_, nullable) for name, type_, nullable in cur.fetchall()]
                lines += diff_columns(table, tables.get(table, []), live)
                cur.execute(_LIVE_KEYS_SQL, (table,))
                found = cur.fetchall()
                primary = next((tuple(cols) for kind, cols in found if kind == "p"), ())
                unique = {tuple(cols) for kind, cols in found if kind == "u"}
                lines += diff_keys(table, keys.get(table), primary, unique)
    finally:
        conn.close()
    assert not lines, "the contract page differs from the live schema:\n" + "\n".join(lines)
    print(f"live schema matches the contract for {len(CONTRACT_TABLES)} tables")


def main() -> int:
    test_parses_keys()
    test_rejects_two_primary_keys()
    test_diff_keys_names_the_table()
    test_parses_each_column_table_in_page_order()
    test_rejects_a_nullable_that_is_not_yes_or_no()
    test_rejects_a_table_described_twice()
    test_diff_names_the_table_and_the_column()
    test_parses_each_reader_role_and_its_tables()
    test_rejects_a_role_with_no_table()
    test_rejects_a_table_the_contract_does_not_describe()
    test_rejects_a_role_listed_twice()
    test_rejects_a_table_before_any_role()
    test_page_describes_the_five_contract_tables()
    test_page_matches_the_live_schema()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
