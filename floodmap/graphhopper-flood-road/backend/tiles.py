#!/usr/bin/env python3
"""Raster depth tiles for the flood map overlay.

Serves `GET /tiles/{run}/{valid_time}/{z}/{x}/{y}.png` straight off the
depth GeoTIFFs the forecast pipeline writes, replacing the buffered
road-sliver polygons the UI used to draw. Colors come from
`scripts/flood_utils.depth_bands_m`, the same table `flood_areas.py` turns
into `custom_model.priority`, so the legend a user reads and the cutoff
routing enforces cannot drift apart.

`rio_tiler`, `rasterio` and `numpy` are imported inside the render path,
not at module scope, so the pure functions here (path resolution, band
coloring, cache) stay importable and testable without those packages.
"""
from __future__ import annotations

import os
import re
import sys
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from flood_utils import depth_bands_m  # noqa: E402

TIMESERIES_DIR = Path(os.environ.get("FLOOD_TIMESERIES_DIR", "/data/flood-timeseries"))
TILE_CACHE_MAX_ENTRIES = int(os.environ.get("FLOOD_TILE_CACHE_MAX_ENTRIES", "750"))
TILE_CACHE_TTL_SECONDS = int(os.environ.get("FLOOD_TILE_CACHE_TTL_SECONDS", "600"))

# `server.py` routes on the raw `urlparse(self.path).path` and calls
# `unquote` nowhere, so the run/valid_time segments arrive with literal
# colons. Match them permissively here and let `normalize_stamp` be the
# only gate: an exact `\d{8}_\d{6}` shape is stronger than any charset
# blacklist and closes path traversal at the same time.
TILE_PATH_RE = re.compile(r"^/tiles/([^/]+)/([^/]+)/(\d{1,2})/(\d{1,9})/(\d{1,9})\.png$")

COMPACT_STAMP_RE = re.compile(r"^\d{8}_\d{6}$")

# Deepest band reads darkest. Keys are the band ids in flood_utils.DEPTH_BANDS.
BAND_RGB = {
    "b4": (127, 0, 0),
    "b3": (227, 74, 51),
    "b2": (253, 187, 132),
}

TILE_SIZE = 256


class TileNotFound(Exception):
    """No `.tif` on disk for this run/valid_time. A client-input problem,
    answered with 404 and a JSON body rather than a rasterio traceback."""


@dataclass(frozen=True)
class TileRequest:
    """Parsed and normalized at the HTTP boundary, so everything downstream
    only ever sees compact stamps that already matched the exact shape."""

    run: str
    valid_time: str
    z: int
    x: int
    y: int


def normalize_stamp(raw: str) -> str:
    """`2026-08-09T16:42:00` -> `20260809_164200`.

    The API hands out ISO stamps with colons; the filesystem uses the
    compact form. Anything not landing on exactly `\\d{8}_\\d{6}` is
    rejected.
    """
    candidate = raw.strip().replace("-", "").replace(":", "").replace("T", "_").replace(" ", "_")
    if not COMPACT_STAMP_RE.match(candidate):
        raise TileNotFound(f"unrecognised timestamp: {raw!r}")
    return candidate


def parse_tile_path(path: str) -> TileRequest | None:
    """Regex against the raw path first, then unquote, then normalize."""
    match = TILE_PATH_RE.match(path)
    if not match:
        return None
    run_raw, valid_raw, z, x, y = match.groups()
    return TileRequest(
        run=normalize_stamp(unquote(run_raw)),
        valid_time=normalize_stamp(unquote(valid_raw)),
        z=int(z),
        x=int(x),
        y=int(y),
    )


def resolve_tif(run: str, valid_time: str, root: Path | None = None) -> Path:
    """`depth_<run>_<end>/depth_<valid_time>.tif`.

    The `_<end>` suffix is a separate end-of-window stamp, not derivable
    from the run id, so the run directory is found by glob rather than
    string-built.
    """
    base = Path(root) if root is not None else TIMESERIES_DIR
    run_compact = normalize_stamp(run)
    valid_compact = normalize_stamp(valid_time)
    run_dirs = sorted(d for d in base.glob(f"depth_{run_compact}_*") if d.is_dir())
    if not run_dirs:
        raise TileNotFound(f"no run directory for run {run!r}")
    for run_dir in run_dirs:
        candidate = run_dir / f"depth_{valid_compact}.tif"
        if candidate.is_file():
            return candidate
    raise TileNotFound(f"no raster for run {run!r} at valid_time {valid_time!r}")


def color_for_depth(depth_m: float, vehicle_type: str = "motorbike") -> tuple[int, int, int] | None:
    """`None` means transparent. Anything shallower than the shallowest
    routing band has no color that would correspond to a routing decision,
    so it is left unpainted rather than given an invented band."""
    for band in depth_bands_m(vehicle_type):
        if depth_m >= band["band_min"]:
            return BAND_RGB[band["id"]]
    return None


class TileCache:
    """TTL plus a hard entry cap with LRU eviction.

    `cached_areas` keys on a handful of (valid_time, vehicle_type, run)
    combos and gets away with an unbounded dict. Tile keys carry z/x/y and
    grow without bound as a user pans, so memory has to be capped rather
    than merely aged out.
    """

    def __init__(self, max_entries: int = TILE_CACHE_MAX_ENTRIES, ttl_seconds: int = TILE_CACHE_TTL_SECONDS) -> None:
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._entries: OrderedDict[tuple, tuple[float, bytes]] = OrderedDict()
        self._lock = threading.Lock()

    def __len__(self) -> int:
        return len(self._entries)

    def get(self, key: tuple) -> bytes | None:
        with self._lock:
            hit = self._entries.get(key)
            if hit is None:
                return None
            if time.monotonic() - hit[0] >= self.ttl_seconds:
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return hit[1]

    def put(self, key: tuple, value: bytes) -> None:
        with self._lock:
            self._entries[key] = (time.monotonic(), value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)


_tile_cache = TileCache()

_overview_lock = threading.Lock()
_overviews_done: set[str] = set()


def ensure_overviews(tif_path: Path) -> None:
    """Build overviews into the source `.tif` the first time it is served.

    The pipeline writes these rasters without overviews, so a city-wide
    zoom would otherwise decimate and warp the full-resolution grid for
    every tile of every request. `ThreadingHTTPServer` can hand two first
    touches of the same file to two threads at once, hence the lock.
    """
    key = str(tif_path)
    if key in _overviews_done:
        return
    with _overview_lock:
        if key in _overviews_done:
            return
        import rasterio
        from rasterio.enums import Resampling

        try:
            with rasterio.open(tif_path, "r+") as dataset:
                if not dataset.overviews(1):
                    dataset.build_overviews([2, 4, 8, 16], Resampling.average)
                    dataset.update_tags(ns="rio_overview", resampling="average")
        except Exception as exc:
            # A read-only mount or a concurrent writer costs latency, not
            # correctness. Record the attempt so it is not retried per tile.
            print(f"tiles: overview build skipped for {tif_path}: {exc}", flush=True)
        _overviews_done.add(key)


def colorize(depth, invalid, vehicle_type: str = "motorbike"):
    """Vectorized `color_for_depth`. Bands come back deepest-first, so the
    first band to claim a pixel is the deepest one that contains it."""
    import numpy

    height, width = depth.shape
    rgb = numpy.zeros((3, height, width), dtype="uint8")
    painted = numpy.zeros((height, width), dtype=bool)
    for band in depth_bands_m(vehicle_type):
        selected = (~painted) & (~invalid) & (depth >= band["band_min"])
        red, green, blue = BAND_RGB[band["id"]]
        rgb[0][selected] = red
        rgb[1][selected] = green
        rgb[2][selected] = blue
        painted |= selected
    return rgb, painted


def render_tile(request: TileRequest, vehicle_type: str = "motorbike", root: Path | None = None) -> bytes:
    key = (request.run, request.valid_time, request.z, request.x, request.y, vehicle_type)
    hit = _tile_cache.get(key)
    if hit is not None:
        return hit

    tif_path = resolve_tif(request.run, request.valid_time, root)
    ensure_overviews(tif_path)

    import numpy
    from rio_tiler.errors import TileOutsideBounds
    from rio_tiler.io import Reader
    from rio_tiler.models import ImageData

    try:
        with Reader(str(tif_path)) as reader:
            image = reader.tile(request.x, request.y, request.z, tilesize=TILE_SIZE)
        band = image.array[0]
        depth = numpy.ma.filled(band, 0.0).astype("float64")
        invalid = numpy.ma.getmaskarray(band) | numpy.zeros(depth.shape, dtype=bool)
        rgb, painted = colorize(depth, invalid, vehicle_type)
    except TileOutsideBounds:
        rgb = numpy.zeros((3, TILE_SIZE, TILE_SIZE), dtype="uint8")
        painted = numpy.zeros((TILE_SIZE, TILE_SIZE), dtype=bool)

    transparent = numpy.repeat((~painted)[numpy.newaxis, ...], 3, axis=0)
    png = ImageData(numpy.ma.MaskedArray(rgb, mask=transparent)).render(img_format="PNG", add_mask=True)
    _tile_cache.put(key, png)
    return png
