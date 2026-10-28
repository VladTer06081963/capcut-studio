"""Atomic file writes.

Every state file in this project is a source of truth that is read back
later — by another script, by the MCP server, or by a human. A write that
is interrupted half-way leaves a truncated JSON file, and the next reader
fails with `json.loads` on truncated data. That failure looks like corrupt
content rather than a failed write, and it is indistinguishable from real
corruption.

Writing to a temporary sibling and renaming it into place removes the
whole class: a reader sees either the old file or the new one, never a
half-written one. `capcut/assemble/final_renderer.py` already used this
pattern for `final.mp4`; this module generalises it to every state file.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

__all__ = [
    "atomic_write_text",
    "atomic_write_json",
]


def atomic_write_text(path: Path, data: str, *, encoding: str = "utf-8") -> Path:
    """Write `data` to `path` atomically.

    The content lands in a unique temporary sibling and is renamed into
    place only after it has been fully written. An existing file at `path`
    is left untouched if anything goes wrong.

    Returns:
        `path`.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp"
    try:
        with tmp.open("w", encoding=encoding) as fh:
            fh.write(data)
        os.replace(tmp, path)
    except Exception:
        # Never leave a partial file behind.
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    return path


def atomic_write_json(
    path: Path,
    payload: Any,
    *,
    indent: int = 2,
    ensure_ascii: bool = False,
) -> Path:
    """Serialize `payload` as JSON and write it to `path` atomically.

    Serialization happens *before* the file is touched, so a payload that
    cannot be serialized leaves the previous file intact.
    """
    data = json.dumps(payload, indent=indent, ensure_ascii=ensure_ascii)
    return atomic_write_text(path, data)
