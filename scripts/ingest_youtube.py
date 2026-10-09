#!/usr/bin/env python3
"""CLI wrapper for YouTube stock ingest.

Usage:
    python scripts/ingest_youtube.py --query "fog night forest" --count 10
    python scripts/ingest_youtube.py --query "city night" --license creativeCommon
    python scripts/ingest_youtube.py --query "fog" --output-dir /custom/path
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from py.ingest import youtube
from py.lib.config import STOCK_DIR, has_youtube


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest stock videos from YouTube Data API v3 + yt-dlp",
    )
    parser.add_argument(
        "--query", required=True,
        help="free-text search query",
    )
    parser.add_argument(
        "--count", type=int, default=10,
        help="how many videos to download (1-50)",
    )
    parser.add_argument(
        "--license", choices=[youtube.LICENSE_ANY, youtube.LICENSE_CC],
        default=youtube.LICENSE_ANY,
        help="license filter (default: any)",
    )
    parser.add_argument(
        "--output-dir", default=None,
        help=f"output directory (default: {STOCK_DIR / 'youtube'})",
    )
    parser.add_argument(
        "--duration", choices=["any", "short", "medium", "long"], default="medium",
        help="filter by video duration (default: medium, 4-20 min)",
    )
    args = parser.parse_args()

    if not has_youtube():
        print(
            "ERROR: YOUTUBE_API_KEY not set in .env. "
            "See .env.example — get a key at "
            "https://console.cloud.google.com/apis/credentials",
            file=sys.stderr,
        )
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else (STOCK_DIR / "youtube")

    print(f"[youtube] query={args.query!r} count={args.count} license={args.license}")
    print(f"[youtube] output_dir={output_dir}")

    result = youtube.ingest(
        query=args.query,
        output_dir=output_dir,
        count=args.count,
        license=args.license,
    )

    print(f"[youtube] downloaded: {len(result.files)}/{len(result.videos)}")
    if result.errors:
        print(f"[youtube] errors: {len(result.errors)}")
        for vid, err in result.errors:
            print(f"  - {vid}: {err[:120]}")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())