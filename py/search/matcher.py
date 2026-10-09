"""
Episode matcher — match scenes from spec.json against library/index.sqlite.

For each scene with a `query`, embed the query via LM Studio, search the
index for top-N candidates by cosine similarity, apply `preferred_source`
priority (ai → stock → any), and pick the best match. Writes matched.json.

Architecture:
- Uses embedder.search_by_text (F5) for the actual similarity search.
- `preferred_source` filter chain: 'ai' first, then 'stock', then 'any'.
- Empty matches produce a warning (not a hard fail) — caller can decide
  whether to add the missing clip via AI generation or skip the scene.
- Idempotent: re-running with same spec produces identical matched.json
  (assuming library is unchanged).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from py.episode.spec_writer import EpisodeSpec
from py.index import embedder
from py.lib.config import (
    DEFAULT_VIDEO_PROVIDER,
    LIBRARY_INDEX,
    LM_STUDIO_EMBED_MODEL,
    LM_STUDIO_URL,
    has_openrouter,
)


SOURCE_PRIORITY: dict[str, list[str | None]] = {
    # preferred_source → ordered list of source filters to try
    "ai":    ["ai", "stock", None],   # ai first, then stock, then any
    "stock": ["stock", "ai", None],
    "any":   [None],                   # already any
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SceneMatch:
    n: int
    clip_id: str | None               # None if no match
    score: float                       # cosine similarity (0..1)
    source: str                        # 'ai' | 'stock' | 'archive' | 'youtube' | 'mixkit' | 'coverr' | 'none'
    clip_path: str | None = None       # relative to library_root
    duration_sec: float = 0.0          # duration of matched clip
    warnings: list[str] = field(default_factory=list)


@dataclass
class MatchedEpisode:
    spec_id: str
    spec_sha256: str
    matched_at: str
    embed_model: str
    scenes: list[SceneMatch]

    def unmatched_scenes(self) -> list[int]:
        """Return list of scene.n with no match (caller may want to handle)."""
        return [s.n for s in self.scenes if s.clip_id is None]


# ---------------------------------------------------------------------------
# Query embedding helper (reuse F5)
# ---------------------------------------------------------------------------

def _embed_query(query: str, model: str) -> list[float]:
    """Embed a scene query via LM Studio. Raises on failure."""
    if not query.strip():
        raise ValueError("empty query")
    return embedder.embed_text(query, timeout=30)


# ---------------------------------------------------------------------------
# Source priority resolver
# ---------------------------------------------------------------------------

def _resolve_source_filter(preferred_source: str) -> list[str | None]:
    """Return ordered list of source filters to try."""
    return SOURCE_PRIORITY.get(preferred_source, [None])


# ---------------------------------------------------------------------------
# Main: match an episode
# ---------------------------------------------------------------------------

def match_episode(
    spec: EpisodeSpec,
    *,
    db_path: Path = LIBRARY_INDEX,
    embed_model: str = LM_STUDIO_EMBED_MODEL,
    candidates_per_filter: int = 5,
) -> MatchedEpisode:
    """Match each scene in spec against the library index.

    Args:
        spec: parsed EpisodeSpec (from spec.json).
        db_path: SQLite index path.
        embed_model: LM Studio embedding model.
        candidates_per_filter: how many candidates to fetch per source filter.

    Returns: MatchedEpisode with one SceneMatch per scene.

    Raises:
        RuntimeError: if LM Studio is unreachable.
    """
    if not embedder.lm_studio_alive():
        raise RuntimeError(
            f"LM Studio unreachable at {LM_STUDIO_URL}. "
            "Start LM Studio or set LM_STUDIO_URL in .env"
        )

    matches: list[SceneMatch] = []

    for scene in spec.scenes:
        # Skip audio tracks (no visual query)
        if scene.track == "audio" or not scene.query.strip():
            matches.append(SceneMatch(
                n=scene.n,
                clip_id=None,
                score=0.0,
                source="none",
                warnings=["audio track or empty query, no visual match"],
            ))
            continue

        # Embed query
        try:
            query_vec = _embed_query(scene.query, embed_model)
        except Exception as e:
            matches.append(SceneMatch(
                n=scene.n,
                clip_id=None,
                score=0.0,
                source="none",
                warnings=[f"embed failed: {e}"],
            ))
            continue

        # Try source filters in priority order
        best_clip_id: str | None = None
        best_score: float = 0.0
        best_source: str = "none"
        best_path: str | None = None
        best_duration: float = 0.0
        warnings: list[str] = []

        for src_filter in _resolve_source_filter(scene.preferred_source):
            candidates = embedder.search_by_text(
                db_path, query_vec,
                limit=candidates_per_filter,
                source_filter=src_filter,
            )
            if not candidates:
                continue

            clip_id, score = candidates[0]
            if score < 0.1:  # very low similarity → skip
                warnings.append(
                    f"low similarity ({score:.2f}) for source={src_filter}"
                )
                continue

            clip = embedder.get_clip_by_id(db_path, clip_id)
            if not clip:
                warnings.append(f"matched id {clip_id} not found in db")
                continue

            best_clip_id = clip_id
            best_score = score
            best_source = clip["source"]
            best_path = clip["path"]
            best_duration = clip["duration_sec"]
            break  # first match wins (priority order)

        if best_clip_id is None:
            warnings.append("no candidate passed threshold for any source filter")

        matches.append(SceneMatch(
            n=scene.n,
            clip_id=best_clip_id,
            score=best_score,
            source=best_source,
            clip_path=best_path,
            duration_sec=best_duration,
            warnings=warnings,
        ))

    # Compute spec sha256 for idempotency
    import hashlib
    spec_str = json.dumps([asdict(s) for s in spec.scenes], sort_keys=True)
    spec_sha256 = hashlib.sha256(spec_str.encode()).hexdigest()

    return MatchedEpisode(
        spec_id=spec.id,
        spec_sha256=spec_sha256,
        matched_at=datetime.now(timezone.utc).isoformat(),
        embed_model=embed_model,
        scenes=matches,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def write_matched(matched: MatchedEpisode, output_path: Path) -> Path:
    """Write matched.json to output_path (typically serials/<show>/<ep>/matched.json)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(matched), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def load_matched(path: Path) -> MatchedEpisode:
    """Read matched.json and parse into MatchedEpisode."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    scenes = [SceneMatch(**s) for s in raw["scenes"]]
    return MatchedEpisode(
        spec_id=raw["spec_id"],
        spec_sha256=raw["spec_sha256"],
        matched_at=raw["matched_at"],
        embed_model=raw["embed_model"],
        scenes=scenes,
    )


__all__ = [
    "SceneMatch",
    "MatchedEpisode",
    "match_episode",
    "write_matched",
    "load_matched",
    "SOURCE_PRIORITY",
]