#!/usr/bin/env python3
"""GraphHopper flood-road backend.

Fork of ../valhalla-flood-road-test/backend/server.py for Workstream B of
the Phase 2 plan. PostGIS (flood_road_values.geom_4326) is now the source
of truth for flood geometry instead of a polled MinIO GeoJSON file, and
GraphHopper's custom_model.areas replaces Valhalla's linear_cost_factors /
exclude_locations. /flood/areas and POST /route share one derivation
(flood_areas.derive_areas) so the map overlay and the routing gate can
never drift apart.

/flood/runs and /flood/timesteps are a separate concern: they back the
map's timestep picker, not routing, and read flood_extent_runs.py's
flood_extent_polygon table instead. See artifacts/raw/T3-Digital-Twin_Architecture.md section 4.2.
/flood/points reads the exact depth at one point from flood_depth_raster_tile;
see flood_points.py. POST /flood/forecast reads depth over time along a route from the same
table; see flood_forecast.py. POST /flood/profile reads the depth at samples along a route at one
timestep; see flood_profile.py.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
from datetime import datetime, timezone
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import db  # noqa: E402
import departures  # noqa: E402
import edge_depth_reader  # noqa: E402
import time_aware_route  # noqa: E402
from flood_utils import vehicle_threshold_cm  # noqa: E402
from flood_areas import DEFAULT_BUFFER_M, DEFAULT_MIN_AREA_M2, DEFAULT_SIMPLIFY_M, build_custom_model, derive_areas  # noqa: E402
from flood_extent_runs import list_runs, list_timesteps  # noqa: E402
from flood_forecast import lookup_forecast, parse_forecast_body  # noqa: E402
from flood_profile import lookup_profile, parse_profile_body  # noqa: E402
from flood_points import FloodPointNotFound, lookup_point_depth, parse_point_query  # noqa: E402
from place_search import (  # noqa: E402
    PlaceSearchTimeout,
    PlaceSearchUnavailable,
    PlaceSearchValidationError,
    _optional_number,
    _parse_point,
    geocode_gh_shape,
    reverse_place,
    search_places,
)

GRAPHHOPPER_URL = os.environ.get("GRAPHHOPPER_URL", "http://localhost:8989")
AREAS_CACHE_TTL_SECONDS = int(os.environ.get("FLOOD_AREAS_CACHE_TTL_SECONDS", "30"))

_areas_cache: dict[tuple, tuple[float, dict]] = {}


def cached_areas(valid_time: str, vehicle_type: str, run: str, buffer_m: float, simplify_m: float, min_area_m2: float) -> dict:
    key = (valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2)
    now = time.monotonic()
    hit = _areas_cache.get(key)
    if hit and now - hit[0] < AREAS_CACHE_TTL_SECONDS:
        return hit[1]
    with db.connection() as conn:
        areas_fc = derive_areas(conn, valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2)
    _areas_cache[key] = (now, areas_fc)
    return areas_fc


def post_graphhopper_route(body: dict, timeout: int = 15) -> dict:
    """The one place `ch.disable` lives. This build rejects the documented
    `?ch.disable=true` query-param form ("custom_model is currently not
    supported for speed mode") — it must be a field in the JSON body."""
    req = urllib.request.Request(
        f"{GRAPHHOPPER_URL.rstrip('/')}/route",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return {"ok": True, "status": res.status, "json": json.loads(res.read().decode("utf-8"))}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": exc.read().decode("utf-8", errors="replace")}
    except Exception as exc:
        return {"ok": False, "status": None, "error": str(exc)}


def route_error_payload(raw: str | None) -> dict:
    """The body for a failed /route. graphhopper-maps' Api.ts reads `message` and `hints` from a
    400 response, so GraphHopper's own error JSON goes through unchanged. Anything else becomes
    the message, with `error` kept for callers that read it."""
    try:
        parsed = json.loads(raw) if raw else None
    except ValueError:
        parsed = None
    if isinstance(parsed, dict) and isinstance(parsed.get("message"), str):
        return parsed
    text = raw or "Routing failed"
    return {"message": text, "error": text}


def graphhopper_health() -> dict:
    req = urllib.request.Request(f"{GRAPHHOPPER_URL.rstrip('/')}/health", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return {"ok": True, "status": res.status}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def postgis_health() -> dict:
    try:
        with db.connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT PostGIS_Version();")
            version = cur.fetchone()[0]
        return {"ok": True, "postgis_version": version}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict, headers: dict[str, str] | None = None) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self) -> None:
        self._send(204, {})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        try:
            if parsed.path == "/health":
                self._send(200, {"ok": True, "graphhopper": graphhopper_health(), "postgis": postgis_health()})
            elif parsed.path in ("/info", "/nearest"):
                # graphhopper-maps calls these on routingApi directly (app bootstrap
                # and click-to-snap); no flood logic involved, just forward as-is.
                self._proxy_get_to_graphhopper(parsed.path, parsed.query)
            elif parsed.path == "/flood/runs":
                with db.connection() as conn:
                    self._send(200, {"runs": list_runs(conn)})
            elif parsed.path == "/flood/timesteps":
                run = qs.get("run", ["latest"])[0]
                with db.connection() as conn:
                    self._send(200, {"run": run, "timesteps": list_timesteps(conn, run)})
            elif parsed.path == "/flood/areas":
                valid_time = qs.get("valid_time", [""])[0]
                if not valid_time:
                    raise ValueError("valid_time is required")
                vehicle_type = qs.get("vehicle_type", ["motorbike"])[0]
                run = qs.get("run", ["latest"])[0]
                buffer_m = float(qs.get("buffer", [DEFAULT_BUFFER_M])[0])
                simplify_m = float(qs.get("simplify", [DEFAULT_SIMPLIFY_M])[0])
                min_area_m2 = float(qs.get("min_area", [DEFAULT_MIN_AREA_M2])[0])
                self._send(200, cached_areas(valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2))
            elif parsed.path == "/flood/points":
                query = parse_point_query(qs)
                with db.connection() as conn:
                    self._send(200, lookup_point_depth(conn, query))
            elif parsed.path == "/places/search":
                results = search_places(
                    qs.get("q", [""])[0],
                    qs.get("lat", [None])[0],
                    qs.get("lon", [None])[0],
                    qs.get("zoom", [None])[0],
                )
                self._send(200, {"results": results})
            elif parsed.path == "/places/reverse":
                place = reverse_place(qs.get("lat", [None])[0], qs.get("lon", [None])[0])
                self._send(200, {"result": place})
            elif parsed.path == "/geocode":
                point = _parse_point(qs.get("point", [None])[0])
                location_bias_scale = _optional_number(
                    qs.get("location_bias_scale", [None])[0], "location_bias_scale", 0.0, 1.0
                )
                self._send(
                    200,
                    geocode_gh_shape(
                        qs.get("q", [""])[0],
                        qs.get("locale", ["en"])[0],
                        point=point,
                        location_bias_scale=location_bias_scale,
                    ),
                )
            else:
                self._send(404, {"error": "not found"})
        except FloodPointNotFound as exc:
            self._send(404, {"error": str(exc)})
        except PlaceSearchValidationError as exc:
            self._send(400, {"error": str(exc)})
        except PlaceSearchTimeout:
            self._send(504, {"error": "Place search timed out. Please try again."})
        except PlaceSearchUnavailable:
            self._send(502, {"error": "Place search is temporarily unavailable."})
        except db.PoolTimeout:
            self._send_busy()
        except Exception as exc:
            self._send(400, {"error": str(exc)})

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            path = urlparse(self.path).path
            if path == "/route":
                self._handle_route(body)
            elif path == "/route/departures":
                self._handle_departures(body)
            elif path == "/flood/forecast":
                query = parse_forecast_body(body, datetime.now(timezone.utc))
                with db.connection() as conn:
                    self._send(200, lookup_forecast(conn, query))
            elif path == "/flood/profile":
                profile_query = parse_profile_body(body)
                with db.connection() as conn:
                    self._send(200, lookup_profile(conn, profile_query))
            else:
                self._send(404, {"error": "not found"})
        except FloodPointNotFound as exc:
            self._send(404, {"error": str(exc)})
        except db.PoolTimeout:
            self._send_busy()
        except Exception as exc:
            self._send(400, {"error": str(exc)})

    def _send_busy(self) -> None:
        self._send(503, {"error": "The server is busy. Please try again."}, {"Retry-After": "1"})

    def _proxy_get_to_graphhopper(self, path: str, query: str) -> None:
        url = f"{GRAPHHOPPER_URL.rstrip('/')}{path}"
        if query:
            url += f"?{query}"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                self._send(res.status, json.loads(res.read().decode("utf-8")))
        except urllib.error.HTTPError as exc:
            self._send(exc.code, {"error": exc.read().decode("utf-8", errors="replace")})
        except Exception as exc:
            self._send(502, {"error": str(exc)})

    def _handle_route(self, body: dict) -> None:
        """Transparent GraphHopper /route proxy.

        graphhopper-maps sends this body verbatim (points, profile,
        points_encoded, ...) — see graphhopper-maps' src/api/Api.ts. Instead
        of relying on its built-in custom_model editor (which would require
        the browser to hold ~1000 flood-polygon vertices client-side), the
        vendored fork's TimeSlider/FloodStore additions tack on three plain
        fields (valid_time, run, vehicle_type) to that same body. We strip
        those here, derive the graded custom_model server-side from PostGIS,
        and forward the rest of the request unchanged. GraphHopper's own
        response, success or error, is returned as-is so Api.ts needs no changes to parse it.

        With TIME_AWARE_ROUTING on, the request goes to the time-aware engine first and falls back to today's request
        when the engine cannot run (time_aware_route.py, US-052).
        """
        def flood_custom_model(valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2):
            areas_fc = cached_areas(valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2)
            return build_custom_model(areas_fc) if areas_fc["features"] else None

        outcome = time_aware_route.route_request(
            body,
            post=post_graphhopper_route,
            custom_model=flood_custom_model,
            enabled=time_aware_route.flag_enabled(os.environ),
            now=datetime.now(timezone.utc),
            defaults=(DEFAULT_BUFFER_M, DEFAULT_SIMPLIFY_M, DEFAULT_MIN_AREA_M2),
        )
        if outcome.ok:
            self._send(outcome.status, outcome.data)
        else:
            self._send(outcome.status, route_error_payload(outcome.data))


    def _handle_departures(self, body: dict) -> None:
        """The earliest clear departure of the usual route (US-053, departures.py). The client sends only points and
        profile. The clock, the margin, and the depth limit are the server's."""
        outcome = departures.departures_request(
            body,
            post=post_graphhopper_route,
            load_table=lambda: edge_depth_reader.read_latest(Path(os.environ.get("EDGE_TABLE_DIR", "/tables"))),
            limit_for=lambda profile: int(vehicle_threshold_cm(profile)),
            now=datetime.now(timezone.utc),
        )
        if outcome.ok:
            self._send(outcome.status, outcome.data)
        else:
            self._send(outcome.status, route_error_payload(outcome.data))


def main() -> int:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8010"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Backend listening on http://{host}:{port}, GraphHopper at {GRAPHHOPPER_URL}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
