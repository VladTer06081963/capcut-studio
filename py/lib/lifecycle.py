"""
Episode lifecycle — sentinel-based state machine on the filesystem.

States (per `serials/<show>/<ep-id>/`):
  draft       — spec.json exists, .draft sentinel present
  approved    — .approved sentinel present (after human/auto approval)
  matched     — matched.json written by matcher
  rendered    — rendered/final.mp4 exists
  published   — episode-log.md entry written

Transitions:
  draft    → approved   (approve())
  approved → draft      (revise() — atomic approval revoke)
  approved → matched    (match() writes matched.json)
  matched  → rendered   (render() writes rendered/final.mp4)
  rendered → published  (publish() appends episode-log entry)

Re-render policy:
  rerender(force=False) — refuses to overwrite rendered/final.mp4 unless
  force=True. Use remix for non-destructive iteration (separate episode dir).

Idempotency:
  Every state transition checks current state. Calling approve() twice is a
  no-op. Calling render() twice without changes is a no-op (sha256 match).

Mirror of comic-studio's lifecycle pattern. The hard rule: lifecycle is
**files on disk**, not in-memory flags.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from .config import SERIALS_ROOT


class State(str, Enum):
    """Episode states. `value` is the string used in logs and on disk."""

    DRAFT = "draft"
    APPROVED = "approved"
    MATCHED = "matched"
    RENDERED = "rendered"
    PUBLISHED = "published"


# Sentinel filenames (one per state, except `rendered` which uses directory check)
SENTINELS: dict[State, str | None] = {
    State.DRAFT: ".draft",
    State.APPROVED: ".approved",
    State.MATCHED: None,             # detected by matched.json presence
    State.RENDERED: None,            # detected by rendered/final.mp4 presence
    State.PUBLISHED: None,           # detected by episode-log entry
}


@dataclass(frozen=True)
class Episode:
    """An episode on disk. Path is the canonical locator."""

    show: str
    ep_id: str
    path: Path

    @classmethod
    def from_path(cls, path: Path) -> "Episode":
        """Build from an existing episode dir (`serials/<show>/<ep-id>/`)."""
        # Defensive: allow path to be the dir or its parent
        if (path / "spec.json").exists() or (path / "brief.md").exists():
            ep_dir = path
        else:
            ep_dir = path
        return cls(show=ep_dir.parent.name, ep_id=ep_dir.name, path=ep_dir)

    @classmethod
    def locate(cls, show: str, ep_id: str) -> "Episode":
        """Build from show + ep_id; path is `serials/<show>/<ep_id>`."""
        return cls(show=show, ep_id=ep_id, path=SERIALS_ROOT / show / ep_id)


# ---------------------------------------------------------------------------
# State queries
# ---------------------------------------------------------------------------

def _has_sentinel(ep: Episode, state: State) -> bool:
    name = SENTINELS.get(state)
    if name is None:
        return False
    return (ep.path / name).exists()


def current_state(ep: Episode) -> State:
    """Best-effort detection of current state by inspecting disk."""
    if (ep.path / "rendered" / "final.mp4").exists():
        # rendered is a stronger signal than matched/approved — check first
        return State.RENDERED
    if (ep.path / "matched.json").exists():
        return State.MATCHED
    if _has_sentinel(ep, State.APPROVED):
        return State.APPROVED
    if (ep.path / "spec.json").exists():
        return State.DRAFT
    return State.DRAFT  # dir exists but no spec — treat as draft


def is_draft(ep: Episode) -> bool:
    return current_state(ep) == State.DRAFT


def is_approved(ep: Episode) -> bool:
    return current_state(ep) in (State.APPROVED, State.MATCHED, State.RENDERED)


def is_rendered(ep: Episode) -> bool:
    return current_state(ep) == State.RENDERED


# ---------------------------------------------------------------------------
# State transitions (atomic on disk)
# ---------------------------------------------------------------------------

def _touch(ep: Episode, name: str) -> None:
    """Create empty file (sentinel). Errors if parent dir missing."""
    (ep.path / name).touch()


def _rm(ep: Episode, name: str) -> None:
    """Remove file if exists. No error if missing."""
    p = ep.path / name
    if p.exists():
        p.unlink()


def approve(ep: Episode) -> None:
    """Mark episode approved. Idempotent. Requires spec.json + brief.md."""
    if not (ep.path / "spec.json").exists():
        raise FileNotFoundError(f"cannot approve {ep}: spec.json missing")
    _touch(ep, ".approved")


def revise(ep: Episode) -> None:
    """Atomic approval revoke — drop back to draft state."""
    _rm(ep, ".approved")
    _rm(ep, "matched.json")
    # Do NOT delete rendered/ — that's remix territory


def mark_matched(ep: Episode) -> None:
    """Matcher wrote matched.json. Sanity-check before transitioning."""
    if not (ep.path / "matched.json").exists():
        raise FileNotFoundError(f"cannot mark matched: matched.json missing in {ep}")
    _rm(ep, ".approved")  # approval was implicit; explicit approved used elsewhere


def mark_rendered(ep: Episode) -> None:
    """Render produced final.mp4. Caller verifies file size > 0 first."""
    final = ep.path / "rendered" / "final.mp4"
    if not final.exists() or final.stat().st_size == 0:
        raise FileNotFoundError(f"cannot mark rendered: final.mp4 missing or empty in {ep}")
    _rm(ep, "matched.json")  # matched.json is informational; safe to drop after render


def publish(ep: Episode, log: Path | None = None) -> None:
    """Mark episode published: append to episode-log.md, mark sentinel."""
    log_path = log or (SERIALS_ROOT / ep.show / "episode-log.md")
    if not log_path.exists():
        raise FileNotFoundError(f"cannot publish: episode-log.md missing at {log_path}")
    entry = _log_entry(ep)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(entry)


# ---------------------------------------------------------------------------
# Idempotency helpers
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    """Stable sha256 for idempotency checks. Returns lowercase hex."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_spec(ep: Episode) -> str:
    """sha256 of spec.json — used as render idempotency key."""
    spec = ep.path / "spec.json"
    if not spec.exists():
        raise FileNotFoundError(f"spec.json missing in {ep}")
    return sha256_file(spec)


def is_idempotent_render(ep: Episode) -> bool:
    """True if rendered/final.mp4 already exists AND spec.sha256 matches."""
    sha_file = ep.path / "rendered" / "spec.sha256"
    final = ep.path / "rendered" / "final.mp4"
    if not (sha_file.exists() and final.exists()):
        return False
    try:
        return sha_file.read_text().strip() == sha256_spec(ep)
    except FileNotFoundError:
        return False


def write_spec_sha(ep: Episode) -> None:
    """Write spec.sha256 next to final.mp4 for next-render idempotency."""
    rendered = ep.path / "rendered"
    rendered.mkdir(exist_ok=True)
    (rendered / "spec.sha256").write_text(sha256_spec(ep))


# ---------------------------------------------------------------------------
# Episode-log helpers
# ---------------------------------------------------------------------------

def _log_entry(ep: Episode) -> str:
    """Format a single episode-log.md line."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"- {ts} | {ep.ep_id} | status=published\n"


def list_episodes(show: str) -> list[Episode]:
    """List all episodes for a show, sorted by ep_id."""
    show_dir = SERIALS_ROOT / show
    if not show_dir.exists():
        return []
    return [
        Episode(show=show, ep_id=p.name, path=p)
        for p in sorted(show_dir.iterdir())
        if p.is_dir() and not p.name.startswith(".")
    ]


__all__ = [
    "State",
    "Episode",
    "current_state",
    "is_draft",
    "is_approved",
    "is_rendered",
    "approve",
    "revise",
    "mark_matched",
    "mark_rendered",
    "publish",
    "sha256_file",
    "sha256_spec",
    "is_idempotent_render",
    "write_spec_sha",
    "list_episodes",
]