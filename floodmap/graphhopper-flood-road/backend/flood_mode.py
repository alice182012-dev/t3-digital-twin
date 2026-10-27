"""The forecast mode of the flood map and the pinned demo step, for GET /flood/mode (US-130, D-030).

The pipeline writes one `forecast_mode` row per rain gate decision (scripts/forecast_mode.py), and `demo_pin` holds the
step of the demo flood (scripts/database/demo_pin.py). The newest row by slot is the mode.

    LIVE     rain is forecast above the gate or a flood stands, and a step is published: the map shows the newest run.
    PENDING  the same gate, but no step is published yet: the map is dry with a warning.
    DEMO     no rain and no standing flood: the map shows the pinned step.

A database with no decision yet is LIVE, which is what the backend did before this module. In DEMO, GET /flood/points,
GET /flood/areas, and POST /route read the pinned run and step. `demo` is None when the mode is not DEMO and when no step is
pinned, and then those calls read the newest run as in LIVE.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

LIVE, PENDING, DEMO = "LIVE", "PENDING", "DEMO"


@dataclass(frozen=True)
class DemoStep:
    run: str
    valid_time: str  # ISO 8601 with an offset, the form the other endpoints take


@dataclass(frozen=True)
class ModeStatus:
    mode: str
    decided_at: datetime | None
    demo: DemoStep | None

    def as_json(self) -> dict:
        return {
            "mode": self.mode,
            "decided_at": None if self.decided_at is None else self.decided_at.isoformat(),
            "demo": None if self.demo is None else {"run": self.demo.run, "valid_time": self.demo.valid_time},
        }


_TABLES_SQL = "SELECT to_regclass('forecast_mode') IS NOT NULL, to_regclass('demo_pin') IS NOT NULL"
_MODE_SQL = "SELECT mode, decided_at FROM forecast_mode ORDER BY slot DESC LIMIT 1"
_PIN_SQL = "SELECT run_ts, valid_time_utc FROM demo_pin"


def read_mode(conn) -> ModeStatus:
    """The newest decision. A database without the tables, or without a row, is LIVE with no demo step."""
    with conn.cursor() as cur:
        cur.execute(_TABLES_SQL)
        has_mode, has_pin = cur.fetchone()
        if not has_mode:
            return ModeStatus(LIVE, None, None)
        cur.execute(_MODE_SQL)
        row = cur.fetchone()
        if row is None:
            return ModeStatus(LIVE, None, None)
        mode, decided_at = row
        demo = None
        if mode == DEMO and has_pin:
            cur.execute(_PIN_SQL)
            pin = cur.fetchone()
            if pin is not None:
                run_ts, valid_time_utc = pin
                demo = DemoStep(run_ts, valid_time_utc.replace(tzinfo=timezone.utc).isoformat())
    return ModeStatus(mode, decided_at, demo)
