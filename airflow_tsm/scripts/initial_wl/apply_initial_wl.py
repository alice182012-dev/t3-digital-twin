"""Apply an initial 1D waterlevel resource on 3Di, built on the official
threedi-api-client. MinIO/CSV logic is unchanged; the 3Di resource-create +
upload flow uses the typed client and threedi_api_client.files.upload_file
instead of a raw requests.put.
"""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import boto3
from threedi_api_client.files import upload_file
from threedi_api_client.openapi import InitialWaterlevel, Upload

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from threedi_client import get_client  # noqa: E402

MODEL_ID = os.getenv("MODEL_ID", "83022")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")

MINIO_BUCKET = os.getenv("INITIAL_WL_MINIO_BUCKET", "initial-wl")
MINIO_PREFIX = os.getenv("INITIAL_WL_MINIO_PREFIX", "dummy-files")


def get_latest_csv():
    s3 = boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )

    paginator = s3.get_paginator("list_objects_v2")

    csv_files = []
    for page in paginator.paginate(Bucket=MINIO_BUCKET, Prefix=MINIO_PREFIX):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".csv"):
                csv_files.append(obj)

    if not csv_files:
        raise ValueError("No CSV found in MinIO")

    latest = max(csv_files, key=lambda x: x["LastModified"])
    key = latest["Key"]

    local_path = f"/tmp/{os.path.basename(key)}"
    s3.download_file(MINIO_BUCKET, key, local_path)

    print(f"📥 CSV: {key}")
    return local_path


def load_csv(csv_file):
    node_ids = []
    values = []

    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            node_ids.append(int(row["node_id"]))
            values.append(float(row["initial_waterlevel"]))

    return {"node_ids": node_ids, "values": values}


def create_resource(api):
    resource = api.threedimodels_initial_waterlevels_create(
        MODEL_ID, InitialWaterlevel(dimension="one_d")
    )
    return resource.id


def upload_initial_waterlevels(api, resource_id, data):
    filename = f"initial_wl_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    upload = api.threedimodels_initial_waterlevels_upload(
        resource_id, MODEL_ID, Upload(filename=filename)
    )

    print("⬆️ Uploading initial waterlevels JSON to 3Di storage...")

    tmp_path = Path(f"/tmp/{filename}")
    tmp_path.write_text(json.dumps(data), encoding="utf-8")
    try:
        upload_file(upload.put_url, tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    print("✅ Uploaded initial waterlevels JSON")


def run_apply_initial_wl():
    csv_path = get_latest_csv()
    data = load_csv(csv_path)

    api = get_client()
    resource_id = create_resource(api)
    upload_initial_waterlevels(api, resource_id, data)

    print(f"✅ initial_wl_id = {resource_id}")

    return resource_id, None
