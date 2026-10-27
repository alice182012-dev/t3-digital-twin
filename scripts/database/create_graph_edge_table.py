import psycopg2

from db_config import DB_CONFIG

SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;

-- The edges of the GraphHopper graph, from the export of java/time-aware-routing (ExportEdges).
-- edge_id is GraphHopper's own edge id, so it changes whenever the graph is re-imported.
-- edge_key is <osm_way_id>:<position along the way> (US-117). It does not change when the same OSM
-- file is imported again, and it is NULL for an export before format 3.
CREATE TABLE IF NOT EXISTS graph_edge (
    edge_id INTEGER PRIMARY KEY,
    length_m DOUBLE PRECISION NOT NULL,
    geom geometry(LineString,4326) NOT NULL
);

ALTER TABLE graph_edge ADD COLUMN IF NOT EXISTS edge_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_graph_edge_edge_key
ON graph_edge(edge_key);

CREATE INDEX IF NOT EXISTS idx_graph_edge_geom
ON graph_edge USING GIST(geom);

-- One row: which export graph_edge holds. The edge depth table task loads a new export only when
-- the hash in graph.json differs from this one.
CREATE TABLE IF NOT EXISTS graph_edge_export (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    graph_hash TEXT NOT NULL,
    edge_count INTEGER NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.close()
    conn.close()

    print("Tables graph_edge and graph_edge_export ready.")


if __name__ == "__main__":
    main()
