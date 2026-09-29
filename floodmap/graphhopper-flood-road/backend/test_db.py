"""Unit tests for db.connection()'s pool contract: release, waiting when the pool is full,
and how server.py reports a wait that runs out. No real PostGIS needed: db._get_pool is
monkeypatched to a fake pool, so this runs anywhere psycopg2 is installed. See
test_server.py for the integration test against a real PostGIS.

    python test_db.py
"""
from __future__ import annotations

import threading
import time
import urllib.error
import urllib.request
from contextlib import ExitStack, contextmanager
from http.server import ThreadingHTTPServer

from psycopg2 import InterfaceError
from psycopg2.pool import PoolError

import db
import server


class FakeConn:
    def __init__(self) -> None:
        self.rolled_back = False
        self.committed = False

    def rollback(self) -> None:
        self.rolled_back = True

    def commit(self) -> None:
        self.committed = True


class DeadConn(FakeConn):
    def rollback(self) -> None:
        raise InterfaceError("connection already closed")


class FakePool:
    def __init__(self, conn: FakeConn) -> None:
        self._conn = conn
        self.returned: list[FakeConn] = []
        self.closed: list[FakeConn] = []

    def getconn(self) -> FakeConn:
        return self._conn

    def putconn(self, conn: FakeConn, close: bool = False) -> None:
        self.returned.append(conn)
        if close:
            self.closed.append(conn)


class CappedPool:
    """Raises PoolError at capacity, as psycopg2's ThreadedConnectionPool does. It never waits."""

    def __init__(self, capacity: int) -> None:
        self._lock = threading.Lock()
        self._free = [FakeConn() for _ in range(capacity)]

    def getconn(self) -> FakeConn:
        with self._lock:
            if not self._free:
                raise PoolError("connection pool exhausted")
            return self._free.pop()

    def putconn(self, conn: FakeConn, close: bool = False) -> None:
        with self._lock:
            self._free.append(FakeConn() if close else conn)


@contextmanager
def patched(**attrs):
    originals = {name: getattr(db, name) for name in attrs}
    for name, value in attrs.items():
        setattr(db, name, value)
    try:
        yield
    finally:
        for name, value in originals.items():
            setattr(db, name, value)


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


def test_burst_above_the_ceiling_waits_instead_of_failing() -> None:
    pool = CappedPool(db.POOL_MAX_SIZE)
    outcomes: list[str] = []

    def request() -> None:
        try:
            with db.connection():
                time.sleep(0.02)
            outcomes.append("ok")
        except Exception as exc:
            outcomes.append(repr(exc))

    burst = 3 * db.POOL_MAX_SIZE
    with patched(_get_pool=lambda: pool):
        threads = [threading.Thread(target=request) for _ in range(burst)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    assert outcomes == ["ok"] * burst, f"{burst} concurrent requests must all get a connection: {outcomes}"


def test_wait_that_runs_out_raises_pool_timeout() -> None:
    pool = CappedPool(db.POOL_MAX_SIZE)
    with patched(_get_pool=lambda: pool, POOL_WAIT_SECONDS=0.05), ExitStack() as held:
        for _ in range(db.POOL_MAX_SIZE):
            held.enter_context(db.connection())
        raised = False
        try:
            with db.connection():
                pass
        except db.PoolTimeout:
            raised = True
        assert raised, "an 11th borrower must raise PoolTimeout once the wait limit passes"


@with_fake_pool
def test_dead_connection_is_discarded_not_leaked(conn: FakeConn, pool: FakePool) -> None:
    pool._conn = DeadConn()
    with db.connection():
        pass
    assert pool.closed == [pool._conn], "a connection whose rollback fails must be closed, not reused"
    assert pool.returned == [pool._conn], "the pool must still get the connection back, or its slot leaks"


def test_full_pool_is_503_with_retry_after() -> None:
    @contextmanager
    def no_connection_frees_up():
        raise db.PoolTimeout("no connection freed up")
        yield

    with patched(connection=no_connection_frees_up):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{httpd.server_address[1]}/flood/points?lat=21.0&lon=105.7&valid_time=2026-05-22T09:00:00%2B00:00"
            try:
                urllib.request.urlopen(url, timeout=5)
                raise AssertionError("expected an HTTP error")
            except urllib.error.HTTPError as err:
                assert err.code == 503, f"a full pool is the server's overload, not a bad request: {err.code}"
                assert err.headers["Retry-After"], "a 503 must tell the client when to retry"
        finally:
            httpd.shutdown()
            httpd.server_close()


def main() -> int:
    test_normal_exit_rolls_back_and_returns()
    test_exception_still_rolls_back_and_returns()
    test_burst_above_the_ceiling_waits_instead_of_failing()
    test_wait_that_runs_out_raises_pool_timeout()
    test_dead_connection_is_discarded_not_leaked()
    test_full_pool_is_503_with_retry_after()
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
