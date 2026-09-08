from __future__ import annotations

import json
import os
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PHOTON_BASE_URL = os.environ.get("PHOTON_BASE_URL", "https://photon.komoot.io").rstrip("/")
PHOTON_TIMEOUT_SECONDS = 5
PHOTON_RESULT_LIMIT = 6
MAX_QUERY_LENGTH = 120


class PlaceSearchValidationError(ValueError):
    pass


class PlaceSearchTimeout(RuntimeError):
    pass


class PlaceSearchUnavailable(RuntimeError):
    pass


def _optional_number(value: str | None, name: str, minimum: float, maximum: float) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PlaceSearchValidationError(f"invalid {name}") from exc
    if number < minimum or number > maximum:
        raise PlaceSearchValidationError(f"invalid {name}")
    return number


def _address(properties: dict, name: str) -> str:
    parts: list[str] = []
    street = str(properties.get("street") or "").strip()
    house_number = str(properties.get("housenumber") or "").strip()
    street_line = " ".join(part for part in (house_number, street) if part)
    if street_line and street_line.casefold() != name.casefold():
        parts.append(street_line)
    for key in ("district", "city", "county", "state", "postcode", "country"):
        value = str(properties.get(key) or "").strip()
        if value and value.casefold() != name.casefold() and value.casefold() not in {part.casefold() for part in parts}:
            parts.append(value)
    return ", ".join(parts)


def _normalize_feature(feature: object, index: int) -> dict | None:
    if not isinstance(feature, dict):
        return None
    properties = feature.get("properties")
    geometry = feature.get("geometry")
    if not isinstance(properties, dict) or not isinstance(geometry, dict):
        return None
    if str(properties.get("countrycode") or "").upper() != "VN":
        return None
    coordinates = geometry.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        return None
    try:
        lon = float(coordinates[0])
        lat = float(coordinates[1])
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    name = str(properties.get("name") or properties.get("street") or properties.get("city") or "").strip()
    if not name:
        return None
    osm_type = str(properties.get("osm_type") or "").strip()
    osm_id = str(properties.get("osm_id") or "").strip()
    result_id = f"{osm_type}:{osm_id}" if osm_type and osm_id else f"photon:{index}:{lat:.6f}:{lon:.6f}"
    return {
        "id": result_id,
        "name": name,
        "address": _address(properties, name),
        "kind": str(properties.get("type") or properties.get("osm_value") or "place"),
        "lat": lat,
        "lon": lon,
    }


def _photon_bbox(properties: dict) -> list[float] | None:
    extent = properties.get("extent")
    if isinstance(extent, list) and len(extent) == 4:
        # Photon's extent is [minLon, maxLat, maxLon, minLat]; GraphHopper's
        # Bbox is [minLon, minLat, maxLon, maxLat].
        min_lon, max_lat, max_lon, min_lat = (float(v) for v in extent)
        return [min_lon, min_lat, max_lon, max_lat]
    return None


def geocode_gh_shape(query: str, locale: str = "en", limit: int = PHOTON_RESULT_LIMIT) -> dict:
    """graphhopper-maps' Api.ts expects the GraphHopper Geocoding API shape
    ({hits: [...]}, see src/api/graphhopper.d.ts GeocodingResult/GeocodingHit),
    which differs from raw Photon's GeoJSON FeatureCollection. This adapts
    one to the other so the vendored fork's geocodingApi can point straight
    at this backend with no source changes."""
    query = str(query or "").strip()
    if not query:
        return {"hits": [], "took": 0}

    params = [("q", query), ("lang", locale or "en"), ("limit", str(limit))]
    request = Request(
        f"{PHOTON_BASE_URL}/api?{urlencode(params)}",
        headers={"Accept": "application/json", "User-Agent": "FloodRouteVietnam/1.0"},
    )
    try:
        with urlopen(request, timeout=PHOTON_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (socket.timeout, TimeoutError) as exc:
        raise PlaceSearchTimeout("geocoding timed out") from exc
    except (HTTPError, URLError) as exc:
        raise PlaceSearchUnavailable("geocoding provider is unavailable") from exc

    hits = []
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        coordinates = (feature.get("geometry") or {}).get("coordinates")
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            continue
        lon, lat = float(coordinates[0]), float(coordinates[1])
        name = str(properties.get("name") or properties.get("street") or properties.get("city") or "")
        if not name:
            continue
        bbox = _photon_bbox(properties)
        hits.append(
            {
                "point": {"lat": lat, "lng": lon},
                "extent": bbox or [lon, lat, lon, lat],
                "osm_id": str(properties.get("osm_id") or ""),
                "osm_type": str(properties.get("osm_type") or ""),
                "osm_key": str(properties.get("osm_key") or ""),
                "osm_value": str(properties.get("osm_value") or ""),
                "name": name,
                "country": str(properties.get("country") or ""),
                "city": str(properties.get("city") or ""),
                "state": str(properties.get("state") or ""),
                "street": str(properties.get("street") or ""),
                "housenumber": str(properties.get("housenumber") or ""),
                "postcode": str(properties.get("postcode") or ""),
            }
        )
    return {"hits": hits[:limit], "took": 0}


def search_places(
    query: str,
    lat_value: str | None = None,
    lon_value: str | None = None,
    zoom_value: str | None = None,
) -> list[dict]:
    query = str(query or "").strip()
    if len(query) < 2:
        raise PlaceSearchValidationError("query must contain at least 2 characters")
    if len(query) > MAX_QUERY_LENGTH:
        raise PlaceSearchValidationError(f"query must not exceed {MAX_QUERY_LENGTH} characters")

    lat = _optional_number(lat_value, "lat", -90, 90)
    lon = _optional_number(lon_value, "lon", -180, 180)
    zoom = _optional_number(zoom_value, "zoom", 1, 20)
    if zoom is not None and not zoom.is_integer():
        raise PlaceSearchValidationError("invalid zoom")
    zoom = int(zoom) if zoom is not None else None
    if (lat is None) != (lon is None):
        raise PlaceSearchValidationError("lat and lon must be provided together")

    params: list[tuple[str, str]] = [
        ("q", query),
        ("countrycode", "VN"),
        ("lang", "default"),
        ("limit", str(PHOTON_RESULT_LIMIT)),
    ]
    if lat is not None and lon is not None:
        params.extend((("lat", str(lat)), ("lon", str(lon))))
    if zoom is not None:
        params.append(("zoom", str(zoom)))

    request = Request(
        f"{PHOTON_BASE_URL}/api?{urlencode(params)}",
        headers={
            "Accept": "application/json",
            "User-Agent": "FloodRouteVietnam/1.0",
        },
    )
    try:
        with urlopen(request, timeout=PHOTON_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (socket.timeout, TimeoutError) as exc:
        raise PlaceSearchTimeout("place search timed out") from exc
    except HTTPError as exc:
        raise PlaceSearchUnavailable(f"place search provider returned HTTP {exc.code}") from exc
    except URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            raise PlaceSearchTimeout("place search timed out") from exc
        raise PlaceSearchUnavailable("place search provider is unavailable") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PlaceSearchUnavailable("place search provider returned invalid data") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        raise PlaceSearchUnavailable("place search provider returned invalid data")
    results = []
    for index, feature in enumerate(payload["features"]):
        normalized = _normalize_feature(feature, index)
        if normalized:
            results.append(normalized)
    return results[:PHOTON_RESULT_LIMIT]
