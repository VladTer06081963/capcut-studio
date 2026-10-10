"""
Episode spec writer — brief.md + bible/<show>.md → spec.json via Qwen3-Max.

Reads a markdown brief and the show's bible template, sends to OpenRouter
(Qwen3-Max), parses the structured response into a validated EpisodeSpec,
and writes it to `serials/<show>/<ep-id>/spec.json`.

Architecture notes:
- LLM is told to output strict JSON (no prose around it).
- We re-validate on parse — never trust LLM output blindly.
- Schema version embedded in spec.json (`schema: 1`) for future migrations.
- `brief_sha256` stored in spec for idempotency (re-running with same brief
  is a no-op; different brief → bump version).

Mirror of comic-studio `py/scenario/writer.py` Stage 2 pattern, adapted
for video episodes (scenes instead of panels).
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from py.lib.config import (
    DEFAULT_TEXT_PROVIDER,
    LM_STUDIO_URL,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    has_lm_studio_text,
    has_openrouter,
)
from py.lib.lifecycle import sha256_file


SCHEMA_VERSION = 1

# Default model for spec writing. Override per-call with `model=`.
# Default is LM Studio local (qwen2.5-coder is what user typically loads).
# Falls back to OpenRouter if LM Studio unreachable.
DEFAULT_MODEL = "qwen2.5-coder-7b-instruct-mlx"

# Hard cap on input tokens to keep cost predictable.
MAX_BRIEF_CHARS = 8_000
MAX_BIBLE_CHARS = 8_000


# ---------------------------------------------------------------------------
# Spec data classes
# ---------------------------------------------------------------------------

@dataclass
class SceneSpec:
    """One scene in an episode."""

    n: int                                # 1-based scene index
    type: str                             # "establishing" | "dialogue" | "action" | "transition" | "voiceover"
    query: str                            # natural-language visual description (for matcher)
    preferred_source: str = "ai"          # "ai" | "stock" | "any"
    track: str = "video"                  # "video" | "overlay" | "audio"
    duration_sec: int = 5
    character_ref: str | None = None      # "ai:reznik:reference.png" (None if B-roll)
    scene_ref: str | None = None          # "ai:pripyat-evening:wide" (None if no canonical scene)
    caption: str | None = None            # on-screen text / dialogue
    voiceover: str | None = None          # voice-over narration text
    tags: list[str] = field(default_factory=list)


@dataclass
class EpisodeSpec:
    """Full episode spec."""

    schema: int                           # SCHEMA_VERSION
    id: str                               # "ep-01-pilot"
    show: str                             # "stalker-reznik"
    title: str
    summary: str                          # one-line plot
    scenes: list[SceneSpec]
    provider: dict[str, str]              # override per-provider ("text": "qwen3-max", ...)
    model: str                            # which LLM generated this
    created_at: str                       # ISO-8601 UTC
    brief_sha256: str                     # for idempotency
    bible_sha256: str                     # for cache invalidation


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

VALID_SCENE_TYPES = {
    # Canonical base types
    "establishing", "dialogue", "action", "transition", "voiceover",
    # Common cinematic compounds (from briefs in the wild)
    "dialogue-reaction", "establishing-wide", "establishing-reverse",
    "silhouette", "insert", "montage",
}
VALID_TRACKS = {"video", "overlay", "audio"}
VALID_SOURCES = {"ai", "stock", "any"}


def _normalize_scene_type(t: str) -> str:
    """Slash/underscore-tolerant normalisation: 'dialogue/reaction' -> 'dialogue-reaction'."""
    return (t or "").strip().lower().replace("/", "-").replace("_", "-")


def validate_spec(spec: EpisodeSpec) -> list[str]:
    """Return list of warnings/errors. Empty list = OK."""
    issues: list[str] = []

    if spec.schema != SCHEMA_VERSION:
        issues.append(f"schema mismatch: expected {SCHEMA_VERSION}, got {spec.schema}")

    if not spec.id or not re.match(r"^[a-z0-9][a-z0-9\-_]*$", spec.id):
        issues.append(f"id invalid: {spec.id!r} (must be kebab/snake-case)")

    if not spec.show:
        issues.append("show is required")

    if not spec.title:
        issues.append("title is required")

    if not spec.scenes:
        issues.append("scenes list is empty")

    for i, s in enumerate(spec.scenes):
        if s.n != i + 1:
            issues.append(f"scene[{i}].n should be {i + 1}, got {s.n}")
        normalized_type = _normalize_scene_type(s.type)
        if normalized_type not in VALID_SCENE_TYPES:
            issues.append(f"scene[{i}].type invalid: {s.type!r}")
        if s.track not in VALID_TRACKS:
            issues.append(f"scene[{i}].track invalid: {s.track!r}")
        if s.preferred_source not in VALID_SOURCES:
            issues.append(f"scene[{i}].preferred_source invalid: {s.preferred_source!r}")
        if s.duration_sec <= 0 or s.duration_sec > 120:
            issues.append(f"scene[{i}].duration_sec out of range: {s.duration_sec}")
        if not s.query and s.track == "video":
            issues.append(f"scene[{i}].query required for video track")

    if spec.provider.get("text") and not isinstance(spec.provider["text"], str):
        issues.append(f"provider.text must be a string: {spec.provider['text']!r}")

    return issues


# ---------------------------------------------------------------------------
# LLM call (OpenRouter)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a video editor's assistant. Convert a creative brief
into a structured scene-by-scene episode spec. The output is consumed by a
video assembly pipeline that searches a library of pre-generated clips.

Output ONLY a valid JSON object. No markdown, no prose before/after, no code
fences. The JSON must match this exact shape:

{
  "id": "ep-XX-slug",
  "show": "<show slug from bible>",
  "title": "<one-line title>",
  "summary": "<one-line plot summary>",
  "scenes": [
    {
      "n": 1,
      "type": "establishing" | "dialogue" | "action" | "transition" | "voiceover",
      "query": "<natural-language visual description for matcher>",
      "preferred_source": "ai" | "stock" | "any",
      "track": "video" | "overlay" | "audio",
      "duration_sec": <int 1-120>,
      "character_ref": "<ai:<char>:reference.png | null>",
      "scene_ref": "<ai:<scene-slug>:<shot> | null>",
      "caption": "<on-screen text | null>",
      "voiceover": "<narration text | null>",
      "tags": ["<tag>", ...]
    }
  ],
  "provider": {"text": "<model-name>"}
}

Constraints:
- 5-15 scenes per episode (target 60-180 sec total)
- scene.n must be 1-based and sequential
- preferred_source: "ai" for hero shots, "stock" for B-roll
- character_ref must reference a character from the bible (or null)
- scene_ref must reference a scene from the bible (or null)
- query should describe what should be SEEN, not narrated
- voiceover tracks (track="audio") have no query but require voiceover text
"""


def _build_user_prompt(brief: str, bible_excerpt: str) -> str:
    """Build the user message: brief + relevant bible sections."""
    return (
        f"## SHOW BIBLE (excerpt)\n\n{bible_excerpt}\n\n"
        f"## EPISODE BRIEF\n\n{brief}\n\n"
        f"## TASK\n\n"
        f"Generate a JSON EpisodeSpec matching the schema. "
        f"Reference characters and scenes by their slugs from the bible. "
        f"Prefer 'ai' for character moments, 'stock' for atmosphere/B-roll."
    )


def call_openrouter(
    messages: list[dict[str, str]],
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.4,
    max_tokens: int = 4096,
    timeout: int = 60,
) -> dict[str, Any]:
    """Send chat completion. Tries LM Studio first, then OpenRouter.

    LM Studio: OpenAI-compatible /v1/chat/completions, requires bearer token
    (LM_STUDIO_API_TOKEN env). Default for local Qwen models.

    OpenRouter: same shape, requires OPENROUTER_API_KEY.

    Selection logic:
    - If `model` is an OpenRouter-style name ("provider/model"), use OpenRouter
    - Otherwise, use LM Studio first; fall back to OpenRouter if LM Studio down

    Returns parsed response dict.

    Raises:
        RuntimeError: if neither LM Studio nor OpenRouter is configured.
        requests.HTTPError: on non-2xx.
    """
    is_openrouter_model = "/" in model

    if is_openrouter_model or not has_lm_studio_text():
        return _call_openrouter_only(messages, model=model, temperature=temperature,
                                      max_tokens=max_tokens, timeout=timeout)
    # Default: LM Studio local
    try:
        return _call_lm_studio_chat(messages, model=model, temperature=temperature,
                                    max_tokens=max_tokens, timeout=timeout)
    except (requests.RequestException, RuntimeError) as e:
        if has_openrouter():
            return _call_openrouter_only(messages, model=model, temperature=temperature,
                                          max_tokens=max_tokens, timeout=timeout)
        raise RuntimeError(f"LM Studio call failed and no OpenRouter fallback: {e}") from e


def _call_lm_studio_chat(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> dict[str, Any]:
    """Call LM Studio's OpenAI-compatible /v1/chat/completions.

    LM Studio (llama.cpp server) does NOT support
    `response_format={"type": "json_object"}` — only `json_schema` or `text`.
    Strategy: try with json_object first (matches OpenRouter behaviour, useful
    if running on a server that supports it); on 400 Bad Request for that
    specific field, retry without `response_format` and rely on prompt
    engineering to get JSON back.
    """
    from py.lib.config import LM_STUDIO_API_TOKEN

    url = f"{LM_STUDIO_URL}/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
    }
    if LM_STUDIO_API_TOKEN:
        headers["Authorization"] = f"Bearer {LM_STUDIO_API_TOKEN}"

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code == 400 and "response_format" in resp.text:
        # LM Studio (llama.cpp) doesn't accept json_object — retry without it
        payload.pop("response_format", None)
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _call_openrouter_only(
    messages: list[dict[str, str]],
    *,
    model: str,
    temperature: float,
    max_tokens: int,
    timeout: int,
) -> dict[str, Any]:
    """Call OpenRouter (legacy fallback)."""
    if not has_openrouter():
        raise RuntimeError(
            "Neither LM Studio nor OpenRouter configured. "
            "Set LM_STUDIO_API_TOKEN or OPENROUTER_API_KEY in .env"
        )

    url = f"{OPENROUTER_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _extract_json_content(response: dict[str, Any]) -> str:
    """Pull the message content from OpenRouter response. Defensive parsing.

    Local models (e.g. qwen2.5-coder via LM Studio) often wrap JSON in
    markdown ```...``` fences even when the prompt says "no fences". Strip the
    fence block before returning, so json.loads doesn't fail on char 0.
    """
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"unexpected OpenRouter response shape: {e}")

    # Strip ```json ... ``` or ``` ... ``` fence if present
    fence_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", content, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return content.strip()


# ---------------------------------------------------------------------------
# Bible excerpt extraction
# ---------------------------------------------------------------------------

_BIBLE_KEY_SECTIONS = [
    "Visual style",
    "Frozen video prompt suffix",
    "Negative prompt",
    "Color palette",
    "Camera & composition",
    "Editing style",
    "Cast",
    "Locations",
]


def extract_bible_excerpt(bible_text: str) -> str:
    """Pick the most useful sections from bible markdown for the prompt.

    Matches `## <heading>` even if the actual heading has a parenthetical
    suffix (e.g. "Frozen video prompt suffix (H3.0 / H3 Max)").
    """
    sections: list[str] = []
    for heading in _BIBLE_KEY_SECTIONS:
        # Match "## heading" with optional trailing text on the same line
        pattern = rf"##\s+{re.escape(heading)}[^\n]*\n(.*?)(?=\n##\s|\Z)"
        match = re.search(pattern, bible_text, re.DOTALL)
        if match:
            sections.append(f"## {heading}\n\n{match.group(1).strip()}")
    if not sections:
        # Fallback: first 2000 chars
        return bible_text[:MAX_BIBLE_CHARS]
    return "\n\n".join(sections)[:MAX_BIBLE_CHARS]


# ---------------------------------------------------------------------------
# Main: brief + bible → spec.json
# ---------------------------------------------------------------------------

def _parse_spec_dict(raw: dict[str, Any]) -> EpisodeSpec:
    """Convert raw dict from LLM (or hand-written JSON) into EpisodeSpec."""
    scenes = [SceneSpec(**s) for s in raw.get("scenes", [])]
    return EpisodeSpec(
        schema=raw.get("schema", SCHEMA_VERSION),
        id=raw["id"],
        show=raw["show"],
        title=raw.get("title", ""),
        summary=raw.get("summary", ""),
        scenes=scenes,
        provider=raw.get("provider", {}),
        model=raw.get("model", "unknown"),
        created_at=raw.get("created_at", datetime.now(timezone.utc).isoformat()),
        brief_sha256=raw.get("brief_sha256", ""),
        bible_sha256=raw.get("bible_sha256", ""),
    )


def write_spec_from_brief(
    brief_path: Path,
    bible_path: Path,
    output_path: Path,
    *,
    model: str | None = None,
    dry_run: bool = False,
) -> EpisodeSpec:
    """Read brief.md + bible/<show>.md, call LLM, validate, write spec.json.

    Args:
        brief_path: path to brief.md.
        bible_path: path to bible/<show>.md.
        output_path: where to write spec.json (typically serials/<show>/<ep>/spec.json).
        model: override LLM model (default qwen/qwen3-max).
        dry_run: if True, don't call LLM or write file. Useful for testing schema.

    Returns: validated EpisodeSpec (raises if validation fails).
    """
    brief_text = brief_path.read_text(encoding="utf-8")[:MAX_BRIEF_CHARS]
    bible_text = bible_path.read_text(encoding="utf-8")
    bible_excerpt = extract_bible_excerpt(bible_text)

    brief_sha = sha256_file(brief_path)
    bible_sha = sha256_file(bible_path)

    model = model or DEFAULT_MODEL

    if dry_run:
        # Construct a minimal stub spec from brief without LLM
        spec = EpisodeSpec(
            schema=SCHEMA_VERSION,
            id=output_path.parent.name,
            show=output_path.parent.parent.name,
            title="(dry-run)",
            summary="(dry-run)",
            scenes=[],
            provider={"text": model},
            model=model,
            created_at=datetime.now(timezone.utc).isoformat(),
            brief_sha256=brief_sha,
            bible_sha256=bible_sha,
        )
        # Skip validation for dry-run stub — empty scenes are expected
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(asdict(spec), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return spec
    else:
        user_prompt = _build_user_prompt(brief_text, bible_excerpt)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        response = call_openrouter(messages, model=model)
        content = _extract_json_content(response)

        try:
            raw = json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"LLM returned invalid JSON: {e}\n\n{content[:500]}") from e

        # Inject metadata we control (don't trust LLM)
        raw["schema"] = SCHEMA_VERSION
        raw["model"] = model
        raw["created_at"] = datetime.now(timezone.utc).isoformat()
        raw["brief_sha256"] = brief_sha
        raw["bible_sha256"] = bible_sha

        spec = _parse_spec_dict(raw)

    # Validate
    issues = validate_spec(spec)
    if issues:
        raise ValueError(f"spec validation failed:\n  - " + "\n  - ".join(issues))

    # Write
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(spec), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return spec


def load_spec(path: Path) -> EpisodeSpec:
    """Load and validate a spec.json from disk."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    spec = _parse_spec_dict(raw)
    issues = validate_spec(spec)
    if issues:
        raise ValueError(f"spec at {path} is invalid:\n  - " + "\n  - ".join(issues))
    return spec


__all__ = [
    "SCHEMA_VERSION",
    "DEFAULT_MODEL",
    "SceneSpec",
    "EpisodeSpec",
    "validate_spec",
    "call_openrouter",
    "extract_bible_excerpt",
    "write_spec_from_brief",
    "load_spec",
]