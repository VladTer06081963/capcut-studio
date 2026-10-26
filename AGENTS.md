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
pip install -r capcut/requirements.txt

# Node sub-packages — no workspaces, install each
(cd mcp-server && npm install)

cp .env.example .env   # add only keys required for the selected, approved workflow
```

## Run

| Service | Command | Default bind |
|---|---|---|
| MCP server | `node mcp-server/index.js` | stdio |
| Ingest stock | `python scripts/ingest_youtube.py --help` (also `ingest_coverr.py`, `ingest_mixkit.py`, `ingest_archive.py`) | — |
| Index library | `python scripts/index_library.py` | LM Studio at `$LM_STUDIO_URL` |
| Assemble episode | `python scripts/assemble_episode.py --serial <slug> --ep <id>` | — |
| Nightly batch | Not implemented in the current tree (`cron/nightly.sh` is absent) | — |

External services and models are configurable and may change during evaluation:
- **Video generation:** current config default is `kie/veo-3-1` through `capcut/render/kie_client.py`; this is not a user-approved permanent production choice.
- **Text/spec writing:** local LM Studio is tried for the default model in `capcut/episode/spec_writer.py`; OpenRouter is a conditional fallback/route. Check current code and environment rather than assuming a fixed model.
- **Pixabay / Pexels / YouTube** — `capcut/ingest/` for stock library
- **LM Studio** (local, WireGuard) — `capcut/index/` for BLIP-2 / CLIP embeddings
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
│  ├─ ai/                        ← AI-generated with selected models
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
│        └─ final.mp4             ← immutable from creation by project policy
├─ capcut/
│  ├─ ingest/                    ← stock downloaders (pexels.py, pixabay.py, youtube.py)
│  ├─ episode/                   ← script → spec.json (LLM)
│  ├─ render/                    ← configurable provider clients and router
│  ├─ index/                     ← BLIP-2 / CLIP embedder
│  ├─ search/                    ← embedding search → ranked candidates
│  ├─ assemble/                  ← spec.json + matched.json → Concat draft
│  └─ lib/                       ← config, lifecycle, logging
├─ mcp-server/                   ← exposes tools to Hermes / Mavis
├─ scripts/                      ← CLI entry points (Python)
├─ cron/                         ← reserved for automation; nightly script is not currently present
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
- **Approval gate (policy).** Do not publish a final render without review and
  approval. The current `scripts/assemble_episode.py` builds a draft and does
  not enforce `.approved`; no automated final-render CLI is confirmed. Do not
  claim the approval gate is technically enforced until that path exists and
  is tested.
- **Idempotency (policy/helpers).** `capcut/lib/lifecycle.py` provides spec-hash
  helpers. The current draft assembler is not a final renderer and does not
  provide the documented `--force`/no-op contract for `final.mp4`.
- **Updates only via revise / remix.**
  - `draft` / `approved` → `revise` (regenerate spec.json from brief, atomic approval revoke)
  - `rendered` → `remix` (creates new episode with `remix_of`)
- **`rendered/final.mp4` is immutable.** Never edit, delete, or re-render.
  New edits produce a remix.
  This is the project policy from the moment the file is created; the current
  tree has no verified final-render writer enforcing this rule yet.
- **`library/index.sqlite` is shared.** All episodes read it. Index updates
  must be additive (new rows); deletes only via explicit GC.
- **Source attribution mandatory.** Every asset in `library/` carries
  `source` in `metadata.json`: `"ai"`, `"pixabay"`, `"pexels"`, `"youtube"`,
  `"recorded"`. License metadata required for non-ai sources.

## Series workflow

```
bible/<show-slug>.md
    ↓ frozen style + cast
planned automation (not implemented)
    ↓ optional, explicitly approved generation / stock ingest
library/ai/{characters,scenes}/*.mp4 + library/stock/<source>/*
scripts/index_library.py
    ↓ BLIP-2 / CLIP → library/index.sqlite
brief.md
    ↓ spec writer (local LM Studio / configured fallback)
spec.json
    ↓ matcher (embedding search)
matched.json
    ↓ Concat MCP
draft.json + preview.mp4
    ↓ human review + .approved sentinel
manual render/export workflow (no final-render CLI confirmed)
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

- **Model choice requires explicit user approval before generation.** State the provider and exact model for the requested task; proceed when the user specifies or approves that model. A default is not approval. Never silently switch to another provider/model or start an unrelated future run under a previous approval. Do not require price research, a price snapshot, output-count cap, or budget cap as a precondition. The user may check prices independently if they want to.
- **Subscription providers:** MiniMax image generation is covered by the user's subscription for this workflow. Do not query or impose provider usage limits, calculate a per-output price, or ask for a monetary/credit cap. Still obtain the user's approval of the model before generating; do not assume subscription coverage authorizes another model or unrelated task.
- Local, free-tier, and trial routes may be used for prototypes when their selected model/provider is clear. Do not silently route a failed local request to a different paid provider.
- Record provider/model, task, observed latency/quality, failures, and whether the result is prototype-only or approved for production in the relevant `summary/tasks/` or `summary/audit/` entry. Record price only when the user requests it or it is needed for a specific decision; never record credentials.
- Current implementation snapshot: `capcut/lib/config.py` sets video default
  `kie/veo-3-1`, text config value `qwen3-max`, and image config value
  `qwen-image`. These are runtime/config defaults, not approved provider
  decisions. `capcut/episode/spec_writer.py` separately defaults to
  `qwen2.5-coder-7b-instruct-mlx` and routes through local LM Studio/OpenRouter
  according to its call logic.
- Video provider selection in `capcut/render/provider_router.py` accepts per-scene
  provider/model overrides and environment defaults. Direct `minimax` backend
  is not implemented there. `DEFAULT_VIDEO_FALLBACK` exists in config, but
  `ProviderRouter.generate()` only uses the explicit fallback list passed to
  the method; do not assume the env list is automatically applied.
- These values may change as local/trial options are evaluated against cloud
  candidates for final speed and quality. See `summary/audit/` for measured
  decisions and use current code for exact runtime behavior.
- **Fallback B-roll:** stock — **UA-friendly order**:
  YouTube → Coverr → Mixkit → Archive.org. Pixabay/Pexels kept as
  skip-if-blocked fallbacks (their web returns 403 from UA; API may
  still answer with a valid key but we don't depend on them).
  When matcher cannot find an adequate AI clip, it falls back to stock
  and tags `source: stock` (with sub-source: youtube/coverr/...) in
  `matched.json`.

**Asset matching priority:** AI clip from library → stock candidate according
to source preference. Any placeholder/fallback behavior must be explicit in
the returned data; verify the current matcher/assembler before relying on a
specific chain.

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

- **Character consistency across AI clips** — historical R&D estimates cite
  H3.0/reference-image consistency, but no current stress-test evidence is
  recorded; validate before using those figures as a project baseline.
- **Scene drift across episodes** — historical estimates exist, but a current
  measured baseline and stress test are not recorded.
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
│     ├─ capcut/                    ← Python pipeline        │
│     ├─ library/               ← AI + stock assets      │
│     ├─ serials/               ← episodes               │
│     ├─ index.sqlite           ← embeddings + tags      │
│     ├─ bible/                 ← frozen templates       │
│     └─ cron/                 ← automation planned, absent│
│                                                        │
│   Concat.app             (auto-compose, MCP)           │
│   Hermes / Mavis Plus    (LLM orchestration)           │
│   LM Studio              (local text/embedding tasks)   │
│   Cloud providers        (selected per approved experiment)│
│   Local/trial models     (prototype where suitable)    │
│   Stock sources          (YouTube, Coverr, Mixkit, Archive.org)
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
not cron. Nightly automation is planned but `cron/nightly.sh` and its launchd
plist are absent from the current tree; do not document or invoke them as
available commands.

## Image / video gen provider

Mirrors comic-studio routing but for video. Override hierarchy for video
generation:

1. Per-scene `spec.json["scenes"][i]["provider"]`
2. Per-scene `model_id` shorthand
3. Caller-supplied default
4. env `DEFAULT_VIDEO_PROVIDER` (current code default: `kie/veo-3-1`)

The documented CLI and bible overrides are not confirmed in the current
router/callers. Verify an override path in code before relying on it. A
provider default or fallback never authorizes a paid generation.

## Fixation procedure

When the user says **«фиксируем»**, **«фиксация»**, or **«зафиксируй»**,
follow the 5-step procedure in `FIXATION.md` (mirror of comic-studio).
Numbering shared with `summary/tasks/` and `summary/audit/` (TBD).

## Branch workflow

- Branch from `main`; never push to it directly.
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`,
  `test:`.
- Use OpenSpec for future changes that affect multiple components, pipeline
  contracts/data formats, lifecycle/approval rules, provider architecture, or
  introduce a substantial capability. Before implementation, create
  `openspec/changes/<slug>/proposal.md` and `tasks.md`; add
  `specs/<module>/spec.md` when the change alters a module's behavior or
  contract. Keep the proposal concise and record the intended behavior,
  boundaries, and validation.
- Small, isolated fixes that do not change a contract do not need OpenSpec;
  record them in `summary/tasks/` and `summary/audit/` as appropriate.
- Do not retroactively create OpenSpec changes for work already completed.
  When an in-flight change is complete, record actual outcomes and validation
  in the summary audit, update `CHANGELOG.md` when warranted, and move the
  change directory to `openspec/changes/archive/`. `openspec/` is the source
  of truth for in-flight changes.

## Extension points

- New stock source → `capcut/ingest/<name>.py` exporting `ingest_<name>(query, **opts) -> list[Clip]`.
- New video provider → `capcut/render/<name>_client.py` implementing the
  `VideoProvider` protocol from `capcut/render/base.py`.
- New embedding model → parameterise `capcut/index/embedder.py`.
- New Concat transport (e.g. HTTP vs stdio) → parameterise
  `capcut/assemble/concat_exporter.py`.