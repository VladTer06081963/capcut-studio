#!/usr/bin/env python3
"""CLI wrapper for Coverr stock ingest.

Usage:
    python scripts/ingest_coverr.py --query "fog night forest" --count 10
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running scripts without `PYTHONPATH=.` — scripts/ sits next to py/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from py.ingest import coverr
from py.lib.config import STOCK_DIR, has_coverr


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest stock videos from Coverr API")
    parser.add_argument("--query", required=True)
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    if not has_coverr():
        print(
            "ERROR: COVERR_API_KEY not set. Signup at https://coverr.co/api",
            file=sys.stderr,
        )
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else (STOCK_DIR / "coverr")
    print(f"[coverr] query={args.query!r} count={args.count}")
    print(f"[coverr] output_dir={output_dir}")

    result = coverr.ingest(args.query, output_dir, args.count)

    print(f"[coverr] downloaded: {len(result.files)}/{len(result.videos)}")
    if result.errors:
        for vid, err in result.errors:
            print(f"  - {vid}: {err[:120]}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())