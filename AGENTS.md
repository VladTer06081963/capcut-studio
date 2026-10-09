# AGENTS.md

Pipeline for producing long-form video series: brief → asset library → spec → assemble → polish.

Sister project to `comic-studio/`. Same lifecycle discipline (lifecycle as files on
disk, approval as persisted artifact, revise/remix for non-destructive iteration),
adapted from comics to video. Library-first: assets are pre-generated and indexed,
episodes are assembled from the library, not freshly generated per scene.

## Setup

```bash
# Python (3.11+)
python3 -m venv .venv
source .venv/bin/activate
pip install -r py/requirements.txt   # to be added in step 2

# Node sub-packages — no workspaces, install each
(cd mcp-server && npm install)      # to be added in step 3

cp .env.example .env   # fill MINIMAX_API_KEY + OPENROUTER_API_KEY at minimum
```

## Run

| Service | Command | Default bind |
|---|---|---|
| MCP server | `node mcp-server/index.js` | stdio |
| Ingest library | `python scripts/ingest_pixabay.py --query "..."` | — |
| Index library | `python scripts/index_library.py` | LM Studio at `$LM_STUDIO_URL` |
| Assemble episode | `python scripts/assemble_episode.py --serial <slug> --ep <id>` | — |
| Nightly batch (dry) | `bash cron/nightly.sh --dry-run` | — |

External services used:
- **MiniMax Plus** (cloud) — `py/render/minimax_client.py` for H3.0/H3 Max video gen
- **OpenRouter** — `py/render/openrouter_client.py` for Qwen3-Max text + Qwen-Image
- **Pixabay / Pexels / YouTube** — `py/ingest/` for stock library
- **LM Studio** (local, WireGuard) — `py/index/` for BLIP-2 / CLIP embeddings
- **Concat** (Mac Studio, MCP) — auto-compose timeline
- **CapCut / DaVinci Resolve** (MacBook Pro, Thunderbolt) — manual polish

## Project layout

```
capcut-studio/
├─ AGENTS.md
├─ README.md
├─ .env.example
├─ bible/                        ← frozen templates (one per show + character)
│  ├─ _TEMPLATE_show.md
│  ├─ _TEMPLATE_character.md
│  └─ <show-slug>.md             ← real shows
├─ library/                      ← growing asset base (shared across shows)
│  ├─ ai/                        ← AI-generated (H3.0, Qwen-Image)
│  │  ├─ characters/<slug>/*.mp4
│  │  └─ scenes/<slug>/*.mp4
│  ├─ stock/                     ← downloaded from Pixabay / Pexels / YouTube
│  │  └─ <source>/<id>.mp4 + metadata.json
│  ├─ index.sqlite               ← embeddings + tags
│  └─ README.md
├─ serials/<show-slug>/          ← output, one dir per show
│  ├─ episode-log.md             ← continuity chronicle
│  └─ <ep-id>-<slug>/            ← flexible id (linear: ep-XX; season-XX: sXXeXX)
│     ├─ brief.md
│     ├─ spec.json               ← declarative episode spec (output of LLM)
│     ├─ matched.json            ← which library clips were picked
│     └─ rendered/
│        ├─ draft.json           ← Concat draft
│        ├─ preview.mp4
│        └─ final.mp4
├─ py/
│  ├─ ingest/                    ← stock downloaders (pexels.py, pixabay.py, youtube.py)
│  ├─ episode/                   ← script → spec.json (LLM)
│  ├─ render/                    ← MiniMax + OpenRouter clients, provider_router
│  ├─ index/                     ← BLIP-2 / CLIP embedder
│  ├─ search/                    ← embedding search → ranked candidates
│  ├─ assemble/                  ← spec.json + matched.json → Concat draft
│  └─ lib/                       ← config, lifecycle, logging
├─ mcp-server/                   ← exposes tools to Hermes / Mavis
├─ scripts/                      ← CLI entry points (Python)
├─ cron/                         ← nightly batch (asset gen, ingest, reindex)
├─ openspec/                     ← in-flight spec changes (mirror comic-studio)
├─ tests/                        ← Python unittest
└─ docs/
```

## Code style

- Python 3.11+, ESM Node.js (each sub-package uses `"type": "module"`).
- Match neighbouring files; no formatter/linter configured.
- TypeScript not used. Plain `.js` and `.py`.

## Project invariants (read before changing anything)

- **Library is the source of truth.** Episodes reference library clips by ID +
  sha256 of source file. If the file changes, the reference breaks loudly.
- **Lifecycle as files on disk.** Episodes live in `serials/<show>/<ep-id>/`
  with sentinel files (`.draft`, `.approved`) and `rendered/`. State is never
  in memory.
- **Approval gate.** Auto-assembly requires `.approved` sentinel in the
  episode dir. No sentinel → no render.
- **Idempotency.** Use episode id + asset sha. Re-running `assemble_episode`
  on an already-rendered episode without explicit `--force` is a no-op.
- **Updates only via revise / remix.**
  - `draft` / `approved` → `revise` (regenerate spec.json from brief, atomic approval revoke)
  - `rendered` → `remix` (creates new episode with `remix_of`)
- **`rendered/final.mp4` is immutable.** Never edit, delete, or re-render.
  New edits produce a remix.
- **`library/index.sqlite` is shared.** All episodes read it. Index updates
  must be additive (new rows); deletes only via explicit GC.
- **Source attribution mandatory.** Every asset in `library/` carries
  `source` in `metadata.json`: `"ai"`, `"pixabay"`, `"pexels"`, `"youtube"`,
  `"recorded"`. License metadata required for non-ai sources.

## Series workflow

```
bible/<show-slug>.md
    ↓ frozen style + cast
cron/nightly.sh
    ↓ generates library/ai/{characters,scenes}/*.mp4
scripts/ingest_pixabay.py
    ↓ B-roll into library/stock/pixabay/*.mp4
scripts/index_library.py
    ↓ BLIP-2 / CLIP → library/index.sqlite
brief.md
    ↓ Hermes / Qwen3-Max
spec.json
    ↓ matcher (embedding search)
matched.json
    ↓ Concat MCP
draft.json + preview.mp4
    ↓ human review + .approved sentinel
scripts/render_episode.py
    ↓ MiniMax H3.0 (only for clips library doesn't have) + assemble
rendered/final.mp4
    ↓ append to episode-log.md
next episode
```

**Continuity check (spec-level):** before approving a new episode, the
`@episode-writer` agent must diff against `episode-log.md` and the show bible,
and flag inconsistencies (location, props, character state, timeline).

## Asset library schema

```
library/
  ai/characters/<slug>/
      walk.mp4          + .meta.json
      talk.mp4          + .meta.json
      sit.mp4           + .meta.json
      fight.mp4         + .meta.json
      reference.png     (first frame of walk — used as H3.0 reference image)
  ai/scenes/<slug>/
      wide.mp4          + .meta.json
      medium.mp4        + .meta.json
      close.mp4         + .meta.json
  stock/pixabay/<id>.mp4  + metadata.json
  stock/pexels/<id>.mp4   + metadata.json
  stock/youtube/<id>.mp4  + metadata.json
```

`metadata.json` (per clip):
```json
{
  "id": "ai:reznik:walk",
  "source": "ai",
  "model": "minimax-h3-max",
  "seed": 42,
  "prompt": "...",
  "duration_sec": 5,
  "resolution": "1920x1080",
  "character_ref": "ai:reznik:reference.png",
  "scene_ref": "ai:pripyat-evening:wide",
  "tags": ["reznik", "stalker", "walk", "evening"],
  "license": "self",
  "created_at": "2026-10-09T..."
}
```

`library/index.sqlite` (BLIP-2 caption + CLIP embedding per clip):
```
clips(id, path, sha256, source, model, caption, embedding BLOB, tags JSON)
```

## AI providers

- **Default video:** `minimax-h3-max` (cloud) via `py/render/minimax_client.py`.
  Override per-scene in `spec.json` (`provider`, `model`).
- **Default text:** `qwen3-max` via OpenRouter subscription.
- **Default image:** `qwen-image` via OpenRouter (used for character
  reference sheets that get fed to H3.0 as init images).
- **Fallback B-roll:** stock (Pixabay). When matcher cannot find an
  adequate AI clip, it falls back to stock and tags the result
  `source: stock` in `matched.json`.

**Auto-fallback chain:**
1. AI clip from library (exact character/scene match)
2. AI clip from library (close match — different scene, same character)
3. Stock clip (Pexels/Pixabay by visual embedding)
5. Stub — Concat placeholder clip (NEVER silently, always with `warning`)

## Polishing

- **Concat MCP** (auto) — 80% of timeline work: place clips, add captions,
  add basic transitions, export draft.
- **CapCut** (MBP, manual) — when creative effect polish is needed.
- **DaVinci Resolve** (MBP, manual) — frame-by-frame fix, color grade,
  chroma key, audio sync.

## Status

R&D / prep, **not production**. Same discipline as comic-studio: lifecycle,
bible, approval gate, .env hygiene, fixation procedure. The pipeline pieces
exist; the open problems are:

- **Character consistency across AI clips** — H3.0 with reference images
  is ~85% reliable; the remaining 15% requires DaVinci touch-up.
- **Scene drift across episodes** — same setting regenerated looks 70–80%
  similar; need to test if `bible/_TEMPLATE_scene.md` recipe pins it.
- **Automated assembly quality** — Hermes matches clips; Concat places
  them; humans grade. We don't yet know how often human review is needed.

Default to R&D pace; don't push production-grade answers unless explicitly asked.

## Deployment model

**Local-first, single-machine.** Oracle is out of scope (free tier is too
limited for 24/7 cron + multi-GB library). When commercial scale justifies
it, deploy to a paid VPS (Hetzner / DO / Vultr / similar — to be picked
when needed). Until then, everything runs on Mac Studio + MacBook Pro
over Thunderbolt.

```
┌─ Mac Studio (Apple Silicon) ──────────────────────────┐
│                                                        │
│   ~/Projects/capcut-studio/   ← everything lives here │
│     ├─ py/                    ← Python pipeline        │
│     ├─ library/               ← AI + stock assets      │
│     ├─ serials/               ← episodes               │
│     ├─ index.sqlite           ← embeddings + tags      │
│     ├─ bible/                 ← frozen templates       │
│     └─ cron/ (via launchd)    ← daily batch jobs       │
│                                                        │
│   Concat.app             (auto-compose, MCP)           │
│   Hermes / Mavis Plus    (LLM orchestration)           │
│   LM Studio              (BLIP-2 / CLIP indexer)       │
│   MiniMax H3.0           (cloud, via Plus Plan)        │
│   OpenRouter / Qwen      (cloud subscription)          │
│   Pixabay / Pexels / YT  (stock APIs)                  │
│                                                        │
└────────────────────────────────────────────────────────┘
          │ Thunderbolt 40 Gb/s (read/write)
          ▼
┌─ MacBook Pro (Intel i9) ──────────────────────────────┐
│                                                        │
│   DaVinci Resolve           (frame polish)             │
│   CapCut                    (effect polish)            │
│   Lapian Notes               (story QC, emotion curve)  │
│   Concat.app                 (alt GUI composer)        │
│                                                        │
│   /Volumes/CapCut-Assets/   ← Thunderbolt share, RW   │
│   (also exposed via SMB for the user's other devices)  │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**Asset storage reality:** local disks are slow for active model loading
(see `comic-studio/AGENTS.md` → "Branch workflow" for the Mac Studio vs MBP
hardware context). Plan accordingly:

- **`library/ai/`** generated clips: write once, read many → fine on the
  Transcend 2TB HDD or internal Studio SSD
- **`library/stock/`** downloaded clips: write once, read many → same
- **`index.sqlite`**: small (~MB even for 10k clips), keep on Studio SSD
- **Active scratch space** (e.g. Concat draft exports during polish):
  Thunderbolt share on MBP, fast local edits

**When to move to VPS:** only if (a) commercial revenue justifies the
recurring cost, (b) library exceeds local storage budget, or (c) cron needs
to run when Mac Studio is asleep. None of these are blockers now.

**Cron on macOS:** use `launchd` (`.plist` in `~/Library/LaunchAgents/`),
not cron. `cron/nightly.sh` exists as the script; `cron/com.MiniMax.capcut-studio.nightly.plist`
will be the launchd wrapper when we add it.

## Image / video gen provider

Mirrors comic-studio routing but for video. Override hierarchy for video
generation:

1. CLI override (`--video-provider` flag in `scripts/`)
2. `spec.json["scenes"][i]["provider"]` (per-scene)
3. `bible/<show>.md` → `GENRE_DEFAULT` (table TBD)
4. env `DEFAULT_VIDEO_PROVIDER` (default `minimax-h3-max`)

## Fixation procedure

When the user says **«фиксируем»**, **«фиксация»**, or **«зафиксируй»**,
follow the 5-step procedure in `FIXATION.md` (mirror of comic-studio).
Numbering shared with `summary/tasks/` and `summary/audit/` (TBD).

## Branch workflow

- Branch from `main`; never push to it directly.
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`,
  `test:`.
- `openspec/` is source of truth for in-flight changes — archive when landed.

## Extension points

- New stock source → `py/ingest/<name>.py` exporting `ingest_<name>(query, **opts) -> list[Clip]`.
- New video provider → `py/render/<name>_client.py` implementing the
  `VideoProvider` protocol from `py/render/base.py`.
- New embedding model → parameterise `py/index/embedder.py`.
- New Concat transport (e.g. HTTP vs stdio) → parameterise
  `py/assemble/concat_exporter.py`.