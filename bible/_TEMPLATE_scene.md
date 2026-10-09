# Scene — <slug>

> **Slug:** `<kebab-case>` (e.g. `pripyat-riverbank`, `pripyat-square-night`)
> **Display name:** `<human-readable>` (e.g. «Pripyat riverbank, dusk»)
> **Show:** `<link to bible/<show>.md>`
> **First appearance:** `<ep-id>`
> **Scene type:** `<exterior | interior | transit | abstract>`

---

## Setting

- **Location:** `<where physically — Припять, левый берег реки, у старого моста>`
- **Time of day:** `<dawn | morning | noon | afternoon | dusk | night | late-night>`
- **Weather / atmosphere:** `<clear | overcast | rain | fog | snow | ash-fall | storm>`
- **Era / year:** `<1986 | 2012-present | undetermined>`
- **Real-world reference:** `<optional: google maps, location scout photos>`

## Visual

Опиши так, чтобы H3.0 мог воспроизвести:

- **Composition:** `<wide | medium | close-up | over-the-shoulder | POV>`
- **Camera height:** `<eye-level | low-angle | high-angle | drone>`
- **Depth of field:** `<shallow (f/2.8) | medium (f/5.6) | deep (f/11)>`
- **Lighting:** `<golden-hour | overcast-diffuse | single-source-practical | moonlight | firelight>`
- **Lens feel:** `<e.g. anamorphic 35mm, vintage Soviet Helios 44-2, modern cinema>`
- **Color temperature:** `<warm 3200K | neutral 5500K | cool 7000K>`
- **Atmospheric particles:** `<fog | dust | ash | rain | snow | embers | none>`
- **Frame composition:** `<rule-of-thirds | center | leading-lines | symmetric>`

Reference frames for AI gen:
- `library/ai/scenes/<slug>/wide.mp4`
- `library/ai/scenes/<slug>/medium.mp4`
- `library/ai/scenes/<slug>/close.mp4`

## Props

Items expected to be visible in this scene (consistency check between episodes):

| Prop | Description | Required in scene? |
|---|---|---|
| `<campfire>` | small, dying embers, no active flame | yes |
| `<river>` | slow-moving, dark water | yes |
| `<old-bridge>` | rusted metal, broken railings | sometimes |
| `<rubble>` | scattered concrete debris | sometimes |

## Signature elements

**These MUST be present** (or visibly absent) for continuity:

- `<e.g. всегда видна ржавая вывеска на мосту>`
- `<e.g. костёр всегда догоревший, не активный>`
- `<e.g. в правом нижнем углу — половина бетонного блока>`

## Sound (для DaVinci mixing)

- **Ambience:** `<e.g. distant wind, occasional water drip, no music>`
- **Key foley:** `<e.g. footsteps on rubble, distant metallic creak>`
- **Music slot:** `<none | loop: <track-name> | score: <genre> | voice-only>`

## Frozen video prompt suffix (H3.0 / H3 Max)

```
<paste literal prompt suffix here — DO NOT paraphrase>
```

Includes: composition, lighting, atmospheric particles, color temperature.
**Не включает**: одежду/лицо персонажа — это в character bible.

## Negative prompt (fixed)

```
<paste literal negative prompt here>
```

## Sample prompt (H3.0 image-to-video)

```
<Полный промпт. Композиция + освещение + атмосфера + локация.
Frozen — copy paste verbatim.>
```

**Пример** (Pripyat riverbank dusk):

```
[reference: library/ai/scenes/pripyat-riverbank/wide.png]
cinematic anamorphic 35mm, slow dolly forward,
wide establishing shot of Pripyat riverbank at dusk 1986,
rusted metal bridge visible mid-frame, dying campfire embers on left,
slow-moving dark river on right, low fog hugging the water,
mutant red light through distant broken windows,
ash particles floating in air, hyper-detailed, atmospheric realism
```

## Seed: <int>

**Фиксированный seed** для всех клипов этой сцены.

`// why: <объясни почему этот seed — что в нём хорошо выглядит>`

## Continuity log

Каждая сцена живёт в нескольких эпизодах. Здесь — заметки о том, **что в ней должно меняться и что нет**:

| Episode | Что в этой сцене | Что НЕ должно меняться |
|---|---|---|
| `ep-01-pilot` | Резник идёт к мосту | Костёр догоревший, мост ржавый |
| `ep-02-riverbank-fight` | Резник встречает врага у моста | Положение костра, моста |
| `ep-05-return` | Резник возвращается через мост | Геометрия моста, фог |

## Camera moves (для AI motion / Concat transition)

- **Default move:** `<static | slow-pan-L | slow-pan-R | dolly-in | dolly-out | handheld>`
- **Duration:** `<typical clip length in seconds>`
- **Transition into scene:** `<cut | fade-from-black | match-cut-on-action>`
- **Transition out:** `<cut | fade-to-black | match-cut>`

## Tags

`scene-type-<exterior>`, `time-<dusk>`, `weather-<fog>`, `pripyat`, `river`, `1986`

---

## Checklist before committing a new scene bible

- [ ] Slug kebab-case, matches library path `library/ai/scenes/<slug>/`
- [ ] Все секции заполнены
- [ ] `library/ai/scenes/<slug>/{wide,medium,close}.mp4` + `.meta.json` существуют
- [ ] Frozen prompt suffix + sample prompt протестированы в H3.0 (минимум 2 прогона)
- [ ] Negative prompt заполнен
- [ ] Seed зафиксирован в `## Seed:` секции
- [ ] Continuity log начат (хотя бы один эпизод)
- [ ] Props / signature elements задокументированы (continuity check между эпизодами)
- [ ] Связанные сцены linked (если scene_part_of: <other-scene-slug>)
- [ ] Episode-log.md ссылается на эту scene bible