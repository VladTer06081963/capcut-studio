# Show — <slug>

> **Slug:** `<kebab-case>` (e.g. `stalker-reznik-series`, `pripyat-12-stulyev`)
> **Type:** `<narrative | documentary | anthology | tutorial | mixed>`
> **Aspect ratio:** `<16:9 | 9:16 | 1:1 | 2.39:1>`
> **Target length per episode:** `<sec>` (typical)
> **Series arc:** `<one-line pitch>`

---

## Visual style

Frozen across all episodes. AI generation **must** use this verbatim in prompts;
do not paraphrase.

### Reference works

- `<Title 1>` — for `<what to borrow>`
- `<Title 2>` — for `<what to borrow>`

### Frozen video prompt suffix (H3.0 / H3 Max)

```
<paste the literal prompt suffix here — DO NOT paraphrase>
```

### Negative prompt (fixed)

```
<paste the literal negative prompt here>
```

### Color palette / LUT

| Role | Hex | Notes |
|---|---|---|
| Background base | `#000000` | `<use>` |
| Highlight | `#FFAA33` | `<use>` |
| Shadow | `#0A0A14` | `<use>` |
| Accent | `#C72B26` | `<use>` |

LUT file (if any): `bible/<slug>.cube` — apply in DaVinci per episode.

### Camera & composition

- **Lens:** `<e.g. anamorphic 35mm, vintage Soviet Helios>`
- **Camera moves:** `<e.g. slow dolly, locked tripod for dialogue>`
- **Framing:** `<e.g. subject off-center, negative space top-right>`
- **Depth:** `<e.g. shallow DOF for hero shots, deep focus for establishing>`

### Editing style

- **Average shot length:** `<e.g. 4–6 sec>`
- **Transitions:** `<e.g. cut on action, occasional match cut>`
- **Captions:** `<font, position, animation>`
- **Music:** `<genre, where it sits, fade rules>`
- **Sound design:** `<ambience, foley>`

## Models and parameters

- **Video gen:** MiniMax H3.0 / H3 Max (default `minimax-h3-max`).
- **Image gen (reference):** Qwen-Image via OpenRouter (default `qwen-image`).
- **Seed strategy:** Fixed per-character (see `bible/character-<slug>.md`).
  Scene seeds in `serials/<show>/episode-log.md` for continuity.
- **Sampler:** default H3.0 settings, override per-scene if needed.

## Cast

Link to character bibles — one per recurring role:

- `bible/character-reznik.md` — stalker veteran (lead)
- `bible/character-denis.md` — young recruit (co-lead)
- ...

## Locations / scenes

Link to scene bibles — frozen across episodes:

- `bible/scene-pripyat-riverbank.md` — campfire scenes
- `bible/scene-pripyat-square.md` — urban exploration
- ...

## Episodes log

Source of truth: `serials/<show>/episode-log.md`. Append-only.

## Checklist before committing a new episode bible

- [ ] Slug is kebab-case, matches `serials/<show>/` dir name
- [ ] Visual reference works listed
- [ ] Frozen prompt suffix filled in (test in H3.0 once before committing)
- [ ] Negative prompt filled in
- [ ] Color palette has 4+ entries
- [ ] Camera / composition documented
- [ ] Editing style documented
- [ ] Models and seed strategy filled in
- [ ] All recurring characters linked to their `bible/character-*.md`
- [ ] All recurring scenes linked to their `bible/scene-*.md`
- [ ] One pilot episode rendered end-to-end before adding more