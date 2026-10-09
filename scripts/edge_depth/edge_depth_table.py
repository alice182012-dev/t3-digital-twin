"""Reader and writer for the edge depth table: one file per run, flood depth by GraphHopper edge id.

Story E2 (US-040) of artifacts/docs/epics/EP-08-edge-depth-table.md. The byte layout is
specified in artifacts/docs/concepts/edge-depth-table-format.md, and the Java reader must read the
same bytes. Pure: no database, no GraphHopper. write_table writes straight to its path, because the build
(build_edge_depth.py) writes under a temporary name and renames. write_latest replaces the pointer in one
step. Publishing and retention are in publish_edge_depth.py (US-042).

Edge ids are dense integers from 0, so the edge id is the row index and the file stores no id column.
"""

from __future__ import annotations

import logging
import os
import struct
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

MAGIC = b"EDGD"
VERSION = 1
LATEST_NAME = "latest"

_FIXED = struct.Struct("<4sHHIHH")  # magic, version, step count, edge count, hash length, run length
_STEP_TIME = struct.Struct("<q")
_MAX_STEPS = 0xFFFF
_MAX_TEXT_BYTES = 0xFFFF
_DEPTH_BYTES = 2


logger = logging.getLogger("edge_depth")


class TableFormatError(ValueError):
    """The file is not a version 1 edge depth table, or it is damaged."""


class StaleTableError(ValueError):
    """The table is whole, but it was built for another graph than the one the reader has loaded. Edge ids change
    on every graph re-import, so its depths would land on the wrong roads. Not a TableFormatError: a damaged file
    is a bug, and a stale one is a re-import that is not finished."""


@dataclass(frozen=True)
class TableHeader:
    graph_hash: str
    run_name: str
    step_times: tuple[datetime, ...]
    edge_count: int

    def __post_init__(self) -> None:
        if not self.step_times:
            raise ValueError("a table needs at least one step")
        if len(self.step_times) > _MAX_STEPS:
            raise ValueError(f"{len(self.step_times)} steps, the format holds at most {_MAX_STEPS}")
        if any(t.tzinfo is None for t in self.step_times):
            raise ValueError("step times need a timezone")
        utc_times = tuple(t.astimezone(timezone.utc) for t in self.step_times)
        if any(b <= a for a, b in zip(utc_times, utc_times[1:])):
            raise ValueError("step times must be strictly increasing")
        object.__setattr__(self, "step_times", utc_times)
        if not 0 <= self.edge_count <= 0xFFFFFFFF:
            raise ValueError(f"edge count {self.edge_count} does not fit in 32 bits")
        for label, text in (("graph hash", self.graph_hash), ("run name", self.run_name)):
            if len(text.encode("utf-8")) > _MAX_TEXT_BYTES:
                raise ValueError(f"{label} is longer than {_MAX_TEXT_BYTES} bytes")

    @property
    def step_count(self) -> int:
        return len(self.step_times)


class EdgeDepthTable:
    def __init__(self, header: TableHeader, data: bytes, body_offset: int) -> None:
        self.header = header
        self._data = data
        self._body_offset = body_offset

    def depth_cm(self, edge_id: int, step: int) -> int:
        self._check_edge(edge_id)
        if not 0 <= step < self.header.step_count:
            raise IndexError(f"step {step} is outside 0..{self.header.step_count - 1}")
        return struct.unpack_from("<H", self._data, self._offset(edge_id, step))[0]

    def edge_depths_cm(self, edge_id: int) -> tuple[int, ...]:
        self._check_edge(edge_id)
        return struct.unpack_from(f"<{self.header.step_count}H", self._data, self._offset(edge_id, 0))

    def _offset(self, edge_id: int, step: int) -> int:
        return self._body_offset + (edge_id * self.header.step_count + step) * _DEPTH_BYTES

    def _check_edge(self, edge_id: int) -> None:
        if not 0 <= edge_id < self.header.edge_count:
            raise IndexError(f"edge {edge_id} is outside 0..{self.header.edge_count - 1}")


def write_table(path: Path, header: TableHeader, depths_cm: Iterable[Sequence[int]]) -> None:
    """Write the table. depths_cm yields one row per edge, in edge id order, with one depth per step."""
    graph_hash = header.graph_hash.encode("utf-8")
    run_name = header.run_name.encode("utf-8")
    row = struct.Struct(f"<{header.step_count}H")
    with open(path, "wb") as f:
        f.write(_FIXED.pack(MAGIC, VERSION, header.step_count, header.edge_count, len(graph_hash), len(run_name)))
        f.write(graph_hash)
        f.write(run_name)
        for t in header.step_times:
            f.write(_STEP_TIME.pack(int(t.timestamp())))
        written = 0
        for edge_id, depths in enumerate(depths_cm):
            if edge_id >= header.edge_count:
                raise ValueError(f"more than {header.edge_count} rows for {header.edge_count} edges")
            if len(depths) != header.step_count:
                raise ValueError(f"edge {edge_id} has {len(depths)} depths for {header.step_count} steps")
            try:
                f.write(row.pack(*depths))
            except struct.error as e:
                raise ValueError(f"edge {edge_id}: {e}") from e
            written += 1
    if written != header.edge_count:
        raise ValueError(f"{written} rows for {header.edge_count} edges")


def read_table(path: Path) -> EdgeDepthTable:
    data = Path(path).read_bytes()
    if len(data) < _FIXED.size:
        raise TableFormatError(f"header is cut off: {len(data)} bytes, at least {_FIXED.size} needed")
    magic, version, step_count, edge_count, hash_len, run_len = _FIXED.unpack_from(data)
    if magic != MAGIC:
        raise TableFormatError(f"bad magic {magic!r}, expected {MAGIC!r}")
    if version != VERSION:
        raise TableFormatError(f"version {version}, this reader reads version {VERSION}")
    body_offset = _FIXED.size + hash_len + run_len + step_count * _STEP_TIME.size
    if len(data) < body_offset:
        raise TableFormatError(f"header is cut off: {len(data)} bytes, {body_offset} needed")
    expected_size = body_offset + edge_count * step_count * _DEPTH_BYTES
    if len(data) != expected_size:
        raise TableFormatError(
            f"body is {len(data) - body_offset} bytes, {edge_count} edges and {step_count} steps need "
            f"{expected_size - body_offset}"
        )
    try:
        graph_hash = data[_FIXED.size : _FIXED.size + hash_len].decode("utf-8")
        run_name = data[_FIXED.size + hash_len : _FIXED.size + hash_len + run_len].decode("utf-8")
    except UnicodeDecodeError as e:
        raise TableFormatError(f"header text is not UTF-8: {e}") from e
    times_at = _FIXED.size + hash_len + run_len
    step_times = tuple(
        datetime.fromtimestamp(_STEP_TIME.unpack_from(data, times_at + i * _STEP_TIME.size)[0], timezone.utc)
        for i in range(step_count)
    )
    try:
        header = TableHeader(graph_hash, run_name, step_times, edge_count)
    except ValueError as e:
        raise TableFormatError(str(e)) from e
    return EdgeDepthTable(header, data, body_offset)


def write_latest(directory: Path, table_name: str) -> None:
    """Point `latest` at table_name in one step. The new pointer is written to a temporary file in the same
    folder and renamed over the old one, so a reader that polls sees the old name or the new one, never an
    empty file. A rename inside one folder is atomic on the volume the tables live on."""
    _check_pointer_target(table_name)
    directory = Path(directory)
    temporary = directory / f".{LATEST_NAME}.{os.getpid()}.{threading.get_ident()}.tmp"
    try:
        with open(temporary, "w", encoding="utf-8") as f:
            f.write(f"{table_name}\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, directory / LATEST_NAME)
    finally:
        temporary.unlink(missing_ok=True)


def read_latest(directory: Path) -> Path:
    name = (Path(directory) / LATEST_NAME).read_text(encoding="utf-8").strip()
    _check_pointer_target(name)
    return Path(directory) / name


def require_graph_hash(table: EdgeDepthTable, graph_hash: str) -> EdgeDepthTable:
    """Returns the table when it was built for graph_hash, and raises StaleTableError, naming both hashes, when
    not. A reader calls this with the hash of the graph it has loaded, before it serves a request."""
    if table.header.graph_hash != graph_hash:
        raise StaleTableError(
            f"stale edge depth table: run {table.header.run_name} was built for graph hash "
            f"{table.header.graph_hash}, but the loaded graph has hash {graph_hash}. "
            "Write a new export and build a new table (artifacts/docs/concepts/graph-reimport-procedure.md)."
        )
    return table


def read_latest_table_for_graph(directory: Path, graph_hash: str, retries: int = 1) -> EdgeDepthTable:
    """The table `latest` names, if it was built for graph_hash. A mismatch is logged at ERROR, with both hashes,
    and raised as StaleTableError."""
    table = read_latest_table(directory, retries)
    try:
        return require_graph_hash(table, graph_hash)
    except StaleTableError as e:
        logger.error("%s", e)
        raise


def read_latest_table(directory: Path, retries: int = 1, _read_pointer=None) -> EdgeDepthTable:
    """The table `latest` names. The pointer and the table are two files, so a publish that removes the table
    between the two reads would fail the read. The pointer already names a newer table by then, so the read
    starts again from the pointer, `retries` times."""
    read_pointer = _read_pointer or read_latest
    for attempt in range(retries + 1):
        path = read_pointer(directory)
        try:
            return read_table(path)
        except FileNotFoundError:
            if attempt == retries:
                raise
    raise AssertionError("unreachable")


def _check_pointer_target(name: str) -> None:
    if not name or name == LATEST_NAME or Path(name).name != name or name in (".", ".."):
        raise ValueError(f"{name!r} is not a table file name in the pointer's directory")
