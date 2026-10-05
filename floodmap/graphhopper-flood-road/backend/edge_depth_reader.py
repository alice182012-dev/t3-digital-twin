"""The backend's reader of the edge depth table (US-053): flood depth in centimetres by GraphHopper edge id and forecast step.

The format is in artifacts/docs/concepts/edge-depth-table-format.md. The backend image is built from this folder, so it cannot
import scripts/edge_depth/edge_depth_table.py. This is the same reader, with the same checks, and it is tested on the same
golden fixture as the Python and Java readers (test_edge_depth_reader.py).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

MAGIC = b"EDGD"
VERSION = 1
LATEST_NAME = "latest"
_FIXED = struct.Struct("<4sHHIHH")  # magic, version, step count, edge count, hash length, run length
_TIME = struct.Struct("<q")


class TableFormatError(ValueError):
    """The file is not a version 1 edge depth table, or it is damaged."""


class TableUnavailable(Exception):
    """There is no usable table: none is published, the file is damaged, or it was built for another graph."""


@dataclass(frozen=True)
class Table:
    graph_hash: str
    run_name: str
    step_times: tuple[datetime, ...]
    edge_count: int
    _data: bytes
    _body: int

    @property
    def step_count(self) -> int:
        return len(self.step_times)

    def depth_cm(self, edge_id: int, step: int) -> int:
        if not 0 <= edge_id < self.edge_count:
            raise IndexError(f"edge {edge_id} is outside 0..{self.edge_count - 1}")
        if not 0 <= step < self.step_count:
            raise IndexError(f"step {step} is outside 0..{self.step_count - 1}")
        return struct.unpack_from("<H", self._data, self._body + (edge_id * self.step_count + step) * 2)[0]


def read_table(path: Path) -> Table:
    data = Path(path).read_bytes()
    if len(data) < _FIXED.size:
        raise TableFormatError(f"header is cut off: {len(data)} bytes, at least {_FIXED.size} needed")
    magic, version, steps, edges, hash_len, run_len = _FIXED.unpack_from(data)
    if magic != MAGIC:
        raise TableFormatError(f"bad magic {magic!r}, expected {MAGIC!r}")
    if version != VERSION:
        raise TableFormatError(f"version {version}, this reader reads version {VERSION}")
    body = _FIXED.size + hash_len + run_len + steps * _TIME.size
    if len(data) < body:
        raise TableFormatError(f"header is cut off: {len(data)} bytes, {body} needed")
    if len(data) - body != edges * steps * 2:
        raise TableFormatError(f"body is {len(data) - body} bytes, {edges} edges and {steps} steps need {edges * steps * 2}")
    try:
        graph_hash = data[_FIXED.size : _FIXED.size + hash_len].decode("utf-8")
        run_name = data[_FIXED.size + hash_len : _FIXED.size + hash_len + run_len].decode("utf-8")
    except UnicodeDecodeError as error:
        raise TableFormatError(f"header text is not UTF-8: {error}") from error
    if steps == 0:
        raise TableFormatError("a table needs at least one step")
    at = _FIXED.size + hash_len + run_len
    seconds = [_TIME.unpack_from(data, at + i * _TIME.size)[0] for i in range(steps)]
    if any(b <= a for a, b in zip(seconds, seconds[1:])):
        raise TableFormatError("step times must increase")
    return Table(graph_hash, run_name, tuple(datetime.fromtimestamp(s, timezone.utc) for s in seconds), edges, data, body)


_cache: dict[Path, tuple[int, int, Table]] = {}


def read_latest(directory: Path) -> Table:
    """The table that `latest` names. Raises TableUnavailable, with the reason, when there is none to use. A table file that
    has not changed (same size and modification time) is read once, because a request must not read 1 MB again."""
    directory = Path(directory)
    try:
        name = (directory / LATEST_NAME).read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise TableUnavailable(f"no table has been published in {directory}") from None
    if not name or Path(name).name != name or name == LATEST_NAME:
        raise TableUnavailable(f"the pointer in {directory} names {name!r}, which is not a table file")
    path = directory / name
    try:
        stat = path.stat()
        cached = _cache.get(path)
        if cached and cached[0] == stat.st_mtime_ns and cached[1] == stat.st_size:
            return cached[2]
        table = read_table(path)
        _cache.clear()  # only the newest table is worth keeping
        _cache[path] = (stat.st_mtime_ns, stat.st_size, table)
        return table
    except FileNotFoundError:
        raise TableUnavailable(f"the pointer in {directory} names {name}, but the file is not there") from None
    except TableFormatError as error:
        raise TableUnavailable(f"the table {name} cannot be read: {error}") from error


def require_graph_hash(table: Table, loaded_graph_hash: str) -> Table:
    """The table, when it was built for the loaded graph. TableUnavailable, naming both hashes, when not."""
    if table.graph_hash != loaded_graph_hash:
        raise TableUnavailable(
            f"stale edge depth table: run {table.run_name} was built for graph hash {table.graph_hash}, but the loaded "
            f"graph has hash {loaded_graph_hash}. Write a new export and build a new table "
            "(artifacts/docs/concepts/graph-reimport-procedure.md)."
        )
    return table
