"""The routing backend reads only tables listed in the core output contract.

    python test_backend_reads_contract_tables.py

The scan parses each non-test module of backend/ with ast and reads the table names after FROM and
JOIN in every string that looks like SQL. A table name the scan cannot read, such as one filled in by
an f-string, fails the test with its file and line. The contract check reads
artifacts/docs/concepts/core-output-contract.md, or CORE_CONTRACT_PAGE when set, and skips when the
page is absent.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import NamedTuple

from core_contract import contract_tables
from test_core_contract import page_path

BACKEND = Path(__file__).resolve().parent

READ_TODAY = {"flood_depth_raster_tile", "flood_extent_polygon", "flood_extent_step", "flood_road_values"}

_TOKEN = re.compile(
    r"""
    (?P<skip>\s+|--[^\n]*|/\*.*?\*/)
    |(?P<literal>'(?:[^']|'')*')
    |(?P<param>%\([^)]*\)s|%s)
    |(?P<hole>\{[^{}]*\})
    |(?P<quoted>"(?:[^"]|"")*")
    |(?P<word>[A-Za-z_][A-Za-z0-9_$]*)
    |(?P<sym>::|.)
    """,
    re.VERBOSE | re.DOTALL,
)
INTERPOLATED = "a table name in this SQL is interpolated, so the guard cannot check it"
NOT_LISTED = "which the core output contract does not list"

_LOOKS_LIKE_SQL =re.compile(r"\b(select|insert|update|delete)\b", re.IGNORECASE)
_KEYWORD_FROM_FUNCTIONS = {"extract", "substring", "trim", "overlay", "position"}
_NOT_AN_ALIAS = {
    "where", "join", "left", "right", "inner", "outer", "cross", "full", "natural", "on", "using",
    "group", "order", "limit", "offset", "union", "except", "intersect", "having", "window", "for",
    "returning", "set", "fetch", "tablesample",
}


class Token(NamedTuple):
    kind: str
    text: str
    offset: int


class TableRef(NamedTuple):
    name: str
    offset: int


class UnanalyzableSQL(ValueError):
    def __init__(self, offset: int) -> None:
        super().__init__(f"a table name at offset {offset} is interpolated")
        self.offset = offset


def _tokens(sql: str) -> list[Token]:
    tokens = []
    for match in _TOKEN.finditer(sql):
        kind = match.lastgroup
        if kind == "skip":
            continue
        text = match.group()
        if kind == "word":
            text = text.lower()
        elif kind == "quoted":
            text = text[1:-1].replace('""', '"')
        tokens.append(Token(kind, text, match.start()))
    return tokens


def _is_word(tokens: list[Token], i: int, *words: str) -> bool:
    return i < len(tokens) and tokens[i].kind == "word" and (not words or tokens[i].text in words)


def _after_group(tokens: list[Token], i: int) -> int:
    depth = 0
    for j in range(i, len(tokens)):
        if tokens[j].text == "(":
            depth += 1
        elif tokens[j].text == ")":
            depth -= 1
            if depth == 0:
                return j + 1
    return len(tokens)


def _enclosing_functions(tokens: list[Token]) -> list[str | None]:
    """For each token, the word before the innermost open parenthesis around it."""
    stack: list[str | None] = []
    enclosing = []
    for i, tok in enumerate(tokens):
        if tok.text == ")" and stack:
            stack.pop()
        enclosing.append(stack[-1] if stack else None)
        if tok.text == "(":
            stack.append(tokens[i - 1].text if _is_word(tokens, i - 1) else None)
    return enclosing


def _cte_names(tokens: list[Token]) -> set[str]:
    names = set()
    for i, tok in enumerate(tokens):
        if tok.kind not in ("word", "quoted"):
            continue
        j = i + 1
        if j < len(tokens) and tokens[j].text == "(":
            j = _after_group(tokens, j)
        if not _is_word(tokens, j, "as"):
            continue
        j += 1
        while _is_word(tokens, j, "not", "materialized"):
            j += 1
        if j < len(tokens) and tokens[j].text == "(":
            names.add(tok.text)
    return names


def _is_clause_from(tokens: list[Token], i: int, enclosing: list[str | None]) -> bool:
    # IS DISTINCT FROM and EXTRACT(x FROM y) use FROM without naming a table.
    if _is_word(tokens, i - 1, "distinct") and _is_word(tokens, i - 2, "is", "not"):
        return False
    return enclosing[i] not in _KEYWORD_FROM_FUNCTIONS


def _from_items(tokens: list[Token], j: int, many: bool) -> list[TableRef]:
    refs = []
    n = len(tokens)
    while j < n:
        while _is_word(tokens, j, "lateral", "only"):
            j += 1
        if j >= n:
            break
        tok = tokens[j]
        if tok.kind in ("hole", "param"):
            raise UnanalyzableSQL(tok.offset)
        if tok.text == "(":
            j = _after_group(tokens, j)
        elif tok.kind in ("word", "quoted"):
            parts = [tok.text]
            j += 1
            while j + 1 < n and tokens[j].text == ".":
                if tokens[j + 1].kind in ("hole", "param"):
                    raise UnanalyzableSQL(tokens[j + 1].offset)
                parts.append(tokens[j + 1].text)
                j += 2
            if j < n and tokens[j].text == "(":
                j = _after_group(tokens, j)
            else:
                if parts[0] == "public" and len(parts) == 2:
                    parts = parts[1:]
                refs.append(TableRef(".".join(parts), tok.offset))
        else:
            break
        if not many:
            break
        if _is_word(tokens, j, "with") and _is_word(tokens, j + 1, "ordinality"):
            j += 2
        if _is_word(tokens, j, "as"):
            j += 1
        if j < n and tokens[j].kind in ("word", "quoted") and tokens[j].text not in _NOT_AN_ALIAS:
            j += 1
            if j < n and tokens[j].text == "(":
                j = _after_group(tokens, j)
        if j < n and tokens[j].text == ",":
            j += 1
            continue
        break
    return refs


def table_refs(sql: str) -> list[TableRef]:
    """Each table named after FROM or JOIN, with its offset in sql. Raises UnanalyzableSQL."""
    tokens = _tokens(sql)
    enclosing = _enclosing_functions(tokens)
    refs = []
    for i, tok in enumerate(tokens):
        if tok.kind != "word":
            continue
        if tok.text == "join":
            refs += _from_items(tokens, i + 1, many=False)
        elif tok.text == "from" and _is_clause_from(tokens, i, enclosing):
            refs += _from_items(tokens, i + 1, many=True)
    ctes = _cte_names(tokens)
    return [ref for ref in refs if ref.name not in ctes]


def tables_read(sql: str) -> set[str]:
    return {ref.name for ref in table_refs(sql)}


class Read(NamedTuple):
    table: str
    path: str
    line: int


class Unreadable(NamedTuple):
    path: str
    line: int


def _docstring_nodes(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                ids.add(id(first.value))
    return ids


def _is_text(node: ast.AST) -> bool:
    return isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, str))


def _addends(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _addends(node.left) + _addends(node.right)
    return [node]


def _render(node: ast.AST) -> str:
    """The node's text, with "{}" in place of each part only known at run time."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(_render(value) if _is_text(value) else "{}" for value in node.values)
    return "{}"


def _string_expressions(tree: ast.AST) -> list[tuple[int, str]]:
    skip = _docstring_nodes(tree)
    found = []

    def visit(node: ast.AST) -> None:
        addends = _addends(node)
        if any(_is_text(part) for part in addends) and id(node) not in skip:
            found.append((node.lineno, "".join(_render(part) for part in addends)))
            for part in addends:
                if not _is_text(part):
                    visit(part)
            return
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(tree)
    return found


def scan_source(source: str, path: str) -> tuple[list[Read], list[Unreadable]]:
    """The tables each SQL string in source reads, and the SQL strings whose tables are unknowable."""
    reads, unreadable = [], []
    for start, text in _string_expressions(ast.parse(source, filename=path)):
        if not _LOOKS_LIKE_SQL.search(text):
            continue
        try:
            refs = table_refs(text)
        except UnanalyzableSQL as error:
            unreadable.append(Unreadable(path, start + text[: error.offset].count("\n")))
            continue
        reads += [Read(ref.name, path, start + text[: ref.offset].count("\n")) for ref in refs]
    return reads, unreadable


def violations(source: str, path: str, allowed: frozenset[str]) -> list[str]:
    reads, unreadable = scan_source(source, path)
    lines = [f"{u.path}:{u.line}: {INTERPOLATED}" for u in unreadable]
    lines += [f"{r.path}:{r.line}: reads {r.table}, {NOT_LISTED}" for r in reads if r.table not in allowed]
    return lines


def backend_modules() -> list[Path]:
    return sorted(p for p in BACKEND.glob("*.py") if not p.name.startswith("test_"))


def scan_backend() -> tuple[list[Read], list[Unreadable]]:
    reads, unreadable = [], []
    for module in backend_modules():
        r, u = scan_source(module.read_text(encoding="utf-8"), module.name)
        reads += r
        unreadable += u
    return reads, unreadable


def test_tables_read_follows_from_and_join() -> None:
    assert tables_read("SELECT a FROM t1 JOIN t2 ON t1.id = t2.id LEFT JOIN t3 USING (id)") == {"t1", "t2", "t3"}
    assert tables_read("SELECT x FROM (SELECT x FROM inner_t) sub") == {"inner_t"}
    assert tables_read("WITH w AS (SELECT * FROM base) SELECT * FROM w JOIN other o ON true") == {"base", "other"}
    cte = "WITH a AS NOT MATERIALIZED (SELECT 1 FROM x), b (c) AS (SELECT c FROM a) SELECT * FROM b"
    assert tables_read(cte) == {"x"}
    assert tables_read("SELECT v.depth FROM flood_road_values AS v WHERE v.depth > 0") == {"flood_road_values"}
    assert tables_read("SELECT * FROM t1 a, t2 AS b, t3") == {"t1", "t2", "t3"}
    assert tables_read("SELECT * FROM generate_series(1, 3) g, ST_MakePoint(1, 2) AS p, tile") == {"tile"}
    assert tables_read("SELECT * FROM unnest(%(lons)s::float8[]) WITH ORDINALITY AS s(lon, ord), tile") == {"tile"}
    assert tables_read("SELECT * FROM s LEFT JOIN LATERAL (SELECT 1 FROM tile t) px ON true") == {"s", "tile"}
    qualified = 'SELECT * FROM public.road JOIN "Mixed" ON true JOIN other.road ON true'
    assert tables_read(qualified) == {"road", "Mixed", "other.road"}
    assert tables_read("SELECT extract(epoch FROM ts), a IS DISTINCT FROM b FROM t -- FROM gone\n") == {"t"}
    assert tables_read("SELECT 'FROM quoted' FROM t /* JOIN gone */ ORDER BY a, b") == {"t"}
    assert tables_read("SELECT PostGIS_Version();") == set()


def test_tables_read_rejects_an_interpolated_table() -> None:
    for sql in ("SELECT 1 FROM {}", "SELECT 1 FROM %s", "SELECT 1 FROM t JOIN {table} ON true", "SELECT 1 FROM {}.t"):
        try:
            tables_read(sql)
        except UnanalyzableSQL:
            continue
        raise AssertionError(f"{sql!r} was analyzed although its table is interpolated")
    assert tables_read("SELECT 1 FROM t WHERE depth >= %(min)s {band_max_clause}") == {"t"}


def test_a_table_outside_the_contract_fails_with_its_line() -> None:
    allowed = frozenset({"flood_road_values"})
    source = 'X = 1\nQ = """\nSELECT 1\nFROM road_segment\n"""\n'
    assert violations(source, "fake.py", allowed) == [
        "fake.py:4: reads road_segment, which the core output contract does not list"
    ]
    concatenated = 'Q = (\n    "SELECT 1 "\n    + "FROM flood_road_values JOIN road_segment ON true"\n)\n'
    assert violations(concatenated, "fake.py", allowed) == [
        "fake.py:2: reads road_segment, which the core output contract does not list"
    ]


def test_an_interpolated_table_fails_with_its_line() -> None:
    allowed = frozenset({"flood_road_values"})
    for source in (
        'T = "flood_road_values"\nQ = f"SELECT 1 FROM {T}"\n',
        'T = "flood_road_values"\nQ = "SELECT 1 FROM " + T\n',
    ):
        assert violations(source, "fake.py", allowed) == [
            "fake.py:2: a table name in this SQL is interpolated, so the guard cannot check it"
        ], source


def test_docstrings_and_prose_are_not_scanned() -> None:
    source = '"""Select a run from the list."""\nMESSAGE = "no rows"\n'
    assert scan_source(source, "fake.py") == ([], [])


def test_backend_scan_finds_the_tables_it_reads_today() -> None:
    reads, unreadable = scan_backend()
    assert not unreadable, "SQL the guard cannot check: " + ", ".join(f"{u.path}:{u.line}" for u in unreadable)
    found = {r.table for r in reads}
    missing = READ_TODAY - found
    assert not missing, f"the scan did not find {sorted(missing)} in {len(backend_modules())} modules"
    print(f"backend reads {sorted(found)}")


def test_backend_reads_only_contract_tables() -> None:
    path = page_path()
    if path is None or not path.is_file():
        print(f"skip: no contract page at {path}, so the backend tables were not checked against it")
        return
    allowed = contract_tables(path.read_text(encoding="utf-8"))
    assert READ_TODAY <= allowed, f"the contract page does not list {sorted(READ_TODAY - allowed)}"
    lines = []
    for module in backend_modules():
        lines += violations(module.read_text(encoding="utf-8"), module.name, allowed)
    assert not lines, "the backend reads outside the core output contract:\n" + "\n".join(lines)
    print(f"backend reads only contract tables ({len(allowed)} listed)")


def main() -> int:
    test_tables_read_follows_from_and_join()
    test_tables_read_rejects_an_interpolated_table()
    test_a_table_outside_the_contract_fails_with_its_line()
    test_an_interpolated_table_fails_with_its_line()
    test_docstrings_and_prose_are_not_scanned()
    test_backend_reads_only_contract_tables()
    test_backend_scan_finds_the_tables_it_reads_today()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
