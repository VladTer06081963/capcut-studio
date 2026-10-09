# Episode: ep-01-pilot

> **Episode ID:** `ep-01-pilot`
> **Show:** `stalker-reznik-series`
> **Title:** *Reznik at the Riverbank*
> **First appearance of:** `pripyat-riverbank` scene, `reznik` character

---

## Logline

A veteran stalker returns to Pripyat one evening, approaches a dying
campfire at the riverbank by the rusted bridge, sees a silhouette on
the far shore, and decides not to engage.

## Plot (3-paragraph brief)

Reznik crosses a broken parking lot, SEVA suit catching on twisted
rebar. The bridge silhouette grows as he walks. By the time he reaches
the riverbank, the dusk has almost gone; only the dying campfire
provides light.

He sets down his Ecologist detector on its tripod. The detector's red
LED blinks twice, then steadies. Reznik looks across the river. There
— a figure, still, watching. He studies it for a long moment.

He picks up the detector without hurry, shoulders his rifle, and
walks back the way he came. Voice-over, his own voice, measured:
*"Some things aren't worth the ammo."*

## Scenes (rough, for the LLM to formalize into spec.json)

1. **Establishing** — Wide shot of Pripyat exclusion zone riverbank at
   dusk, no character. Slow dolly in. Fog. Dying campfire. (~6 sec)

2. **Action** — Reznik walks into frame from right, crosses broken
   parking lot, reaches the riverbank by the bridge. Sets down his
   Ecologist detector on its tripod. LED blinks red. (~8 sec)

3. **Dialogue/Reaction** — Reznik looks across the river. Close shot
   of his weathered face, tired grey-green eyes, scanning the far
   shore. A figure is faintly visible across the water. (~5 sec)

4. **Establishing** — Wide reverse: silhouette on the far shore,
   indistinct, watching. Very long hold. (~4 sec)

5. **Voiceover** — Audio track only. Reznik's voice, low and
   measured: *"Some things aren't worth the ammo."* (~3 sec)

6. **Establishing** — Wide shot from behind: Reznik shoulders his
   rifle and walks back across the broken parking lot, fading into
   dusk. (~5 sec)

**Target total duration:** 30-35 sec
**Aspect ratio:** 16:9 (anamorphic 35mm look)
**Music:** none (silence + ambient wind + water + footsteps)

## Continuity expectations

- Reuses scene: `pripyat-riverbank` (see `bible/scene-pripyat-riverbank.md`)
- Introduces character: `reznik` (see `bible/character-reznik.md`)
- Sets up ongoing mystery: who is the silhouette? (multi-episode arc)
- First appearance of Reznik's Ecologist detector blinking red LED —
  this becomes a recurring visual motif

## Tone

Contemplative. Quiet. The danger is unspoken. The decision not to
engage is the climax, not the absence of an action scene.

## Notes for `scripts/spec_from_brief.py`

When invoking the spec writer, prefer:
- `--model qwen/qwen3-max` (best for structured JSON + visual language)
- All video tracks should set `preferred_source: "ai"` (hero shots, character moments)
- Scene 4 (the far-shore silhouette) can use `preferred_source: "stock"` if needed
  (we don't have AI to render another character here; can fake with stock footage)