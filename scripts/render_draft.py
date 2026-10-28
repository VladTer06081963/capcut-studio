#!/usr/bin/env python3
"""Render a draft.json into a preview.mp4 with the ffmpeg concat demuxer.

Usage:
    python3 scripts/render_draft.py <draft.json>

The output is written to a temporary sibling and renamed into place only
after ffmpeg succeeds, so a failed render never leaves a partial file where
a valid preview used to be. Progress goes to stderr, so stdout stays clean.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def _fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def _concat_escape(path: str) -> str:
    """Escape a path for the ffmpeg concat demuxer.

    The demuxer reads `file '<path>'`; a single quote inside the path has
    to be escaped as '\\''.
    """
    return path.replace("'", r"'\''")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: render_draft.py <draft.json>", file=sys.stderr)
        return 1

    draft_path = Path(sys.argv[1])
    if not draft_path.exists():
        return _fail(f"{draft_path} not found")

    try:
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _fail(f"cannot read {draft_path}: {exc}")

    try:
        clips = draft["tracks"][0]["clips"]
    except (KeyError, IndexError, TypeError):
        return _fail(f"{draft_path}: expected a tracks[0].clips list")

    out_dir = draft_path.parent
    list_file = out_dir / "ffmpeg_list.txt"
    out_mp4 = out_dir / "preview.mp4"
    tmp_mp4 = out_dir / f".preview.mp4.{os.getpid()}.tmp"

    try:
        list_file.write_text(
            "".join(f"file '{_concat_escape(c['src'])}'\n" for c in clips),
            encoding="utf-8",
        )
    except (OSError, KeyError, TypeError) as exc:
        return _fail(f"cannot write {list_file}: {exc}")

    print(f"Rendering {out_mp4} with ffmpeg...", file=sys.stderr)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                str(tmp_mp4),
            ],
            check=True,
        )
    except FileNotFoundError:
        return _fail("ffmpeg not found on PATH")
    except subprocess.CalledProcessError as exc:
        tmp_mp4.unlink(missing_ok=True)
        return _fail(f"ffmpeg failed with exit code {exc.returncode}")

    try:
        os.replace(tmp_mp4, out_mp4)
    except OSError as exc:
        tmp_mp4.unlink(missing_ok=True)
        return _fail(f"cannot write {out_mp4}: {exc}")

    print(f"Done: {out_mp4}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
