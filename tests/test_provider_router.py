"""Tests for capcut.render.provider_router — the documented override hierarchy.

AGENTS.md describes the hierarchy explicitly (per-scene `provider` →
per-scene `model_id` → caller default → env → hardcoded), and used to
flag it as unverified. These tests pin it down.

Nothing here touches a live provider: the router is exercised with injected
env mappings and stub clients.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from capcut.render.base import GenerationRequest, GenerationResult
from capcut.render.provider_router import (
    ProviderRouter,
    ProviderSpec,
    parse_scene_provider,
)


class ProviderSpecTest(unittest.TestCase):
    def test_bare_model_id_defaults_to_kie(self) -> None:
        spec = ProviderSpec.parse("veo-3-1")
        self.assertEqual(spec.backend, "kie")
        self.assertEqual(spec.model_id, "veo-3-1")
        self.assertEqual(spec.raw, "veo-3-1")

    def test_known_backend_prefix_is_split(self) -> None:
        spec = ProviderSpec.parse("kie/veo-3-1")
        self.assertEqual(spec.backend, "kie")
        self.assertEqual(spec.model_id, "veo-3-1")

    def test_canonical_kie_id_keeps_its_provider_segment(self) -> None:
        """`kling/...` is a model namespace, not a backend selector."""
        spec = ProviderSpec.parse("kling/v2-1-master-text-to-video")
        self.assertEqual(spec.backend, "kie")
        self.assertEqual(spec.model_id, "kling/v2-1-master-text-to-video")

    def test_minimax_backend_is_recognised(self) -> None:
        spec = ProviderSpec.parse("minimax/h3-max")
        self.assertEqual(spec.backend, "minimax")
        self.assertEqual(spec.model_id, "h3-max")

    def test_str_roundtrips(self) -> None:
        self.assertEqual(str(ProviderSpec.parse("kie/veo-3-1")), "kie/veo-3-1")


class ParseSceneProviderTest(unittest.TestCase):
    def test_explicit_provider_wins(self) -> None:
        scene = {"provider": "kie/explicit-model", "model_id": "other"}
        self.assertEqual(parse_scene_provider(scene, default="kie/default"), "kie/explicit-model")

    def test_model_id_shorthand_expands_to_kie(self) -> None:
        self.assertEqual(
            parse_scene_provider({"model_id": "veo-3-1"}, default="kie/default"),
            "kie/veo-3-1",
        )

    def test_caller_default_is_next(self) -> None:
        self.assertEqual(parse_scene_provider({}, default="kie/caller"), "kie/caller")

    def test_env_default_is_used_when_nothing_else_is_set(self) -> None:
        with patch.dict("os.environ", {"DEFAULT_VIDEO_PROVIDER": "kie/from-env"}):
            self.assertEqual(parse_scene_provider({}), "kie/from-env")

    def test_ultimate_fallback(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(parse_scene_provider({}), "kie/veo-3-1")


class _StubClient:
    """Minimal client with the is_available/submit/wait shape the router uses."""

    def __init__(self, *, available: bool = True, succeed: bool = True) -> None:
        self.available = available
        self.succeed = succeed
        self.submitted: list[GenerationRequest] = []

    def is_available(self) -> bool:
        return self.available

    def submit(self, req: GenerationRequest) -> str:
        self.submitted.append(req)
        return "job-1"

    def wait(self, job_id: str, timeout_sec: int = 600) -> GenerationResult:
        if self.succeed:
            return GenerationResult(success=True, provider_job_id=job_id, model_id="m")
        return GenerationResult(success=False, error="failed")


class ProviderRouterTest(unittest.TestCase):
    def test_resolve_default_uses_env(self) -> None:
        router = ProviderRouter(env={"DEFAULT_VIDEO_PROVIDER": "kie/from-env"})
        self.assertEqual(router.resolve_default(), "kie/from-env")

    def test_resolve_default_falls_back_to_hardcoded(self) -> None:
        self.assertEqual(ProviderRouter(env={}).resolve_default(), "kie/veo-3-1")

    def test_generate_maps_the_model_id_onto_the_request(self) -> None:
        router = ProviderRouter(env={})
        client = _StubClient()
        router.get = lambda provider_str: client  # type: ignore[method-assign]

        result = router.generate(
            GenerationRequest(prompt="p", model_id="ignored"),
            provider_str="kie/veo-3-1",
        )

        self.assertTrue(result.success)
        self.assertEqual(client.submitted[0].model_id, "veo-3-1")

    def test_generate_reports_an_unavailable_provider(self) -> None:
        router = ProviderRouter(env={})
        router.get = lambda provider_str: _StubClient(available=False)  # type: ignore[method-assign]

        result = router.generate(
            GenerationRequest(prompt="p", model_id="m"), provider_str="kie/veo-3-1"
        )
        self.assertFalse(result.success)
        self.assertIn("unavailable", result.error or "")

    def test_unknown_backend_raises(self) -> None:
        router = ProviderRouter(env={})
        with self.assertRaises(NotImplementedError):
            router.get("minimax/h3-max")


if __name__ == "__main__":
    unittest.main()
