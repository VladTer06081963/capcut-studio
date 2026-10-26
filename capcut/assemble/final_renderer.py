"""
Final renderer — produce `rendered/final.mp4` from a Concat timeline.

Policy notes (see AGENTS.md → "Project invariants"):

- `rendered/final.mp4` is **immutable from creation**. This module never
  overwrites an existing final.mp4; the caller refuses before we are
  invoked, and `render_final()` itself writes to a temp path and renames
  into place only after a successful encode.
- Caption burn-in, transitions beyond the timeline's declared values,
  audio mixing and voiceover TTS are **out of scope** — those stay
  Concat/CapCut polish steps. This writer concatenates the video track.
- The approval gate is enforced by the CLI wrapper
  (`scripts/render_final.py`), not here: this module is a pure
  "timeline → mp4" primitive and is unit-testable in isolation.

The ffmpeg invocation has two paths:

1. **Stream copy** (`-c copy`) — fast, no re-encode. Works when all
   source clips share compatible codec/params.
2. **Re-encode** — fallback when ffmpeg rejects the copy (mismatched
   codecs, resolution or pixel format). Re-encodes to H.264/AAC with
   a scale filter that fits the target resolution.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_FFMPEG = "ffmpeg"
DEFAULT_FFPROBE = "ffprobe"

DEFAULT_VIDEO_CODEC = "libx264"
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_PRESET = "medium"
DEFAULT_CRF = "20"


class FinalRenderError(RuntimeError):
    """Raised when the final render cannot be produced."""


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------

def _video_clips(timeline: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the clips of the first `video` track, in timeline order."""
    for track in timeline.get("tracks", []):
        if track.get("type") == "video":
            return [c for c in track.get("clips", []) if c.get("src")]
    return []


def _concat_list_path(timeline: dict[str, Any]) -> str:
    """Deterministic temp name for the ffmpeg concat list, derived from
    the project name so concurrent renders of different episodes do not
    collide."""
    name = (timeline.get("project", {}) or {}).get("name", "episode")
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)
    return f"capcut_final_{safe}_concat.txt"


def build_ffmpeg_command(
    timeline: dict[str, Any],
    output_path: Path,
    *,
    ffmpeg_bin: str = DEFAULT_FFMPEG,
    concat_list: Path | None = None,
    reencode: bool = False,
    resolution: str | None = None,
    fps: float | None = None,
) -> list[str]:
    """Build the ffmpeg argv for a Concat timeline.

    Args:
        timeline: parsed `draft.json` (Concat timeline schema).
        output_path: target mp4 path.
        ffmpeg_bin: ffmpeg executable name.
        concat_list: where the concat list file lives. Defaults to a
            deterministic name next to `output_path`.
        reencode: force the re-encode path (skip stream copy).
        resolution: target WxH for the re-encode path. Defaults to the
            timeline's project resolution.
        fps: target fps for the re-encode path. Defaults to the
            timeline's project fps.

    Returns:
        argv list ready for `subprocess.run`.

    Raises:
        FinalRenderError: if the timeline has no usable video clips.
    """
    clips = _video_clips(timeline)
    if not clips:
        raise FinalRenderError(
            "timeline has no video clips with a source path — nothing to render"
        )

    project = timeline.get("project", {}) or {}
    if resolution is None:
        resolution = project.get("resolution", "1920x1080")
    if fps is None:
        fps = project.get("fps", 24.0)

    if concat_list is None:
        concat_list = output_path.parent / _concat_list_path(timeline)

    cmd = [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list)]

    if reencode:
        w, _, h = str(resolution).partition("x")
        vf = f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:-1:-1,fps={fps}"
        cmd += [
            "-c:v", DEFAULT_VIDEO_CODEC,
            "-preset", DEFAULT_PRESET,
            "-crf", str(DEFAULT_CRF),
            "-vf", vf,
        ]
        cmd += ["-c:a", DEFAULT_AUDIO_CODEC]
    else:
        cmd += ["-c", "copy"]

    cmd.append(str(output_path))
    return cmd


def build_concat_list(timeline: dict[str, Any], concat_list: Path) -> Path:
    """Write the ffmpeg concat list file for the timeline's video track."""
    clips = _video_clips(timeline)
    if not clips:
        raise FinalRenderError("timeline has no video clips with a source path")
    lines = []
    for clip in clips:
        src = str(clip["src"]).replace("'", r"'\''")
        lines.append(f"file '{src}'")
    concat_list.parent.mkdir(parents=True, exist_ok=True)
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return concat_list


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_final(
    timeline: dict[str, Any],
    output_path: Path,
    *,
    ffmpeg_bin: str = DEFAULT_FFMPEG,
    reencode: bool = False,
    resolution: str | None = None,
    fps: float | None = None,
) -> Path:
    """Render the timeline's video track to `output_path`.

    Writes to a temporary sibling path and renames into place only after
    ffmpeg succeeds, so a failed render never leaves a partial file at
    the final path.

    Raises:
        FinalRenderError: on missing ffmpeg, missing sources, or a
            failed ffmpeg invocation.
    """
    if shutil.which(ffmpeg_bin) is None:
        raise FinalRenderError(f"ffmpeg not found on PATH: {ffmpeg_bin}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    clips = _video_clips(timeline)
    if not clips:
        raise FinalRenderError("timeline has no video clips with a source path")

    missing = [str(c["src"]) for c in clips if not Path(str(c["src"])).exists()]
    if missing:
        raise FinalRenderError(
            f"{len(missing)} source clip(s) missing, first: {missing[0]}"
        )

    concat_list = output_path.parent / _concat_list_path(timeline)
    build_concat_list(timeline, concat_list)

    tmp_output = output_path.parent / f".{output_path.name}.tmp.mp4"
    if tmp_output.exists():
        tmp_output.unlink()

    def _run(cmd: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(cmd, capture_output=True, text=True)

    cmd = build_ffmpeg_command(
        timeline,
        tmp_output,
        ffmpeg_bin=ffmpeg_bin,
        concat_list=concat_list,
        reencode=reencode,
        resolution=resolution,
        fps=fps,
    )
    proc = _run(cmd)

    if proc.returncode != 0 and not reencode:
        # Stream copy rejected (mismatched codecs/params) — retry re-encoding.
        cmd = build_ffmpeg_command(
            timeline,
            tmp_output,
            ffmpeg_bin=ffmpeg_bin,
            concat_list=concat_list,
            reencode=True,
            resolution=resolution,
            fps=fps,
        )
        proc = _run(cmd)

    if proc.returncode != 0:
        if tmp_output.exists():
            tmp_output.unlink()
        tail = (proc.stderr or "").strip().splitlines()[-8:]
        raise FinalRenderError(
            "ffmpeg failed:\n" + "\n".join(tail)
        )

    if not tmp_output.exists() or tmp_output.stat().st_size == 0:
        if tmp_output.exists():
            tmp_output.unlink()
        raise FinalRenderError("ffmpeg produced no output")

    os.replace(tmp_output, output_path)
    return output_path


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------

def probe_duration(
    path: Path,
    *,
    ffprobe_bin: str = DEFAULT_FFPROBE,
) -> float | None:
    """Return the media duration in seconds, or None if ffprobe is
    unavailable / the file is unreadable."""
    if shutil.which(ffprobe_bin) is None:
        return None
    try:
        proc = subprocess.run(
            [
                ffprobe_bin,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    try:
        return float((proc.stdout or "").strip())
    except ValueError:
        return None


__all__ = [
    "FinalRenderError",
    "build_ffmpeg_command",
    "build_concat_list",
    "render_final",
    "probe_duration",
    "DEFAULT_FFMPEG",
    "DEFAULT_FFPROBE",
]
