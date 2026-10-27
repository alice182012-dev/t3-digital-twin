import psycopg2

from db_config import DB_CONFIG

SQL = """
-- The one step of the demo flood (US-129, D-030). The row is a singleton. Every prune of a run table keeps run_ts,
-- so the step stays however many runs follow. valid_time_utc is in UTC without an offset, like edge_depth.
CREATE TABLE IF NOT EXISTS demo_pin (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    run_ts TEXT NOT NULL,
    valid_time_utc TIMESTAMP NOT NULL,
    wet_edges INTEGER NOT NULL,
    chosen_at TIMESTAMP NOT NULL DEFAULT NOW()
);
"""


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.close()
    conn.close()

    print("Table demo_pin ready.")


if __name__ == "__main__":
    main()
