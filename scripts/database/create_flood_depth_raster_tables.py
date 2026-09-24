import psycopg2

from db_config import DB_CONFIG

SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;

-- One row per tile of a timestep's raster. A whole timestep in one row made PostgreSQL unpack all
-- of it (209 MB) for every ST_Value.
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

    print("Table flood_depth_raster_tile ready.")


if __name__ == "__main__":
    main()
