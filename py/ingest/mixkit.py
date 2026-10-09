"""
Mixkit stock video ingest — HTML scrape (no public API).

Mixkit (https://mixkit.co) has free stock videos but no API. We scrape the
search results page with polite delays (`MIXKIT_SCRAPE_DELAY_SEC`).

Verified UA-friendly (curl 2026-10-09T18:13Z returned 200 on web).

Caveats:
- HTML layout may change — selectors are isolated in `_find_video_cards()`.
  When Mixkit updates, only that function needs to be patched.
- We never bypass Mixkit's CDN or scrape private endpoints.
- Be polite: default 2s delay between requests.

Usage:
    from py.ingest import mixkit
    result = mixkit.ingest("forest", Path("library/stock/mixkit"), count=5)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from py.lib.config import (
    MIXKIT_SCRAPE_DELAY_SEC,
    STOCK_DIR,
)
from py.lib.lifecycle import sha256_file


MIXKIT_SEARCH_URL = "https://mixkit.co/free-stock-video/"

DEFAULT_HEADERS = {
    "User-Agent": "capcut-studio/0.1 (research; +https://github.com/VladTer06081963/capcut-studio)",
    "Accept": "text/html",
    "Accept-Language": "en",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VideoMeta:
    id: str                              # Mixkit slug
    title: str
    download_url: str                    # direct MP4 URL
    thumbnail_url: str
    duration_sec: int                    # parsed from duration label if present


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
# HTML scraping
# ---------------------------------------------------------------------------

def _find_video_cards(html: str) -> list[dict[str, str]]:
    """Parse Mixkit search results HTML into list of {title, url, thumb, duration}.

    Mixkit's HTML structure (as of 2025): each video is in an <article> with
    a data-href attribute pointing to the video page; thumbnail is in an <img>;
    duration is in a <span class="...duration..."> if visible.

    This is the **only** function that depends on Mixkit's HTML layout.
    If Mixkit updates, only this needs to change.
    """
    import re
    out: list[dict[str, str]] = []

    # Find <article> blocks with data-href (Mixkit's main video cards)
    for m in re.finditer(
        r'<article[^>]*?data-href="([^"]+)"[^>]*>(.*?)</article>',
        html,
        re.DOTALL,
    ):
        url = m.group(1)
        block = m.group(2)

        # Title: first <h3> or <h2>
        title_m = re.search(r"<h[23][^>]*>(.*?)</h[23]>", block, re.DOTALL)
        title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else ""

        # Thumbnail: first <img src="...">
        thumb_m = re.search(r'<img[^>]+src="([^"]+)"', block)
        thumb = thumb_m.group(1) if thumb_m else ""

        # Duration: span with "duration" class
        dur_m = re.search(
            r'class="[^"]*duration[^"]*"[^>]*>(.*?)<',
            block,
            re.DOTALL,
        )
        duration = re.sub(r"<[^>]+>", "", dur_m.group(1)).strip() if dur_m else ""

        # ID from URL slug
        id_m = re.search(r"/free-stock-video/([a-z0-9\-_]+)/?$", url)
        vid_id = id_m.group(1) if id_m else url.rstrip("/").split("/")[-1]

        out.append({
            "id": vid_id,
            "title": title,
            "url": url,
            "thumb": thumb,
            "duration_text": duration,
        })
    return out


def _parse_duration_to_seconds(text: str) -> int:
    """Parse '0:45' / '1:23' / '12:34' style duration to seconds."""
    import re
    m = re.match(r"(\d+):(\d{1,2})", text.strip())
    if not m:
        return 0
    return int(m.group(1)) * 60 + int(m.group(2))


def search_videos(
    query: str,
    max_results: int = 20,
    polite_delay_sec: float | None = None,
) -> list[VideoMeta]:
    """Scrape Mixkit search results.

    Args:
        query: free-text search.
        max_results: limit on returned results.
        polite_delay_sec: delay between successive page requests (default from config).

    Returns: list of VideoMeta from Mixkit search.

    Note: Mixkit search uses query params (`?s=<query>`), single page.
    """
    delay = polite_delay_sec if polite_delay_sec is not None else MIXKIT_SCRAPE_DELAY_SEC

    params = {"s": query}
    time.sleep(delay)  # always polite, even single request

    resp = requests.get(MIXKIT_SEARCH_URL, params=params, headers=DEFAULT_HEADERS, timeout=20)
    resp.raise_for_status()

    cards = _find_video_cards(resp.text)

    out: list[VideoMeta] = []
    for card in cards[:max_results]:
        # We don't have direct MP4 URL from the search page; need to fetch
        # the video page to extract the download URL. For now, defer the
        # download URL extraction to download_video() which fetches the page.
        out.append(
            VideoMeta(
                id=card["id"],
                title=card["title"],
                download_url=card["url"],   # page URL; download_video resolves
                thumbnail_url=card["thumb"],
                duration_sec=_parse_duration_to_seconds(card["duration_text"]),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Download (resolves video page → MP4 URL)
# ---------------------------------------------------------------------------

def _resolve_download_url(page_url: str, polite_delay_sec: float) -> str:
    """Fetch a Mixkit video page and extract the MP4 download URL."""
    import re
    time.sleep(polite_delay_sec)
    resp = requests.get(page_url, headers=DEFAULT_HEADERS, timeout=20)
    resp.raise_for_status()

    # Mixkit video pages expose MP4 via:
    #   <video> tag with <source src="...mp4">
    # or via meta og:video
    # Try <source src="...mp4"> first
    m = re.search(r'<source[^>]+src="([^"]+\.mp4)"', resp.text)
    if m:
        return m.group(1)

    # Fallback: og:video meta
    m = re.search(r'<meta[^>]+property="og:video"[^>]+content="([^"]+)"', resp.text)
    if m:
        return m.group(1)

    raise RuntimeError(f"could not extract MP4 URL from {page_url}")


def download_video(
    video_meta: VideoMeta,
    output_dir: Path,
    polite_delay_sec: float | None = None,
) -> Path:
    """Download a Mixkit video. Resolves video page → MP4 URL first."""
    delay = polite_delay_sec if polite_delay_sec is not None else MIXKIT_SCRAPE_DELAY_SEC

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{video_meta.id}.mp4"

    mp4_url = _resolve_download_url(video_meta.download_url, delay)

    with requests.get(mp4_url, headers=DEFAULT_HEADERS, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with target.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)

    return target


# ---------------------------------------------------------------------------
# ffprobe (same shape as coverr/youtube)
# ---------------------------------------------------------------------------

def probe_metadata(mp4_path: Path) -> ProbeResult:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise RuntimeError("ffprobe not found in PATH")

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
    metadata = {
        "id": f"mixkit:{video_meta.id}",
        "source": "mixkit",
        "model": None,
        "seed": None,
        "prompt": video_meta.title,
        "negative_prompt": None,
        "duration_sec": probe.duration_sec,
        "resolution": f"{probe.width}x{probe.height}",
        "fps": probe.fps,
        "character_ref": None,
        "scene_ref": None,
        "tags": ["mixkit"],
        "license": "mixkit-free",
        "attribution": f"Mixkit (https://mixkit.co/free-stock-video/{video_meta.id})",
        "created_at": None,
        "sha256": sha256_file(mp4_path),
        "mixkit_id": video_meta.id,
        "mixkit_title": video_meta.title,
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
    polite_delay_sec: float | None = None,
) -> IngestResult:
    """Scrape Mixkit, download top-N, probe, write metadata."""
    output_dir = output_dir or (STOCK_DIR / "mixkit")

    metas = search_videos(query, max_results=count, polite_delay_sec=polite_delay_sec)
    files: list[Path] = []
    errors: list[tuple[str, str]] = []

    for vm in metas[:count]:
        try:
            mp4 = download_video(vm, output_dir, polite_delay_sec)
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
    "_find_video_cards",
    "_parse_duration_to_seconds",
]