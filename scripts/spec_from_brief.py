#!/usr/bin/env python3
"""CLI wrapper for episode spec writer.

Usage:
    python scripts/spec_from_brief.py \
        --brief serials/stalker-reznik/ep-01-pilot/brief.md \
        --bible bible/stalker-reznik.md \
        --output serials/stalker-reznik/ep-01-pilot/spec.json

With --dry-run, skip LLM call and write a minimal stub spec.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from py.episode import spec_writer
from py.lib.config import has_openrouter


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate episode spec.json from brief.md + bible/<show>.md",
    )
    parser.add_argument("--brief", required=True, type=Path, help="path to brief.md")
    parser.add_argument("--bible", required=True, type=Path, help="path to bible/<show>.md")
    parser.add_argument("--output", required=True, type=Path, help="path to spec.json")
    parser.add_argument(
        "--model", default=spec_writer.DEFAULT_MODEL,
        help=f"OpenRouter model (default: {spec_writer.DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="skip LLM call, write minimal stub spec (for testing schema)",
    )
    args = parser.parse_args()

    if not args.dry_run and not has_openrouter():
        print(
            "ERROR: OPENROUTER_API_KEY not set in .env. "
            "See .env.example — get a key at https://openrouter.ai/keys",
            file=sys.stderr,
        )
        return 1

    print(f"[spec] brief={args.brief}")
    print(f"[spec] bible={args.bible}")
    print(f"[spec] output={args.output}")
    print(f"[spec] model={args.model} dry_run={args.dry_run}")

    spec = spec_writer.write_spec_from_brief(
        brief_path=args.brief,
        bible_path=args.bible,
        output_path=args.output,
        model=args.model,
        dry_run=args.dry_run,
    )

    print(f"[spec] OK: id={spec.id} show={spec.show} scenes={len(spec.scenes)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())