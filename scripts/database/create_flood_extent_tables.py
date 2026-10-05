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

-- Runs published before flood_extent_step existed get their wet steps listed. Only into an empty
-- table: this backfill runs once, before flood_extent_step has any rows of its own, so by the
-- time publish.py's prune_polygon_rows starts pruning flood_extent_polygon on every publish,
-- flood_extent_step is already populated and this INSERT is a no-op (its WHERE NOT EXISTS guard).
-- Only the newest 3 runs, the bucket's keep_runs before the 15-minute cycle, since older runs
-- have no tiles left.
INSERT INTO flood_extent_step (run_ts, valid_time_utc, is_empty)
SELECT DISTINCT run_ts, valid_time_utc, false
FROM flood_extent_polygon
WHERE NOT EXISTS (SELECT 1 FROM flood_extent_step)
  AND run_ts IN (SELECT DISTINCT run_ts FROM flood_extent_polygon ORDER BY run_ts DESC LIMIT 3)
ON CONFLICT DO NOTHING;
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
