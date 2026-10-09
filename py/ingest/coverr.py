"""
Coverr stock video ingest — official REST API.

Coverr (https://coverr.co) provides free 4K stock footage. Has a documented
REST API at https://api.coverr.co. Requires an API key (free signup).

API access verified UA-friendly (curl 2026-10-09T18:13Z returned 200 on web,
401 on API — auth required, not blocked).

Usage:
    from py.ingest import coverr
    result = coverr.ingest("fog night forest", Path("library/stock/coverr"), count=10)
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from py.lib.config import (
    COVERR_API_KEY,
    STOCK_DIR,
    has_coverr,
)
from py.lib.lifecycle import sha256_file


COVERR_API_URL = "https://api.coverr.co/v1/videos"

DEFAULT_DOWNLOAD_HEADERS = {
    "User-Agent": "capcut-studio/0.1 (https://github.com/VladTer06081963/capcut-studio)",
}


# ---------------------------------------------------------------------------
# Data classes (mirror youtube.py shape for consistency)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VideoMeta:
    id: str
    title: str
    duration_sec: int
    download_url: str
    thumbnail_url: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class ProbeResult:
    duration_sec: float
    width: int
    height: int
    fps: float


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
) -> list[VideoMeta]:
    """Search Coverr via official API.

    Args:
        query: free-text search.
        max_results: how many results to return (1-50).

    Returns: list of VideoMeta. May be empty if no matches.

    Raises:
        RuntimeError: if COVERR_API_KEY is not configured.
        requests.HTTPError: on API error.
    """
    if not has_coverr():
        raise RuntimeError(
            "COVERR_API_KEY not set in .env — see .env.example "
            "(signup at https://coverr.co/api)"
        )

    params: dict[str, Any] = {
        "query": query,
        "per_page": min(max_results, 50),
    }
    headers = {
        "Authorization": f"Bearer {COVERR_API_KEY}",
        "Accept": "application/json",
        **DEFAULT_DOWNLOAD_HEADERS,
    }

    resp = requests.get(COVERR_API_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    out: list[VideoMeta] = []
    for item in data.get("videos", []):
        # Coverr API shape (as of 2025): id, name, duration, video_url, poster, tags
        out.append(
            VideoMeta(
                id=str(item.get("id", item.get("slug", ""))),
                title=item.get("name", ""),
                duration_sec=int(item.get("duration", 0)),
                download_url=item.get("video_url") or item.get("download_url", ""),
                thumbnail_url=item.get("poster") or item.get("thumbnail_url", ""),
                tags=tuple(item.get("tags", [])),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_video(
    video_meta: VideoMeta,
    output_dir: Path,
) -> Path:
    """Download a Coverr video as MP4 to output_dir/<id>.mp4."""
    if not video_meta.download_url:
        raise ValueError(f"video {video_meta.id} has no download_url")

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{video_meta.id}.mp4"

    with requests.get(
        video_meta.download_url,
        headers=DEFAULT_DOWNLOAD_HEADERS,
        stream=True,
        timeout=60,
    ) as resp:
        resp.raise_for_status()
        with target.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)

    return target


# ---------------------------------------------------------------------------
# ffprobe (reuses same shape as youtube.py)
# ---------------------------------------------------------------------------

def probe_metadata(mp4_path: Path) -> ProbeResult:
    """Use ffprobe to extract duration / resolution / fps."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("ffprobe not found in PATH — install ffmpeg")

    cmd = [
        ffprobe, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate:format=duration",
        "-of", "json",
        str(mp4_path),
    ]
    out = subprocess.check_output(cmd, timeout=15).decode()
    data = json.loads(out)

    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}
    fps_str = stream.get("r_frame_rate", "0/1")
    try:
        num, den = fps_str.split("/")
        fps = float(num) / float(den) if float(den) != 0 else 0.0
    except (ValueError, ZeroDivisionError):
        fps = 0.0

    return ProbeResult(
        duration_sec=float(fmt.get("duration", 0)),
        width=int(stream.get("width", 0)),
        height=int(stream.get("height", 0)),
        fps=fps,
    )


# ---------------------------------------------------------------------------
# metadata.json writer
# ---------------------------------------------------------------------------

def write_metadata(
    mp4_path: Path,
    *,
    video_meta: VideoMeta,
    probe: ProbeResult,
) -> Path:
    """Write `<mp4>.metadata.json` sibling. Returns metadata path."""
    metadata = {
        "id": f"coverr:{video_meta.id}",
        "source": "coverr",
        "model": None,
        "seed": None,
        "prompt": video_meta.title,
        "negative_prompt": None,
        "duration_sec": probe.duration_sec,
        "resolution": f"{probe.width}x{probe.height}",
        "fps": probe.fps,
        "character_ref": None,
        "scene_ref": None,
        "tags": list(video_meta.tags) + ["coverr"],
        "license": "coverr",
        "attribution": f"Coverr (https://coverr.co/videos/{video_meta.id})",
        "created_at": None,
        "sha256": sha256_file(mp4_path),
        "coverr_id": video_meta.id,
        "coverr_title": video_meta.title,
    }
    metadata_path = mp4_path.with_suffix(mp4_path.suffix + ".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    return metadata_path


# ---------------------------------------------------------------------------
# High-level ingest
# ---------------------------------------------------------------------------

def ingest(
    query: str,
    output_dir: Path | None = None,
    count: int = 10,
) -> IngestResult:
    """Search Coverr, download top-N, probe, write metadata."""
    output_dir = output_dir or (STOCK_DIR / "coverr")

    metas = search_videos(query, max_results=count)
    files: list[Path] = []
    errors: list[tuple[str, str]] = []

    for vm in metas[:count]:
        try:
            mp4 = download_video(vm, output_dir)
            probe = probe_metadata(mp4)
            write_metadata(mp4, video_meta=vm, probe=probe)
            files.append(mp4)
        except Exception as e:
            errors.append((vm.id, str(e)))

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