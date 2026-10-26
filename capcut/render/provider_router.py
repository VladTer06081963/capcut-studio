"""Provider router — picks a VideoProvider for each scene based on overrides.

Override hierarchy in parse_scene_provider:
    1. spec.json["scenes"][i]["provider"]   explicit, e.g. "kling/v2-1-master-text-to-video"
    2. spec.json["scenes"][i]["model_id"]   shorthand → "kie/<model_id>"
    3. caller-supplied default
    4. env DEFAULT_VIDEO_PROVIDER
    5. hardcoded fallback: "kie/veo-3-1"

The "provider" string format is "<backend>/<model_id>":
    "kling/v2-1-master-text-to-video"  → KieClient + model_id="kling/v2-1-master-text-to-video"
    "kie/veo-3-1"                       → KieClient + model_id="veo-3-1"
    "minimax/h3-max"                    → direct MiniMax provider (not implemented yet)
    "openrouter/..."                    → reserved for future

The slash in canonical Kie model ids like "kling/v2-1-master-text-to-video"
is NOT a backend selector — ProviderSpec.parse() only treats the FIRST
slash-segment as a backend when it matches a known name; otherwise the
whole string is the model id and backend defaults to "kie".

If a single provider fails, the router can fall back to the next entry in
spec.json["scenes"][i].get("fallback", []) (a list of provider strings).
Default fallback: same provider, no retry.
The config variable DEFAULT_VIDEO_FALLBACK is not loaded automatically here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from typing import Any

from capcut.render.base import GenerationRequest, GenerationResult
from capcut.render.kie_client import KieClient

_SUPPORTED_BACKENDS = {"kie", "minimax", "openrouter"}


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

@dataclass
class ProviderSpec:
    backend: str          # "kie" | "minimax" | "openrouter"
    model_id: str         # canonical model id from kie.ai discovery (e.g.
                          # "kling/v2-1-master-text-to-video", "veo-3-1")
    raw: str              # the original "kie/<model>" string

    @classmethod
    def parse(cls, s: str) -> "ProviderSpec":
        if "/" not in s:
            return cls(backend="kie", model_id=s, raw=s)
        prefix, model_id = s.split("/", 1)
        if prefix in _SUPPORTED_BACKENDS:
            return cls(backend=prefix, model_id=model_id, raw=s)
        # Canonical Kie model IDs commonly include a provider segment, e.g.
        # "kling/v2-1-master-text-to-video"; that is not a backend selector.
        return cls(backend="kie", model_id=s, raw=s)

    def __str__(self) -> str:
        return self.raw


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class ProviderRouter:
    """Caches provider instances, resolves provider strings to clients.

    `KieClient` doesn't formally implement `py.render.base.VideoProvider`
    (signature differences on `wait()` and `list_models()`), so we use
    structural typing here. Any object with `is_available()`, `submit()`,
    and `wait()` methods works.
    """

    def __init__(self, env: dict[str, str | None] | None = None) -> None:
        # Inject env-like mapping for testability
        self._env = env if env is not None else dict(os.environ)
        self._cache: dict[str, object] = {}

    def get(self, provider_str: str) -> object:
        if provider_str in self._cache:
            return self._cache[provider_str]
        spec = ProviderSpec.parse(provider_str)
        client = self._build(spec)
        self._cache[provider_str] = client
        return client

    def _build(self, spec: ProviderSpec) -> object:
        if spec.backend == "kie":
            return KieClient(api_key=self._env.get("KIE_API_KEY"))
        if spec.backend == "minimax":
            # Direct MiniMax client — not implemented yet.
            # When it lands, import here. For now raise loudly so the
            # caller knows the path doesn't work.
            raise NotImplementedError(
                "Direct MiniMax provider not yet wrapped; "
                "use 'kie/minimax-hailuo-3' via Kie.ai instead."
            )
        raise ValueError(f"Unknown backend {spec.backend!r} in {spec.raw!r}")

    def resolve_default(self) -> str:
        """What the env says to use when no scene override is present."""
        return self._env.get("DEFAULT_VIDEO_PROVIDER") or "kie/veo-3-1"

    # ---- high-level: generate one shot with optional fallback chain ----

    def generate(
        self,
        request: GenerationRequest,
        provider_str: str | None = None,
        fallback: list[str] | None = None,
        timeout_sec: int = 600,
    ) -> GenerationResult:
        """Submit + wait, with fallback. Returns the first successful result
        or the last error if all attempts failed.
        """
        chain = [provider_str or self.resolve_default()]
        chain.extend(fallback or [])
        last_error: GenerationResult | None = None
        for spec_str in chain:
            spec = ProviderSpec.parse(spec_str)
            client = self.get(spec_str)
            if not client.is_available():  # type: ignore[attr-defined]
                last_error = GenerationResult(
                    success=False, error=f"unavailable: {spec_str}",
                    model_id=spec.model_id,
                )
                continue
            try:
                provider_request = replace(request, model_id=spec.model_id)
                job_id = client.submit(provider_request)  # type: ignore[attr-defined]
                result = client.wait(job_id, timeout_sec=timeout_sec)  # type: ignore[attr-defined]
            except Exception as e:  # noqa: BLE001 — surface as result
                last_error = GenerationResult(
                    success=False, error=f"transport: {e!s}",
                    model_id=spec.model_id,
                )
                continue
            if result.success:
                return result
            last_error = result
        # All attempts failed
        return last_error or GenerationResult(success=False, error="no_providers")


# ---------------------------------------------------------------------------
# Convenience for callers (assemble_episode, render scripts)
# ---------------------------------------------------------------------------

def parse_scene_provider(scene: dict[str, Any], default: str | None = None) -> str:
    """Pull a provider string from a scene dict using the override hierarchy.

    Precedence:
        scene["provider"]      explicit "backend/model"
        scene["model_id"]      bare model id → assumes kie/
        default                (caller-supplied)
        env DEFAULT_VIDEO_PROVIDER
        "kie/veo-3-1"          ultimate fallback
    """
    if scene.get("provider"):
        return str(scene["provider"])
    if scene.get("model_id"):
        return f"kie/{scene['model_id']}"
    if default:
        return default
    env_default = os.environ.get("DEFAULT_VIDEO_PROVIDER")
    if env_default:
        return env_default
    return "kie/veo-3-1"


__all__ = [
    "ProviderRouter",
    "ProviderSpec",
    "parse_scene_provider",
]
