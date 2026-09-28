"""Regression pass for geocode_gh_shape(), the Photon adapter behind server.py's GET /geocode.

The request-building and country-filter checks patch place_search.urlopen, so they need no
network and always run:

    python test_place_search.py

The live check queries the real Photon instance for "Hồ Gươm" with a Hanoi bias point, and
asserts the Hanoi lake ranks first with no non-Vietnam hit. It needs network access, so it runs
only when asked:

    PHOTON_LIVE_TEST=1 python test_place_search.py
"""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from place_search import PlaceSearchValidationError, _parse_point, geocode_gh_shape

HANOI = (21.028511, 105.852402)


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc) -> None:
        return None


def feature(name: str, countrycode: str, lon: float, lat: float) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {"name": name, "countrycode": countrycode, "osm_id": 1, "osm_type": "W"},
    }


def photon_request(payload: dict, *args, **kwargs) -> tuple[dict, dict[str, list[str]]]:
    with patch("place_search.urlopen", return_value=FakeResponse(payload)) as urlopen:
        result = geocode_gh_shape(*args, **kwargs)
    request = urlopen.call_args.args[0]
    return result, parse_qs(urlparse(request.full_url).query)


def test_unbiased_request_filters_to_vietnam() -> None:
    _, query = photon_request({"features": []}, "query", point=None)
    assert query == {"q": ["query"], "lang": ["en"], "limit": ["6"], "countrycode": ["VN"]}, query


def test_biased_request_forwards_point_and_scale() -> None:
    _, query = photon_request({"features": []}, "query", point=(21.03, 105.85), location_bias_scale=0.2)
    assert query == {
        "q": ["query"],
        "lang": ["en"],
        "limit": ["6"],
        "countrycode": ["VN"],
        "lat": ["21.03"],
        "lon": ["105.85"],
        "location_bias_scale": ["0.2"],
    }, query


def test_non_vietnam_features_are_dropped() -> None:
    payload = {
        "features": [
            feature("Ottawa lake", "CA", -75.7, 45.4),
            feature("Hồ Hoàn Kiếm", "vn", 105.8524, 21.0287),
        ]
    }
    result, _ = photon_request(payload, "Hồ Gươm")
    assert [(hit["name"], hit["point"]) for hit in result["hits"]] == [
        ("Hồ Hoàn Kiếm", {"lat": 21.0287, "lng": 105.8524})
    ], result


def test_parse_point() -> None:
    assert _parse_point("21.03,105.85") == (21.03, 105.85)
    assert _parse_point(" 21.03 , 105.85 ") == (21.03, 105.85)
    assert _parse_point(None) is None
    assert _parse_point("") is None
    for bad in ("bad", "999,105.85", "21.03,", "21.03,105.85,1", "21.03,abc"):
        try:
            _parse_point(bad)
        except PlaceSearchValidationError as exc:
            assert str(exc) == "invalid point", (bad, str(exc))
        else:
            raise AssertionError(f"accepted malformed point {bad!r}")


def check_real_photon_ranks_hanoi_first() -> None:
    hits = geocode_gh_shape("Hồ Gươm", point=HANOI, location_bias_scale=0.2)["hits"]
    for hit in hits[:3]:
        print(f"  name={hit['name']!r} city={hit['city']!r} country={hit['country']!r}")
    assert hits, "Photon returned no Vietnam hit for Hồ Gươm"
    first = hits[0]
    assert "Hà Nội" in first["city"] or "Hanoi" in first["city"] or "Hà Nội" in first["state"], first
    vietnam = {"Việt Nam", "Vietnam"}
    assert all(hit["country"] in vietnam for hit in hits), [hit["country"] for hit in hits]


def main() -> int:
    test_unbiased_request_filters_to_vietnam()
    test_biased_request_forwards_point_and_scale()
    test_non_vietnam_features_are_dropped()
    test_parse_point()
    if os.environ.get("PHOTON_LIVE_TEST") == "1":
        check_real_photon_ranks_hanoi_first()
    else:
        print("PHOTON_LIVE_TEST unset; skipping the live Photon check", file=sys.stderr)
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
