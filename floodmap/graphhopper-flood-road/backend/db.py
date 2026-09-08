from __future__ import annotations

import os

import psycopg2

DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "storage-postgres"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "database": os.environ.get("POSTGRES_DB", "minio_custom"),
    "user": os.environ.get("POSTGRES_USER", "minio_custom"),
    "password": os.environ.get("POSTGRES_PASSWORD"),
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)
