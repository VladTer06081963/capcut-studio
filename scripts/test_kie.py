#!/usr/bin/env python3
"""Smoke test for the Kie.ai video provider (per kie-models skill).

Run after exporting KIE_API_KEY in the environment (or after putting it in
.env and sourcing it). This exercises:

    1. get_credit_balance()
    2. list_models()  — discovery (the 1 req/sec shared pool)
    3. get_model_schema() — schema lookup for the chosen model
    4. submit + wait — actual generation (~$0.05-$0.50 depending on model)

Set KIE_SMOKE=0 to skip the actual generation and only exercise discovery.

Usage:
    KIE_API_KEY=*** python3 scripts/test_kie.py
    KIE_SMOKE=0 python3 scripts/test_kie.py
    KIE_MODEL=kling/v2-1-master-text-to-video python3 scripts/test_kie.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Make `py` importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from capcut.lib import config  # noqa: E402
from capcut.render import KieClient  # noqa: E402
from capcut.render.base import GenerationRequest  # noqa: E402


def main() -> int:
    print("=== Kie.ai smoke test ===")
    print(f"KIE_API_KEY configured: {config.has_kie()}")
    print(f"KIE_BASE_URL: {config.KIE_BASE_URL}")
    print(f"DEFAULT_VIDEO_PROVIDER: {config.DEFAULT_VIDEO_PROVIDER}")
    print(f"DEFAULT_VIDEO_FALLBACK: {config.DEFAULT_VIDEO_FALLBACK}")
    print()

    if not config.has_kie():
        print("ERROR: KIE_API_KEY not set.")
        print("  1) Sign up at https://kie.ai (credit-based)")
        print("  2) Add KIE_API_KEY=... to .env (or export it)")
        print("  3) Re-run this script")
        return 1

    client = KieClient(api_key=config.KIE_API_KEY)

    # Balance check
    try:
        bal = client.get_credit_balance()
        print(f"Account balance: {bal} credits")
    except Exception as e:
        print(f"Could not fetch balance: {e}")

    # Discovery — find a few text-to-video models
    print()
    print("Discovering Text-to-Video models (1 req/sec shared pool)...")
    try:
        models = client.list_models(task_type="Text%20to%20Video")
        print(f"Found {len(models)} text-to-video models. First 5:")
        for m in models[:5]:
            print(f"  {m.model:<40} [{m.provider}] {m.pricing_desc or ''}")
    except Exception as e:
        print(f"list_models failed: {e}")
        return 2

    if not models:
        print("No video models returned. Check your account tier.")
        return 2

    # Pick a model: from env, else first Kling (cheap + reliable)
    chosen_id = os.environ.get("KIE_MODEL")
    if not chosen_id:
        kling = next((m for m in models if "kling" in m.model.lower()), None)
        chosen_id = kling.model if kling else models[0].model
    print(f"\nChosen model: {chosen_id}")

    # Schema check
    try:
        schema = client.get_model_schema(chosen_id)
        if schema is None:
            print(f"  schema=None (not yet synced for {chosen_id})")
        else:
            paths = list((schema.get("paths") or {}).keys())
            print(f"  schema OK, paths: {paths}")
    except Exception as e:
        print(f"  schema fetch failed: {e}")

    if os.environ.get("KIE_SMOKE") == "0":
        print("\nKIE_SMOKE=0 → skipping actual generation.")
        return 0

    # Submit a real generation
    print(f"\nSubmitting generation (prompt: a single leaf in golden light)...")
    req = GenerationRequest(
        prompt="A single leaf falling slowly in golden-hour light, "
               "shallow depth of field, cinematic, no text",
        model_id=chosen_id,
        duration_sec=5,           # 5s is supported by most models; cost-cheapest
        aspect_ratio="16:9",
    )
    t0 = time.monotonic()
    try:
        job_id = client.submit(req)
    except Exception as e:
        print(f"submit failed: {e!s}")
        return 3
    print(f"  taskId: {job_id}")
    print("  Polling (max 300s, 3s interval)...")
    result = client.wait(job_id, timeout_sec=300, poll_interval_sec=3)
    dt = time.monotonic() - t0
    if result.success:
        print(f"\n✅ Success in {dt:.1f}s")
        print(f"   local: {result.video_path}")
        print(f"   remote: {result.remote_url}")
        print(f"   credits consumed: {result.cost_credits}")
    else:
        print(f"\n❌ Failed in {dt:.1f}s: {result.error}")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
