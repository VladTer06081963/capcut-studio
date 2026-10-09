# bible/

Frozen templates — one per show, character, and scene. The bible is the
**single source of truth** for visual consistency across episodes.

## Files

- `_TEMPLATE_show.md` — copy to `<show-slug>.md` and fill
- `_TEMPLATE_character.md` — copy to `character-<slug>.md` and fill
- `_TEMPLATE_scene.md` — copy to `scene-<slug>.md` and fill (frozen location/
  lighting/composition across episodes)

## Scene bible (F9)

`bible/scene-<slug>.md` defines a **reusable location** — the same physical
place across many episodes. Examples:

- `bible/scene-pripyat-riverbank.md` — used in 5 episodes (campfire scenes)
- `bible/scene-pripyat-square-night.md` — used in 3 episodes
- `bible/scene-denis-bunker.md` — interior, used in 2 episodes

Scene bibles freeze **what doesn't change between episodes**:
- Composition, lighting, atmosphere, color temperature
- Props and signature elements (always present or always absent)
- Camera moves (default motion + transitions)

The **continuity log** in each scene bible tracks which episodes used it
and what was different in each — this is your drift detector. If two
episodes show the same scene with conflicting prop placement, the log
flags it.

## Why "frozen"

Everything that affects visual consistency goes in the bible **as literal
strings** that AI generation uses verbatim:

- Video prompt suffix
- Negative prompt
- Color palette / LUT
- Reference image path (for H3.0 init)
- Seed

Do not paraphrase. Do not "improve". If something needs to change, write
a new episode, not a hot edit.

## Seed strategy

Each character and scene gets a fixed seed. H3.0 / Stable Diffusion style
models are seed-deterministic, but H3.0 with reference image is *mostly*
deterministic (~85% reliable). Drift is real and you will hit it.

When drift happens:

1. **First try**: regenerate with same seed + same reference. ~30% of the
   time the second pass is closer to the original.
2. **Second try**: bump seed by ±1, see if a nearby seed gives a closer
   match. If yes, update the bible **and** re-render prior episodes that
   used the old seed (mark them `remixed`).
3. **Worst case**: hand-fix in DaVinci (chroma key + frame interp).

Never change a seed retroactively. Always update the bible, then handle
the chain reaction.

## Lifecycle

| State | Location | Notes |
|---|---|---|
| Draft | `bible/_TEMPLATE_*.md` | Read-only reference |
| Live | `bible/<show-slug>.md`, `bible/character-<slug>.md` | Frozen for that show/character |
| Archived | `bible/archive/<date>-<slug>.md` | When retired (rare) |

Shows are append-only in practice — once `stalker-reznik-series` exists,
it stays. New series = new file.