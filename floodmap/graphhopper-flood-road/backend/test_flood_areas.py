"""Single-run invariant for list_timesteps(), against a real Postgres.

Run it against any throwaway Postgres (no PostGIS needed — these two functions
never touch geom_4326):

    docker run -d --rm --name flood-verify-pg -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=floodtest -p 55432:5432 postgres:15
    PYTHONPATH=../scripts \
        FLOOD_TEST_DSN='postgresql://postgres:test@127.0.0.1:55432/floodtest' \
        python test_flood_areas.py

flood_areas imports flood_utils, which the Dockerfile supplies by copying
../scripts alongside ../backend; PYTHONPATH stands in for that outside the image.
"""

from __future__ import annotations

import os
import sys

import psycopg2

from flood_areas import latest_run, list_timesteps

OLD_RUN = "2026-05-22T06:00:00+00:00"
NEW_RUN = "2026-05-22T12:00:00+00:00"

# The newer run is missing the 06:00 forecast_time that the older run has, so a
# cross-run composite and a single-run answer differ observably.
ROWS = [
    (OLD_RUN, "2026-05-22T06:00:00+00:00"),
    (OLD_RUN, "2026-05-22T09:00:00+00:00"),
    (OLD_RUN, "2026-05-22T12:00:00+00:00"),
    (NEW_RUN, "2026-05-22T09:00:00+00:00"),
    (NEW_RUN, "2026-05-22T12:00:00+00:00"),
]


def reset(conn, rows) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS flood_road_values;")
        cur.execute(
            """
            CREATE TABLE flood_road_values (
                timestamp timestamptz NOT NULL,
                forecast_time timestamptz NOT NULL,
                depth double precision NOT NULL
            );
            """
        )
        # Two rows per (run, forecast_time) so DISTINCT is doing real work.
        for run, forecast_time in rows:
            cur.execute(
                "INSERT INTO flood_road_values VALUES (%s, %s, 0.3), (%s, %s, 0.7);",
                (run, forecast_time, run, forecast_time),
            )
    conn.commit()


def main() -> int:
    dsn = os.environ.get("FLOOD_TEST_DSN")
    if not dsn:
        print("FLOOD_TEST_DSN unset; skipping", file=sys.stderr)
        return 0

    conn = psycopg2.connect(dsn)
    with conn.cursor() as cur:
        cur.execute("SET TIME ZONE 'UTC';")

    reset(conn, [])
    assert latest_run(conn) is None, "empty table must yield None, not raise"
    assert list_timesteps(conn) == [], "empty table must yield []"

    reset(conn, ROWS)
    assert latest_run(conn) == NEW_RUN

    default = list_timesteps(conn)
    assert default == [
        {"valid_time": "2026-05-22T09:00:00+00:00", "run": NEW_RUN},
        {"valid_time": "2026-05-22T12:00:00+00:00", "run": NEW_RUN},
    ], default
    assert list_timesteps(conn, "latest") == default
    assert list_timesteps(conn, None) == default

    assert list_timesteps(conn, OLD_RUN) == [
        {"valid_time": "2026-05-22T06:00:00+00:00", "run": OLD_RUN},
        {"valid_time": "2026-05-22T09:00:00+00:00", "run": OLD_RUN},
        {"valid_time": "2026-05-22T12:00:00+00:00", "run": OLD_RUN},
    ]
    assert list_timesteps(conn, "2026-05-22T03:00:00+00:00") == []

    conn.close()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
