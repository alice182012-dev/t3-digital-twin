"""Unit tests for db.connection()'s pool release contract. No real PostGIS needed:
db._get_pool is monkeypatched to a fake pool, so this runs anywhere psycopg2 is
installed. See test_server.py for the integration test against a real PostGIS.

    python test_db.py
"""
from __future__ import annotations

import db


class FakeConn:
    def __init__(self) -> None:
        self.rolled_back = False
        self.committed = False

    def rollback(self) -> None:
        self.rolled_back = True

    def commit(self) -> None:
        self.committed = True


class FakePool:
    def __init__(self, conn: FakeConn) -> None:
        self._conn = conn
        self.returned: list[FakeConn] = []

    def getconn(self) -> FakeConn:
        return self._conn

    def putconn(self, conn: FakeConn) -> None:
        self.returned.append(conn)


def with_fake_pool(test):
    def run() -> None:
        conn = FakeConn()
        pool = FakePool(conn)
        original = db._get_pool
        db._get_pool = lambda: pool
        try:
            test(conn, pool)
        finally:
            db._get_pool = original

    return run


@with_fake_pool
def test_normal_exit_rolls_back_and_returns(conn: FakeConn, pool: FakePool) -> None:
    with db.connection() as borrowed:
        assert borrowed is conn
    assert conn.rolled_back, "connection must be rolled back before returning to the pool"
    assert not conn.committed, "connection() never commits; callers that write must commit themselves"
    assert pool.returned == [conn], "connection must be returned to the pool exactly once"


@with_fake_pool
def test_exception_still_rolls_back_and_returns(conn: FakeConn, pool: FakePool) -> None:
    raised = False
    try:
        with db.connection():
            raise ValueError("boom")
    except ValueError:
        raised = True
    assert raised, "the caller's exception must propagate, not be swallowed"
    assert conn.rolled_back, "a connection left with an open transaction must still be rolled back"
    assert pool.returned == [conn], "a connection must be returned to the pool even on error"


def main() -> int:
    test_normal_exit_rolls_back_and_returns()
    test_exception_still_rolls_back_and_returns()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
