#!/usr/bin/env python3
"""Generate AI clips for an episode using Kie.ai.

Reads spec.json, finds scenes requesting 'ai' source, and generates them using
the KieClient (text-to-video). Saves them to library/ai/scenes/<show>/ and
creates metadata.json.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow running scripts without `PYTHONPATH=.`
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from capcut.episode.spec_writer import load_spec
from capcut.lib.config import LIBRARY_ROOT, SERIALS_ROOT
from capcut.lib.media import metadata_path_for
from capcut.render.base import GenerationRequest
from capcut.render.kie_client import KieClient

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AI clips via Kie.ai")
    parser.add_argument("--serial", required=True, help="show slug")
    parser.add_argument("--ep", required=True, help="episode id")
    parser.add_argument("--model", default="bytedance/v1-lite-text-to-video", help="Kie model id")
    args = parser.parse_args()

    ep_dir = SERIALS_ROOT / args.serial / args.ep
    spec_path = ep_dir / "spec.json"
    if not spec_path.exists():
        print(f"ERROR: {spec_path} not found.", file=sys.stderr)
        return 1

    spec = load_spec(spec_path)
    client = KieClient()
    
    out_dir = LIBRARY_ROOT / "ai" / "scenes" / args.serial
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating clips for {args.serial}/{args.ep} using {args.model}")

    for scene in spec.scenes:
        if scene.preferred_source != "ai" and scene.preferred_source != "any":
            continue
        if scene.track != "video":
            continue

        clip_id = f"ai:{args.serial}:{args.ep}-s{scene.n:02d}"
        file_name = f"{args.ep}-s{scene.n:02d}"
        mp4_path = out_dir / f"{file_name}.mp4"
        # The indexer reads `<name>.mp4.metadata.json` — the same convention
        # every ingest module writes. Writing `<name>.meta.json` here made
        # every AI clip index as `metadata={}`: no source, no license, no
        # tags, and `source_filter="ai"` could never match it.
        meta_path = metadata_path_for(mp4_path)

        # Clips generated before the convention switch carry the legacy
        # `<name>.meta.json` sibling. Migrate it first: without this the
        # skip check below fails, the clip is regenerated — and that is a
        # paid call — and shutil.move() then overwrites the existing mp4.
        if not meta_path.exists():
            legacy = mp4_path.with_suffix(mp4_path.suffix + ".meta.json")
            if legacy.exists():
                legacy.rename(meta_path)
                print(f"Scene {scene.n}: migrated legacy metadata file.")

        if mp4_path.exists() and meta_path.exists():
            print(f"Scene {scene.n} ({clip_id}) already exists, skipping.")
            continue

        prompt = f"{spec.title}. {spec.summary}. Scene description: {scene.query}. Cinematic, highly detailed, 4k."
        print(f"\n--- Scene {scene.n} ---")
        print(f"Prompt: {prompt}")

        req = GenerationRequest(
            prompt=prompt,
            model_id=args.model,
            duration_sec=min(scene.duration_sec, 5),
            aspect_ratio="16:9",
            resolution=None,
        )
        
        try:
            job_id = client.submit(req)
            print(f"Submitted. Job ID: {job_id}")
            result = client.wait(job_id, timeout_sec=600, poll_interval_sec=5)
            
            if not result.success:
                print(f"❌ Failed: {result.error}")
                continue
                
            print(f"✅ Success! Credits consumed: {result.cost_credits}")
            print(f"Downloaded to temp: {result.video_path}")
            
            # Move to library
            import shutil
            shutil.move(str(result.video_path), str(mp4_path))
            print(f"Saved to {mp4_path}")
            
            # Write metadata
            meta = {
                "id": clip_id,
                "source": "ai",
                "model": args.model,
                "seed": 0,
                "prompt": prompt,
                "duration_sec": req.duration_sec,
                "resolution": "1920x1080",
                "character_ref": scene.character_ref,
                "scene_ref": scene.scene_ref,
                "tags": scene.tags,
                "license": "self",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            meta_path.write_text(json.dumps(meta, indent=2))
            print(f"Wrote metadata to {meta_path}")
            
        except Exception as e:
            print(f"❌ Error generating scene {scene.n}: {e}")

    print("\nGeneration complete. Remember to run scripts/index_library.py to add these to index.sqlite!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
