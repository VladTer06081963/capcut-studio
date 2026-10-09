# library/

Growing asset base shared across all shows. Every clip that goes into an
episode lives here first. **Library is the source of truth** — episodes
reference library clips by ID + sha256.

## Layout

```
library/
├─ ai/                          ← AI-generated (H3.0, Qwen-Image)
│  ├─ characters/<slug>/
│  │  ├─ reference.png          ← first frame, used as H3.0 init image
│  │  ├─ walk.mp4               ← behavior template (4-6 sec)
│  │  ├─ talk.mp4
│  │  ├─ sit.mp4
│  │  └─ *.meta.json
│  ├─ scenes/<slug>/
│  │  ├─ wide.mp4
│  │  ├─ medium.mp4
│  │  └─ *.meta.json
│  └─ other/                    ← misc AI clips (intro cards, transitions)
│
├─ stock/                       ← downloaded from external sources
│  ├─ youtube/<id>.mp4  + metadata.json     ← primary (UA-friendly)
│  ├─ coverr/<id>.mp4   + metadata.json     ← secondary (UA-friendly)
│  ├─ mixkit/<id>.mp4   + metadata.json     ← tertiary (UA, scrape-based)
│  ├─ archive/<id>.mp4   + metadata.json    ← fallback (public domain)
│  ├─ pixabay/<id>.mp4  + metadata.json     ← blocked from UA
│  ├─ pexels/<id>.mp4   + metadata.json     ← blocked from UA
│  └─ recorded/<date>-<slug>.mp4  + metadata.json
│
├─ index.sqlite                 ← embeddings + tags (BLIP-2 + CLIP)
└─ .tmp/                        ← staging area for in-progress downloads
```

## metadata.json schema

Every clip in the library has a sibling `*.meta.json`:

```json
{
  "id": "ai:reznik:walk",
  "source": "ai",                            // ai | pixabay | pexels | youtube | recorded
  "model": "minimax-h3-max",                 // provider / generator
  "seed": 42,
  "prompt": "...",
  "negative_prompt": "...",
  "duration_sec": 5.2,
  "resolution": "1920x1080",
  "fps": 24,
  "character_ref": "ai:reznik:reference.png",
  "scene_ref": "ai:pripyat-riverbank:wide",
  "tags": ["reznik", "stalker", "walk", "evening"],
  "license": "self",                         // self | pixabay | pexels | youtube-cc | etc.
  "attribution": null,                       // required for stock sources
  "created_at": "2026-10-09T21:00:00Z",
  "sha256": "abc123..."                      // of the .mp4 file
}
```

`source: ai` with `license: self` is the only path that requires no
attribution. Stock sources need `attribution` filled.

## index.sqlite schema

```sql
CREATE TABLE clips (
  id          TEXT PRIMARY KEY,        -- matches metadata.json "id"
  path        TEXT NOT NULL,
  sha256      TEXT NOT NULL,
  source      TEXT NOT NULL,
  model       TEXT,
  caption     TEXT,                    -- BLIP-2 generated
  embedding   BLOB,                    -- CLIP vector (384-dim bge-small)
  tags        TEXT,                    -- JSON array
  duration_sec REAL,
  created_at  TEXT
);

CREATE INDEX idx_clips_source ON clips(source);
CREATE INDEX idx_clips_tags ON clips(tags);
```

## How a clip gets into the library

**AI path** (cron/nightly.sh):
1. Read `bible/character-<slug>.md` for reference + seed + prompt suffix
2. Call MiniMax H3.0 / H3 Max with reference image + sample prompt
3. Save MP4 to `library/ai/characters/<slug>/<action>.mp4`
4. Write `<action>.meta.json`
5. Re-index (BLIP-2 caption + CLIP embedding) → update `index.sqlite`

**Stock path** (one script per source):
1. `scripts/ingest_youtube.py` — YouTube Data API v3 search → download via yt-dlp
2. `scripts/ingest_coverr.py` — Coverr API → direct MP4 download
3. `scripts/ingest_mixkit.py` — Mixkit HTML scrape (no public API)
4. `scripts/ingest_archive.py` — Archive.org advancedsearch API → derivative MP4
5. `scripts/ingest_pixabay.py` — Pixabay API (skipped if blocked)
6. `scripts/ingest_pexels.py` — Pexels API (skipped if blocked)

For each result:
1. Download MP4 to `library/stock/<source>/<id>.mp4`
2. Probe with ffmpeg: duration, resolution, fps
3. Compute sha256
4. Write `metadata.json` with `attribution` from source
5. Index

## How a clip gets matched to an episode

1. `scripts/assemble_episode.py` reads `spec.json`
2. For each scene, computes a text query from scene description
3. Embeds query via CLIP, runs similarity search in `index.sqlite`
4. Ranks candidates; prefers `source: ai` for hero scenes,
   `source: stock` for B-roll
5. Writes `matched.json` with chosen clip IDs

## Library hygiene

- **Never delete a clip that an episode references.** Episodes hold the
  reference; if you must remove, set `clips.archived_at` first and run
  a sanity check across all `matched.json`.
- **Reindex periodically.** If you regenerate a clip with the same ID
  and sha256, no action needed. If sha256 changes, the index row is
  updated but every `matched.json` referencing the old sha breaks.
  Resolve before commit.
- **Cost cap.** `cron/nightly.sh` reads `DAILY_AI_BUDGET_USD` from `.env`
  and aborts above the cap. Adjust in `.env` before scaling up.