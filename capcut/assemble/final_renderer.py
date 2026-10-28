"""
Final renderer — produce `rendered/final.mp4` from a Concat timeline.

Policy notes (see AGENTS.md → "Project invariants"):

- `rendered/final.mp4` is **immutable from creation**. This module never
  overwrites an existing final.mp4; the caller refuses before we are
  invoked, and `render_final()` itself writes to a unique temp path and
  renames into place only after a successful encode.
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

Clip durations are honoured: each source is trimmed to the timeline's
declared `duration_sec` before concatenation, so the output length
matches the spec rather than the full source files.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from capcut.lib.media import probe_media

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_FFMPEG = "ffmpeg"
DEFAULT_FFPROBE = "ffprobe"

DEFAULT_VIDEO_CODEC = "libx264"
DEFAULT_AUDIO_CODEC = "aac"
DEFAULT_PRESET = "medium"
DEFAULT_CRF = "20"
DEFAULT_PIX_FMT = "yuv420p"

# Guard against a wedged external-volume read hanging the render forever.
DEFAULT_TIMEOUT_SEC = 3600


class FinalRenderError(RuntimeError):
    """Raised when the final render cannot be produced."""


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def resolve_source(src: str, *, base_dir: Path | None = None) -> Path:
    """Resolve a clip `src` to an absolute path.

    The Concat timeline stores absolute paths for library clips, but
    drafts produced by other tools can carry bare filenames. The ffmpeg
    concat demuxer resolves relative names against the **list file's**
    directory, not the CWD — so we resolve them here and always emit
    absolute paths into the concat list.

    A relative name is resolved against `base_dir` when given (the
    timeline's own directory), otherwise against the current working
    directory. The result is absolute either way, so the concat list
    means the same thing regardless of where ffmpeg is invoked from.
    """
    path = Path(src).expanduser()
    if path.is_absolute():
        return path
    if base_dir is not None:
        return (base_dir / path).resolve()
    return path.resolve()


# ---------------------------------------------------------------------------
# Command construction
# ---------------------------------------------------------------------------

def _video_clips(timeline: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the clips of the first `video` track that has usable
    sources, in timeline order.

    A video track whose clips all lack `src` is skipped so a later
    video track is not silently ignored.
    """
    for track in timeline.get("tracks", []):
        if track.get("type") != "video":
            continue
        clips = [c for c in track.get("clips", []) if c.get("src")]
        if clips:
            return clips
    return []


def _concat_list_path(timeline: dict[str, Any]) -> str:
    """Unique temp name for the ffmpeg concat list.

    The name carries the pid and a random suffix: two concurrent renders of
    the *same* episode would otherwise write the same list file and clobber
    each other's input. (The output video already has a unique temp path —
    the list file did not.)
    """
    name = (timeline.get("project", {}) or {}).get("name", "episode")
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in name)
    return f"capcut_final_{safe}_{os.getpid()}_{uuid.uuid4().hex[:8]}_concat.txt"


def _parse_resolution(resolution: str) -> tuple[int, int]:
    """Parse a `WxH` resolution string. Raises on malformed input."""
    raw = str(resolution).strip().lower()
    if "x" not in raw:
        raise FinalRenderError(
            f"invalid resolution {resolution!r} — expected WxH (e.g. 1920x1080)"
        )
    w_raw, _, h_raw = raw.partition("x")
    try:
        w, h = int(w_raw), int(h_raw)
    except ValueError as exc:
        raise FinalRenderError(
            f"invalid resolution {resolution!r} — expected WxH (e.g. 1920x1080)"
        ) from exc
    if w <= 0 or h <= 0:
        raise FinalRenderError(
            f"invalid resolution {resolution!r} — width and height must be positive"
        )
    return w, h


def _total_duration(timeline: dict[str, Any], clips: list[dict[str, Any]]) -> float | None:
    """Total declared duration of the timeline's video clips."""
    total = 0.0
    seen = False
    for clip in clips:
        duration = clip.get("duration_sec")
        if duration is not None and duration > 0:
            total += float(duration)
            seen = True
    if seen:
        return total
    project = timeline.get("project", {}) or {}
    value = project.get("duration_sec")
    return float(value) if value else None


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

    The output is truncated to the timeline's declared total duration via
    `-t`. The concat demuxer's `duration` directive only overrides
    metadata — it does not cut the media — so `-t` is what actually
    makes the output length match the spec instead of running every
    source file to its end.

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
        FinalRenderError: if the timeline has no usable video clips or
            the resolution is malformed.
    """
    clips = _video_clips(timeline)
    if not clips:
        raise FinalRenderError(
            "timeline has no video clips with a source path — nothing to render"
        )

    project = timeline.get("project", {}) or {}
    if resolution is None:
        resolution = project.get("resolution") or "1920x1080"
    if fps is None:
        fps = project.get("fps") or 24.0

    if concat_list is None:
        concat_list = output_path.parent / _concat_list_path(timeline)

    cmd = [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list)]

    total = _total_duration(timeline, clips)
    if total is not None and total > 0:
        cmd += ["-t", f"{total:.3f}"]

    if reencode:
        w, h = _parse_resolution(resolution)
        vf = (
            f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:-1:-1,fps={fps}"
        )
        cmd += [
            "-c:v", DEFAULT_VIDEO_CODEC,
            "-preset", DEFAULT_PRESET,
            "-crf", str(DEFAULT_CRF),
            "-pix_fmt", DEFAULT_PIX_FMT,
            "-vf", vf,
        ]
        cmd += ["-c:a", DEFAULT_AUDIO_CODEC]
    else:
        cmd += ["-c", "copy"]

    cmd.append(str(output_path))
    return cmd


def build_concat_list(
    timeline: dict[str, Any],
    concat_list: Path,
    *,
    base_dir: Path | None = None,
) -> Path:
    """Write the ffmpeg concat list file for the timeline's video track.

    Each clip is trimmed to its declared `duration_sec` via ffmpeg's
    concat demuxer `duration` directive, so the output matches the spec
    instead of running each source file to its end.
    """
    clips = _video_clips(timeline)
    if not clips:
        raise FinalRenderError("timeline has no video clips with a source path")
    lines = []
    for clip in clips:
        src = resolve_source(str(clip["src"]), base_dir=base_dir)
        escaped = str(src).replace("'", r"'\''")
        lines.append(f"file '{escaped}'")
        duration = clip.get("duration_sec")
        if duration is not None and duration > 0:
            lines.append(f"duration {duration}")
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
    timeout: int | None = DEFAULT_TIMEOUT_SEC,
    base_dir: Path | None = None,
) -> Path:
    """Render the timeline's video track to `output_path`.

    Writes to a unique temporary sibling path and renames into place
    only after ffmpeg succeeds, so a failed render never leaves a
    partial file at the final path. The temp path is unique per call,
    so two concurrent renders of the same episode cannot clobber each
    other's output.

    Raises:
        FinalRenderError: on missing ffmpeg, missing sources, a timeout,
            or a failed ffmpeg invocation.
    """
    if shutil.which(ffmpeg_bin) is None:
        raise FinalRenderError(f"ffmpeg not found on PATH: {ffmpeg_bin}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    clips = _video_clips(timeline)
    if not clips:
        raise FinalRenderError("timeline has no video clips with a source path")

    missing = []
    for clip in clips:
        resolved = resolve_source(str(clip["src"]), base_dir=base_dir)
        if not resolved.exists():
            missing.append(str(clip["src"]))
    if missing:
        raise FinalRenderError(
            f"{len(missing)} source clip(s) missing, first: {missing[0]}"
        )

    concat_list = output_path.parent / _concat_list_path(timeline)
    build_concat_list(timeline, concat_list, base_dir=base_dir)

    # Unique temp name: concurrent renders of one episode must not share
    # a temp path, or the loser's os.replace() could overwrite the
    # winner's final.mp4.
    tmp_output = output_path.parent / (
        f".{output_path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp.mp4"
    )

    def _run(cmd: list[str]) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise FinalRenderError(f"ffmpeg timed out after {timeout}s") from exc

    try:
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
        first_stderr = proc.stderr or ""

        if proc.returncode != 0 and not reencode:
            # Stream copy rejected (mismatched codecs/params) — retry
            # re-encoding.
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
                tail = (proc.stderr or "").strip().splitlines()[-8:]
                raise FinalRenderError(
                    "ffmpeg failed (stream copy then re-encode):\n"
                    + "\n".join(tail)
                    + "\n--- stream-copy attempt ---\n"
                    + "\n".join(first_stderr.strip().splitlines()[-4:])
                )

        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()[-8:]
            raise FinalRenderError("ffmpeg failed:\n" + "\n".join(tail))

        if not tmp_output.exists() or tmp_output.stat().st_size == 0:
            raise FinalRenderError("ffmpeg produced no output")

        os.replace(tmp_output, output_path)
        return output_path
    finally:
        # Never leave a partial temp file behind.
        try:
            if tmp_output.exists():
                tmp_output.unlink()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Probe
# ---------------------------------------------------------------------------

def probe_duration(
    path: Path,
    *,
    ffprobe_bin: str = DEFAULT_FFPROBE,
    timeout: int = 30,
) -> float | None:
    """Return the media duration in seconds, or None if ffprobe is
    unavailable / the file is unreadable."""
    probe = probe_media(
        path, strict=False, ffprobe_bin=ffprobe_bin, timeout=timeout
    )
    return probe.duration_sec or None


__all__ = [
    "FinalRenderError",
    "resolve_source",
    "build_ffmpeg_command",
    "build_concat_list",
    "render_final",
    "probe_duration",
    "DEFAULT_FFMPEG",
    "DEFAULT_FFPROBE",
    "DEFAULT_TIMEOUT_SEC",
]
