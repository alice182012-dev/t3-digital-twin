"""Checks that the edge depth tables are fresh: do the export folder, graph_edge, the tables, and the live graph
agree on the graph hash? (US-044)

Usage: python check_tables.py [--table-dir DIR] [--export-dir DIR] [--graph-hash HASH] [--no-db]

Edge ids change on every graph re-import, and a table is only right for the graph it was built from. The graph
hash in each table's header says which. After a re-import the steps of
artifacts/docs/concepts/graph-reimport-procedure.md bring everything onto the new hash, and this command shows
whether they have. Run it before the re-import to see the starting state, and after to check the end.

--graph-hash is the hash of the live graph. `java/time-aware-routing/export-edges.sh` prints it
(`graph_hash=...`). Without it, the export folder is the reference, and this cannot see an export that is itself
out of date.

A table is stale when the one `latest` names was built for another graph than the reference. Older kept tables of
the old graph are not read and are not a problem, and graph_edge behind the export heals itself, because the next
table build reloads it. Exit code 1 means something needs doing.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import edge_depth_table
import graph_edges

SCRIPTS_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class FreshnessReport:
    lines: tuple[str, ...]
    problems: tuple[str, ...]

    @property
    def stale(self) -> bool:
        return bool(self.problems)


def _short(graph_hash: str | None) -> str:
    return "none" if graph_hash is None else graph_hash[:12]


def check(table_dir, export_dir, graph_edge_hash: str | None = None, live_graph_hash: str | None = None) -> FreshnessReport:
    table_dir, export_dir = Path(table_dir), Path(export_dir)
    lines: list[str] = []
    problems: list[str] = []

    export_hash = None
    try:
        export_hash = graph_edges.read_export(export_dir).graph_hash
    except graph_edges.GraphExportError as e:
        problems.append(f"no usable export: {e}")

    latest_name = latest_hash = latest_run = None
    try:
        latest = edge_depth_table.read_table(edge_depth_table.read_latest(table_dir))
        latest_name = edge_depth_table.read_latest(table_dir).name
        latest_hash, latest_run = latest.header.graph_hash, latest.header.run_name
    except FileNotFoundError:
        problems.append(f"no table published in {table_dir}: build one (scripts/edge_depth/server_check.sh)")
    except (ValueError, edge_depth_table.TableFormatError) as e:
        problems.append(f"the table `latest` names does not read: {e}")

    reference = live_graph_hash if live_graph_hash is not None else export_hash
    lines.append(f"live graph     {_short(live_graph_hash)}" + ("" if live_graph_hash else "  (not given: the export is the reference)"))
    lines.append(f"export folder  {_short(export_hash)}")
    lines.append(f"graph_edge     {_short(graph_edge_hash)}" + ("" if graph_edge_hash else "  (not read)"))
    lines.append(f"latest table   {_short(latest_hash)}" + (f"  ({latest_name})" if latest_name else ""))

    if live_graph_hash is not None and export_hash is not None and export_hash != live_graph_hash:
        problems.append(
            f"the export folder is for graph hash {export_hash}, but the live graph has hash {live_graph_hash}: "
            "write a new export (export-edges.sh with EXPORT_DEST)"
        )
    if latest_hash is not None and reference is not None and latest_hash != reference:
        problems.append(
            f"the `latest` table (run {latest_run}, {latest_name}) was built for graph hash {latest_hash}, "
            f"but the reference has hash {reference}: build a new table from a current export"
        )
    if graph_edge_hash is not None and export_hash is not None and graph_edge_hash != export_hash:
        lines.append(
            f"note: graph_edge holds export {_short(graph_edge_hash)}, not {_short(export_hash)}. "
            "The next table build reloads it, so this is not a problem."
        )

    others = []
    for path in sorted(table_dir.glob("*.bin")) if table_dir.is_dir() else []:
        if path.name == latest_name:
            continue
        try:
            others.append((path.name, edge_depth_table.read_table(path).header.graph_hash))
        except (ValueError, OSError):
            others.append((path.name, None))
    for name, graph_hash in others:
        lines.append(f"older table   {name}  graph {_short(graph_hash)}" + ("" if graph_hash == reference else "  (not read; retention removes it)"))

    return FreshnessReport(tuple(lines), tuple(problems))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--table-dir", default="/opt/airflow/edge_depth_tables")
    parser.add_argument("--export-dir", default="/opt/airflow/data/mapping/graph_export")
    parser.add_argument("--graph-hash", default=None, help="the hash of the live graph, as export-edges.sh prints it")
    parser.add_argument("--no-db", action="store_true", help="do not read graph_edge_export from PostgreSQL")
    args = parser.parse_args(argv)

    graph_edge_hash = None
    if not args.no_db:
        try:
            import psycopg2

            sys.path.insert(0, str(SCRIPTS_DIR / "database"))
            from db_config import DB_CONFIG

            conn = psycopg2.connect(**DB_CONFIG)
            try:
                graph_edge_hash = graph_edges.loaded_hash(conn)
            finally:
                conn.close()
        except Exception as e:  # noqa: BLE001 - the database is optional for this check
            print(f"(graph_edge not read: {e})")

    report = check(args.table_dir, args.export_dir, graph_edge_hash, args.graph_hash)
    for line in report.lines:
        print(line)
    if report.problems:
        print()
        for problem in report.problems:
            print(f"PROBLEM: {problem}")
        print("STALE: follow artifacts/docs/concepts/graph-reimport-procedure.md")
        return 1
    print("FRESH: the export, the tables, and the graph agree on one hash")
    return 0


if __name__ == "__main__":
    sys.exit(main())
