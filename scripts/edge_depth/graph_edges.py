"""Reads the export of the GraphHopper graph's edges and keeps it in PostGIS.

The export is two files, written by ExportEdges in java/time-aware-routing/ (US-039):

- graph.json holds graph_hash, edge_count, node_count, and the GraphHopper commit.
- edges.csv has the header edge_id,wkt and one row per edge, in edge id order. wkt is a LINESTRING in
  EPSG:4326, longitude first.

Airflow cannot run the export, because it runs in the GraphHopper image. An operator writes the two
files into a folder that Airflow reads. load_graph_edges copies them into graph_edge when the hash
differs from the one graph_edge already holds, so a graph re-import needs no database step.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from psycopg2.extras import execute_values

FORMAT_VERSION = 1
_REQUIRED_KEYS = ("format_version", "graph_hash", "edge_count", "node_count")
_PAGE_SIZE = 2000


class GraphExportError(ValueError):
    """The export folder is missing, incomplete, or inconsistent."""


@dataclass(frozen=True)
class GraphExport:
    graph_hash: str
    edge_count: int
    node_count: int
    edges_csv: Path


def read_export(export_dir) -> GraphExport:
    """Checks graph.json and the presence of edges.csv. The rows are checked by iter_edges."""
    export_dir = Path(export_dir)
    meta_path = export_dir / "graph.json"
    edges_path = export_dir / "edges.csv"
    if not meta_path.is_file() or not edges_path.is_file():
        raise GraphExportError(
            f"No graph export in {export_dir} (needs graph.json and edges.csv). "
            "Write one with java/time-aware-routing/export-edges.sh, and see the re-import page of US-044."
        )
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise GraphExportError(f"{meta_path} is not valid JSON: {e}") from e
    for key in _REQUIRED_KEYS:
        if key not in meta:
            raise GraphExportError(f"{meta_path} has no {key}")
    if meta["format_version"] != FORMAT_VERSION:
        raise GraphExportError(
            f"{meta_path} has format_version {meta['format_version']}, this code reads {FORMAT_VERSION}"
        )
    return GraphExport(
        graph_hash=str(meta["graph_hash"]),
        edge_count=int(meta["edge_count"]),
        node_count=int(meta["node_count"]),
        edges_csv=edges_path,
    )


def iter_edges(export: GraphExport) -> Iterator[tuple[int, str]]:
    """Yields (edge_id, wkt) in file order. Raises when the ids are not 0, 1, 2, ... or when the row
    count differs from edge_count in graph.json, so a cut-off file cannot be loaded."""
    expected_id = 0
    with open(export.edges_csv, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header != ["edge_id", "wkt"]:
            raise GraphExportError(f"{export.edges_csv} has the header {header}, expected ['edge_id', 'wkt']")
        for row in reader:
            if len(row) != 2:
                raise GraphExportError(f"{export.edges_csv} line {expected_id + 2} has {len(row)} columns")
            edge_id = int(row[0])
            if edge_id != expected_id:
                raise GraphExportError(f"{export.edges_csv} has edge_id {edge_id} where {expected_id} was expected")
            yield edge_id, row[1]
            expected_id += 1
    if expected_id != export.edge_count:
        raise GraphExportError(
            f"{export.edges_csv} has {expected_id} rows but graph.json says edge_count {export.edge_count}"
        )


def loaded_hash(conn) -> str | None:
    """The hash of the export graph_edge holds, or None before the first load."""
    with conn, conn.cursor() as cur:
        cur.execute("SELECT graph_hash FROM graph_edge_export")
        row = cur.fetchone()
    return row[0] if row else None


_INSERT_SQL = """
INSERT INTO graph_edge (edge_id, length_m, geom)
SELECT v.edge_id, ST_Length(g.geom::geography), g.geom
FROM (VALUES %s) AS v(edge_id, wkt)
CROSS JOIN LATERAL (SELECT ST_GeomFromText(v.wkt, 4326) AS geom) g
"""

_RECORD_SQL = """
INSERT INTO graph_edge_export (singleton, graph_hash, edge_count, loaded_at)
VALUES (TRUE, %(graph_hash)s, %(edge_count)s, NOW())
ON CONFLICT (singleton) DO UPDATE SET
    graph_hash = EXCLUDED.graph_hash,
    edge_count = EXCLUDED.edge_count,
    loaded_at = EXCLUDED.loaded_at
"""


def load_graph_edges(conn, export: GraphExport) -> bool:
    """Replaces graph_edge with the export when its hash differs from the loaded one. Returns True
    when it loaded and False when graph_edge already held this export.

    The rows are read and checked before the database is touched, and the replacement is one
    transaction, so a broken file or a bad geometry leaves the previous graph in place."""
    if loaded_hash(conn) == export.graph_hash:
        return False
    rows = list(iter_edges(export))
    with conn, conn.cursor() as cur:
        # Two tasks of overlapping runs can both see a new hash. The second one waits, then finds
        # the hash already loaded and replaces nothing.
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('graph_edge'))")
        cur.execute("SELECT graph_hash FROM graph_edge_export")
        current = cur.fetchone()
        if current and current[0] == export.graph_hash:
            return False
        cur.execute("TRUNCATE graph_edge")
        execute_values(cur, _INSERT_SQL, rows, page_size=_PAGE_SIZE)
        cur.execute(_RECORD_SQL, {"graph_hash": export.graph_hash, "edge_count": export.edge_count})
    return True
