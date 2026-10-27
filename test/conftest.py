import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = str(ROOT / "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

# scripts/create_simulation.py names these at import time. A client older than the
# pinned one lacks some, so give only the missing ones a stand-in.
CREATE_SIMULATION_OPENAPI_NAMES = (
    "Action",
    "ApiException",
    "FromTemplate",
    "TimedSavedState",
    "TimeseriesRain",
)


def install_missing_openapi_names():
    import threedi_api_client.openapi as openapi

    missing = [n for n in CREATE_SIMULATION_OPENAPI_NAMES if not hasattr(openapi, n)]
    for name in missing:
        base = Exception if name == "ApiException" else object
        setattr(openapi, name, type(name, (base,), {"__module__": openapi.__name__}))
    return missing


STAND_INS = install_missing_openapi_names()
