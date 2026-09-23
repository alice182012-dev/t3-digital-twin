import psycopg2

from db_config import DB_CONFIG

# Lives in storage-postgres, next to flood_road_values, so the extractor does not depend on the
# TimescaleDB service. Story 4 of timescaledb-and-flood-metrics copies from this table.
#
# segment_key is md5(ST_AsEWKB(geom_4326)) of the flood_road_values rows the metrics came from:
# that table has no segment ID, and road_name repeats across a road's segments.
#
# The CHECKs mirror metrics.Passability, so a row cannot claim a closure without its times, or a
# restoration without being closed first.
SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS flood_segment_metrics (
    id BIGSERIAL PRIMARY KEY,

    run_ts TEXT NOT NULL,
    segment_key TEXT NOT NULL,
    road_name TEXT,
    vehicle_type TEXT NOT NULL,
    impassable_from_m DOUBLE PRECISION NOT NULL,

    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,

    peak_time TIMESTAMP,
    peak_depth_m DOUBLE PRECISION,
    time_to_peak INTERVAL,
    peak_at_window_end BOOLEAN,
    recession_onset TIMESTAMP,

    forecast_depth_1h_m DOUBLE PRECISION,
    forecast_depth_2h_m DOUBLE PRECISION,

    passability TEXT NOT NULL,
    closed_at TIMESTAMP,
    pre_closure_time TIMESTAMP,
    restored_at TIMESTAMP,

    geom_4326 geometry(Geometry,4326) NOT NULL,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE (run_ts, segment_key, vehicle_type),

    CHECK (passability IN ('never_impassable', 'restored', 'not_restored')),
    CHECK ((passability = 'never_impassable') = (closed_at IS NULL)),
    CHECK ((closed_at IS NULL) = (pre_closure_time IS NULL)),
    CHECK ((passability = 'restored') = (restored_at IS NOT NULL)),
    CHECK ((peak_time IS NULL) = (peak_depth_m IS NULL)),
    CHECK ((peak_time IS NULL) = (time_to_peak IS NULL)),
    CHECK ((peak_time IS NULL) = (peak_at_window_end IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_flood_segment_metrics_run_ts
ON flood_segment_metrics(run_ts);

CREATE INDEX IF NOT EXISTS idx_flood_segment_metrics_pre_closure_time
ON flood_segment_metrics(pre_closure_time);

CREATE INDEX IF NOT EXISTS idx_flood_segment_metrics_geom_4326
ON flood_segment_metrics USING GIST(geom_4326);
"""


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.close()
    conn.close()

    print("Table flood_segment_metrics ready.")


if __name__ == "__main__":
    main()
