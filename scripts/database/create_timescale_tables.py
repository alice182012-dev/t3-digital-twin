import psycopg2

from db_config import TIMESCALE_DB_CONFIG

SQL = """
-- 0b_ensure_schema of flood_mapping_full and the flood_history DAG both run this script, so two runs can overlap.
SELECT pg_advisory_xact_lock(hashtext('create_timescale_tables'));

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
    'depth_history', by_range('valid_time', INTERVAL '7 days'), if_not_exists => TRUE
);

-- Changing the compression settings fails once a chunk is compressed, so they are set only the first time.
DO $$
BEGIN
    IF NOT (
        SELECT compression_enabled FROM timescaledb_information.hypertables
        WHERE format('%I.%I', hypertable_schema, hypertable_name)::regclass = 'depth_history'::regclass
    ) THEN
        ALTER TABLE depth_history SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'segment_id',
            timescaledb.compress_orderby = 'valid_time'
        );
    END IF;
END
$$;

-- compress_after equals the chunk interval, so each chunk is compressed once it closes (D-032).
SELECT add_compression_policy('depth_history', compress_after => INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('depth_history', drop_after => INTERVAL '365 days', if_not_exists => TRUE);

-- Every moment a run covers, wet or not. A moment listed here with no depth_history row for a piece means the
-- piece was dry; a moment missing here is unknown (D-032, D-036). It is a hypertable with the same chunks and drop
-- policy as depth_history, so a moment is forgotten when its depths are, and an old moment never reads as dry.
CREATE TABLE IF NOT EXISTS history_moment (
    valid_time TIMESTAMPTZ PRIMARY KEY,
    issued_at TIMESTAMPTZ NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (valid_time >= issued_at)
);

SELECT create_hypertable(
    'history_moment', by_range('valid_time', INTERVAL '7 days'), if_not_exists => TRUE
);
SELECT add_retention_policy('history_moment', drop_after => INTERVAL '365 days', if_not_exists => TRUE);
"""


def main():
    conn = psycopg2.connect(**TIMESCALE_DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.close()
    conn.close()

    print("Tables institution_histogram_bar, background_forecast_depth, depth_history, history_moment ready.")


if __name__ == "__main__":
    main()
