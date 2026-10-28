"""Tests for capcut.render.minimax_client.

The provider is not implemented in the router (`provider_router.py` raises
NotImplementedError for the `minimax` backend), but the client still has to
satisfy the `VideoProvider` protocol it claims: `is_available`, `submit`,
`poll`, `wait`, `list_models`.

Nothing here touches the network — the HTTP layer is stubbed.
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from capcut.lib.media import DownloadError
from capcut.render.base import GenerationRequest
from capcut.render.minimax_client import MinimaxClient


class _Resp:
    def __init__(self, payload: dict, text: str = "") -> None:
        self._payload = payload
        self.text = text
        self.status_code = 200

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        return None

    def __enter__(self) -> "_Resp":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class MinimaxClientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = MinimaxClient("test-key")

    # ---- base URL handling ----

    def test_base_url_has_no_trailing_slash(self) -> None:
        # A trailing slash in .env would yield "…/v1//video_generation".
        with patch("capcut.render.minimax_client.MINIMAX_BASE_URL", "https://x/v1/"):
            client = MinimaxClient("k")
        self.assertEqual(client.base_url, "https://x/v1")

    # ---- poll() ----

    def test_poll_contacts_the_api(self) -> None:
        """poll() must actually make a request.

        It used to delegate to wait(timeout_sec=0), whose loop guard was
        false on the first evaluation — so it returned "timeout" without
        ever contacting the API.
        """
        calls: list[str] = []

        def fake_get(url, **kwargs):
            calls.append(url)
            return _Resp({"status": "Processing"})

        with patch("capcut.render.minimax_client.requests.get", fake_get):
            result = self.client.poll("job-1")

        self.assertEqual(len(calls), 1)
        self.assertIn("task_id=job-1", calls[0])
        self.assertFalse(result.success)
        self.assertIn("not ready", result.error or "")

    def test_poll_reports_a_failed_job(self) -> None:
        payload = {"status": "Fail", "base_resp": {"status_msg": "bad prompt"}}
        with patch("capcut.render.minimax_client.requests.get", lambda *a, **k: _Resp(payload)):
            result = self.client.poll("job-1")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "bad prompt")

    def test_poll_reports_a_transport_error(self) -> None:
        import requests

        def boom(*a, **k):
            raise requests.ConnectionError("refused")

        with patch("capcut.render.minimax_client.requests.get", boom):
            result = self.client.poll("job-1")
        self.assertFalse(result.success)
        self.assertIn("poll failed", result.error or "")

    # ---- download ----

    def test_download_error_is_reported_not_raised(self) -> None:
        """atomic_download raises DownloadError, which is not a RequestException."""
        import requests

        calls = {"n": 0}

        def fake_get(url, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return _Resp({"status": "Success", "file_id": "f1"})
            if calls["n"] == 2:
                return _Resp({"file": {"download_url": "https://x/f.mp4"}})
            raise requests.ConnectionError("refused")

        def boom(*a, **k):
            raise DownloadError("incomplete download")

        with patch("capcut.render.minimax_client.requests.get", fake_get), \
             patch("capcut.render.minimax_client.atomic_download", boom):
            result = self.client.wait("job-1", timeout_sec=1, poll_interval_sec=0)

        self.assertFalse(result.success)
        self.assertIn("download failed", result.error or "")

    def test_job_id_is_sanitized_before_it_becomes_a_path(self) -> None:
        """The job id comes from the API and must not escape the download dir."""
        from pathlib import Path

        captured: dict = {}

        def fake_get(url, **kwargs):
            if "files/retrieve" in url:
                return _Resp({"file": {"download_url": "https://x/f.mp4"}})
            return _Resp({"status": "Success", "file_id": "f1"})

        def fake_atomic(resp, dest):
            captured["dest"] = dest
            return dest

        with patch("capcut.render.minimax_client.requests.get", fake_get), \
             patch("capcut.render.minimax_client.atomic_download", fake_atomic):
            self.client.wait("../../evil", timeout_sec=1, poll_interval_sec=0)

        dest = Path(captured["dest"])
        self.assertNotIn("..", dest.name)
        self.assertEqual(dest.parent, self.client._download_to)

    # ---- submit ----

    def test_submit_uses_the_requested_model(self) -> None:
        payload = {"task_id": "t1", "base_resp": {"status_code": 0}}
        with patch("capcut.render.minimax_client.requests.post", lambda *a, **k: _Resp(payload)):
            job_id = self.client.submit(
                GenerationRequest(prompt="p", model_id="h3-max")
            )
        self.assertEqual(job_id, "t1")
        self.assertEqual(self.client._requested_model, "h3-max")

    # ---- protocol ----

    def test_list_models_is_empty(self) -> None:
        self.assertEqual(self.client.list_models(), [])

    def test_is_available_follows_the_key(self) -> None:
        self.assertTrue(self.client.is_available())
        with patch("capcut.render.minimax_client.MINIMAX_API_KEY", None):
            self.assertFalse(MinimaxClient("").is_available())


if __name__ == "__main__":
    unittest.main()
