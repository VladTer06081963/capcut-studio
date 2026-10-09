#!/usr/bin/env python3
"""CLI wrapper for Archive.org stock ingest.

Usage:
    python scripts/ingest_archive.py --query "prelinger" --count 5
    python scripts/ingest_archive.py --query "nature" --mediatype video --count 3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from py.ingest import archive
from py.lib.config import STOCK_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest public-domain videos from Archive.org")
    parser.add_argument("--query", required=True)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--mediatype", default="movies", choices=["movies", "video"])
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else (STOCK_DIR / "archive")
    print(f"[archive] query={args.query!r} count={args.count} mediatype={args.mediatype}")
    print(f"[archive] output_dir={output_dir}")

    result = archive.ingest(args.query, output_dir, args.count, mediatype=args.mediatype)

    print(f"[archive] downloaded: {len(result.files)}/{len(result.videos)}")
    if result.errors:
        for vid, err in result.errors:
            print(f"  - {vid}: {err[:120]}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())