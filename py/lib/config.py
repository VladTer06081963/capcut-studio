"""
Configuration loader for capcut-studio.

Reads `.env` (if present) and exposes typed accessors for paths, providers,
and API keys. Falls back to sensible defaults so the package imports cleanly
even before `.env` exists (e.g. when running `pytest`).

Mirror of comic-studio `py/lib/config.py`. Keeps the surface tiny: paths +
provider names + key flags. Anything that needs logic goes in a domain module.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover — graceful fallback for tests
    load_dotenv = None


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
ENV_FILE: Path = PROJECT_ROOT / ".env"

if load_dotenv is not None:
    # Override=False so the real shell env wins over .env (lets CI override)
    load_dotenv(ENV_FILE, override=False)


# ---------------------------------------------------------------------------
# Path config (with sensible defaults — read from .env when set)
# ---------------------------------------------------------------------------

LIBRARY_ROOT: Path = Path(os.environ.get("LIBRARY_ROOT", PROJECT_ROOT / "library"))
LIBRARY_INDEX: Path = Path(os.environ.get("LIBRARY_INDEX", LIBRARY_ROOT / "index.sqlite"))
LIBRARY_TEMP: Path = Path(os.environ.get("LIBRARY_TEMP", PROJECT_ROOT / ".tmp"))

SERIALS_ROOT: Path = Path(os.environ.get("SERIALS_ROOT", PROJECT_ROOT / "serials"))

AI_DIR: Path = LIBRARY_ROOT / "ai"
STOCK_DIR: Path = LIBRARY_ROOT / "stock"


# ---------------------------------------------------------------------------
# Provider defaults (override hierarchy: CLI > spec > env > hardcoded)
# ---------------------------------------------------------------------------

DEFAULT_VIDEO_PROVIDER: str = os.environ.get("DEFAULT_VIDEO_PROVIDER", "minimax-h3-max")
DEFAULT_TEXT_PROVIDER: str = os.environ.get("DEFAULT_TEXT_PROVIDER", "qwen3-max")
DEFAULT_IMAGE_PROVIDER: str = os.environ.get("DEFAULT_IMAGE_PROVIDER", "qwen-image")


# ---------------------------------------------------------------------------
# Cloud AI endpoints
# ---------------------------------------------------------------------------

MINIMAX_API_KEY: str | None = os.environ.get("MINIMAX_API_KEY")
MINIMAX_BASE_URL: str = os.environ.get("MINIMAX_BASE_URL", "https://api.MiniMax.io")

OPENROUTER_API_KEY: str | None = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL: str = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")


# ---------------------------------------------------------------------------
# Stock sources (UA-aware; Pixabay/Pexels often blocked)
# ---------------------------------------------------------------------------

YOUTUBE_API_KEY: str | None = os.environ.get("YOUTUBE_API_KEY")
COVERR_API_KEY: str | None = os.environ.get("COVERR_API_KEY")
MIXKIT_SCRAPE_DELAY_SEC: float = float(os.environ.get("MIXKIT_SCRAPE_DELAY_SEC", "2.0"))

PIXABAY_API_KEY: str | None = os.environ.get("PIXABAY_API_KEY")
PEXELS_API_KEY: str | None = os.environ.get("PEXELS_API_KEY")


# ---------------------------------------------------------------------------
# Local services (WireGuard-isolated)
# ---------------------------------------------------------------------------

LM_STUDIO_URL: str = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234")
LM_STUDIO_EMBED_MODEL: str = os.environ.get("LM_STUDIO_EMBED_MODEL", "bge-large-en-v1.5")
LM_STUDIO_CAPTION_MODEL: str = os.environ.get("LM_STUDIO_CAPTION_MODEL", "blip-2")

CONCAT_MCP_URL: str = os.environ.get("CONCAT_MCP_URL", "http://127.0.0.1:9847")


# ---------------------------------------------------------------------------
# Cost cap (USD/day) — nightly cron aborts above this
# ---------------------------------------------------------------------------

DAILY_AI_BUDGET_USD: float = float(os.environ.get("DAILY_AI_BUDGET_USD", "10"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def has_minimax() -> bool:
    """True if MiniMax API key is configured."""
    return bool(MINIMAX_API_KEY)


def has_openrouter() -> bool:
    """True if OpenRouter API key is configured."""
    return bool(OPENROUTER_API_KEY)


def has_youtube() -> bool:
    """True if YouTube Data API v3 key is configured."""
    return bool(YOUTUBE_API_KEY)


def has_coverr() -> bool:
    """True if Coverr API key is configured."""
    return bool(COVERR_API_KEY)


def is_test_env() -> bool:
    """True if running under tests (pytest sets this in conftest.py later)."""
    return bool(os.environ.get("CAPCUT_STUDIO_TEST"))


def ensure_dirs() -> None:
    """Create the standard directory tree if missing. Idempotent."""
    for p in (LIBRARY_ROOT, AI_DIR, STOCK_DIR, SERIALS_ROOT, LIBRARY_TEMP):
        p.mkdir(parents=True, exist_ok=True)


__all__ = [
    "PROJECT_ROOT",
    "ENV_FILE",
    "LIBRARY_ROOT",
    "LIBRARY_INDEX",
    "LIBRARY_TEMP",
    "SERIALS_ROOT",
    "AI_DIR",
    "STOCK_DIR",
    "DEFAULT_VIDEO_PROVIDER",
    "DEFAULT_TEXT_PROVIDER",
    "DEFAULT_IMAGE_PROVIDER",
    "MINIMAX_API_KEY",
    "MINIMAX_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "YOUTUBE_API_KEY",
    "COVERR_API_KEY",
    "MIXKIT_SCRAPE_DELAY_SEC",
    "PIXABAY_API_KEY",
    "PEXELS_API_KEY",
    "LM_STUDIO_URL",
    "LM_STUDIO_EMBED_MODEL",
    "LM_STUDIO_CAPTION_MODEL",
    "CONCAT_MCP_URL",
    "DAILY_AI_BUDGET_USD",
    "has_minimax",
    "has_openrouter",
    "has_youtube",
    "has_coverr",
    "is_test_env",
    "ensure_dirs",
]