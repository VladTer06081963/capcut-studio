"""Local, one-task model approval artifacts."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

APPROVAL_ROOT = Path.home() / "Library" / "Application Support" / "capcut-studio" / "model-approvals"
APPROVAL_TTL = timedelta(minutes=30)
_ID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class ApprovalError(ValueError):
    """Raised when a model approval is invalid, expired, or already consumed."""


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def _approval_id(value: str) -> str:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise ApprovalError("Invalid approval ID")
    return str(UUID(value))


def create_approval(
    provider: str,
    model_id: str,
    task_scope: str,
    *,
    root: Path = APPROVAL_ROOT,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(provider, str) or not isinstance(model_id, str) or not isinstance(task_scope, str):
        raise ApprovalError("Provider, model ID, and task scope must be text")
    provider = provider.strip()
    model_id = model_id.strip()
    task_scope = task_scope.strip()
    if not provider or len(provider) > 80:
        raise ApprovalError("Provider is required")
    if not model_id or len(model_id) > 200:
        raise ApprovalError("Exact model ID is required")
    if not task_scope or len(task_scope) > 1000:
        raise ApprovalError("Task description is required (maximum 1000 characters)")

    created = now or datetime.now(timezone.utc)
    if created.tzinfo is None:
        raise ApprovalError("Approval timestamp must include a timezone")
    created = created.astimezone(timezone.utc)
    expires = created + APPROVAL_TTL
    artifact = {
        "id": str(uuid4()),
        "provider": provider,
        "model_id": model_id,
        "task_scope": task_scope,
        "approved_at": created.isoformat(),
        "expires_at": expires.isoformat(),
        "state": "pending",
    }

    pending_dir = root / "pending"
    _ensure_private_dir(root)
    _ensure_private_dir(pending_dir)
    path = pending_dir / f"{artifact['id']}.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(artifact, output, ensure_ascii=False, indent=2)
            output.write("\n")
    except Exception:
        path.unlink(missing_ok=True)
        raise
    path.chmod(0o600)
    return artifact


def _atomic_archive(artifact: dict[str, Any], target_dir: Path) -> None:
    _ensure_private_dir(target_dir)
    artifact_path = target_dir / f"{artifact['id']}.json"
    fd, temp_name = tempfile.mkstemp(prefix=".approval-", dir=target_dir)
    temp_path = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(artifact, output, ensure_ascii=False, indent=2)
            output.write("\n")
        os.link(temp_path, artifact_path)
    except FileExistsError as exc:
        raise ApprovalError("Approval was already claimed") from exc
    finally:
        temp_path.unlink(missing_ok=True)


def _create_claim_marker(approval_id: str, claimed_at: datetime, root: Path) -> None:
    claim_dir = root / "claims"
    _ensure_private_dir(claim_dir)
    marker = claim_dir / f"{approval_id}.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(marker, flags, 0o600)
    except FileExistsError as exc:
        raise ApprovalError("Approval was already claimed") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump({"id": approval_id, "claimed_at": claimed_at.isoformat()}, output)
        output.write("\n")


def claim_approval(
    approval_id: str,
    provider: str,
    model_id: str,
    task_scope: str,
    *,
    root: Path = APPROVAL_ROOT,
    now: datetime | None = None,
) -> dict[str, Any]:
    approval_id = _approval_id(approval_id)
    pending_path = root / "pending" / f"{approval_id}.json"
    try:
        artifact = json.loads(pending_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ApprovalError("Approval does not exist or was already claimed") from exc

    if artifact.get("id") != approval_id:
        raise ApprovalError("Approval ID does not match artifact")
    if artifact.get("provider") != provider or artifact.get("model_id") != model_id:
        raise ApprovalError("Provider/model do not match the approved selection")
    if artifact.get("task_scope") != task_scope:
        raise ApprovalError("Task does not match the approved scope")

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ApprovalError("Claim timestamp must include a timezone")
    current = current.astimezone(timezone.utc)
    expires = datetime.fromisoformat(artifact["expires_at"])
    _create_claim_marker(approval_id, current, root)
    if current >= expires:
        artifact["state"] = "expired"
        artifact["expired_at"] = current.isoformat()
        _atomic_archive(artifact, root / "expired")
        pending_path.unlink(missing_ok=True)
        raise ApprovalError("Approval has expired")

    artifact["state"] = "consumed"
    artifact["consumed_at"] = current.isoformat()
    _atomic_archive(artifact, root / "consumed")
    pending_path.unlink(missing_ok=True)
    return artifact
