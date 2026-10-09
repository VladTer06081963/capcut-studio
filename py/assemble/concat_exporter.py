"""
Concat timeline exporter — build Concat-compatible JSON from spec + matched.

The output is a Concat project JSON that can be imported via Concat MCP
(or loaded directly into Concat GUI for manual polishing).

Schema (Concat-compatible, simplified):
{
  "project": {
    "name": "<show>-<ep>",
    "duration_sec": <float>,
    "resolution": "<WxH>",
    "fps": <float>
  },
  "tracks": [
    {
      "id": "<track-id>",
      "type": "video" | "audio" | "overlay",
      "clips": [
        {
          "id": "<clip-id>",
          "src": "<relative path to .mp4 or null>",
          "start_sec": <float>,
          "duration_sec": <float>,
          "caption": "<text or null>",
          "voiceover": "<text or null>",
          "transition_in": "cut" | "fade" | "dissolve" | null,
          "transition_out": "cut" | "fade" | "dissolve" | null
        }
      ]
    }
  ]
}

Notes:
- Default transitions: 'cut' between video scenes, 'fade' at scene-1 start
  and last-scene end (for nice open/close).
- Audio track populated from scene.voiceover (TTS later fills src).
- Overlay track for character overlays (TBD when overlay clips are matched).
- Timeline is laid out sequentially by scene.n. Non-matched scenes are
  skipped with a warning in `unmatched_scenes`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from py.episode.spec_writer import EpisodeSpec
from py.search.matcher import MatchedEpisode, SceneMatch


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ConcatClip:
    id: str
    src: str | None
    start_sec: float
    duration_sec: float
    caption: str | None = None
    voiceover: str | None = None
    transition_in: str | None = "cut"
    transition_out: str | None = "cut"


@dataclass
class ConcatTrack:
    id: str
    type: str                            # "video" | "audio" | "overlay"
    clips: list[ConcatClip] = field(default_factory=list)


@dataclass
class ConcatProject:
    name: str
    duration_sec: float
    resolution: str
    fps: float


@dataclass
class ConcatTimeline:
    schema: int                          # SCHEMA_VERSION
    project: ConcatProject
    tracks: list[ConcatTrack]
    unmatched_scenes: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


SCHEMA_VERSION = 1

DEFAULT_RESOLUTION = "1920x1080"
DEFAULT_FPS = 24.0
DEFAULT_TRANSITION_INTRA = "cut"
DEFAULT_TRANSITION_OPEN = "fade"
DEFAULT_TRANSITION_CLOSE = "fade"


# ---------------------------------------------------------------------------
# Scene → clip conversion
# ---------------------------------------------------------------------------

def _scene_track_type(track: str) -> str:
    """Map spec track name → Concat track type."""
    if track == "video":
        return "video"
    if track == "audio":
        return "audio"
    if track == "overlay":
        return "overlay"
    return "video"  # default


def _resolve_path(library_root: Path, relative_path: str | None) -> str | None:
    """Resolve relative library path to absolute. Returns None if missing."""
    if not relative_path:
        return None
    abs_path = library_root / relative_path
    return str(abs_path) if abs_path.exists() else None


def _pick_transition(
    scene_index: int,
    total_scenes: int,
    is_first: bool,
    is_last: bool,
) -> tuple[str | None, str | None]:
    """Pick transition_in / transition_out for a video scene.

    Rules:
    - First scene: in=fade, out=cut (or out=fade if single scene)
    - Last scene (not first): in=cut, out=fade
    - Middle scenes: in=cut, out=cut
    - Single scene (first=last): in=fade, out=fade
    """
    if total_scenes == 1:
        return DEFAULT_TRANSITION_OPEN, DEFAULT_TRANSITION_CLOSE
    if is_first:
        return DEFAULT_TRANSITION_OPEN, DEFAULT_TRANSITION_INTRA
    if is_last:
        return DEFAULT_TRANSITION_INTRA, DEFAULT_TRANSITION_CLOSE
    return DEFAULT_TRANSITION_INTRA, DEFAULT_TRANSITION_INTRA


# ---------------------------------------------------------------------------
# Main: build timeline
# ---------------------------------------------------------------------------

def assemble_timeline(
    spec: EpisodeSpec,
    matched: MatchedEpisode,
    *,
    library_root: Path,
    resolution: str = DEFAULT_RESOLUTION,
    fps: float = DEFAULT_FPS,
) -> ConcatTimeline:
    """Build a ConcatTimeline from spec + matched.

    Args:
        spec: EpisodeSpec from spec.json.
        matched: MatchedEpisode from matched.json.
        library_root: root for resolving clip paths.
        resolution: project resolution (default 1920x1080).
        fps: project fps (default 24).

    Returns: ConcatTimeline ready for JSON serialization.
    """
    # Group clips by track type
    tracks_by_type: dict[str, list[ConcatClip]] = {
        "video": [],
        "audio": [],
        "overlay": [],
    }

    unmatched: list[int] = []
    warnings: list[str] = []
    cursor_sec: float = 0.0
    video_scenes = [s for s in spec.scenes if s.track == "video"]
    total_video = len(video_scenes)

    for scene_spec in spec.scenes:
        scene_match = next(
            (m for m in matched.scenes if m.n == scene_spec.n),
            None,
        )

        # Determine transitions (for video tracks)
        if scene_spec.track == "video":
            is_first = scene_spec.n == video_scenes[0].n if video_scenes else True
            is_last = scene_spec.n == video_scenes[-1].n if video_scenes else True
            t_in, t_out = _pick_transition(0, total_video, is_first, is_last)
        else:
            t_in, t_out = None, None

        track_type = _scene_track_type(scene_spec.track)

        if track_type == "video":
            # Need a matched video clip
            if scene_match is None or scene_match.clip_id is None or scene_match.clip_path is None:
                unmatched.append(scene_spec.n)
                warnings.append(f"scene {scene_spec.n}: no video clip matched (query: {scene_spec.query[:60]!r})")
                continue
            src = _resolve_path(library_root, scene_match.clip_path)
            if src is None:
                warnings.append(f"scene {scene_spec.n}: matched clip file not found at {scene_match.clip_path}")
                unmatched.append(scene_spec.n)
                continue
            clip = ConcatClip(
                id=f"scene-{scene_spec.n}",
                src=src,
                start_sec=cursor_sec,
                duration_sec=scene_spec.duration_sec,
                caption=scene_spec.caption,
                voiceover=None,
                transition_in=t_in,
                transition_out=t_out,
            )
            tracks_by_type["video"].append(clip)

        elif track_type == "audio":
            # Audio: voiceover placeholder (TTS will fill src later)
            if not scene_spec.voiceover:
                warnings.append(f"scene {scene_spec.n}: audio track without voiceover, skipping")
                continue
            clip = ConcatClip(
                id=f"scene-{scene_spec.n}",
                src=None,  # TTS-generated later
                start_sec=cursor_sec,
                duration_sec=scene_spec.duration_sec,
                caption=None,
                voiceover=scene_spec.voiceover,
                transition_in=None,
                transition_out=None,
            )
            tracks_by_type["audio"].append(clip)

        elif track_type == "overlay":
            # Overlay: needs source clip — if matched, use it
            if scene_match is None or scene_match.clip_id is None or scene_match.clip_path is None:
                warnings.append(f"scene {scene_spec.n}: overlay without match, skipping")
                continue
            src = _resolve_path(library_root, scene_match.clip_path)
            if src is None:
                warnings.append(f"scene {scene_spec.n}: overlay file not found")
                continue
            clip = ConcatClip(
                id=f"scene-{scene_spec.n}",
                src=src,
                start_sec=cursor_sec,
                duration_sec=scene_spec.duration_sec,
                caption=scene_spec.caption,
                voiceover=None,
                transition_in=None,
                transition_out=None,
            )
            tracks_by_type["overlay"].append(clip)

        cursor_sec += scene_spec.duration_sec

    # Build tracks
    tracks = [
        ConcatTrack(id="video-main", type="video", clips=tracks_by_type["video"]),
        ConcatTrack(id="audio-main", type="audio", clips=tracks_by_type["audio"]),
        ConcatTrack(id="overlay-character", type="overlay", clips=tracks_by_type["overlay"]),
    ]
    # Drop empty tracks
    tracks = [t for t in tracks if t.clips]

    project = ConcatProject(
        name=f"{spec.show}-{spec.id}",
        duration_sec=cursor_sec,
        resolution=resolution,
        fps=fps,
    )

    return ConcatTimeline(
        schema=SCHEMA_VERSION,
        project=project,
        tracks=tracks,
        unmatched_scenes=unmatched,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def write_concat_timeline(timeline: ConcatTimeline, output_path: Path) -> Path:
    """Write Concat-compatible JSON to output_path (typically rendered/draft.json)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(timeline), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def load_concat_timeline(path: Path) -> ConcatTimeline:
    """Read Concat timeline JSON back."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    tracks = []
    for t in raw.get("tracks", []):
        clips = [ConcatClip(**c) for c in t.get("clips", [])]
        tracks.append(ConcatTrack(id=t["id"], type=t["type"], clips=clips))
    project = ConcatProject(**raw["project"])
    return ConcatTimeline(
        schema=raw.get("schema", SCHEMA_VERSION),
        project=project,
        tracks=tracks,
        unmatched_scenes=raw.get("unmatched_scenes", []),
        warnings=raw.get("warnings", []),
    )


__all__ = [
    "ConcatClip",
    "ConcatTrack",
    "ConcatProject",
    "ConcatTimeline",
    "assemble_timeline",
    "write_concat_timeline",
    "load_concat_timeline",
    "SCHEMA_VERSION",
]