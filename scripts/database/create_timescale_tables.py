import psycopg2
from psycopg2.extras import execute_values

from db_config import TIMESCALE_DB_CONFIG
from netcdf_variables import VARIABLE_CATALOG

SQL = """
CREATE EXTENSION IF NOT EXISTS timescaledb;

DO $$
BEGIN
    CREATE TYPE simulation_cycle AS ENUM ('constant_cycle', 'background_cycle');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS institution_histogram_bar (
    institution_id TEXT NOT NULL,
    cycle simulation_cycle NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL,
    bar_index SMALLINT NOT NULL,

    valid_time TIMESTAMPTZ NOT NULL,
    max_depth_m DOUBLE PRECISION NOT NULL CHECK (max_depth_m >= 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (institution_id, cycle, issued_at, bar_index),

    -- Architecture doc section 4.9: the 6 h constant_cycle only reaches bars 1-6,
    -- the 24 h background_cycle owns bars 7-24.
    CONSTRAINT bar_index_matches_cycle CHECK (
        (cycle = 'constant_cycle' AND bar_index BETWEEN 1 AND 6)
        OR (cycle = 'background_cycle' AND bar_index BETWEEN 7 AND 24)
    ),
    CONSTRAINT valid_time_on_the_hour CHECK (
        valid_time AT TIME ZONE 'UTC' = date_trunc('hour', valid_time AT TIME ZONE 'UTC')
    )
);

SELECT create_hypertable(
    'institution_histogram_bar', by_range('issued_at'), if_not_exists => TRUE
);

-- constant_cycle's per-segment series already lives in storage-postgres
-- (flood_road_values), so only background_cycle's is stored here.
CREATE TABLE IF NOT EXISTS background_forecast_depth (
    segment_id TEXT NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL,
    valid_time TIMESTAMPTZ NOT NULL,

    depth_m DOUBLE PRECISION NOT NULL CHECK (depth_m >= 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (segment_id, issued_at, valid_time),
    CHECK (valid_time >= issued_at)
);

SELECT create_hypertable(
    'background_forecast_depth', by_range('issued_at'), if_not_exists => TRUE
);

CREATE TABLE IF NOT EXISTS depth_history (
    segment_id TEXT NOT NULL,
    valid_time TIMESTAMPTZ NOT NULL,

    depth_m DOUBLE PRECISION NOT NULL CHECK (depth_m >= 0),
    cycle simulation_cycle NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (segment_id, valid_time),
    CHECK (valid_time >= issued_at)
);

SELECT create_hypertable(
    'depth_history', by_range('valid_time'), if_not_exists => TRUE
);

CREATE TABLE IF NOT EXISTS netcdf_variable_catalog (
    id SMALLINT PRIMARY KEY,
    variable_name TEXT UNIQUE NOT NULL,
    mesh_type TEXT NOT NULL,
    element_type TEXT NOT NULL
);

-- element_id restarts at 1 per (mesh_type, element_type), so the same number is
-- a different 2D line and 2D node within one model. The key carries both.
CREATE TABLE IF NOT EXISTS mesh_elements (
    model_id BIGINT NOT NULL,
    mesh_type TEXT NOT NULL,
    element_type TEXT NOT NULL,
    element_id BIGINT NOT NULL,
    x DOUBLE PRECISION,
    y DOUBLE PRECISION,
    PRIMARY KEY (model_id, mesh_type, element_type, element_id)
);

-- file_id has no foreign key because netcdf_files lives on storage-postgres.
CREATE TABLE IF NOT EXISTS netcdf_values (
    file_id INT NOT NULL,
    element_id BIGINT NOT NULL,
    variable_id SMALLINT NOT NULL REFERENCES netcdf_variable_catalog(id),
    "timestamp" TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION NOT NULL
);

SELECT create_hypertable('netcdf_values', by_range('timestamp', INTERVAL '1 day'), if_not_exists => TRUE);

ALTER TABLE netcdf_values SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'file_id, variable_id',
  timescaledb.compress_orderby = 'element_id'
);
SELECT add_compression_policy('netcdf_values', INTERVAL '6 hours', if_not_exists => TRUE);
SELECT add_retention_policy('netcdf_values', INTERVAL '48 hours', if_not_exists => TRUE);
"""

CATALOG_SEED_SQL = """
INSERT INTO netcdf_variable_catalog (id, variable_name, mesh_type, element_type)
VALUES %s
ON CONFLICT (id) DO UPDATE SET
    variable_name = EXCLUDED.variable_name,
    mesh_type = EXCLUDED.mesh_type,
    element_type = EXCLUDED.element_type;
"""


def main():
    conn = psycopg2.connect(**TIMESCALE_DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    execute_values(cur, CATALOG_SEED_SQL, VARIABLE_CATALOG)
    conn.commit()

    cur.close()
    conn.close()

    print(
        "Tables institution_histogram_bar, background_forecast_depth, depth_history, "
        "netcdf_variable_catalog, mesh_elements, netcdf_values ready."
    )


if __name__ == "__main__":
    main()
