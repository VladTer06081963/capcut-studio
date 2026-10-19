"""Renderers — convert LLM-friendly specs into media files.

Public surface (used by scripts/ and the assembler):
    from py.render import ProviderRouter, KieClient, GenerationRequest, GenerationResult
"""
from py.render.base import GenerationRequest, GenerationResult, VideoProvider, KNOWN_MODELS
from py.render.kie_client import (
    KieClient, KieError, ModelInfo,
    KieAuthError, KieCreditError, KieNotFoundError,
    KieValidationError, KieRateLimitError, KieSubKeyLimitError,
    KieUnavailableError, KIE_BASE_URL, KIE_UPLOAD_BASE,
)
from py.render.provider_router import ProviderRouter, ProviderSpec, parse_scene_provider

__all__ = [
    "GenerationRequest", "GenerationResult", "VideoProvider", "KNOWN_MODELS",
    "KieClient", "KieError", "ModelInfo",
    "KieAuthError", "KieCreditError", "KieNotFoundError",
    "KieValidationError", "KieRateLimitError", "KieSubKeyLimitError",
    "KieUnavailableError", "KIE_BASE_URL", "KIE_UPLOAD_BASE",
    "ProviderRouter", "ProviderSpec", "parse_scene_provider",
]
