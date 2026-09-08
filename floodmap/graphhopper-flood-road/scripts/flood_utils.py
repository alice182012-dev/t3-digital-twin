#!/usr/bin/env python3
"""Shared vehicle/depth-band helpers for the GraphHopper flood-road backend.

Trimmed fork of valhalla-flood-road-test/scripts/flood_utils.py: the
Valhalla request/response translation, MinIO GeoJSON polling, and
route-vs-polygon proximity math are gone (PostGIS is now the source of
truth for flood geometry, and GraphHopper's own custom_model.areas gates
routing directly — see backend/flood_areas.py). Only the vehicle/depth
domain logic survives, unchanged from Phase 1/2 validation.
"""

from __future__ import annotations

from typing import Any

DEFAULT_ORIGIN = {"lat": 21.0214, "lon": 105.7610}
DEFAULT_DESTINATION = {"lat": 21.0225, "lon": 105.7650}

# costing -> profile: these must match the profile names in graphhopper/config.yml.
VEHICLE_PROFILES = {
    "motorbike": {
        "costing": "motorbike",
        "threshold_cm": 20,
        "label_vi": "Xe máy",
        "label_en": "Motorbike",
    },
    "car": {
        "costing": "car",
        "threshold_cm": 30,
        "label_vi": "Ô tô",
        "label_en": "Car",
    },
    "truck": {
        "costing": "truck",
        "threshold_cm": 50,
        "label_vi": "Xe tải",
        "label_en": "Truck",
    },
}

DEFAULT_COSTING = VEHICLE_PROFILES["motorbike"]["costing"]

# Depth bands as a fraction of the vehicle's wading threshold, relative
# multiplier applied via custom_model.priority. Ordered deepest-first —
# callers must emit these as an if/else_if chain (never independent `if`
# rules) so overlapping buffers don't multiply against each other.
DEPTH_BANDS = (
    ("b4", 1.00, None, 0.0),   # >= threshold: impassable
    ("b3", 0.75, 1.00, 0.05),
    ("b2", 0.50, 0.75, 0.2),
)


def vehicle_profile(vehicle_type: str = "motorbike") -> dict[str, Any]:
    return VEHICLE_PROFILES.get(vehicle_type, VEHICLE_PROFILES["motorbike"])


def vehicle_costing(vehicle_type: str = "motorbike") -> str:
    """Returns the GraphHopper profile name for a vehicle type."""
    return str(vehicle_profile(vehicle_type)["costing"])


def vehicle_threshold_cm(vehicle_type: str = "motorbike") -> float:
    return float(vehicle_profile(vehicle_type)["threshold_cm"])


def vehicle_types() -> list[str]:
    return list(VEHICLE_PROFILES)


def factor_from_depth_m(depth_m: float, vehicle_type: str = "motorbike") -> float:
    """Kept for parity with Phase 1/D2 scripts and tests; DEPTH_BANDS is what
    flood_areas.py actually uses to build custom_model.priority."""
    threshold_cm = max(vehicle_threshold_cm(vehicle_type), 1.0)
    depth_cm = max(depth_m * 100, 0.0)
    if depth_cm < threshold_cm * 0.15:
        return 1
    if depth_cm < threshold_cm * 0.25:
        return 2
    if depth_cm < threshold_cm * 0.50:
        return 8
    if depth_cm < threshold_cm * 0.75:
        return 25
    if depth_cm < threshold_cm:
        return 60
    return 100


def depth_bands_m(vehicle_type: str = "motorbike") -> list[dict[str, Any]]:
    """DEPTH_BANDS converted to absolute metre bounds for a given vehicle."""
    threshold_m = vehicle_threshold_cm(vehicle_type) / 100.0
    bands = []
    for band_id, lo_frac, hi_frac, factor in DEPTH_BANDS:
        bands.append(
            {
                "id": band_id,
                "band_min": lo_frac * threshold_m,
                "band_max": (hi_frac * threshold_m) if hi_frac is not None else None,
                "multiply_by": factor,
            }
        )
    return bands
