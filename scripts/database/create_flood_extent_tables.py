import psycopg2

from db_config import DB_CONFIG

SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS flood_extent_polygon (
    id BIGSERIAL PRIMARY KEY,

    run_ts TEXT NOT NULL,
    valid_time_utc TIMESTAMP NOT NULL,
    dn_code INTEGER NOT NULL,
    area_m2 DOUBLE PRECISION NOT NULL,

    geom geometry(Geometry,4326) NOT NULL,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (run_ts, valid_time_utc, dn_code)
);

CREATE INDEX IF NOT EXISTS idx_flood_extent_polygon_run_ts
ON flood_extent_polygon(run_ts);

CREATE INDEX IF NOT EXISTS idx_flood_extent_polygon_valid_time_utc
ON flood_extent_polygon(valid_time_utc);

CREATE INDEX IF NOT EXISTS idx_flood_extent_polygon_geom
ON flood_extent_polygon USING GIST(geom);

-- One row per timestep whose tiles and polygon rows are fully published. A dry timestep has no
-- polygon rows, so flood_extent_polygon alone can't say it was published.
CREATE TABLE IF NOT EXISTS flood_extent_step (
    run_ts TEXT NOT NULL,
    valid_time_utc TIMESTAMP NOT NULL,
    is_empty BOOLEAN NOT NULL,
    published_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (run_ts, valid_time_utc)
);
"""


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.close()
    conn.close()

    print("Tables flood_extent_polygon and flood_extent_step ready.")


if __name__ == "__main__":
    main()
