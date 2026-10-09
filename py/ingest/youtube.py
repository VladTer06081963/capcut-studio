"""
YouTube stock video ingest — Data API v3 search + yt-dlp download.

Verified working from UA (curl 2026-10-09T18:13Z). Primary stock source
per AGENTS.md fallback chain.

Usage:
    from py.ingest import youtube
    paths = youtube.ingest("fog night forest", Path("library/stock/youtube"), count=10)

Or via CLI:
    python scripts/ingest_youtube.py --query "fog night forest" --count 10
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yt_dlp

from py.lib.config import (
    STOCK_DIR,
    YOUTUBE_API_KEY,
    has_youtube,
)
from py.lib.lifecycle import sha256_file


# ---------------------------------------------------------------------------
# ISO 8601 duration parser (YouTube returns "PT2M30S" format)
# ---------------------------------------------------------------------------

_ISO_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def _parse_iso_duration_seconds(s: str) -> int:
    """Parse YouTube's ISO 8601 duration (e.g. "PT2M30S") to seconds. 0 on parse fail."""
    match = _ISO_DURATION_RE.match(s)
    if not match:
        return 0
    h, m, sec = match.groups()
    return int(h or 0) * 3600 + int(m or 0) * 60 + int(sec or 0)


# ---------------------------------------------------------------------------
# Data API v3 search
# ---------------------------------------------------------------------------

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# Free license / Creative Commons options. Filter to license=creativeCommon
# for re-use safe; default is `any` (includes standard YouTube license which
# restricts reuse). For B-roll we accept "any" — user decides per-clip.
LICENSE_ANY = "any"
LICENSE_CC = "creativeCommon"


@dataclass(frozen=True)
class VideoMeta:
    """Minimal video metadata from YouTube Data API."""

    id: str
    title: str
    channel: str
    duration_sec: int
    license: str            # "any" | "creativeCommon"
    thumbnail_url: str


def _api_get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET YouTube Data API v3. Raises on non-2xx."""
    import requests

    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def search_videos(
    query: str,
    max_results: int = 20,
    license: str = LICENSE_ANY,
    video_duration: str = "medium",  # "short" <4min, "medium" 4-20min, "long" >20min
) -> list[VideoMeta]:
    """Search YouTube videos via Data API v3.

    Args:
        query: free-text search query.
        max_results: max videos to return (1-50).
        license: "any" or "creativeCommon".
        video_duration: filter by duration ("any"/"short"/"medium"/"long").

    Returns: list of VideoMeta (length may be less than max_results if fewer matches).

    Raises:
        RuntimeError: if YOUTUBE_API_KEY is not configured.
        requests.HTTPError: on API error.
    """
    if not has_youtube():
        raise RuntimeError(
            "YOUTUBE_API_KEY not set in .env — see .env.example"
        )

    # Step 1: search returns video IDs
    search_params: dict[str, Any] = {
        "key": YOUTUBE_API_KEY,
        "q": query,
        "part": "id",
        "type": "video",
        "maxResults": min(max_results, 50),
        "videoLicense": license,
        "videoDuration": video_duration,
        "safeSearch": "none",
    }
    data = _api_get(YOUTUBE_SEARCH_URL, search_params)
    ids = [item["id"]["videoId"] for item in data.get("items", []) if "videoId" in item.get("id", {})]

    if not ids:
        return []

    # Step 2: enrich with title, duration, license
    videos_params: dict[str, Any] = {
        "key": YOUTUBE_API_KEY,
        "id": ",".join(ids),
        "part": "snippet,contentDetails,status",
    }
    videos_data = _api_get(YOUTUBE_VIDEOS_URL, videos_params)

    out: list[VideoMeta] = []
    for item in videos_data.get("items", []):
        duration_sec = _parse_iso_duration_seconds(item["contentDetails"]["duration"])
        license_str = (
            "creativeCommon"
            if item["status"].get("license") == "creativeCommon"
            else "any"
        )
        out.append(
            VideoMeta(
                id=item["id"],
                title=item["snippet"]["title"],
                channel=item["snippet"]["channelTitle"],
                duration_sec=duration_sec,
                license=license_str,
                thumbnail_url=item["snippet"]["thumbnails"].get("high", {}).get("url", ""),
            )
        )
    return out


# ---------------------------------------------------------------------------
# yt-dlp download
# ---------------------------------------------------------------------------

# Sensible defaults: 720p MP4, no playlist, single file.
DEFAULT_YDL_OPTS: dict[str, Any] = {
    "format": "best[height<=720][ext=mp4]/best[ext=mp4]/best",
    "outtmpl": "%(id)s.%(ext)s",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "merge_output_format": "mp4",
    "max_filesize": 500 * 1024 * 1024,  # 500 MB hard cap
}


def download_video(
    video_id: str,
    output_dir: Path,
    ydl_opts: dict[str, Any] | None = None,
) -> Path:
    """Download a single YouTube video as MP4 to output_dir/<id>.mp4.

    Args:
        video_id: 11-char YouTube video ID.
        output_dir: directory to write the file to.
        ydl_opts: optional override of yt-dlp options.

    Returns: path to downloaded MP4.

    Raises:
        yt_dlp.utils.DownloadError: on download failure.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    opts = dict(DEFAULT_YDL_OPTS)
    opts.update(ydl_opts or {})
    opts["outtmpl"] = str(output_dir / "%(id)s.%(ext)s")

    url = f"https://www.youtube.com/watch?v={video_id}"
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)

    # yt-dlp may rename ext; resolve from info
    ext = info.get("ext", "mp4")
    candidate = output_dir / f"{video_id}.{ext}"
    if not candidate.exists():
        # Fallback: find any file starting with video_id
        for p in output_dir.iterdir():
            if p.stem == video_id:
                return p
        raise FileNotFoundError(f"download succeeded but file not found at {candidate}")
    return candidate


# ---------------------------------------------------------------------------
# ffprobe metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProbeResult:
    duration_sec: float
    width: int
    height: int
    fps: float


def probe_metadata(mp4_path: Path) -> ProbeResult:
    """Use ffprobe to extract duration / resolution / fps. Requires ffmpeg."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("ffprobe not found in PATH — install ffmpeg")

    cmd = [
        ffprobe,
        "-v", "error",
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
    """Write `<mp4>.metadata.json` sibling to mp4_path. Returns metadata path."""
    metadata = {
        "id": f"youtube:{video_meta.id}",
        "source": "youtube",
        "model": None,
        "seed": None,
        "prompt": video_meta.title,
        "negative_prompt": None,
        "duration_sec": probe.duration_sec,
        "resolution": f"{probe.width}x{probe.height}",
        "fps": probe.fps,
        "character_ref": None,
        "scene_ref": None,
        "tags": [
            video_meta.channel.lower().replace(" ", "-"),
            f"license-{video_meta.license}",
        ],
        "license": video_meta.license,
        "attribution": f"{video_meta.channel} via YouTube ({video_meta.id})",
        "created_at": None,  # filled by caller or library/indexer
        "sha256": sha256_file(mp4_path),
        "youtube_id": video_meta.id,
        "youtube_title": video_meta.title,
    }
    metadata_path = mp4_path.with_suffix(mp4_path.suffix + ".metadata.json")
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    return metadata_path


# ---------------------------------------------------------------------------
# High-level ingest
# ---------------------------------------------------------------------------

@dataclass
class IngestResult:
    videos: list[VideoMeta]
    files: list[Path]
    errors: list[tuple[str, str]]   # (video_id, error message)


def ingest(
    query: str,
    output_dir: Path | None = None,
    count: int = 10,
    license: str = LICENSE_ANY,
    ydl_opts: dict[str, Any] | None = None,
) -> IngestResult:
    """Search YouTube, download top-N, probe, write metadata.

    Args:
        query: free-text search query.
        output_dir: defaults to `<LIBRARY_ROOT>/stock/youtube`.
        count: how many videos to download.
        license: "any" or "creativeCommon".

    Returns: IngestResult with downloaded paths and any per-video errors
        (other videos are still attempted).
    """
    output_dir = output_dir or (STOCK_DIR / "youtube")

    metas = search_videos(query, max_results=count, license=license)
    files: list[Path] = []
    errors: list[tuple[str, str]] = []

    for vm in metas[:count]:
        try:
            mp4 = download_video(vm.id, output_dir, ydl_opts)
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
    "LICENSE_ANY",
    "LICENSE_CC",
]