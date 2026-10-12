import psycopg2

from db_config import DB_CONFIG

SQL = """
-- One row per rain gate decision of flood_mapping_full, written by task 0_check_forecast_rain (US-111, D-030).
-- slot is the 15-minute slot of the DAG run, in UTC without an offset, so a rerun of the task replaces its row.
-- standing_flood is NULL when the forecast rain alone opened the gate, because the task then does not read the flood.
CREATE TABLE IF NOT EXISTS forecast_mode (
    slot TIMESTAMP PRIMARY KEY,
    decided_at TIMESTAMP NOT NULL DEFAULT NOW(),
    rain_peak_mm_hr DOUBLE PRECISION NOT NULL,
    gate_mm_hr DOUBLE PRECISION NOT NULL,
    standing_flood BOOLEAN,
    mode TEXT NOT NULL CHECK (mode IN ('LIVE', 'PENDING', 'DEMO'))
);
"""


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.close()
    conn.close()

    print("Table forecast_mode ready.")


if __name__ == "__main__":
    main()
