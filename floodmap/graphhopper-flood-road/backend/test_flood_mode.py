"""The forecast mode reader of GET /flood/mode, against a fake cursor.

    python test_flood_mode.py

The HTTP surface of the mode and of the pinned reads is in test_server.py, against a real PostGIS.
"""

from __future__ import annotations

from datetime import datetime

from flood_mode import DEMO, LIVE, PENDING, DemoStep, ModeStatus, read_mode

DECIDED = datetime(2026, 10, 12, 3, 15, 4)
PIN = ("20261010T210000", datetime(2026, 10, 10, 14, 15))


class FakeCursor:
    """Answers each query of read_mode from `answers`, keyed by a word of its SQL."""

    def __init__(self, answers):
        self.answers, self.row, self.queries = answers, None, []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql):
        self.queries.append(sql)
        self.row = next(row for word, row in self.answers if word in sql)

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor


def read(*, tables=(True, True), mode=None, pin=PIN):
    cursor = FakeCursor([("to_regclass", tables), ("FROM forecast_mode", mode), ("FROM demo_pin", pin)])
    return read_mode(FakeConnection(cursor)), cursor


def test_a_database_without_the_mode_table_is_live() -> None:
    status, cursor = read(tables=(False, True))
    assert status == ModeStatus(LIVE, None, None), status
    assert len(cursor.queries) == 1, cursor.queries


def test_a_database_with_no_decision_is_live() -> None:
    assert read(mode=None)[0] == ModeStatus(LIVE, None, None)


def test_live_and_pending_carry_no_demo_step_and_do_not_read_the_pin() -> None:
    for mode in (LIVE, PENDING):
        status, cursor = read(mode=(mode, DECIDED))
        assert status == ModeStatus(mode, DECIDED, None), status
        assert not any("demo_pin" in q and "to_regclass" not in q for q in cursor.queries), cursor.queries


def test_demo_carries_the_pinned_step_as_an_iso_time_with_an_offset() -> None:
    status, _ = read(mode=(DEMO, DECIDED))
    assert status == ModeStatus(DEMO, DECIDED, DemoStep("20261010T210000", "2026-10-10T14:15:00+00:00")), status


def test_demo_with_no_pinned_step_has_no_demo_step() -> None:
    assert read(mode=(DEMO, DECIDED), pin=None)[0] == ModeStatus(DEMO, DECIDED, None)
    assert read(tables=(True, False), mode=(DEMO, DECIDED))[0] == ModeStatus(DEMO, DECIDED, None)


def test_the_json_names_the_mode_the_time_and_the_step() -> None:
    status, _ = read(mode=(DEMO, DECIDED))
    assert status.as_json() == {
        "mode": "DEMO",
        "decided_at": "2026-10-12T03:15:04",
        "demo": {"run": "20261010T210000", "valid_time": "2026-10-10T14:15:00+00:00"},
    }, status.as_json()
    assert ModeStatus(LIVE, None, None).as_json() == {"mode": "LIVE", "decided_at": None, "demo": None}


def main() -> int:
    test_a_database_without_the_mode_table_is_live()
    test_a_database_with_no_decision_is_live()
    test_live_and_pending_carry_no_demo_step_and_do_not_read_the_pin()
    test_demo_carries_the_pinned_step_as_an_iso_time_with_an_offset()
    test_demo_with_no_pinned_step_has_no_demo_step()
    test_the_json_names_the_mode_the_time_and_the_step()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
