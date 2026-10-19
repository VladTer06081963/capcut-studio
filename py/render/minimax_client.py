"""Video provider for MiniMax H3.0 / H3 Max."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests

from py.lib.config import MINIMAX_API_KEY, MINIMAX_BASE_URL
from py.render.base import GenerationRequest, GenerationResult


class MinimaxClient:
    """Direct client for MiniMax video generation."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or MINIMAX_API_KEY
        self.base_url = "https://api.minimax.chat/v1"

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
        
        # We need to map model_id correctly, but let's default to standard minimax video-01
        payload = {
            "prompt": req.prompt,
            "model": "video-01"
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        
        try:
            data = resp.json()
        except ValueError:
            raise RuntimeError(f"MiniMax API returned non-JSON: {resp.text}")
            
        if data.get("base_resp", {}).get("status_code") != 0:
            raise RuntimeError(f"MiniMax API error: {data.get('base_resp', {}).get('status_msg')}")
            
        return data["task_id"]

    def wait(self, job_id: str, timeout_sec: int = 600, poll_interval_sec: int = 5) -> GenerationResult:
        if not self.api_key:
            return GenerationResult(success=False, error="no api key")
            
        url = f"{self.base_url}/query/video_generation?task_id={job_id}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        t0 = time.time()
        while time.time() - t0 < timeout_sec:
            resp = requests.get(url, headers=headers, timeout=30)
            data = resp.json()
            
            status = data.get("status")
            
            if status == "Success":
                file_id = data.get("file_id")
                # Now we need to get the download URL
                dl_url = f"{self.base_url}/files/retrieve?file_id={file_id}"
                dl_resp = requests.get(dl_url, headers=headers)
                dl_data = dl_resp.json()
                
                download_url = dl_data.get("file", {}).get("download_url")
                if not download_url:
                    return GenerationResult(success=False, error="Success but no download_url")
                    
                import tempfile
                import urllib.request
                
                temp_file = tempfile.mktemp(suffix=".mp4")
                urllib.request.urlretrieve(download_url, temp_file)
                
                return GenerationResult(
                    success=True,
                    remote_url=download_url,
                    video_path=temp_file,
                    model_id="minimax-video-01"
                )
            elif status == "Fail":
                return GenerationResult(success=False, error=data.get("base_resp", {}).get("status_msg", "Failed"))
                
            time.sleep(poll_interval_sec)

        return GenerationResult(success=False, error="timeout")
