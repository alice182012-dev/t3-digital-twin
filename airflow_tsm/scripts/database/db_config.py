import os

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "storage-postgres"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "minio_custom"),
    "user": os.getenv("POSTGRES_USER", "minio_custom"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}
