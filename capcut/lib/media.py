"""Shared media-file helpers.

Two conventions live here because every producer and every consumer of a
media file has to agree on them, and the project has already been bitten by
both:

* **the sibling metadata path** — the indexer reads exactly
  `<name>.mp4.metadata.json`. A producer that writes a different name is
  invisible to the index: no source, no license, no tags, no caption, and
  the clip can never be matched back by `source_filter="ai"`. Every producer
  and consumer must go through `metadata_path_for()` so the convention
  cannot drift.
* **atomic download** — a transfer that is interrupted must not leave a
  partial file under a valid name. A truncated MP4 is byte-wise a plausible
  MP4: it decodes far enough to look fine and only fails much later, and by
  then it is already in the library, which is the source of truth.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = [
    "metadata_path_for",
    "safe_filename_component",
    "atomic_download",
    "DownloadError",
    "MediaProbe",
    "probe_media",
]

METADATA_SUFFIX = ".metadata.json"


def safe_filename_component(value: str) -> str | None:
    """Return `value` if it is safe as a single path component, else None.

    A provider-supplied id ends up in a file name. A value containing "/" or
    ".." would escape the target directory — and the download helper creates
    parent directories, so the write would silently succeed outside the
    intended layout instead of failing loudly.
    """
    if not value or value in (".", ".."):
        return None
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        return None
    return value


@dataclass(frozen=True)
class MediaProbe:
    """Duration / dimensions / frame rate of a media file."""

    duration_sec: float
    width: int
    height: int
    fps: float


def probe_media(
    mp4_path: Path,
    *,
    strict: bool = True,
    ffprobe_bin: str = "ffprobe",
    timeout: int = 15,
) -> MediaProbe:
    """Probe duration / resolution / fps with ffprobe.

    This is the single implementation — the ingest modules and the indexer
    used to carry four or five byte-identical copies of it, which is how
    they drifted apart.

    Args:
        mp4_path: file to probe.
        strict: raise when ffprobe is missing or the file cannot be probed.
            In non-strict mode an unprobeable file yields a zeroed result
            (duration 0), which every caller already treats as "skip this
            file".
        ffprobe_bin: name or path of the ffprobe binary.
        timeout: seconds to wait for ffprobe.

    Returns:
        A `MediaProbe`.
    """
    ffprobe = shutil.which(ffprobe_bin)
    if ffprobe is None:
        if strict:
            raise RuntimeError(f"{ffprobe_bin} not found in PATH — install ffmpeg")
        return MediaProbe(duration_sec=0.0, width=0, height=0, fps=0.0)

    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate:format=duration",
        "-of", "json",
        str(mp4_path),
    ]
    try:
        out = subprocess.check_output(cmd, timeout=timeout).decode()
        data = json.loads(out)
    except Exception:
        if strict:
            raise
        return MediaProbe(duration_sec=0.0, width=0, height=0, fps=0.0)

    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    fps_str = stream.get("r_frame_rate", "0/1")
    try:
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if float(den) != 0 else 0.0
    except (ValueError, ZeroDivisionError, TypeError):
        fps = 0.0

    # ffprobe emits "N/A" for the duration of some containers (mpegts, some
    # AVI). Converting it unguarded raises even in non-strict mode, which
    # contradicts the "zeroed result" contract — and the `probe_duration()`
    # this replaced explicitly caught ValueError here.
    try:
        duration = float(fmt.get("duration", 0))
    except (ValueError, TypeError):
        duration = 0.0
    try:
        width = int(stream.get("width", 0))
        height = int(stream.get("height", 0))
    except (ValueError, TypeError):
        width = height = 0

    return MediaProbe(
        duration_sec=duration,
        width=width,
        height=height,
        fps=fps,
    )


def metadata_path_for(media_path: Path) -> Path:
    """Return the sibling metadata path for a media file.

    `<name>.mp4` -> `<name>.mp4.metadata.json`.

    Both the ingest writers and the indexer reader use this function, so a
    producer cannot silently write metadata the indexer will not find.

    Idempotent: applying it to an already-suffixed path returns that path
    unchanged, so a caller that feeds the result back in cannot drift the
    name to `X.mp4.metadata.json.metadata.json`.
    """
    if media_path.name.endswith(METADATA_SUFFIX):
        return media_path
    return media_path.with_suffix(media_path.suffix + METADATA_SUFFIX)


class DownloadError(RuntimeError):
    """A download did not complete and no file was published."""


def _content_length(response: Any) -> int | None:
    """Advertised body size, or None when the server does not say."""
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    raw = headers.get("Content-Length")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _is_encoded(response: Any) -> bool:
    """True when the body was transfer-encoded.

    `requests` sends `Accept-Encoding: gzip` by default and `iter_content`
    yields the *decompressed* bytes, while Content-Length counts the
    *compressed* ones. Comparing the two would report every complete
    transfer as truncated — and the ingest cleanup would then delete it.
    """
    headers = getattr(response, "headers", None)
    if not headers:
        return False
    return bool(headers.get("Content-Encoding"))


def _fsync_dir(directory: Path) -> None:
    """Flush a directory entry so a rename survives a power loss."""
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_download(response: Any, target: Path, *, chunk_size: int = 8192) -> Path:
    """Stream an HTTP response into `target` atomically.

    The body is written to a unique temporary sibling and renamed into place
    only after the transfer completes, so an interrupted transfer never
    leaves a partial file under a valid name and never overwrites a good
    file that is already there.

    Args:
        response: a `requests`-style response exposing `iter_content()` and,
            optionally, a `headers` mapping.
        target: final path of the downloaded file.
        chunk_size: streaming chunk size in bytes.

    Returns:
        `target`.

    Raises:
        DownloadError: the body was empty or shorter than the advertised
            Content-Length.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f".{target.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.part"

    written = 0
    try:
        with tmp.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    fh.write(chunk)
                    written += len(chunk)
            fh.flush()
            os.fsync(fh.fileno())

        expected = _content_length(response)
        if written == 0:
            raise DownloadError(f"empty response body for {target}")
        if expected is not None and written != expected and not _is_encoded(response):
            raise DownloadError(
                f"incomplete download for {target}: got {written} bytes, "
                f"expected {expected}"
            )

        os.replace(tmp, target)
        _fsync_dir(target.parent)
        return target
    except BaseException:
        # Never leave the partial transfer behind — not even on Ctrl-C.
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
