import psycopg2

from db_config import DB_CONFIG

SQL = """
-- One row per run and published output (run_output.Output), written last by each output's task.
CREATE TABLE IF NOT EXISTS flood_run_output (
    run_ts TEXT NOT NULL,
    output TEXT NOT NULL,
    published_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (run_ts, output)
);
"""


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.close()
    conn.close()

    print("Table flood_run_output ready.")


if __name__ == "__main__":
    main()
