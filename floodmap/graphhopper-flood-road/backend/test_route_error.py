"""Regression pass for route_error_payload(), which shapes the body server.py's POST /route sends
back when GraphHopper answers with an error. Needs no network or database:

    python test_route_error.py

graphhopper-maps' Api.ts reads `message` and `hints` from a 400 response, so a GraphHopper error
must reach it with those fields at the top level. Before this shape existed the body was
{"error": "<GraphHopper's JSON as a string>"}, Api.ts found no `message`, and the error banner
rendered empty.
"""

from __future__ import annotations

import json
import sys

from server import route_error_payload

CONNECTION_NOT_FOUND = {
    "message": "Connection between locations not found",
    "hints": [
        {
            "message": "Connection between locations not found",
            "details": "com.graphhopper.util.exceptions.ConnectionNotFoundException",
        }
    ],
}


def test_graphhopper_error_is_passed_through_unchanged() -> None:
    assert route_error_payload(json.dumps(CONNECTION_NOT_FOUND)) == CONNECTION_NOT_FOUND


def test_text_that_is_not_json_becomes_the_message() -> None:
    assert route_error_payload("Connection refused") == {
        "message": "Connection refused",
        "error": "Connection refused",
    }


def test_json_without_a_message_becomes_the_message() -> None:
    raw = json.dumps({"detail": "nope"})
    assert route_error_payload(raw) == {"message": raw, "error": raw}


def test_a_missing_error_still_gives_a_message() -> None:
    assert route_error_payload(None) == {"message": "Routing failed", "error": "Routing failed"}


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"{len(tests)} passed")
    sys.exit(0)
