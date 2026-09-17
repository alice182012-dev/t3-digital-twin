#!/usr/bin/env python3
"""Raster depth tiles for the flood map overlay.

Serves `GET /tiles/{run}/{valid_time}/{z}/{x}/{y}.png` straight off the
depth GeoTIFFs the forecast pipeline writes, replacing the buffered
road-sliver polygons the UI used to draw. Colors come from
`DISPLAY_DEPTH_BANDS_CM` below, the same fixed-cm bands and exact hex
values `graphhopper-maps/src/floodmap/depthScale.ts` uses for `FloodLegend`
— this is the map's own paint, so it has to match what the legend promises,
not `flood_utils.DEPTH_BANDS` (routing-cost bands, vehicle-relative, a
different scale by design; see that file's own comment).

`rio_tiler`, `rasterio` and `numpy` are imported inside the render path,
not at module scope, so the pure functions here (path resolution, band
coloring, cache) stay importable and testable without those packages.
"""
from __future__ import annotations

import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

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

# Exact cm thresholds and hex colors from depthScale.ts's DISPLAY_DEPTH_BANDS (values taken
# from the approved mockup's legend swatches). Ordered deepest-first: `color_for_depth`/
# `colorize` scan top-to-bottom and the first band whose min a pixel clears wins, so a pixel
# at 65cm gets d5, not d1. Anything shallower than d1's 1cm floor is left unpainted
# (transparent) rather than invented a color for.
DISPLAY_DEPTH_BANDS_CM: tuple[tuple[str, float, tuple[int, int, int]], ...] = (
    ("d5", 60.0, (22, 63, 128)),
    ("d4", 30.0, (47, 111, 191)),
    ("d3", 10.0, (93, 154, 217)),
    ("d2", 5.0, (158, 197, 236)),
    ("d1", 1.0, (207, 227, 247)),
)

TILE_SIZE = 256

# At this raster's native 1m resolution, a wet cell surrounded by dry ones can
# render as a single output pixel, or even sub-pixel, at city zoom. "max"
# resampling already keeps that pixel's real depth (see render_tile), but a
# lone pixel against a huge dry backdrop reads as sensor noise to a human
# viewer rather than a real, isolated hazard. Growing it to a small minimum
# on-screen radius is a display choice only: it never touches the depth
# values colorize() reads, just which already-painted pixels' color a nearby
# unpainted pixel inherits.
DISPLAY_MIN_FEATURE_RADIUS_PX = 2


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


def color_for_depth(depth_m: float) -> tuple[int, int, int] | None:
    """`None` means transparent. Anything shallower than d1's 1cm floor has
    no display band, so it is left unpainted rather than given an invented
    color."""
    depth_cm = depth_m * 100.0
    for _band_id, min_cm, rgb in DISPLAY_DEPTH_BANDS_CM:
        if depth_cm >= min_cm:
            return rgb
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


def colorize(depth, invalid):
    """Vectorized `color_for_depth`. Bands come back deepest-first, so the
    first band to claim a pixel is the deepest one that contains it."""
    import numpy

    height, width = depth.shape
    depth_cm = depth * 100.0
    rgb = numpy.zeros((3, height, width), dtype="uint8")
    painted = numpy.zeros((height, width), dtype=bool)
    for _band_id, min_cm, (red, green, blue) in DISPLAY_DEPTH_BANDS_CM:
        selected = (~painted) & (~invalid) & (depth_cm >= min_cm)
        rgb[0][selected] = red
        rgb[1][selected] = green
        rgb[2][selected] = blue
        painted |= selected
    return rgb, painted


def dilate_painted(rgb, painted, radius: int = DISPLAY_MIN_FEATURE_RADIUS_PX):
    """Grow `painted` outward by `radius` pixels, 8-connected, one ring per
    iteration. A newly covered pixel inherits the color of whichever already-
    painted neighbor reaches it first; for the isolated single-pixel case
    this fix targets there is only one such neighbor, so the ambiguity this
    creates when two differently colored regions grow into each other does
    not arise in practice. No scipy dependency: shift-and-OR over the 8
    neighbors is enough at this radius."""
    import numpy

    out_rgb = [channel.copy() for channel in rgb]
    out_painted = painted.copy()
    frontier = painted
    for _ in range(radius):
        newly_total = numpy.zeros_like(out_painted)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                shifted_frontier = numpy.roll(numpy.roll(frontier, dy, axis=0), dx, axis=1)
                if dy == 1:
                    shifted_frontier[0, :] = False
                elif dy == -1:
                    shifted_frontier[-1, :] = False
                if dx == 1:
                    shifted_frontier[:, 0] = False
                elif dx == -1:
                    shifted_frontier[:, -1] = False
                newly = shifted_frontier & ~out_painted & ~newly_total
                if not newly.any():
                    continue
                for c in range(3):
                    shifted_channel = numpy.roll(numpy.roll(rgb[c], dy, axis=0), dx, axis=1)
                    out_rgb[c][newly] = shifted_channel[newly]
                newly_total |= newly
        out_painted |= newly_total
        frontier = newly_total
    return numpy.stack(out_rgb), out_painted


def render_tile(request: TileRequest, root: Path | None = None) -> bytes:
    key = (request.run, request.valid_time, request.z, request.x, request.y)
    hit = _tile_cache.get(key)
    if hit is not None:
        return hit

    tif_path = resolve_tif(request.run, request.valid_time, root)

    import numpy
    from rio_tiler.errors import TileOutsideBounds
    from rio_tiler.io import Reader
    from rio_tiler.models import ImageData

    try:
        with Reader(str(tif_path)) as reader:
            # reproject_method="max": the source CRS differs from every tile's Web Mercator, so
            # every read reprojects, and this raster's real flood cells are extremely sparse
            # (often single isolated 1m pixels surrounded by dry cells). The default resampling
            # ("nearest") picks one arbitrary source pixel per output pixel and mostly misses
            # them; "max" instead keeps the deepest value in each output pixel's footprint, so
            # downsampling never hides real depth. Confirmed against real data: a z14 tile over
            # a known-flooded area showed 3 pixels >=1cm at "nearest" vs 55 at "max", including
            # the tile's single deepest, most dangerous cell, which "nearest" dropped entirely.
            image = reader.tile(request.x, request.y, request.z, tilesize=TILE_SIZE, reproject_method="max")
        band = image.array[0]
        depth = numpy.ma.filled(band, 0.0).astype("float64")
        invalid = numpy.ma.getmaskarray(band) | numpy.zeros(depth.shape, dtype=bool)
        rgb, painted = colorize(depth, invalid)
        rgb, painted = dilate_painted(rgb, painted)
    except TileOutsideBounds:
        rgb = numpy.zeros((3, TILE_SIZE, TILE_SIZE), dtype="uint8")
        painted = numpy.zeros((TILE_SIZE, TILE_SIZE), dtype=bool)

    transparent = numpy.repeat((~painted)[numpy.newaxis, ...], 3, axis=0)
    png = ImageData(numpy.ma.MaskedArray(rgb, mask=transparent)).render(img_format="PNG", add_mask=True)
    _tile_cache.put(key, png)
    return png
