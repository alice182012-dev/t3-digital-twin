#!/usr/bin/env python3
"""GraphHopper flood-road backend.

Fork of ../valhalla-flood-road-test/backend/server.py for Workstream B of
the Phase 2 plan. PostGIS (flood_road_values.geom_4326) is now the source
of truth for flood geometry instead of a polled MinIO GeoJSON file, and
GraphHopper's custom_model.areas replaces Valhalla's linear_cost_factors /
exclude_locations. /flood/areas and POST /route share one derivation
(flood_areas.derive_areas) so the map overlay and the routing gate can
never drift apart.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import get_connection  # noqa: E402
from flood_areas import DEFAULT_BUFFER_M, DEFAULT_MIN_AREA_M2, DEFAULT_SIMPLIFY_M, build_custom_model, derive_areas, list_runs, list_timesteps  # noqa: E402
from place_search import (  # noqa: E402
    PlaceSearchTimeout,
    PlaceSearchUnavailable,
    PlaceSearchValidationError,
    geocode_gh_shape,
    search_places,
)
from tiles import TileNotFound, parse_tile_path, render_tile  # noqa: E402

GRAPHHOPPER_URL = os.environ.get("GRAPHHOPPER_URL", "http://localhost:8989")
AREAS_CACHE_TTL_SECONDS = int(os.environ.get("FLOOD_AREAS_CACHE_TTL_SECONDS", "30"))

_areas_cache: dict[tuple, tuple[float, dict]] = {}


def cached_areas(valid_time: str, vehicle_type: str, run: str, buffer_m: float, simplify_m: float, min_area_m2: float) -> dict:
    key = (valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2)
    now = time.monotonic()
    hit = _areas_cache.get(key)
    if hit and now - hit[0] < AREAS_CACHE_TTL_SECONDS:
        return hit[1]
    conn = get_connection()
    try:
        areas_fc = derive_areas(conn, valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2)
    finally:
        conn.close()
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


def graphhopper_health() -> dict:
    req = urllib.request.Request(f"{GRAPHHOPPER_URL.rstrip('/')}/health", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            return {"ok": True, "status": res.status}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def postgis_health() -> dict:
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT PostGIS_Version();")
                version = cur.fetchone()[0]
        finally:
            conn.close()
        return {"ok": True, "postgis_version": version}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_png(self, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "public, max-age=600")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

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
                conn = get_connection()
                try:
                    self._send(200, {"runs": list_runs(conn)})
                finally:
                    conn.close()
            elif parsed.path == "/flood/timesteps":
                run = qs.get("run", ["latest"])[0]
                conn = get_connection()
                try:
                    self._send(200, {"run": run, "timesteps": list_timesteps(conn, run)})
                finally:
                    conn.close()
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
            elif parsed.path == "/places/search":
                results = search_places(
                    qs.get("q", [""])[0],
                    qs.get("lat", [None])[0],
                    qs.get("lon", [None])[0],
                    qs.get("zoom", [None])[0],
                )
                self._send(200, {"results": results})
            elif parsed.path == "/geocode":
                self._send(200, geocode_gh_shape(qs.get("q", [""])[0], qs.get("locale", ["en"])[0]))
            elif parsed.path.startswith("/tiles/"):
                request = parse_tile_path(parsed.path)
                if request is None:
                    raise TileNotFound("malformed tile path")
                self._send_png(render_tile(request))
            else:
                self._send(404, {"error": "not found"})
        except TileNotFound as exc:
            self._send(404, {"error": str(exc)})
        except PlaceSearchValidationError as exc:
            self._send(400, {"error": str(exc)})
        except PlaceSearchTimeout:
            self._send(504, {"error": "Place search timed out. Please try again."})
        except PlaceSearchUnavailable:
            self._send(502, {"error": "Place search is temporarily unavailable."})
        except Exception as exc:
            self._send(400, {"error": str(exc)})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        try:
            if urlparse(self.path).path == "/route":
                self._handle_route(body)
            else:
                self._send(404, {"error": "not found"})
        except Exception as exc:
            self._send(400, {"error": str(exc)})

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
        response is returned as-is so Api.ts needs no changes to parse it.
        """
        valid_time = body.pop("valid_time", None)
        run = body.pop("run", "latest")
        vehicle_type = body.pop("vehicle_type", None) or body.get("profile", "motorbike")
        buffer_m = float(body.pop("buffer", DEFAULT_BUFFER_M))
        simplify_m = float(body.pop("simplify", DEFAULT_SIMPLIFY_M))
        min_area_m2 = float(body.pop("min_area", DEFAULT_MIN_AREA_M2))

        if valid_time:
            areas_fc = cached_areas(valid_time, vehicle_type, run, buffer_m, simplify_m, min_area_m2)
            if areas_fc["features"]:
                body["ch.disable"] = True
                body["custom_model"] = build_custom_model(areas_fc)

        response = post_graphhopper_route(body)
        if response.get("ok"):
            self._send(response.get("status") or 200, response["json"])
        else:
            self._send(response.get("status") or 400, {"error": response.get("error")})


def main() -> int:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8010"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Backend listening on http://{host}:{port}, GraphHopper at {GRAPHHOPPER_URL}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
