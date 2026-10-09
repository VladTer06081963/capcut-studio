#!/usr/bin/env python3
"""CLI wrapper for episode matcher + Concat timeline builder.

Reads spec.json, runs matcher, writes matched.json, builds Concat timeline,
writes rendered/draft.json.

Usage:
    python scripts/assemble_episode.py \
        --serial stalker-reznik --ep ep-01-pilot
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from py.assemble import concat_exporter
from py.episode.spec_writer import load_spec
from py.lib.config import LIBRARY_INDEX, LIBRARY_ROOT, SERIALS_ROOT
from py.search import matcher


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Match scenes to library clips and build Concat timeline",
    )
    parser.add_argument("--serial", required=True, help="show slug")
    parser.add_argument("--ep", required=True, help="episode id")
    parser.add_argument("--library-root", default=None, type=Path)
    parser.add_argument("--db", default=None, type=Path)
    args = parser.parse_args()

    ep_dir = SERIALS_ROOT / args.serial / args.ep
    spec_path = ep_dir / "spec.json"
    if not spec_path.exists():
        print(f"ERROR: {spec_path} not found. Run spec_from_brief.py first.", file=sys.stderr)
        return 1

    library_root = args.library_root or LIBRARY_ROOT
    db_path = args.db or LIBRARY_INDEX

    print(f"[assemble] loading spec: {spec_path}")
    spec = load_spec(spec_path)

    print(f"[assemble] matching {len(spec.scenes)} scenes against library")
    matched = matcher.match_episode(spec, db_path=db_path)

    matched_path = ep_dir / "matched.json"
    matcher.write_matched(matched, matched_path)
    print(f"[assemble] wrote {matched_path}")
    print(f"[assemble] matched: {sum(1 for s in matched.scenes if s.clip_id)}/{len(matched.scenes)}")
    if matched.unmatched_scenes():
        print(f"[assemble] unmatched scenes: {matched.unmatched_scenes()}")

    print(f"[assemble] building Concat timeline")
    timeline = concat_exporter.assemble_timeline(spec, matched, library_root=library_root)
    draft_path = ep_dir / "rendered" / "draft.json"
    concat_exporter.write_concat_timeline(timeline, draft_path)
    print(f"[assemble] wrote {draft_path}")
    print(f"[assemble] duration: {timeline.project.duration_sec}s, tracks: {len(timeline.tracks)}")
    if timeline.unmatched_scenes:
        print(f"[assemble] timeline unmatched: {timeline.unmatched_scenes}")

    return 0


if __name__ == "__main__":
    sys.exit(main())