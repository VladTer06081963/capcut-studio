# bible/

Frozen templates — one per show, character, and scene. The bible is the
**single source of truth** for visual consistency across episodes.

## Files

- `_TEMPLATE_show.md` — copy to `<show-slug>.md` and fill
- `_TEMPLATE_character.md` — copy to `character-<slug>.md` and fill
- (TBD) `_TEMPLATE_scene.md` — frozen scene bible (lighting, props, composition)

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