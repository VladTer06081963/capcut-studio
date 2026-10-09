# Show — stalker-reznik-series

> **Slug:** `stalker-reznik-series`
> **Type:** `narrative` (long-form serialized story)
> **Aspect ratio:** `16:9`
> **Target length per episode:** `60-120 sec` (typical)
> **Series arc:** *A veteran stalker returns to Pripyat fifteen years after the disaster, hunting for something he lost — and finding what he became.*

---

## Visual style

Frozen across all episodes. AI generation **must** use this verbatim in prompts;
do not paraphrase.

### Reference works

- S.T.A.L.K.E.R.: Shadow of Chernobyl (2007) — for atmosphere, decay, color grade
- Andrei Tarkovsky's *Stalker* (1979) — for pacing, negative space, restraint
- Philip Glass — minimalist score reference

### Frozen video prompt suffix (H3.0 / H3 Max)

```
cinematic anamorphic 35mm, slow contemplative dolly, Pripyat exclusion
zone 1986, post-Soviet decay, atmospheric realism, hyper-detailed,
muted desaturated palette with single warm accent (fire or rust),
shallow depth of field on hero shots, deep focus for establishing,
fog particles floating in still air, no CGI gloss, no neon, no modern
clothing, no bright clean surfaces
```

### Negative prompt (fixed)

```
western, modern clothing, neon lights, bright clean surfaces, plastic
skin, painterly, photorealistic oil painting, anime, chibi, kawaii,
cartoon, blurry, deformed, extra fingers, watermark, signature,
text overlay, bright saturated colors
```

### Color palette / LUT

| Role | Hex | Notes |
|---|---|---|
| Background base | `#1A1A1F` | dead-grey concrete, sky |
| Highlight | `#FF6B35` | campfire embers, rusted metal |
| Shadow | `#0A0A14` | deep recesses, night sky |
| Mid-tone | `#3D3D3D` | SEVA suits, concrete |
| Accent (rare) | `#C72B26` | blood, anomaly warning |

LUT file: `bible/stalker-reznik-series.cube` — apply in DaVinci per episode.

### Camera & composition

- **Lens:** anamorphic 35mm vintage (Helios 44-2 or similar Soviet-era lens look)
- **Camera moves:** slow dolly in/out, locked tripod for dialogue, occasional handheld for action
- **Framing:** subject off-center (rule of thirds), generous negative space top of frame
- **Depth:** shallow DOF (f/2.8) for character moments, deep focus for establishing shots

### Editing style

- **Average shot length:** 5–8 sec (deliberately slow)
- **Transitions:** match cut on action, occasional long dissolve for time passage
- **Captions:** white sans-serif (Helvetica/Akzidenz), lower-left, 70% opacity, no animation
- **Music:** sparse, single sustained note or silence; occasional folk music (accordion, sparse)
- **Sound design:** wind, distant metal creaks, water drip, footsteps on rubble; radio static when Ecologist detector active

## Models and parameters

- **Video gen:** MiniMax H3.0 / H3 Max (default `minimax-h3-max`).
- **Image gen (reference):** Qwen-Image via OpenRouter (default `qwen-image`).
- **Seed strategy:** Fixed per-character (see `bible/character-reznik.md`).
  Scene seeds in `serials/stalker-reznik/episode-log.md` for continuity.
- **Sampler:** default H3.0 settings, override per-scene if needed.

## Cast

Link to character bibles — one per recurring role:

- `bible/character-reznik.md` — stalker veteran (lead)
- `bible/character-denis.md` — young recruit (co-lead, future)
- (future: `bible/character-leader.md` — faction leader)

## Locations / scenes

Link to scene bibles — frozen across episodes:

- `bible/scene-pripyat-riverbank.md` — campfire scenes (used in 5+ episodes)
- `bible/scene-pripyat-square-night.md` — urban exploration (future)
- `bible/scene-denis-bunker.md` — interior bunker (future)

## Episodes log

Source of truth: `serials/stalker-reznik/episode-log.md`. Append-only.

## Checklist before committing a new episode bible

- [x] Slug kebab-case, matches `serials/stalker-reznik/` dir name
- [x] Visual reference works listed (Shadow of Chernobyl, Tarkovsky's Stalker)
- [x] Frozen prompt suffix filled in (test in H3.0 once before committing)
- [x] Negative prompt filled in
- [x] Color palette has 5 entries
- [x] Camera / composition documented (anamorphic 35mm Soviet-era lens)
- [x] Editing style documented (5-8 sec, match cut, sparse music)
- [x] Models and seed strategy filled in
- [x] All recurring characters linked
- [x] All recurring scenes linked
- [x] One pilot episode rendered end-to-end before adding more