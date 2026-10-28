"""
Library indexer — walks library/, captions + embeds clips, writes index.sqlite.

Architecture:
- For each clip in `library/` (any source), extract one representative frame
  (mid-video or t=0.5s) and:
    1. Caption via LM Studio (BLIP-2 multimodal) → descriptive text
    2. Embed (caption + tags + prompt) via LM Studio text-embedding model
       (bge-large-en-v1.5 by default) → float32 vector
    3. Write into `library/index.sqlite` with sha256 as a key
- Idempotent: re-indexing skips clips whose (sha256, indexed_at) is unchanged.
- Graceful fallback: if LM Studio unreachable, index is built without
  caption/embedding (NULL values) and a warning. Matcher can still fall back
  to text matching.

LM Studio endpoints:
- `/v1/chat/completions` with image content for captioning
- `/v1/embeddings` for text embeddings

Schema in SQLite (matches library/README.md):
    clips(id, path, sha256, source, caption, embedding, tags,
          duration_sec, width, height, fps, indexed_at)
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import struct
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from capcut.lib.config import (
    LIBRARY_INDEX,
    LIBRARY_ROOT,
    LM_STUDIO_API_TOKEN,
    LM_STUDIO_CAPTION_MODEL,
    LM_STUDIO_EMBED_MODEL,
    LM_STUDIO_URL,
)
from capcut.lib.media import metadata_path_for, probe_media


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS clips (
  id            TEXT PRIMARY KEY,
  path          TEXT NOT NULL,
  sha256        TEXT NOT NULL,
  source        TEXT,
  caption       TEXT,
  embedding     BLOB,              -- packed float32 array
  tags          TEXT,              -- JSON array
  duration_sec  REAL,
  width         INTEGER,
  height        INTEGER,
  fps           REAL,
  indexed_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_clips_source ON clips(source);
CREATE INDEX IF NOT EXISTS idx_clips_sha256 ON clips(sha256);
"""


def init_db(db_path: Path = LIBRARY_INDEX) -> sqlite3.Connection:
    """Create database + tables if missing. Returns connection."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# Vector helpers (float32 <-> bytes for SQLite storage)
# ---------------------------------------------------------------------------

def pack_embedding(vec: list[float]) -> bytes:
    """Pack list[float] to bytes (little-endian float32)."""
    return struct.pack(f"<{len(vec)}f", *vec)


def unpack_embedding(blob: bytes) -> list[float]:
    """Unpack bytes back to list[float]."""
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob))


# ---------------------------------------------------------------------------
# LM Studio clients
# ---------------------------------------------------------------------------

def caption_image(image_path: Path, *, timeout: int = 60) -> str:
    """Caption an image via LM Studio multimodal chat (BLIP-2).

    Returns descriptive text. Raises on connection error / unexpected response.
    """
    import base64
    b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    data_url = f"data:image/png;base64,{b64}"

    payload = {
        "model": LM_STUDIO_CAPTION_MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this video frame in 1-2 sentences. Focus on the main subject, action, and setting."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }],
        "temperature": 0.2,
        "max_tokens": 100,
    }
    url = f"{LM_STUDIO_URL}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if LM_STUDIO_API_TOKEN:
        headers["Authorization"] = f"Bearer {LM_STUDIO_API_TOKEN}"
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def embed_text(
    text: str, *, model: str | None = None, timeout: int = 30
) -> list[float]:
    """Embed text via the LM Studio embedding endpoint.

    `model` overrides the configured embedding model for this call; the
    default comes from `LM_STUDIO_EMBED_MODEL`.
    """
    payload = {
        "model": model or LM_STUDIO_EMBED_MODEL,
        "input": text,
    }
    url = f"{LM_STUDIO_URL}/v1/embeddings"
    headers = {"Content-Type": "application/json"}
    if LM_STUDIO_API_TOKEN:
        headers["Authorization"] = f"Bearer {LM_STUDIO_API_TOKEN}"
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    return data["data"][0]["embedding"]


def lm_studio_alive() -> bool:
    """Quick liveness check: GET /v1/models. False if LM Studio is down.

    Uses bearer auth from LM_STUDIO_API_TOKEN if set (LM Studio may require
    auth even for /v1/models endpoint).
    """
    try:
        headers = {}
        if LM_STUDIO_API_TOKEN:
            headers["Authorization"] = f"Bearer {LM_STUDIO_API_TOKEN}"
        resp = requests.get(f"{LM_STUDIO_URL}/v1/models", headers=headers, timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Frame extraction (ffmpeg)
# ---------------------------------------------------------------------------

def extract_frame(mp4_path: Path, output_path: Path, *, t_sec: float = 0.5) -> Path:
    """Extract one frame at t_sec (default 0.5s) to PNG via ffmpeg."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg not found in PATH")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-ss", str(t_sec),
        "-i", str(mp4_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=30)
    return output_path


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

@dataclass
class IndexStats:
    scanned: int = 0
    indexed: int = 0
    skipped: int = 0          # already indexed, sha256 unchanged
    removed: int = 0           # orphan rows dropped (path-derived ids)
    errors: list[tuple[str, str]] = None  # (clip_path, error)

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


def _load_metadata_for(mp4_path: Path) -> dict[str, Any]:
    """Read sibling .metadata.json. Empty dict if missing."""
    meta_path = metadata_path_for(mp4_path)
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _is_already_indexed(conn: sqlite3.Connection, clip_id: str, sha256: str) -> bool:
    """True if clip with this id+sha256 is already indexed."""
    cur = conn.execute(
        "SELECT 1 FROM clips WHERE id = ? AND sha256 = ?",
        (clip_id, sha256),
    )
    return cur.fetchone() is not None


def _probe_for_indexing(mp4_path: Path) -> dict[str, Any]:
    """Quick probe: duration / width / height / fps via ffprobe.

    Lenient: a file that cannot be probed yields zeros, and the caller
    skips clips with a non-positive duration.
    """
    probe = probe_media(mp4_path, strict=False)
    return {
        "duration_sec": probe.duration_sec,
        "width": probe.width,
        "height": probe.height,
        "fps": probe.fps,
    }

def _build_clip_id(
    mp4_path: Path,
    metadata: dict[str, Any],
    library_root: Path,
) -> str:
    """Prefer metadata.id (canonical); fall back to the path relative to the
    library root.

    The fallback has to be the *relative* path, not the file name: two assets
    with the same base name in different shows or episodes would otherwise
    share one id, and the second one indexed would silently replace the
    first in the shared index.
    """
    if "id" in metadata and metadata["id"]:
        return metadata["id"]
    try:
        rel = mp4_path.resolve().relative_to(library_root.resolve())
    except ValueError:
        rel = mp4_path
    return f"unknown:{rel.as_posix()}"


def _build_embedding_text(metadata: dict[str, Any], caption: str) -> str:
    """Compose text for embedding: caption + tags + prompt."""
    parts: list[str] = []
    if caption:
        parts.append(caption)
    tags = metadata.get("tags") or []
    if tags:
        parts.append("tags: " + ", ".join(str(t) for t in tags))
    prompt = metadata.get("prompt") or metadata.get("youtube_title") or metadata.get("mixkit_title")
    if prompt:
        parts.append(f"title: {prompt}")
    return "\n".join(parts)


def index_clip(
    conn: sqlite3.Connection,
    mp4_path: Path,
    library_root: Path,
    *,
    caption: bool = True,
    embed: bool = True,
    frame_tmp_dir: Path | None = None,
) -> bool:
    """Index a single clip. Returns True if newly added, False if skipped/error.

    Side effect: writes/updates a row in `clips`.
    """
    from capcut.lib.lifecycle import sha256_file

    sha256 = sha256_file(mp4_path)
    metadata = _load_metadata_for(mp4_path)
    rel_path = str(mp4_path.relative_to(library_root))
    clip_id = _build_clip_id(mp4_path, metadata, library_root)

    if _is_already_indexed(conn, clip_id, sha256):
        return False

    # Probe video
    probe = _probe_for_indexing(mp4_path)
    if probe.get("duration_sec", 0) <= 0:
        return False  # skip corrupt or empty videos

    # Extract frame (for captioning)
    frame_path: Path | None = None
    caption_text = ""
    embedding_blob: bytes | None = None

    tmp_dir = frame_tmp_dir or (library_root / ".tmp" / "frames")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    frame_path = tmp_dir / f"{sha256[:16]}.png"

    if caption and lm_studio_alive():
        try:
            extract_frame(mp4_path, frame_path)
            caption_text = caption_image(frame_path)
        except Exception:
            caption_text = ""  # graceful: index without caption

    # Embed (text-based: caption + tags + title)
    if embed and lm_studio_alive():
        text = _build_embedding_text(metadata, caption_text)
        if text:
            try:
                vec = embed_text(text)
                embedding_blob = pack_embedding(vec)
            except Exception:
                embedding_blob = None

    # Cleanup frame
    if frame_path and frame_path.exists():
        frame_path.unlink()

    # Insert row
    conn.execute(
        """
        INSERT INTO clips
        (id, path, sha256, source, caption, embedding, tags,
         duration_sec, width, height, fps, indexed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            path = excluded.path,
            sha256 = excluded.sha256,
            source = excluded.source,
            caption = excluded.caption,
            embedding = excluded.embedding,
            tags = excluded.tags,
            duration_sec = excluded.duration_sec,
            width = excluded.width,
            height = excluded.height,
            fps = excluded.fps,
            indexed_at = excluded.indexed_at
        """,
        (
            clip_id,
            rel_path,
            sha256,
            metadata.get("source"),
            caption_text,
            embedding_blob,
            json.dumps(metadata.get("tags", []), ensure_ascii=False),
            probe.get("duration_sec", 0),
            probe.get("width", 0),
            probe.get("height", 0),
            probe.get("fps", 0.0),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    # Commit here so that a direct caller cannot lose the row by closing the
    # connection. index_library() commits as well — a redundant commit is
    # harmless, a missing one is not.
    conn.commit()
    return True


def index_library(
    library_root: Path = LIBRARY_ROOT,
    db_path: Path = LIBRARY_INDEX,
    *,
    caption: bool = True,
    embed: bool = True,
) -> IndexStats:
    """Walk library/ recursively, index all .mp4 files.

    Args:
        library_root: root to walk.
        db_path: SQLite database.
        caption: whether to call LM Studio for BLIP-2 captioning.
        embed: whether to call LM Studio for embeddings.

    Returns: IndexStats with counts and errors.
    """
    stats = IndexStats()
    conn = init_db(db_path)
    seen_ids: set[str] = set()

    for mp4_path in sorted(library_root.rglob("*.mp4")):
        # Skip hidden / .tmp directories
        if any(part.startswith(".") for part in mp4_path.parts):
            continue
        stats.scanned += 1
        try:
            clip_id = _build_clip_id(
                mp4_path, _load_metadata_for(mp4_path), library_root
            )
            seen_ids.add(clip_id)
            added = index_clip(conn, mp4_path, library_root, caption=caption, embed=embed)
            if added:
                stats.indexed += 1
                conn.commit()
            else:
                stats.skipped += 1
        except Exception as e:
            stats.errors.append((str(mp4_path), str(e)))

    # Rows whose id is derived from the path (no metadata.id) die with the
    # file: renaming or moving a clip used to reuse its id, and the
    # path-based id no longer does. Without this the index keeps returning
    # ids whose files no longer exist, and the matcher can match dead paths.
    orphans = [
        row[0]
        for row in conn.execute(
            "SELECT id FROM clips WHERE id LIKE 'unknown:%'"
        ).fetchall()
        if row[0] not in seen_ids
    ]
    for orphan in orphans:
        conn.execute("DELETE FROM clips WHERE id = ?", (orphan,))
        stats.removed += 1
    if orphans:
        conn.commit()

    conn.close()
    return stats


# ---------------------------------------------------------------------------
# Lookup helpers (used by F6 matcher)
# ---------------------------------------------------------------------------

def get_clip_by_id(db_path: Path, clip_id: str) -> dict[str, Any] | None:
    """Fetch clip row by id. Returns dict or None."""
    conn = init_db(db_path)
    try:
        row = conn.execute(
            "SELECT id, path, sha256, source, caption, embedding, tags, "
            "duration_sec, width, height, fps, indexed_at FROM clips WHERE id = ?",
            (clip_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "path": row[1],
            "sha256": row[2],
            "source": row[3],
            "caption": row[4],
            "embedding": unpack_embedding(row[5]) if row[5] else None,
            "tags": json.loads(row[6]) if row[6] else [],
            "duration_sec": row[7],
            "width": row[8],
            "height": row[9],
            "fps": row[10],
            "indexed_at": row[11],
        }
    finally:
        conn.close()


class EmbeddingDimensionMismatch(ValueError):
    """A query was embedded with a different model than the index.

    Comparing vectors of different lengths would silently truncate to the
    shorter one and return a plausible-looking score. That is worse than no
    result at all, so it raises instead.
    """


def search_by_text(
    db_path: Path,
    query_embedding: list[float],
    *,
    limit: int = 10,
    source_filter: str | None = None,
) -> list[tuple[str, float]]:
    """Brute-force cosine similarity search. Returns [(clip_id, score), ...] sorted desc.

    For 10k+ clips, replace with FAISS or sqlite-vss. Until then, this is fine.

    Raises:
        EmbeddingDimensionMismatch: the index holds vectors of a different
            length than the query — the query was embedded with another
            model.
    """
    import math
    conn = init_db(db_path)
    try:
        if source_filter:
            rows = conn.execute(
                "SELECT id, embedding FROM clips WHERE source = ? AND embedding IS NOT NULL",
                (source_filter,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, embedding FROM clips WHERE embedding IS NOT NULL"
            ).fetchall()

        scored: list[tuple[str, float]] = []
        for clip_id, blob in rows:
            vec = unpack_embedding(blob)
            if len(vec) != len(query_embedding):
                raise EmbeddingDimensionMismatch(
                    f"embedding dimension mismatch for {clip_id}: index has "
                    f"{len(vec)}, query has {len(query_embedding)}. The query was "
                    f"embedded with a different model than the index."
                )
            # cosine similarity
            dot = sum(a * b for a, b in zip(query_embedding, vec))
            norm_a = math.sqrt(sum(a * a for a in query_embedding))
            norm_b = math.sqrt(sum(b * b for b in vec))
            if norm_a == 0 or norm_b == 0:
                continue
            scored.append((clip_id, dot / (norm_a * norm_b)))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]
    finally:
        conn.close()


__all__ = [
    "init_db",
    "pack_embedding",
    "unpack_embedding",
    "caption_image",
    "embed_text",
    "lm_studio_alive",
    "extract_frame",
    "IndexStats",
    "index_clip",
    "index_library",
    "get_clip_by_id",
    "search_by_text",
]