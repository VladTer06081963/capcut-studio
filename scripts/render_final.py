#!/usr/bin/env python3
"""CLI: produce `rendered/final.mp4` for an approved episode.

Closes the `matched → rendered` lifecycle transition. Enforces the
project's approval gate and the immutability of `final.mp4`.

Usage:
    python scripts/render_final.py --serial <slug> --ep <id>
    python scripts/render_final.py --serial <slug> --ep <id> --reencode

Behavior:
  - Refuses unless `.approved` exists (the approval gate).
  - No-op if `rendered/final.mp4` already exists and `rendered/spec.sha256`
    matches the current `spec.json` (idempotent).
  - Refuses if `rendered/final.mp4` exists but the spec hash differs —
    `final.mp4` is immutable; a changed spec needs a remix, not an
    overwrite.
  - Writes to a temp path and renames into place only on success.
  - After a successful render, writes `rendered/spec.sha256` and marks
    the episode rendered.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running scripts without `PYTHONPATH=.` — scripts/ sits next to capcut/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from capcut.assemble import final_renderer
from capcut.lib import lifecycle
from capcut.lib.config import SERIALS_ROOT


def _fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render the final.mp4 for an approved episode",
    )
    parser.add_argument("--serial", required=True, help="show slug")
    parser.add_argument("--ep", required=True, help="episode id")
    parser.add_argument(
        "--reencode",
        action="store_true",
        help="force the re-encode path instead of stream copy",
    )
    parser.add_argument(
        "--resolution",
        default=None,
        help="target WxH for the re-encode path (default: timeline project resolution)",
    )
    args = parser.parse_args()

    ep_dir = SERIALS_ROOT / args.serial / args.ep
    if not ep_dir.exists():
        return _fail(f"episode not found: {ep_dir}")

    spec_path = ep_dir / "spec.json"
    if not spec_path.exists():
        return _fail(f"{spec_path} not found — run spec_from_brief.py first")

    draft_path = ep_dir / "rendered" / "draft.json"
    if not draft_path.exists():
        return _fail(
            f"{draft_path} not found — run assemble_episode.py first"
        )

    ep = lifecycle.Episode(show=args.serial, ep_id=args.ep, path=ep_dir)

    # --- approval gate ---------------------------------------------------
    if not (ep_dir / ".approved").exists():
        state = lifecycle.current_state(ep)
        return _fail(
            f"approval gate: {ep_dir} has no `.approved` sentinel "
            f"(current state: {state.value}). "
            f"Review the episode and approve it before rendering a final."
        )

    # --- idempotency / immutability -------------------------------------
    final_path = ep_dir / "rendered" / "final.mp4"
    if final_path.exists():
        if lifecycle.is_idempotent_render(ep):
            print(f"[render_final] {final_path} already rendered for this spec — no-op")
            print(f"[render_final] spec sha256: {lifecycle.sha256_spec(ep)}")
            return 0
        return _fail(
            f"{final_path} already exists but its spec.sha256 does not match the "
            f"current spec.json. `final.mp4` is immutable by project policy — "
            f"create a remix (new episode dir) instead of overwriting it."
        )

    # --- render ----------------------------------------------------------
    import json

    try:
        timeline = json.loads(draft_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _fail(f"cannot read {draft_path}: {exc}")

    print(f"[render_final] rendering {final_path}")
    try:
        final_renderer.render_final(
            timeline,
            final_path,
            reencode=args.reencode,
            resolution=args.resolution,
        )
    except final_renderer.FinalRenderError as exc:
        return _fail(str(exc))

    size = final_path.stat().st_size
    duration = final_renderer.probe_duration(final_path)
    sha = lifecycle.sha256_spec(ep)

    lifecycle.write_spec_sha(ep)
    lifecycle.mark_rendered(ep)

    print(f"[render_final] wrote {final_path} ({size} bytes)")
    if duration is not None:
        print(f"[render_final] duration: {duration:.2f}s")
    print(f"[render_final] spec sha256: {sha}")
    print(f"[render_final] state: {lifecycle.current_state(ep).value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
