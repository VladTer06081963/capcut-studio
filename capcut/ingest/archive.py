"""
Archive.org stock video ingest — public-domain footage via advancedsearch API.

Archive.org (https://archive.org) hosts millions of public-domain video items.
Their advancedsearch API is free and anonymous-friendly.

API: https://archive.org/advancedsearch.php?q=<query>&fl[]=identifier&...

Verified UA-friendly (curl 2026-10-09T18:13Z returned 200 on web).

Usage:
    from capcut.ingest import archive
    result = archive.ingest("nature", Path("library/stock/archive"), count=5)
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from capcut.lib.config import STOCK_DIR
from capcut.lib.atomic import atomic_write_json
from capcut.lib.lifecycle import sha256_file
from capcut.lib.media import (
    MediaProbe,
    atomic_download,
    metadata_path_for,
    probe_media,
)


ARCHIVE_SEARCH_URL = "https://archive.org/advancedsearch.php"
ARCHIVE_DOWNLOAD_URL = "https://archive.org/download/{identifier}/{filename}"

DEFAULT_HEADERS = {
    "User-Agent": "capcut-studio/0.1 (research; +https://github.com/VladTer06081963/capcut-studio)",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VideoMeta:
    identifier: str                        # Archive.org identifier (e.g. "Prelinger_...")
    title: str
    year: int
    mediatype: str                        # "movies" | "video" etc.
    download_url: str
    license: str                          # "publicdomain" | "cc-by" etc.


# The probe result used to be declared separately in every ingest module;
# the implementation now lives in capcut.lib.media. The alias keeps
# `youtube.ProbeResult(...)` and friends working.
ProbeResult = MediaProbe


@dataclass
class IngestResult:
    videos: list[VideoMeta]
    files: list[Path]
    errors: list[tuple[str, str]]


# ---------------------------------------------------------------------------
# API search
# ---------------------------------------------------------------------------

def search_videos(
    query: str,
    max_results: int = 20,
    mediatype: str = "movies",
) -> list[VideoMeta]:
    """Search Archive.org for public-domain videos.

    Args:
        query: free-text search query.
        max_results: 1-50.
        mediatype: filter (default "movies"). Other options: "video".

    Returns: list of VideoMeta.

    Note: Archive.org uses Lucene syntax. We quote the query for safety.
    """
    # Lucene query — quote user input to avoid syntax errors
    lucene_q = f'("{query}") AND mediatype:{mediatype}'
    params: dict[str, Any] = {
        "q": lucene_q,
        "fl[]": ["identifier", "title", "year", "mediatype", "licenseurl"],
        "rows": min(max_results, 50),
        "output": "json",
        "sort[]": ["downloads desc"],  # space-separated (not '+'); Archive.org treats literal '+' in sort value as char
    }

    resp = requests.get(ARCHIVE_SEARCH_URL, params=params, headers=DEFAULT_HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    out: list[VideoMeta] = []
    for doc in data.get("response", {}).get("docs", []):
        identifier = doc.get("identifier", "")
        if not identifier:
            continue
        out.append(
            VideoMeta(
                identifier=identifier,
                title=doc.get("title", identifier),
                year=int(doc.get("year", 0) or 0),
                mediatype=doc.get("mediatype", mediatype),
                download_url=f"https://archive.org/details/{identifier}",
                license=doc.get("licenseurl", "publicdomain").rstrip("/").split("/")[-1] if doc.get("licenseurl") else "publicdomain",
            )
        )
    return out


# ---------------------------------------------------------------------------
# Download (resolves identifier → MP4 derivative)
# ---------------------------------------------------------------------------

def _resolve_mp4_url(identifier: str) -> str:
    """Get the direct MP4 URL for an Archive.org identifier.

    Archive.org stores videos as derivatives (multiple formats). We prefer
    MP4 (H.264/AAC) for compatibility. Falls back to MPEG-2 or webm if needed.
    """
    metadata_url = f"https://archive.org/metadata/{identifier}"
    resp = requests.get(metadata_url, headers=DEFAULT_HEADERS, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    files = data.get("files", [])
    # Prefer MP4
    for f in files:
        name = f.get("name", "")
        fmt = f.get("format", "")
        if name.endswith(".mp4") or "h.264" in fmt.lower() or "mpeg-4" in fmt.lower():
            return ARCHIVE_DOWNLOAD_URL.format(identifier=identifier, filename=name)

    # Fallback to any video file
    for f in files:
        name = f.get("name", "")
        fmt = f.get("format", "")
        if any(name.endswith(ext) for ext in (".mp4", ".webm", ".ogv", ".mpeg", ".mpg")):
            return ARCHIVE_DOWNLOAD_URL.format(identifier=identifier, filename=name)

    raise RuntimeError(f"no video file found for Archive.org identifier {identifier}")


def download_video(
    video_meta: VideoMeta,
    output_dir: Path,
) -> Path:
    """Download an Archive.org video MP4 to output_dir/<id>.mp4."""
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{video_meta.identifier}.mp4"

    mp4_url = _resolve_mp4_url(video_meta.identifier)

    with requests.get(mp4_url, headers=DEFAULT_HEADERS, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        return atomic_download(resp, target)


# ---------------------------------------------------------------------------
# ffprobe
# ---------------------------------------------------------------------------

def probe_metadata(mp4_path: Path) -> ProbeResult:
    """Use ffprobe to extract duration / resolution / fps. Requires ffmpeg."""
    return probe_media(mp4_path, strict=True)

# ---------------------------------------------------------------------------
# metadata.json writer
# ---------------------------------------------------------------------------

def write_metadata(
    mp4_path: Path,
    *,
    video_meta: VideoMeta,
    probe: ProbeResult,
) -> Path:
    metadata = {
        "id": f"archive:{video_meta.identifier}",
        "source": "archive",
        "model": None,
        "seed": None,
        "prompt": video_meta.title,
        "negative_prompt": None,
        "duration_sec": probe.duration_sec,
        "resolution": f"{probe.width}x{probe.height}",
        "fps": probe.fps,
        "character_ref": None,
        "scene_ref": None,
        "tags": ["archive", f"year-{video_meta.year}"],
        "license": video_meta.license,
        "attribution": f"Internet Archive ({video_meta.identifier})",
        "created_at": None,
        "sha256": sha256_file(mp4_path),
        "archive_identifier": video_meta.identifier,
        "archive_title": video_meta.title,
        "archive_year": video_meta.year,
    }
    metadata_path = metadata_path_for(mp4_path)
    atomic_write_json(metadata_path, metadata)
    return metadata_path


# ---------------------------------------------------------------------------
# High-level ingest
# ---------------------------------------------------------------------------

def ingest(
    query: str,
    output_dir: Path | None = None,
    count: int = 5,
    mediatype: str = "movies",
) -> IngestResult:
    """Search Archive.org, download top-N, probe, write metadata."""
    output_dir = output_dir or (STOCK_DIR / "archive")

    metas = search_videos(query, max_results=count, mediatype=mediatype)
    files: list[Path] = []
    errors: list[tuple[str, str]] = []

    for vm in metas[:count]:
        mp4: Path | None = None
        try:
            mp4 = download_video(vm, output_dir)
            probe = probe_metadata(mp4)
            write_metadata(mp4, video_meta=vm, probe=probe)
            files.append(mp4)
        except Exception as e:
            errors.append((vm.identifier, str(e)))
            # The file is unusable — do not leave it in the library under a
            # valid name. A truncated MP4 looks like a valid MP4 until
            # something tries to decode it.
            if mp4 is not None:
                mp4.unlink(missing_ok=True)

    return IngestResult(videos=metas, files=files, errors=errors)


__all__ = [
    "VideoMeta",
    "ProbeResult",
    "IngestResult",
    "search_videos",
    "download_video",
    "probe_metadata",
    "write_metadata",
    "ingest",
]