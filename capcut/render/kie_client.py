"""Kie.ai unified video/image/audio/LLM API client (per official kie-models skill).

API contract (from https://kie.ai/docs):
    Discovery:    GET  /api/v1/models?taskType=...&provider=...&q=...
    Schema:       GET  /api/v1/models/<model>/schema  → OpenAPI doc inline
    Price:        GET  /api/v1/models/<model>/price
    Success rate: GET  /api/v1/models/<model>/success-rate
    Balance:      GET  /api/v1/chat/credit
    Create task:  POST /api/v1/jobs/createTask
    Poll:         GET  /api/v1/jobs/recordInfo?taskId=...
    Direct DL:    POST /api/v1/common/download-url    (optional; resultUrls work)
    Upload base64: POST https://kieai.redpandaai.co/api/file-base64-upload
    Upload stream: POST https://kieai.redpandaai.co/api/file-stream-upload
    Upload url:    POST https://kieai.redpandaai.co/api/file-url-upload

Model id format:
    "wan/v2-2-t2v"          (provider/name — slashes NOT URL-encoded)
    "kling/v2-1-master-text-to-video"
    "gpt-image-2-text-to-image"
    "veo-3-1", "sora-2"     (single-segment for some models)

State machine:
    state="waiting"     successFlag=0   pending
    state="queuing"     successFlag=0   pending
    state="generating"  successFlag=0   pending
    state="success"     successFlag=1   terminal → resultUrls or response.data
    state="fail"        successFlag=3   terminal → failCode, failMsg

Error codes (in body.code, NOT http status):
    200 OK, 401 unauthorized, 402 insufficient credit, 404 not found,
    422 validation, 429 rate limit, 433 sub-key limit, 455 service unavailable

Rate limits (shared pools):
    discovery + schema + price + success-rate: 1 req/sec total
    createTask: 20 req / 10 sec
    recordInfo: 10 req/sec per taskId
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from capcut.lib.config import KIE_BASE_URL, KIE_DOWNLOAD_DIR, KIE_UPLOAD_BASE
from capcut.lib.media import atomic_download
from capcut.render.base import GenerationRequest, GenerationResult


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Per-pool sliding window. Min interval between consecutive calls."""
    def __init__(self, min_interval_sec: float) -> None:
        self._min = min_interval_sec
        self._last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        sleep = self._min - (now - self._last)
        if sleep > 0:
            time.sleep(sleep)
        self._last = time.monotonic()


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class KieError(RuntimeError):
    """General Kie API error."""
    def __init__(self, message: str, code: int | None = None,
                 fail_code: int | None = None, fail_msg: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.fail_code = fail_code
        self.fail_msg = fail_msg


class KieAuthError(KieError):    pass  # 401
class KieCreditError(KieError):  pass  # 402
class KieNotFoundError(KieError): pass  # 404
class KieValidationError(KieError): pass  # 422
class KieRateLimitError(KieError): pass  # 429
class KieSubKeyLimitError(KieError): pass  # 433
class KieUnavailableError(KieError): pass  # 455


_CODE_TO_EXC = {
    401: KieAuthError, 402: KieCreditError, 404: KieNotFoundError,
    422: KieValidationError, 429: KieRateLimitError, 433: KieSubKeyLimitError,
    455: KieUnavailableError,
}


# ---------------------------------------------------------------------------
# Model info helpers
# ---------------------------------------------------------------------------

@dataclass
class ModelInfo:
    """Catalog row from /api/v1/models."""
    model: str             # canonical id, e.g. "kling/v2-1-master-text-to-video"
    slug: str
    title: str
    provider: str
    task_types: list[str]  # e.g. ["Text to Video"]
    pricing_desc: str | None
    description: str | None

    @classmethod
    def from_api(cls, row: dict[str, Any]) -> "ModelInfo":
        return cls(
            model=row.get("model", ""),
            slug=row.get("slug", row.get("model", "")),
            title=row.get("title", ""),
            provider=row.get("provider", ""),
            task_types=list(row.get("taskType") or []),
            pricing_desc=row.get("pricingDesc"),
            description=row.get("description"),
        )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class KieClient:
    """Video/image/audio/LLM provider for Kie.ai (per kie-models skill)."""

    name = "kie"

    def __init__(self, api_key: str | None = None,
                 base_url: str = KIE_BASE_URL,
                 upload_base: str = KIE_UPLOAD_BASE,
                 download_to: Path | None = None,
                 request_timeout_sec: int = 30) -> None:
        import os
        self._api_key = api_key or os.environ.get("KIE_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._upload_base = upload_base.rstrip("/")
        self._download_to = download_to or KIE_DOWNLOAD_DIR
        self._download_to.mkdir(parents=True, exist_ok=True)
        self._timeout = request_timeout_sec
        # Three rate-limit pools per skill docs
        self._rl_discovery = _RateLimiter(1.1)   # 1/sec shared
        self._rl_create = _RateLimiter(0.5)      # 20/10s = 0.5s
        # Per-task poll limiter so we don't blow past 10/sec on a single task
        self._last_poll_per_task: dict[str, float] = {}

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        })

    # ---- availability ----

    def is_available(self) -> bool:
        return bool(self._api_key)

    # ---- low-level transport ----

    def _check_envelope(self, data: dict[str, Any], ctx: str) -> dict[str, Any]:
        code = data.get("code")
        if code is None:
            raise KieError(f"{ctx}: no 'code' in response: {data!r}")
        if code not in (200, 0):
            msg = data.get("msg", "")
            exc = _CODE_TO_EXC.get(code, KieError)
            raise exc(f"{ctx}: code={code} msg={msg}", code=code)
        return data.get("data", {})

    def _get(self, path: str, params: dict[str, Any] | None = None,
             rate: _RateLimiter | None = None) -> dict[str, Any]:
        if rate:
            rate.wait()
        url = f"{self._base_url}{path}"
        resp = self._session.get(url, params=params, timeout=self._timeout)
        # Skill says: HTTP 200 can still have code≠200 in body
        resp.raise_for_status()
        return self._check_envelope(resp.json(), path)

    def _post(self, path: str, payload: dict[str, Any],
              rate: _RateLimiter | None = None,
              base: str | None = None) -> dict[str, Any]:
        if rate:
            rate.wait()
        url = f"{base or self._base_url}{path}"
        resp = self._session.post(url, json=payload, timeout=self._timeout)
        resp.raise_for_status()
        return self._check_envelope(resp.json(), path)

    # ---- discovery (skill: §发现模型) ----

    def list_models(self, task_type: str | None = None,
                    provider: str | None = None,
                    q: str | None = None) -> list[ModelInfo]:
        """§查询目录. taskType may be comma-separated; SPACES MUST be %20-encoded."""
        params: dict[str, str] = {}
        if task_type:
            params["taskType"] = task_type.replace(" ", "%20")
        if provider:
            params["provider"] = provider
        if q:
            params["q"] = q
        data = self._get("/api/v1/models", params, rate=self._rl_discovery)
        return [ModelInfo.from_api(m) for m in data.get("models", [])]

    def get_model_schema(self, model: str) -> dict[str, Any] | None:
        """§读 schema. Returns the OpenAPI doc dict, or None if not synced."""
        data = self._get(f"/api/v1/models/{model}/schema", rate=self._rl_discovery)
        return data.get("openapi")

    def get_model_price(self, model: str) -> dict[str, Any]:
        return self._get(f"/api/v1/models/{model}/price", rate=self._rl_discovery)

    def get_model_success_rate(self, model: str) -> dict[str, Any]:
        return self._get(f"/api/v1/models/{model}/success-rate", rate=self._rl_discovery)

    def get_credit_balance(self) -> float:
        """§查余额. Returns numeric balance; raise on 402."""
        data = self._get("/api/v1/chat/credit", rate=self._rl_discovery)
        return float(data) if isinstance(data, (int, float)) else 0.0

    # ---- upload (skill: §图/视频模型的文件上传) ----

    def upload_base64(self, data_b64_or_data_url: str,
                      upload_path: str = "images/user-uploads",
                      file_name: str | None = None) -> str:
        """POST /api/file-base64-upload (≤10MB). Returns downloadUrl."""
        payload: dict[str, Any] = {
            "base64Data": data_b64_or_data_url,
            "uploadPath": upload_path,
        }
        if file_name:
            payload["fileName"] = file_name
        data = self._post("/api/file-base64-upload", payload, base=self._upload_base)
        return data["downloadUrl"]

    def upload_file(self, file_path: str | Path,
                    upload_path: str = "images/user-uploads",
                    file_name: str | None = None) -> str:
        """POST /api/file-stream-upload (>10MB, multipart). Returns downloadUrl."""
        url = f"{self._upload_base}/api/file-stream-upload"
        with open(file_path, "rb") as f:
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {self._api_key}"},
                files={"file": (file_name or Path(file_path).name, f)},
                data={"uploadPath": upload_path, **({"fileName": file_name} if file_name else {})},
                timeout=self._timeout,
            )
        resp.raise_for_status()
        data = self._check_envelope(resp.json(), "/api/file-stream-upload")
        return data["downloadUrl"]

    def upload_url(self, source_url: str,
                   upload_path: str = "images/downloaded",
                   file_name: str | None = None) -> str:
        """POST /api/file-url-upload (re-host a public URL on KIE CDN)."""
        payload: dict[str, Any] = {"fileUrl": source_url, "uploadPath": upload_path}
        if file_name:
            payload["fileName"] = file_name
        data = self._post("/api/file-url-upload", payload, base=self._upload_base)
        return data["downloadUrl"]

    # ---- task lifecycle (skill: §调用模型 / §取结果) ----

    def submit(self, req: GenerationRequest) -> str:
        """§创建任务. Builds a {model, input} payload from GenerationRequest.
        Schema-aware: calls /api/v1/models/<model>/schema and inspects `input`
        to know the right field name for the reference image (image_url vs
        input_image vs first_frame_image, etc.).
        """
        if not self.is_available():
            raise KieError("KIE_API_KEY not set")

        # Resolve input field names from schema (per skill rule 2)
        schema = self.get_model_schema(req.model_id)
        input_field_names: set[str] = set()
        uses_create_task = True
        if schema:
            paths = schema.get("paths") or {}
            uses_create_task = "/api/v1/jobs/createTask" in paths
            # Find the createTask POST operation's request body schema
            op = paths.get("/api/v1/jobs/createTask", {}).get("post")
            if op:
                rb = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
                # $ref resolution: keep it simple — one level of indirection
                ref = rb.get("$ref", "")
                if ref.startswith("#/components/schemas/"):
                    name = ref.rsplit("/", 1)[-1]
                    comp = (schema.get("components", {}).get("schemas", {}) or {}).get(name, {})
                    # The body schema has 'input' field — its own schema has the per-model fields
                    input_ref = (comp.get("properties", {}).get("input", {}).get("$ref") or "")
                    if input_ref.startswith("#/components/schemas/"):
                        input_name = input_ref.rsplit("/", 1)[-1]
                        input_schema = (schema.get("components", {}).get("schemas", {}) or {}).get(input_name, {})
                        for fname in (input_schema.get("properties") or {}):
                            input_field_names.add(fname)

        if not uses_create_task:
            raise KieError(
                f"Model {req.model_id!r} is synchronous (not /api/v1/jobs/createTask). "
                "Use the path defined in its schema. (Not implemented in this client yet.)"
            )

        # Build input dict from GenerationRequest
        input_obj: dict[str, Any] = {
            "prompt": req.prompt,
            "duration": str(req.duration_sec),
            "aspect_ratio": req.aspect_ratio,
        }
        if req.resolution:
            input_obj["resolution"] = req.resolution
        if req.seed is not None:
            input_obj["seed"] = req.seed

        # Reference image: figure out the right field name from schema
        if req.reference_image:
            ref = req.reference_image if isinstance(req.reference_image, str) \
                  else str(req.reference_image)
            if not (ref.startswith("http://") or ref.startswith("https://")):
                raise ValueError(
                    "reference_image must be an http(s) URL string. "
                    "For local files, call upload_file()/upload_base64() first. "
                    f"Got: {ref!r}"
                )
            # Common field names; pick the first that appears in schema
            for candidate in ("image_url", "input_image", "image",
                              "first_frame_image", "video_url"):
                if candidate in input_field_names:
                    input_obj[candidate] = ref
                    break
            else:
                if input_field_names:
                    raise KieError(
                        f"Schema for {req.model_id!r} doesn't expose any known "
                        f"reference-image field. Known input fields: "
                        f"{sorted(input_field_names)}"
                    )
                # No schema? Best-effort: image_url
                input_obj["image_url"] = ref

        # Pass-through extra fields
        for k, v in (req.extra or {}).items():
            input_obj[k] = v

        data = self._post(
            "/api/v1/jobs/createTask",
            {"model": req.model_id, "input": input_obj},
            rate=self._rl_create,
        )
        task_id = data.get("taskId")
        if not task_id:
            raise KieError(f"No taskId in createTask response: {data!r}")
        return task_id

    def poll(self, job_id: str) -> GenerationResult:
        # Per-task 10/sec limit
        now = time.monotonic()
        last = self._last_poll_per_task.get(job_id, 0.0)
        if now - last < 0.1:
            time.sleep(0.1 - (now - last))
        self._last_poll_per_task[job_id] = time.monotonic()

        data = self._get("/api/v1/jobs/recordInfo",
                         {"taskId": job_id}, rate=self._rl_discovery)
        return self._data_to_result(data, job_id)

    def wait(self, job_id: str, timeout_sec: int = 600, poll_interval_sec: int = 3) -> GenerationResult:
        # Skill recommends 3s interval; recordInfo is rate-limited at 10/sec per task.
        deadline = time.monotonic() + timeout_sec
        last = GenerationResult(success=False, error="pending", provider_job_id=job_id)
        while time.monotonic() < deadline:
            last = self.poll(job_id)
            if last.success or (last.error and last.error not in ("pending", None)):
                return last
            time.sleep(poll_interval_sec)
        if last.error is None:
            last = self.poll(job_id)
        last.error = last.error or "timeout"
        last.success = False
        return last

    def _data_to_result(self, data: dict[str, Any], job_id: str) -> GenerationResult:
        state = (data.get("state") or "").lower()
        model = data.get("model", "")
        cost_time_ms = data.get("costTime")
        credits = data.get("creditsConsumed")

        if state in ("waiting", "queuing", "generating"):
            return GenerationResult(
                success=False, error="pending",
                provider_job_id=job_id, model_id=model, raw=data,
            )

        if state == "fail":
            return GenerationResult(
                success=False,
                error=data.get("failMsg") or "kiefail",
                provider_job_id=job_id, model_id=model, raw=data,
            )

        if state == "success":
            # Prefer parsed `response`; fall back to resultJson
            response = data.get("response")
            if response is None and data.get("resultJson"):
                try:
                    response = json.loads(data["resultJson"])
                except json.JSONDecodeError:
                    response = {}
            response = response or {}

            # Most models: response.resultUrls[]
            urls = response.get("resultUrls") or []
            remote = urls[0] if urls else None
            local = None
            if remote:
                try:
                    local = self._download(remote, job_id)
                except Exception as e:  # noqa: BLE001
                    return GenerationResult(
                        success=False, error=f"download_failed: {e}",
                        provider_job_id=job_id, remote_url=remote,
                        model_id=model, raw=data,
                    )
            return GenerationResult(
                success=True,
                video_path=local, remote_url=remote,
                provider_job_id=job_id, model_id=model, raw=data,
                cost_credits=float(credits) if credits is not None else None,
                latency_sec=float(cost_time_ms) / 1000.0 if cost_time_ms is not None else None,
            )

        return GenerationResult(
            success=False, error=f"unknown_state:{state}",
            provider_job_id=job_id, model_id=model, raw=data,
        )

    def _download(self, url: str, job_id: str) -> Path:
        # Result URLs valid 14d. Download synchronously to local cache.
        ext = ".mp4"
        for e in (".webm", ".mov", ".mp4", ".png", ".jpg", ".jpeg", ".wav", ".mp3"):
            if url.lower().split("?")[0].endswith(e):
                ext = e
                break
        dest = self._download_to / f"{job_id}{ext}"
        if dest.exists() and dest.stat().st_size > 0:
            return dest
        with self._session.get(url, stream=True, timeout=self._timeout) as r:
            r.raise_for_status()
            # Atomic: the body lands in a temp sibling and is renamed into
            # place only after the transfer completes. A partial file is never
            # published under the final name, so the cache hit above can only
            # ever return a complete download.
            return atomic_download(r, dest, chunk_size=1 << 20)


__all__ = [
    "KieClient", "KieError",
    "KieAuthError", "KieCreditError", "KieNotFoundError",
    "KieValidationError", "KieRateLimitError", "KieSubKeyLimitError",
    "KieUnavailableError", "ModelInfo",
    "KIE_BASE_URL", "KIE_UPLOAD_BASE",
]
