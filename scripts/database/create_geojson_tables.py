import os
import psycopg2

from db_config import DB_CONFIG

SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS flood_road_file (
    id BIGSERIAL PRIMARY KEY,

    timestamp TIMESTAMP NOT NULL,

    source_file TEXT NOT NULL UNIQUE,

    geojson_type TEXT,
    feature_count INTEGER,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS flood_road_values (
    id BIGSERIAL PRIMARY KEY,

    file_id BIGINT NOT NULL
        REFERENCES flood_road_file(id)
        ON DELETE CASCADE,

    timestamp TIMESTAMP NOT NULL,

    road_name TEXT,
    forecast_time TIMESTAMP NOT NULL,
    depth DOUBLE PRECISION,

    geom JSONB,

    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE flood_road_values
    ADD COLUMN IF NOT EXISTS geom_4326 geometry(Geometry,4326);

-- Written by scripts/flood_roads/flood_on_roads.py, NULL on rows from the GeoJSON chain.
ALTER TABLE flood_road_values
    ADD COLUMN IF NOT EXISTS segment_id TEXT;

CREATE INDEX IF NOT EXISTS idx_flood_file_timestamp
ON flood_road_file(timestamp);

CREATE INDEX IF NOT EXISTS idx_flood_values_timestamp
ON flood_road_values(timestamp);

CREATE INDEX IF NOT EXISTS idx_flood_values_forecast_time
ON flood_road_values(forecast_time);

CREATE INDEX IF NOT EXISTS idx_flood_values_depth
ON flood_road_values(depth);

CREATE INDEX IF NOT EXISTS idx_flood_values_geom_4326
ON flood_road_values USING GIST(geom_4326);

CREATE INDEX IF NOT EXISTS idx_flood_values_forecast_timestamp
ON flood_road_values(forecast_time, timestamp DESC);
"""

BACKFILL_SQL = """
UPDATE flood_road_values
SET geom_4326 = ST_SetSRID(ST_GeomFromGeoJSON(geom::text), 4326)
WHERE geom_4326 IS NULL AND geom IS NOT NULL;
"""


def main():

    conn = psycopg2.connect(**DB_CONFIG)

    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.execute(BACKFILL_SQL)
    backfilled = cur.rowcount
    conn.commit()

    cur.close()
    conn.close()

    print(f"Tables created successfully. Backfilled geom_4326 for {backfilled} rows.")


if __name__ == "__main__":
    main()