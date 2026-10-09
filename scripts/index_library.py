#!/usr/bin/env python3
"""CLI wrapper for library indexer.

Walks library/, captions + embeds each clip via LM Studio (or skips if LM
Studio unreachable), writes index.sqlite.

Usage:
    python scripts/index_library.py                    # full index
    python scripts/index_library.py --no-caption       # skip BLIP-2
    python scripts/index_library.py --no-embed         # skip embeddings
    python scripts/index_library.py --db /custom/path.sqlite
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running scripts without `PYTHONPATH=.`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from py.index import embedder
from py.lib.config import LIBRARY_INDEX, LIBRARY_ROOT, LM_STUDIO_URL


def main() -> int:
    parser = argparse.ArgumentParser(description="Index library clips into SQLite")
    parser.add_argument("--library-root", default=None, type=Path)
    parser.add_argument("--db", default=None, type=Path)
    parser.add_argument("--no-caption", action="store_true",
                        help="skip BLIP-2 captioning")
    parser.add_argument("--no-embed", action="store_true",
                        help="skip text embedding")
    args = parser.parse_args()

    library_root = args.library_root or LIBRARY_ROOT
    db_path = args.db or LIBRARY_INDEX

    print(f"[index] library_root={library_root}")
    print(f"[index] db={db_path}")
    print(f"[index] LM Studio: {LM_STUDIO_URL} -> {'OK' if embedder.lm_studio_alive() else 'UNREACHABLE'}")

    stats = embedder.index_library(
        library_root=library_root,
        db_path=db_path,
        caption=not args.no_caption,
        embed=not args.no_embed,
    )

    print(f"[index] scanned: {stats.scanned}")
    print(f"[index] indexed: {stats.indexed}")
    print(f"[index] skipped (already up-to-date): {stats.skipped}")
    if stats.errors:
        print(f"[index] errors: {len(stats.errors)}")
        for path, err in stats.errors[:5]:
            print(f"  - {path}: {err[:120]}")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())