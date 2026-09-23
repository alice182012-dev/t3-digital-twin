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
"""


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.close()
    conn.close()

    print("Table flood_depth_raster ready.")


if __name__ == "__main__":
    main()
