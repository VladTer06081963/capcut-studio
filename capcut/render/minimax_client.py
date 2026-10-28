"""Video provider for MiniMax H3.0 / H3 Max."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import requests

from capcut.lib.config import LIBRARY_TEMP, MINIMAX_API_KEY, MINIMAX_BASE_URL
from capcut.lib.media import DownloadError, atomic_download
from capcut.render.base import GenerationRequest, GenerationResult


class MinimaxClient:
    """Direct client for MiniMax video generation."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or MINIMAX_API_KEY
        # From config, so the env var actually takes effect. The value used
        # to be hardcoded here, which made MINIMAX_BASE_URL a no-op setting.
        self.base_url = MINIMAX_BASE_URL.rstrip("/")
        # The model actually requested for the current task. The API does
        # not reliably echo it back, and falling back to a default here
        # would mislabel the provenance of the produced clip.
        self._requested_model: str | None = None
        self._download_to = LIBRARY_TEMP / "minimax_downloads"
        self._download_to.mkdir(parents=True, exist_ok=True)
        self._timeout = 600

    def is_available(self) -> bool:
        return bool(self.api_key)

    def submit(self, req: GenerationRequest) -> str:
        if not self.api_key:
            raise RuntimeError("MINIMAX_API_KEY not set")

        # MiniMax Video Generation API
        url = f"{self.base_url}/video_generation"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # The model comes from the request, not from a hardcoded default:
        # the provider is selected per scene, and silently substituting a
        # different model would be exactly the silent switch the approval
        # contract forbids.
        payload = {
            "prompt": req.prompt,
            "model": req.model_id or "video-01",
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        
        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError(f"MiniMax API returned non-JSON: {resp.text}")
            
        if data.get("base_resp", {}).get("status_code") != 0:
            raise RuntimeError(f"MiniMax API error: {data.get('base_resp', {}).get('status_msg')}")
            
        self._requested_model = req.model_id or "video-01"
        return data["task_id"]

    def _query(self, job_id: str) -> dict[str, Any]:
        """One status query. Raises on transport or non-JSON failure."""
        url = f"{self.base_url}/query/video_generation?task_id={job_id}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError as exc:
            raise RuntimeError(
                f"MiniMax API returned non-JSON: {resp.text[:200]}"
            ) from exc

    def poll(self, job_id: str) -> GenerationResult:
        """One-shot poll — part of the VideoProvider protocol.

        Contacts the API exactly once and reports the current state; it
        never blocks. `wait()` is the blocking variant.
        """
        if not self.api_key:
            return GenerationResult(success=False, error="no api key")
        try:
            data = self._query(job_id)
        except (requests.RequestException, RuntimeError) as exc:
            return GenerationResult(success=False, error=f"poll failed: {exc}")
        status = data.get("status")
        if status == "Success":
            return self._download_result(job_id, data)
        if status == "Fail":
            return GenerationResult(
                success=False,
                error=data.get("base_resp", {}).get("status_msg", "Failed"),
            )
        return GenerationResult(success=False, error=f"not ready: {status}")

    def list_models(self) -> list[dict[str, Any]]:
        """Model catalog. MiniMax does not expose one over this API."""
        return []

    def _download_result(self, job_id: str, data: dict[str, Any]) -> GenerationResult:
        """Fetch the finished clip. Returns a failed result on any problem."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        file_id = data.get("file_id")
        dl_url = f"{self.base_url}/files/retrieve?file_id={file_id}"
        dl_resp = requests.get(dl_url, headers=headers, timeout=30)
        try:
            dl_data = dl_resp.json()
        except ValueError:
            return GenerationResult(
                success=False,
                error=f"MiniMax file retrieve returned non-JSON: {dl_resp.text[:200]}",
            )

        download_url = dl_data.get("file", {}).get("download_url")
        if not download_url:
            return GenerationResult(success=False, error="Success but no download_url")

        # Download atomically: a truncated file must not be published under
        # the final name, and the old tempfile.mktemp() call was racy and
        # had no timeout. The job id comes from the API, so it is sanitized
        # before it becomes a path component.
        safe_job = re.sub(r"[^A-Za-z0-9_-]", "_", job_id)
        dest = self._download_to / f"{safe_job}.mp4"
        try:
            with requests.get(
                download_url, stream=True, timeout=self._timeout
            ) as dl:
                dl.raise_for_status()
                atomic_download(dl, dest)
        except (requests.RequestException, DownloadError) as exc:
            return GenerationResult(success=False, error=f"download failed: {exc}")

        return GenerationResult(
            success=True,
            remote_url=download_url,
            video_path=dest,
            model_id=self._requested_model or "video-01",
        )

    def wait(self, job_id: str, timeout_sec: int = 600, poll_interval_sec: int = 5) -> GenerationResult:
        if not self.api_key:
            return GenerationResult(success=False, error="no api key")

        t0 = time.time()
        while time.time() - t0 < timeout_sec:
            try:
                data = self._query(job_id)
            except (requests.RequestException, RuntimeError) as exc:
                return GenerationResult(success=False, error=f"query failed: {exc}")

            status = data.get("status")

            if status == "Success":
                return self._download_result(job_id, data)
            if status == "Fail":
                return GenerationResult(
                    success=False,
                    error=data.get("base_resp", {}).get("status_msg", "Failed"),
                )

            time.sleep(poll_interval_sec)

        return GenerationResult(success=False, error="timeout")
