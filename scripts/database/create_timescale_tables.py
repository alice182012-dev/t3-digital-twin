import psycopg2

from db_config import TIMESCALE_DB_CONFIG

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
"""


def main():
    conn = psycopg2.connect(**TIMESCALE_DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.close()
    conn.close()

    print("Tables institution_histogram_bar, background_forecast_depth, depth_history ready.")


if __name__ == "__main__":
    main()
