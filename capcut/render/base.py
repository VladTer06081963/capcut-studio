"""Provider protocol for video generation.

All video providers (Kie.ai, MiniMax, etc.) implement this Protocol so the
assembler can pick one per scene without caring about the underlying API.

Per-scene override hierarchy (high → low):
    spec.json["scenes"][i]["provider"]   # per-scene explicit
    bible/<show>.md GENRE_DEFAULT        # per-show default
    env DEFAULT_VIDEO_PROVIDER            # global default
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Job model
# ---------------------------------------------------------------------------

@dataclass
class GenerationRequest:
    """What to generate. Provider-agnostic.

    `model_id` is a canonical Kie.ai id such as "kling/v2-1-master-text-to-video"
    or "veo-3-1" (single-segment for some models). Use the kie-models skill
    to discover live model names; this client does not maintain a hardcoded
    catalog because the upstream set changes frequently.
    """

    prompt: str
    model_id: str = "veo-3-1"               # canonical Kie id, e.g. "kling/v2-1-master-text-to-video"
    duration_sec: int = 8                   # 5, 8, 10, 15, 20 — model-specific
    aspect_ratio: str = "16:9"              # "16:9", "9:16", "1:1", "4:3", "3:4"
    resolution: str = "1080p"               # "720p", "1080p", "2k", "4k" — model-specific
    reference_image: str | Path | None = None    # http(s) URL preferred, or local Path (uploaded first)
    seed: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    # Provider-specific passthrough (e.g. camera_motion, audio=False, style_ref)
    # Always model-gated: each provider documents which keys it accepts.


@dataclass
class GenerationResult:
    """What the provider returned."""

    success: bool
    video_path: Path | None = None
    remote_url: str | None = None          # cloud-side URL (expires; cache via video_path)
    duration_sec: float = 0.0
    cost_usd: float | None = None
    cost_credits: float | None = None      # raw kie.ai credits consumed
    latency_sec: float | None = None
    provider_job_id: str | None = None
    model_id: str = ""
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    # Full provider response for debugging (logged, not acted on)


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class VideoProvider(Protocol):
    """Anything that can submit and poll a video generation job."""

    name: str

    def is_available(self) -> bool:
        """True if the provider is configured (key set, etc.). Cheap."""
        ...

    def submit(self, req: GenerationRequest) -> str:
        """Submit a generation job. Returns the provider's job id (poll target).
        Raises on transport/auth error. Long generation runs are async;
        poll with `poll()` or wait with `wait()`.
        """
        ...

    def poll(self, job_id: str) -> GenerationResult:
        """One-shot poll. Returns GenerationResult(success=False) if not ready.
        Does not block waiting — caller decides the cadence.
        """
        ...

    def wait(self, job_id: str, timeout_sec: int = 600, poll_interval_sec: int = 5) -> GenerationResult:
        """Block until success/failure/timeout. Default cadence: poll every 5s.
        On timeout, returns success=False with error="timeout".
        """
        ...

    def list_models(self) -> list[dict[str, Any]]:
        """Optional: list of models this provider exposes (for routing UIs).
        Format: [{"id": "veo-3-fast", "name": "Veo 3 Fast", "price_per_sec": 0.0375,
                  "max_duration_sec": 8, "supports_image_input": True,
                  "supports_audio": True}, ...]
        Empty list if the provider doesn't expose a model catalog.
        """
        ...


# ---------------------------------------------------------------------------
# Model registry (LEGACY — prefer live discovery via KieClient.list_models)
# ---------------------------------------------------------------------------
#
# This hardcoded catalog is OUT OF DATE with kie.ai as of Oct 2026.
# Use `KieClient().list_models(task_type="Text to Video")` for the live
# catalog of 200+ models. Kept here only for backward compatibility with
# code that referenced KNOWN_MODELS; treat as a fallback hint, not a source
# of truth. Real model names use the "provider/name" format (e.g.
# "kling/v2-1-master-text-to-video") and are discovered at runtime.

KNOWN_MODELS: dict[str, dict[str, Any]] = {
    # Legacy convenience aliases — DO NOT rely on these for actual calls.
    "veo-3-fast":         {"provider": "kie", "kind": "video", "price_per_sec": 0.0375, "max_duration_sec": 8,  "supports_audio": True,  "supports_image_input": True,  "_alias_for": "google/veo-3-fast"},
    "veo-3-quality":      {"provider": "kie", "kind": "video", "price_per_sec": 0.25,   "max_duration_sec": 8,  "supports_audio": True,  "supports_image_input": True,  "_alias_for": "google/veo-3-quality"},
    "kling-2.0":          {"provider": "kie", "kind": "video", "price_per_sec": 0.05,   "max_duration_sec": 10, "supports_audio": True,  "supports_image_input": True,  "_alias_for": "kling/v2-1-master-text-to-video"},
    "runway-gen-4":       {"provider": "kie", "kind": "video", "price_per_sec": 0.50,   "max_duration_sec": 10, "supports_audio": False, "supports_image_input": True,  "_alias_for": "runway/gen-4"},
}


__all__ = [
    "GenerationRequest",
    "GenerationResult",
    "VideoProvider",
    "KNOWN_MODELS",
]
