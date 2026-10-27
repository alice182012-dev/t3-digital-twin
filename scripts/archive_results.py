"""Copies a real-rain run's results_3di.nc and a run record to the archive folder (US-094).

The cleanup in publish.publish_run deletes RESULT_DIR after 24 hours, so a past storm is lost unless this copy
exists. Each run gets <archive_dir>/<sim_id>/results_3di.nc and run_record.json. Running it twice gives the same
archive. Free space is read after the copy, and a value below the floor raises ArchiveError so the task fails.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

REAL_RAIN_SOURCE = "tomorrow.io"
GB = 1024**3


class ArchiveError(RuntimeError):
    pass


@dataclass(frozen=True)
class ArchiveResult:
    nc_path: Path
    record_path: Path
    free_bytes: int


def is_real_rain(source: str) -> bool:
    """rain_source() in create_simulation.py names the branch that supplied the rain."""
    return source == REAL_RAIN_SOURCE


def read_graph_hash(export_dir) -> str | None:
    path = Path(export_dir) / "graph.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get("graph_hash")


def build_record(sim_id, run_timestamp: str, rain_ingested: dict, model_id: str, graph_hash: str | None) -> dict:
    return {"sim_id": sim_id, "run_timestamp": run_timestamp, "rain_input": rain_ingested, "model_id": model_id,
            "graph_hash": graph_hash}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _replace_with(target: Path, write: Callable[[Path], None]) -> None:
    tmp = target.with_name(target.name + ".part")
    try:
        write(tmp)
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)


def archive_run(*, sim_id, nc_path, archive_dir, record: dict, floor_bytes: int,
                disk_usage: Callable[[str], object] = shutil.disk_usage) -> ArchiveResult:
    nc_path = Path(nc_path)
    if not nc_path.exists():
        raise ArchiveError(f"no results_3di.nc to archive at {nc_path}")
    folder = Path(archive_dir) / str(sim_id)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "results_3di.nc"
    _replace_with(target, lambda tmp: shutil.copyfile(nc_path, tmp))
    full_record = {**record, "bytes": target.stat().st_size, "sha256": _sha256(target)}
    record_path = folder / "run_record.json"
    _replace_with(record_path, lambda tmp: tmp.write_text(json.dumps(full_record, indent=1) + "\n", encoding="utf-8"))
    free = disk_usage(str(folder)).free
    print(f"Archived sim {sim_id}: {full_record['bytes']} bytes to {target}, {free / GB:.1f} GB free")
    if free < floor_bytes:
        raise ArchiveError(
            f"the archive drive has {free / GB:.1f} GB free, below the floor of {floor_bytes / GB:.1f} GB"
        )
    return ArchiveResult(target, record_path, free)
