"""Read-only connectivity check for the 3Di integration (threedi-api-client).

Does NOT create, start, or modify anything on 3Di — only GET calls. Run this
first to confirm THREEDI_API_HOST / THREEDI_API_PERSONAL_API_TOKEN / ORG_UUID /
MODEL_ID / TEMPLATE_ID are all valid before running anything that actually
creates a simulation (which consumes 3Di compute quota).

Usage (from repo root, with a Python env that has requirements.txt installed):
    python airflow_tsm/scripts/test_threedi_connection.py
"""

import os
import sys

from dotenv import load_dotenv

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

# Load .env from the repo root (two levels up from airflow_tsm/scripts/)
load_dotenv(os.path.join(SCRIPTS_DIR, "..", "..", ".env"))

from threedi_client import get_client  # noqa: E402

ORG_UUID = os.getenv("ORG_UUID")
MODEL_ID = os.getenv("MODEL_ID", "83022")
TEMPLATE_ID = os.getenv("TEMPLATE_ID")


def main():
    failures = []

    print(f"THREEDI_API_HOST = {os.getenv('THREEDI_API_HOST', '(default) https://api.3di.live')}")
    token = os.getenv("THREEDI_API_PERSONAL_API_TOKEN")
    print(f"THREEDI_API_PERSONAL_API_TOKEN = {'set (' + str(len(token)) + ' chars)' if token else 'NOT SET'}")

    try:
        api = get_client()
        print("✅ ThreediApi client constructed")
    except Exception as e:
        print(f"❌ Failed to construct client: {e}")
        return 1

    if ORG_UUID:
        try:
            org = api.organisations_read(ORG_UUID)
            print(f"✅ Organisation OK: {org.name} ({org.unique_id})")
        except Exception as e:
            print(f"❌ organisations_read({ORG_UUID}) failed: {e}")
            failures.append("organisation")
    else:
        print("⚠️ ORG_UUID not set, skipping organisation check")

    try:
        model = api.threedimodels_read(int(MODEL_ID))
        print(f"✅ Model OK: {model.name} (id={model.id})")
    except Exception as e:
        print(f"❌ threedimodels_read({MODEL_ID}) failed: {e}")
        failures.append("model")

    if TEMPLATE_ID:
        try:
            template = api.simulation_templates_read(int(TEMPLATE_ID))
            print(f"✅ Template OK: {template.name} (id={TEMPLATE_ID})")
        except Exception as e:
            print(f"❌ simulation_templates_read({TEMPLATE_ID}) failed: {e}")
            failures.append("template")
    else:
        print("⚠️ TEMPLATE_ID not set, skipping template check")

    if failures:
        print(f"\n❌ {len(failures)} check(s) failed: {', '.join(failures)}")
        return 1

    print("\n🎉 All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
