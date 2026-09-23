import os

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "storage-postgres"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "minio_custom"),
    "user": os.getenv("POSTGRES_USER", "minio_custom"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

TIMESCALE_DB_CONFIG = {
    "host": os.getenv("TIMESCALE_HOST", "timescaledb"),
    "port": int(os.getenv("TIMESCALE_PORT", "5432")),
    "database": os.getenv("TIMESCALE_DB", "flood_metrics"),
    "user": os.getenv("TIMESCALE_USER", "flood_metrics"),
    "password": os.getenv("TIMESCALE_PASSWORD"),
}
