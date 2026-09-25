"""Cross-run timestep listing + local-time conversion for list_timesteps(), against a real Postgres.

Run it against any throwaway Postgres (no PostGIS needed: these functions never
touch geom):

    docker run -d --rm --name flood-verify-pg -e POSTGRES_PASSWORD=test \
        -e POSTGRES_DB=floodtest -p 55432:5432 postgres:15
    FLOOD_TEST_DSN='postgresql://postgres:test@127.0.0.1:55432/floodtest' \
        python test_flood_extent_runs.py
"""

from __future__ import annotations

import os
import sys

import psycopg2

from flood_extent_runs import latest_run, list_timesteps

OLD_RUN = "20260522T060000"
NEW_RUN = "20260522T120000"

# (run, valid_time_utc, is_empty). Both runs published 09:00 and 12:00; the newer run found
# 09:00 dry. Only the older run has 06:00, so the listing has to reach back to it.
STEPS = [
    (OLD_RUN, "2026-05-22 06:00:00", False),
    (OLD_RUN, "2026-05-22 09:00:00", False),
    (OLD_RUN, "2026-05-22 12:00:00", False),
    (NEW_RUN, "2026-05-22 09:00:00", True),
    (NEW_RUN, "2026-05-22 12:00:00", False),
]


def reset(conn, steps) -> None:
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS flood_extent_polygon, flood_extent_step;")
        cur.execute(
            """
            CREATE TABLE flood_extent_polygon (
                run_ts text NOT NULL,
                valid_time_utc timestamp NOT NULL,
                dn_code integer NOT NULL,
                area_m2 double precision NOT NULL
            );
            CREATE TABLE flood_extent_step (
                run_ts text NOT NULL,
                valid_time_utc timestamp NOT NULL,
                is_empty boolean NOT NULL,
                PRIMARY KEY (run_ts, valid_time_utc)
            );
            """
        )
        for run, valid_time, is_empty in steps:
            cur.execute("INSERT INTO flood_extent_step VALUES (%s, %s, %s);", (run, valid_time, is_empty))
            if not is_empty:
                cur.execute(
                    "INSERT INTO flood_extent_polygon VALUES (%s, %s, 1, 100), (%s, %s, 2, 200);",
                    (run, valid_time, run, valid_time),
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

    reset(conn, STEPS)
    assert latest_run(conn) == NEW_RUN

    default = list_timesteps(conn)
    # 06:00/09:00/12:00 UTC -> 13:00/16:00/19:00 Vietnam local (+07:00), matching the MinIO tile
    # folder names built from the same offset in scripts/flood_extent/publish.py.
    assert default == [
        {"valid_time": "2026-05-22T13:00:00+07:00", "run": OLD_RUN},
        {"valid_time": "2026-05-22T16:00:00+07:00", "run": NEW_RUN},
        {"valid_time": "2026-05-22T19:00:00+07:00", "run": NEW_RUN},
    ], default
    assert list_timesteps(conn, "latest") == default
    assert list_timesteps(conn, None) == default

    assert list_timesteps(conn, NEW_RUN) == [
        {"valid_time": "2026-05-22T16:00:00+07:00", "run": NEW_RUN},
        {"valid_time": "2026-05-22T19:00:00+07:00", "run": NEW_RUN},
    ]
    assert list_timesteps(conn, "20260101T000000") == []

    conn.close()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
