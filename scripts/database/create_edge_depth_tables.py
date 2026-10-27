import psycopg2

from db_config import DB_CONFIG

SQL = """
-- One row per run whose edge depth `9c` has written, including a run with no wet edge (US-118, D-038).
-- valid_times is the run's forecast times, in naive UTC like flood_depth_raster_tile.valid_time_utc. A run with no wet
-- edge has no rows in edge_depth, so this row is the only record that the run covers those times.
CREATE TABLE IF NOT EXISTS edge_depth_run (
    run_ts TEXT PRIMARY KEY,
    graph_hash TEXT NOT NULL,
    valid_times TIMESTAMP[] NOT NULL,
    built_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- The wet edges of a run: the deepest sample along the edge, in whole centimetres, at one forecast time. An edge that is
-- dry at a time has no row. edge_key is graph_edge.edge_key, which survives a re-import of the same OSM file.
CREATE TABLE IF NOT EXISTS edge_depth (
    run_ts TEXT NOT NULL REFERENCES edge_depth_run(run_ts) ON DELETE CASCADE,
    valid_time_utc TIMESTAMP NOT NULL,
    edge_key TEXT NOT NULL,
    depth_cm INTEGER NOT NULL CHECK (depth_cm > 0),
    PRIMARY KEY (run_ts, valid_time_utc, edge_key)
);

-- The readers ask for one forecast time at a time, across the newest runs.
CREATE INDEX IF NOT EXISTS idx_edge_depth_time_run
ON edge_depth(valid_time_utc, run_ts DESC);
"""


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.close()
    conn.close()

    print("Tables edge_depth_run and edge_depth ready.")


if __name__ == "__main__":
    main()
