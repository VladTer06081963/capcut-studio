"""Unit tests for py/render (Kie.ai client + provider router).

These tests do NOT require a real KIE_API_KEY — they mock the HTTP layer
or operate on the routing logic only. The live smoke test is
`scripts/test_kie.py`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from capcut.render import ProviderRouter, ProviderSpec, parse_scene_provider  # noqa: E402
from capcut.render.base import GenerationRequest, GenerationResult  # noqa: E402
from capcut.render.kie_client import (  # noqa: E402
    KieClient, KieError, KieAuthError, KieCreditError, KieNotFoundError,
    KieValidationError, KieRateLimitError, ModelInfo,
)


# ---------------------------------------------------------------------------
# ProviderSpec parsing
# ---------------------------------------------------------------------------

class TestProviderSpec:
    def test_parse_qualified(self) -> None:
        s = ProviderSpec.parse("kling/v2-1-master-text-to-video")
        assert s.backend == "kie"
        assert s.model_id == "kling/v2-1-master-text-to-video"
        assert s.raw == "kling/v2-1-master-text-to-video"

    def test_parse_with_explicit_kie(self) -> None:
        s = ProviderSpec.parse("kie/veo-3-1")
        assert s.backend == "kie"
        assert s.model_id == "veo-3-1"

    def test_parse_bare_defaults_to_kie(self) -> None:
        s = ProviderSpec.parse("veo-3-1")
        assert s.backend == "kie"
        assert s.model_id == "veo-3-1"

    def test_parse_with_slash_in_model_name(self) -> None:
        # Canonical Kie model IDs retain their provider segment.
        s = ProviderSpec.parse("kling/v2-1-master-text-to-video")
        assert s.backend == "kie"
        assert s.model_id == "kling/v2-1-master-text-to-video"


# ---------------------------------------------------------------------------
# parse_scene_provider hierarchy
# ---------------------------------------------------------------------------

class TestParseSceneProvider:
    def test_explicit_provider_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEFAULT_VIDEO_PROVIDER", raising=False)
        scene = {"provider": "kling/v2-1-master-text-to-video"}
        assert parse_scene_provider(scene) == "kling/v2-1-master-text-to-video"

    def test_model_id_fallback_prefixed_with_kie(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEFAULT_VIDEO_PROVIDER", raising=False)
        scene = {"model_id": "veo-3-1"}
        assert parse_scene_provider(scene) == "kie/veo-3-1"

    def test_explicit_default_arg(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEFAULT_VIDEO_PROVIDER", raising=False)
        assert parse_scene_provider({}, default="kling/v2-1-master-text-to-video") \
            == "kling/v2-1-master-text-to-video"

    def test_env_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEFAULT_VIDEO_PROVIDER", "runway/gen-4-turbo")
        assert parse_scene_provider({}) == "runway/gen-4-turbo"

    def test_hardcoded_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEFAULT_VIDEO_PROVIDER", raising=False)
        assert parse_scene_provider({}) == "kie/veo-3-1"

    def test_provider_wins_over_model_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEFAULT_VIDEO_PROVIDER", raising=False)
        scene = {"provider": "kling/v2-1-master-text-to-video", "model_id": "veo-3-1"}
        assert parse_scene_provider(scene) == "kling/v2-1-master-text-to-video"


# ---------------------------------------------------------------------------
# Router get / build
# ---------------------------------------------------------------------------

class TestProviderRouter:
    def test_kie_backend_uses_kie_client(self) -> None:
        router = ProviderRouter(env={"KIE_API_KEY": "test-key"})
        client = router.get("kie/veo-3-1")
        assert isinstance(client, KieClient)
        assert client.is_available() is True

    def test_minimax_backend_not_implemented(self) -> None:
        router = ProviderRouter(env={})
        with pytest.raises(NotImplementedError):
            router.get("minimax/h3-max")

    def test_unknown_backend_raises(self) -> None:
        router = ProviderRouter(env={})
        with pytest.raises(ValueError, match="Unknown backend 'openrouter'"):
            router.get("openrouter/model")

    def test_client_is_cached(self) -> None:
        router = ProviderRouter(env={"KIE_API_KEY": "x"})
        a = router.get("kie/veo-3-1")
        b = router.get("kie/veo-3-1")
        assert a is b

    def test_resolve_default_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEFAULT_VIDEO_PROVIDER", "kling/v2-1-master-text-to-video")
        router = ProviderRouter()
        assert router.resolve_default() == "kling/v2-1-master-text-to-video"

    def test_resolve_default_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DEFAULT_VIDEO_PROVIDER", raising=False)
        router = ProviderRouter()
        assert router.resolve_default() == "kie/veo-3-1"


# ---------------------------------------------------------------------------
# Router.generate with mocked client
# ---------------------------------------------------------------------------

class TestRouterGenerate:
    def test_generate_success_first_try(self) -> None:
        router = ProviderRouter(env={"KIE_API_KEY": "x"})
        mock = MagicMock(spec=KieClient)
        mock.name = "kie"
        mock.is_available.return_value = True
        mock.submit.return_value = "job-1"
        mock.wait.return_value = GenerationResult(
            success=True, video_path=Path("/tmp/v.mp4"),
            provider_job_id="job-1", model_id="veo-3-1",
        )
        router._cache["kie/veo-3-1"] = mock

        req = GenerationRequest(prompt="test", model_id="veo-3-fast")
        result = router.generate(req)
        assert result.success
        assert result.provider_job_id == "job-1"
        submitted = mock.submit.call_args.args[0]
        assert submitted.model_id == "veo-3-1"
        mock.wait.assert_called_once()

    def test_generate_fallback_on_failure(self) -> None:
        router = ProviderRouter(env={"KIE_API_KEY": "x"})
        primary = MagicMock(spec=KieClient)
        primary.name = "kie"
        primary.is_available.return_value = True
        primary.submit.side_effect = KieError("primary down")
        fallback = MagicMock(spec=KieClient)
        fallback.name = "kie"
        fallback.is_available.return_value = True
        fallback.submit.return_value = "job-2"
        fallback.wait.return_value = GenerationResult(
            success=True, video_path=Path("/tmp/v.mp4"),
            provider_job_id="job-2", model_id="runway/gen-4-turbo",
        )
        router._cache["kie/veo-3-1"] = primary
        router._cache["runway/gen-4-turbo"] = fallback

        req = GenerationRequest(prompt="test", model_id="veo-3-1")
        result = router.generate(req, fallback=["runway/gen-4-turbo"])
        assert result.success
        assert result.provider_job_id == "job-2"
        assert fallback.submit.call_args.args[0].model_id == "runway/gen-4-turbo"

    def test_generate_unavailable_skipped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # KieClient falls back to os.environ; make sure no real key leaks in.
        monkeypatch.delenv("KIE_API_KEY", raising=False)
        router = ProviderRouter(env={})  # no key
        req = GenerationRequest(prompt="test", model_id="veo-3-1")
        result = router.generate(req)
        assert not result.success
        assert "unavailable" in result.error


# ---------------------------------------------------------------------------
# KieClient envelope parsing (error codes 401/402/404/422/429/433/455)
# ---------------------------------------------------------------------------

class TestEnvelopeCodes:
    """Skill: code is in response BODY, not HTTP status."""

    def _mock_resp(self, code: int, msg: str = "fail") -> MagicMock:
        resp = MagicMock()
        resp.json.return_value = {"code": code, "msg": msg, "data": None}
        resp.raise_for_status.return_value = None
        return resp

    def test_401_raises_auth(self) -> None:
        c = KieClient(api_key="x")
        with patch.object(c._session, "get", return_value=self._mock_resp(401, "bad key")):
            with pytest.raises(KieAuthError):
                c.get_credit_balance()

    def test_402_raises_credit(self) -> None:
        c = KieClient(api_key="x")
        with patch.object(c._session, "get", return_value=self._mock_resp(402, "no money")):
            with pytest.raises(KieCreditError):
                c.get_credit_balance()

    def test_404_raises_not_found(self) -> None:
        c = KieClient(api_key="x")
        with patch.object(c._session, "get", return_value=self._mock_resp(404)):
            with pytest.raises(KieNotFoundError):
                c.get_model_schema("nonexistent/model")

    def test_422_raises_validation(self) -> None:
        c = KieClient(api_key="x")
        with patch.object(c._session, "get", return_value=self._mock_resp(422, "bad input")):
            with pytest.raises(KieValidationError):
                c.list_models()

    def test_429_raises_rate_limit(self) -> None:
        c = KieClient(api_key="x")
        with patch.object(c._session, "get", return_value=self._mock_resp(429, "slow down")):
            with pytest.raises(KieRateLimitError):
                c.get_credit_balance()


# ---------------------------------------------------------------------------
# KieClient state → GenerationResult (per kie-models skill state machine)
# ---------------------------------------------------------------------------

class TestKieClientStateMapping:
    def test_pending_state(self) -> None:
        c = KieClient(api_key="x")
        r = c._data_to_result({"state": "generating"}, "job-1")
        assert not r.success
        assert r.error == "pending"

    def test_queuing_state(self) -> None:
        c = KieClient(api_key="x")
        r = c._data_to_result({"state": "queuing"}, "job-1")
        assert not r.success
        assert r.error == "pending"

    def test_waiting_state(self) -> None:
        c = KieClient(api_key="x")
        r = c._data_to_result({"state": "waiting"}, "job-1")
        assert not r.success
        assert r.error == "pending"

    def test_fail_state(self) -> None:
        c = KieClient(api_key="x")
        r = c._data_to_result({"state": "fail", "failMsg": "nsfw detected"},
                              "job-1")
        assert not r.success
        assert r.error == "nsfw detected"

    def test_success_state_with_response_object(self) -> None:
        c = KieClient(api_key="x", download_to=Path("/tmp/kie_test"))
        with patch.object(c, "_download", return_value=Path("/tmp/kie_test/job-1.mp4")):
            data = {
                "state": "success",
                "model": "kling/v2-1-master-text-to-video",
                "costTime": 60000,         # 60s in ms
                "creditsConsumed": 120.0,  # credits
                "response": {
                    "resultUrls": ["https://tempfile.redpandaai.co/x/output.mp4"],
                },
            }
            r = c._data_to_result(data, "job-1")
            assert r.success
            assert r.video_path == Path("/tmp/kie_test/job-1.mp4")
            assert r.remote_url == "https://tempfile.redpandaai.co/x/output.mp4"
            assert r.cost_credits == 120.0
            assert r.cost_usd is None
            assert r.latency_sec == 60.0
            assert r.model_id == "kling/v2-1-master-text-to-video"

    def test_success_state_with_resultJson_string(self) -> None:
        c = KieClient(api_key="x", download_to=Path("/tmp/kie_test"))
        with patch.object(c, "_download", return_value=Path("/tmp/kie_test/job-1.mp4")):
            data = {
                "state": "success",
                "model": "veo-3-1",
                "costTime": 30000,
                "creditsConsumed": 40.0,
                "resultJson": '{"resultUrls": ["https://cdn.kie.ai/x.mp4"]}',
            }
            r = c._data_to_result(data, "job-1")
            assert r.success
            assert r.remote_url == "https://cdn.kie.ai/x.mp4"

    def test_unknown_state(self) -> None:
        c = KieClient(api_key="x")
        r = c._data_to_result({"state": "weird"}, "job-1")
        assert not r.success
        assert r.error is not None and "unknown_state" in r.error


# ---------------------------------------------------------------------------
# KieClient.submit uses schema to choose the right field name
# ---------------------------------------------------------------------------

class TestSubmitSchemaAware:
    """Skill rule 2: read schema to know which image field the model uses."""

    def _schema_with_input_fields(self, fields: list[str]) -> dict:
        # get_model_schema() returns the openapi object itself (already unboxed
        # from data.openapi), so we mimic that shape — no extra "openapi" wrapper.
        return {
            "paths": {
                "/api/v1/jobs/createTask": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Body"}
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "Body": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string"},
                            "input": {"$ref": "#/components/schemas/Input"}
                        },
                        "required": ["model", "input"],
                    },
                    "Input": {
                        "type": "object",
                        "properties": {f: {"type": "string"} for f in fields},
                    },
                }
            }
        }

    def test_schema_input_image_when_schema_says_input_image(self) -> None:
        c = KieClient(api_key="x")
        schema = self._schema_with_input_fields(["prompt", "input_image", "duration"])
        with patch.object(c, "get_model_schema", return_value=schema):
            with patch.object(c, "_post", return_value={"taskId": "abc"}) as post:
                req = GenerationRequest(
                    prompt="x", model_id="some/image2vid-model",
                    reference_image="https://example.com/seed.png",
                )
                c.submit(req)
                args, _ = post.call_args
                payload = args[1]
                assert "input_image" in payload["input"]
                assert "image_url" not in payload["input"]

    def test_schema_image_url_when_schema_says_image_url(self) -> None:
        c = KieClient(api_key="x")
        schema = self._schema_with_input_fields(["prompt", "image_url", "duration"])
        with patch.object(c, "get_model_schema", return_value=schema):
            with patch.object(c, "_post", return_value={"taskId": "abc"}) as post:
                req = GenerationRequest(
                    prompt="x", model_id="some/img-model",
                    reference_image="https://example.com/seed.png",
                )
                c.submit(req)
                args, _ = post.call_args
                payload = args[1]
                assert payload["input"]["image_url"] == "https://example.com/seed.png"

    def test_no_schema_falls_back_to_image_url(self) -> None:
        c = KieClient(api_key="x")
        with patch.object(c, "get_model_schema", return_value=None):
            with patch.object(c, "_post", return_value={"taskId": "abc"}) as post:
                req = GenerationRequest(
                    prompt="x", model_id="any/model",
                    reference_image="https://example.com/seed.png",
                )
                c.submit(req)
                args, _ = post.call_args
                payload = args[1]
                assert payload["input"]["image_url"] == "https://example.com/seed.png"

    def test_reference_image_local_path_rejected(self) -> None:
        c = KieClient(api_key="x")
        with patch.object(c, "get_model_schema", return_value=None):
            req = GenerationRequest(
                prompt="x", model_id="any/model",
                reference_image="/local/file.png",
            )
            with pytest.raises(ValueError, match="http"):
                c.submit(req)

    def test_synchronous_model_rejected(self) -> None:
        c = KieClient(api_key="x")
        # Schema with no /api/v1/jobs/createTask path = synchronous (chat) model
        schema = {"paths": {"/claude/v1/messages": {"post": {}}}}
        with patch.object(c, "get_model_schema", return_value=schema):
            req = GenerationRequest(prompt="x", model_id="claude/sonnet")
            with pytest.raises(KieError, match="synchronous"):
                c.submit(req)

    def test_extra_fields_passed_through(self) -> None:
        c = KieClient(api_key="x")
        with patch.object(c, "get_model_schema", return_value=None):
            with patch.object(c, "_post", return_value={"taskId": "abc"}) as post:
                req = GenerationRequest(
                    prompt="x", model_id="any/model",
                    extra={"camera_motion": "pan_left", "audio": False},
                )
                c.submit(req)
                args, _ = post.call_args
                payload = args[1]
                assert payload["input"]["camera_motion"] == "pan_left"
                assert payload["input"]["audio"] is False


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------

class TestAvailability:
    def test_no_key_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("KIE_API_KEY", raising=False)
        assert KieClient(api_key="").is_available() is False

    def test_with_key_available(self) -> None:
        assert KieClient(api_key="abc").is_available() is True


# ---------------------------------------------------------------------------
# ModelInfo parsing
# ---------------------------------------------------------------------------

class TestModelInfo:
    def test_from_api(self) -> None:
        row = {
            "model": "kling/v2-1-master-text-to-video",
            "slug": "kling/v2-1-master-text-to-video",
            "title": "Kling 2.1 Master Text-to-Video",
            "provider": "Kling",
            "taskType": ["Text to Video"],
            "pricingDesc": "160 credits per 5s",
            "description": "Premium t2v",
        }
        info = ModelInfo.from_api(row)
        assert info.model == "kling/v2-1-master-text-to-video"
        assert info.provider == "Kling"
        assert "Text to Video" in info.task_types
        assert info.pricing_desc == "160 credits per 5s"

    def test_from_api_with_missing_fields(self) -> None:
        info = ModelInfo.from_api({"model": "x"})
        assert info.model == "x"
        assert info.task_types == []
        assert info.pricing_desc is None
        assert info.description is None
