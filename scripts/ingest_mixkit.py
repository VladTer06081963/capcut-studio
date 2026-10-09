#!/usr/bin/env python3
"""CLI wrapper for Mixkit stock ingest.

Usage:
    python scripts/ingest_mixkit.py --query "forest" --count 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from py.ingest import mixkit
from py.lib.config import STOCK_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape Mixkit free stock videos")
    parser.add_argument("--query", required=True)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument(
        "--polite-delay-sec", type=float, default=None,
        help="override default polite delay (default: from MIXKIT_SCRAPE_DELAY_SEC)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else (STOCK_DIR / "mixkit")
    print(f"[mixkit] query={args.query!r} count={args.count} delay={args.polite_delay_sec}")
    print(f"[mixkit] output_dir={output_dir}")

    result = mixkit.ingest(
        args.query, output_dir, args.count,
        polite_delay_sec=args.polite_delay_sec,
    )

    print(f"[mixkit] downloaded: {len(result.files)}/{len(result.videos)}")
    if result.errors:
        for vid, err in result.errors:
            print(f"  - {vid}: {err[:120]}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())