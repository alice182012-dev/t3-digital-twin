"""Shared factory for the official `threedi-api-client` library.

This is the single point of config for the `*_v2.py` scripts, which reimplement
create_simulation.py / download_result.py / initial_wl/*.py on top of
threedi_api_client.ThreediApi instead of hand-rolled `requests` calls.

Auth note: THREEDI_API_KEY (used by the original scripts) is HTTP Basic auth
(a base64'd username:password pair) and is NOT compatible with ThreediApi's
personal-API-token auth. Set THREEDI_API_PERSONAL_API_TOKEN separately, using
a personal API token generated from the 3Di platform.
"""

import os

from threedi_api_client import ThreediApi

THREEDI_API_HOST = os.getenv("THREEDI_API_HOST", "https://api.3di.live")
THREEDI_API_PERSONAL_API_TOKEN = os.getenv("THREEDI_API_PERSONAL_API_TOKEN")


def get_client() -> ThreediApi:
    """Build a `ThreediApi` instance from THREEDI_API_HOST / THREEDI_API_PERSONAL_API_TOKEN."""
    if not THREEDI_API_PERSONAL_API_TOKEN:
        raise ValueError(
            "THREEDI_API_PERSONAL_API_TOKEN is not set. This is a 3Di personal "
            "API token, not the legacy THREEDI_API_KEY (which is HTTP Basic auth "
            "and not accepted by the official client)."
        )

    config = {
        "THREEDI_API_HOST": THREEDI_API_HOST,
        "THREEDI_API_PERSONAL_API_TOKEN": THREEDI_API_PERSONAL_API_TOKEN,
    }
    return ThreediApi(config=config)
