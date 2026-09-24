import psycopg2

from db_config import DB_CONFIG

SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS road_segment (
    segment_id TEXT PRIMARY KEY,

    way_id TEXT NOT NULL,
    piece_index INTEGER NOT NULL,
    road_name TEXT,
    highway TEXT,
    length_m DOUBLE PRECISION NOT NULL,

    geom geometry(LineString,4326) NOT NULL,

    UNIQUE (way_id, piece_index)
);

CREATE INDEX IF NOT EXISTS idx_road_segment_geom
ON road_segment USING GIST(geom);
"""


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute(SQL)
    conn.commit()

    cur.close()
    conn.close()

    print("Table road_segment ready.")


if __name__ == "__main__":
    main()
