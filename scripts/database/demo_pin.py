"""The pinned step of the demo flood (US-129, D-030).

The demo is one frame, the step of the stored storm with the most wet edges. `demo_pin` holds that step's run, and every
prune of a run table keeps the run: `kept_runs` is the set a prune passes where it passed only the run it publishes.

Usage: python demo_pin.py [--run RUN_TS --valid-time 2026-10-10T15:00:00]
Without arguments it chooses the step with the most wet edges in edge_depth, and replaces the pin.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from typing import NamedTuple

import create_demo_pin_table


class Pin(NamedTuple):
    run_ts: str
    valid_time_utc: datetime
    wet_edges: int


_CHOOSE_SQL = """
SELECT run_ts, valid_time_utc, count(*) AS wet_edges
FROM edge_depth
GROUP BY run_ts, valid_time_utc
ORDER BY wet_edges DESC, run_ts, valid_time_utc
LIMIT 1
"""

_COUNT_SQL = "SELECT count(*) FROM edge_depth WHERE run_ts = %s AND valid_time_utc = %s"

_WRITE_SQL = """
INSERT INTO demo_pin (run_ts, valid_time_utc, wet_edges) VALUES (%(run_ts)s, %(valid_time_utc)s, %(wet_edges)s)
ON CONFLICT (singleton) DO UPDATE SET
    run_ts = EXCLUDED.run_ts, valid_time_utc = EXCLUDED.valid_time_utc, wet_edges = EXCLUDED.wet_edges,
    chosen_at = NOW()
"""


def read_pin(cur) -> Pin | None:
    """The pin, or None when there is none. A database without the table has no pin."""
    cur.execute("SELECT to_regclass('demo_pin') IS NOT NULL")
    if not cur.fetchone()[0]:
        return None
    cur.execute("SELECT run_ts, valid_time_utc, wet_edges FROM demo_pin")
    row = cur.fetchone()
    return None if row is None else Pin(*row)


def kept_runs(cur, publishing: str) -> frozenset[str]:
    """The runs a prune must keep: the one being published and the pinned one."""
    pin = read_pin(cur)
    return frozenset({publishing} if pin is None else {publishing, pin.run_ts})


def choose_peak(cur) -> Pin:
    """The step of edge_depth with the most wet edges, the earliest on a tie."""
    cur.execute(_CHOOSE_SQL)
    row = cur.fetchone()
    if row is None:
        raise ValueError("edge_depth has no wet edge, so no step can be pinned")
    return Pin(*row)


def write_pin(conn, run_ts: str | None = None, valid_time_utc: datetime | None = None) -> Pin:
    """Chooses the peak step, or takes the run and time given, and replaces the pin in one transaction."""
    with conn, conn.cursor() as cur:
        cur.execute(create_demo_pin_table.SQL)
        if run_ts is None:
            pin = choose_peak(cur)
        else:
            cur.execute(_COUNT_SQL, (run_ts, valid_time_utc))
            wet_edges = cur.fetchone()[0]
            if wet_edges == 0:
                raise ValueError(f"edge_depth has no wet edge for run {run_ts} at {valid_time_utc}")
            pin = Pin(run_ts, valid_time_utc, wet_edges)
        cur.execute(_WRITE_SQL, pin._asdict())
    return pin


def main(argv: list[str] | None = None) -> Pin:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run")
    parser.add_argument("--valid-time", type=datetime.fromisoformat)
    args = parser.parse_args(argv)
    if (args.run is None) != (args.valid_time is None):
        parser.error("--run and --valid-time go together")

    import psycopg2

    from db_config import DB_CONFIG

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        pin = write_pin(conn, args.run, args.valid_time)
    finally:
        conn.close()
    print(f"Pinned run {pin.run_ts} at {pin.valid_time_utc} UTC, {pin.wet_edges} wet edges.")
    return pin


if __name__ == "__main__":
    main()
