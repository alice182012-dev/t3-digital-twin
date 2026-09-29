from __future__ import annotations

import os
from contextlib import contextmanager

from psycopg2.pool import ThreadedConnectionPool

DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "storage-postgres"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "database": os.environ.get("POSTGRES_DB", "minio_custom"),
    "user": os.environ.get("POSTGRES_USER", "minio_custom"),
    "password": os.environ.get("POSTGRES_PASSWORD"),
}

# server.py's ThreadingHTTPServer runs one thread per request. A pooled connection
# pays PostGIS's ~57ms first-call raster-library load once per pooled connection
# instead of once per request (see artifacts/docs/blockers/flood-points-connection-per-request.md).
# Keep the ceiling well under storage-postgres's connection limit, shared with
# Airflow and the storage backend.
POOL_MIN_SIZE = int(os.environ.get("FLOOD_DB_POOL_MIN", "1"))
POOL_MAX_SIZE = int(os.environ.get("FLOOD_DB_POOL_MAX", "10"))

_pool: ThreadedConnectionPool | None = None


def _get_pool() -> ThreadedConnectionPool:
    # Built lazily, not at import time, so a caller that patches DB_CONFIG after
    # importing this module (both test_server.py and test_flood_forecast.py do)
    # still gets a pool that connects to the patched target.
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(POOL_MIN_SIZE, POOL_MAX_SIZE, **DB_CONFIG)
    return _pool


@contextmanager
def connection():
    """Borrow a pooled connection for the caller's block.

    Always rolled back before returning to the pool, so a request that left an
    open transaction (an uncommitted write, or a failed query) can't leave the
    next borrower starting inside someone else's aborted transaction.
    """
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        conn.rollback()
        pool.putconn(conn)
