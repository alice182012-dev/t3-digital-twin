import psycopg2

from db_config import DB_CONFIG

SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;

CREATE TABLE IF NOT EXISTS flood_depth_raster (
    id BIGSERIAL PRIMARY KEY,

    run_ts TEXT NOT NULL,
    valid_time_utc TIMESTAMP NOT NULL,

    rast raster NOT NULL,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (run_ts, valid_time_utc)
);

CREATE INDEX IF NOT EXISTS idx_flood_depth_raster_valid_time_utc
ON flood_depth_raster(valid_time_utc);

CREATE INDEX IF NOT EXISTS idx_flood_depth_raster_rast_gist
ON flood_depth_raster USING GIST(ST_ConvexHull(rast));

-- One row per tile of a timestep's raster. flood_depth_raster above keeps one whole raster per
-- row, which PostgreSQL unpacks in full (209 MB) for every ST_Value; it stays until nothing reads
-- it, so a DAG run already in flight keeps loading into the table it knows.
CREATE TABLE IF NOT EXISTS flood_depth_raster_tile (
    run_ts TEXT NOT NULL,
    valid_time_utc TIMESTAMP NOT NULL,
    tile_x INTEGER NOT NULL,
    tile_y INTEGER NOT NULL,

    rast raster NOT NULL,

    created_at TIMESTAMP DEFAULT NOW(),

    -- The key's (run_ts, valid_time_utc) prefix also serves the per-timestep lookup and delete.
    PRIMARY KEY (run_ts, valid_time_utc, tile_y, tile_x)
);

CREATE INDEX IF NOT EXISTS idx_flood_depth_raster_tile_rast_gist
ON flood_depth_raster_tile USING GIST(ST_ConvexHull(rast));
"""


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.close()
    conn.close()

    print("Tables flood_depth_raster and flood_depth_raster_tile ready.")


if __name__ == "__main__":
    main()
