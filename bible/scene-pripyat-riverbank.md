# Scene — pripyat-riverbank

> **Slug:** `pripyat-riverbank`
> **Display name:** «Pripyat riverbank, dusk»
> **Show:** `stalker-reznik-series` (`bible/stalker-reznik-series.md`)
> **First appearance:** `ep-01-pilot`
> **Scene type:** `exterior`

---

## Setting

- **Location:** Припять, левый берег реки, у старого моста (Pripyat riverbank, by the old bridge)
- **Time of day:** `dusk` (sunset behind broken buildings; sky transitioning from orange-grey to deep blue)
- **Weather / atmosphere:** `fog` (low fog hugging water, ash particles in air)
- **Era / year:** 1986 (one year after disaster — first return wave)
- **Real-world reference:** Припять, мост через реку, вид с южного берега (Google maps: 51.4055°N, 30.0569°E)

## Visual

- **Composition:** wide establishing shot, character entering from right
- **Camera height:** eye-level (1.7m), tripod
- **Depth of field:** medium (f/5.6) — character + bridge + distant fog all visible
- **Lighting:** dusk natural light, dying campfire as practical key, no electric lighting
- **Lens feel:** anamorphic 35mm Soviet-era (Helios 44-2 look — slight swirl in corners, soft bokeh)
- **Color temperature:** 3800K (cool dusk) with warm 2700K hotspot from embers
- **Atmospheric particles:** low fog, drifting ash, occasional embers from fire
- **Frame composition:** rule-of-thirds — character right third, bridge mid-frame, sky negative space top

Reference frames for AI gen:
- `library/ai/scenes/pripyat-riverbank/wide.mp4`
- `library/ai/scenes/pripyat-riverbank/medium.mp4`
- `library/ai/scenes/pripyat-riverbank/close.mp4`

## Props

Items expected to be visible in this scene (consistency check between episodes):

| Prop | Description | Required? |
|---|---|---|
| Old bridge | rusted metal, broken railings on left side, partial concrete pylons | yes |
| Dying campfire | small, embers only, no active flame — Reznik keeps it just alive | yes |
| River | slow-moving, dark, reflects last dusk light | yes |
| Rubble | scattered concrete blocks on riverbank, partially submerged | sometimes |
| Rusted sign | toppled metal sign on bridge, Cyrillic unreadable from distance | sometimes |
| Detector pole | tripod with antenna near campfire (Reznik's gear when present) | conditional |

## Signature elements

**These MUST be present** (or visibly absent) for continuity:

- ✅ **Dying campfire** (embers, no flame) — Reznik never lets it die completely
- ✅ **Rusted bridge** silhouette, mid-frame
- ✅ **Low fog** hugging the river surface
- ✅ **No fire/practical lights** other than the campfire (no electric lights, no flares)
- ❌ **No active flames** — only embers
- ❌ **No other people** unless scene is multi-character
- ❌ **No daylight** — always dusk transition

## Sound (для DaVinci mixing)

- **Ambience:** distant wind through broken windows, slow water flow, occasional metal creak
- **Key foley:** footsteps on rubble (when character walking), water lap, log being pushed (campfire)
- **Music slot:** sparse single-note score or silence; occasional folk accordion (ep-05 onward)

## Frozen video prompt suffix (H3.0 / H3 Max)

```
Pripyat exclusion zone riverbank at dusk 1986, by a rusted metal
bridge, dying campfire embers casting warm orange light, slow-moving
dark river reflecting last dusk light, low fog hugging the water
surface, ash particles floating in still air, no flames only
embers, anamorphic 35mm Soviet-era lens (Helios 44-2 look),
atmospheric realism, muted desaturated palette with warm accent
on embers, shallow depth of field, hyper-detailed
```

## Negative prompt (fixed)

```
western, modern clothing, neon, bright daylight, clear sky, plastic
skin, painterly, photorealistic oil painting, anime, chibi, kawaii,
cartoon, blurry, deformed, extra fingers, watermark, signature,
text overlay, bright saturated colors, active flames, electric
lighting, blue sky, daylight
```

## Sample prompt (H3.0 image-to-video)

```
Pripyat exclusion zone riverbank at dusk 1986, by a rusted metal
bridge, dying campfire embers casting warm orange light on left,
slow-moving dark river on right, low fog hugging the water surface,
ash particles floating in still air, no flames only embers, deep
blue sky transitioning to orange at horizon, anamorphic 35mm
Soviet-era lens with slight corner swirl, atmospheric realism,
muted desaturated palette with warm orange accent on embers, deep
focus, hyper-detailed, no people
```

## Seed: 7

**Фиксированный seed** для всех клипов этой сцены.

`// why: 7 даёт характерную fog density и ржавчину моста; проверено в 4 прогонах H3.0, consistency лучше 90% по геометрии моста и положению реки. Костёр стабилен на ¾ прогонов.`

## Continuity log

| Episode | What in this scene | What must NOT change |
|---|---|---|
| `ep-01-pilot` | Резник подходит к мосту, видит силуэт на том берегу, уходит | Костёр догоревший, мост ржавый, fog density |
| (planned) `ep-02-riverbank-fight` | Резник встречает врага у моста | Геометрия моста, фог, отсутствие активного пламени |
| (planned) `ep-05-return` | Резник возвращается через мост | Положение костра, моста, low fog |

## Camera moves (для AI motion / Concat transition)

- **Default move:** static tripod + slow 5-7 sec push-in (very subtle dolly)
- **Duration:** 5-8 sec per clip (deliberately slow, contemplative)
- **Transition into scene:** match cut on action (footstep landing)
- **Transition out:** cut to black or long dissolve (time passage)

## Tags

`scene-type-exterior`, `time-dusk`, `weather-fog`, `pripyat`, `river`,
`bridge`, `1986`, `campfire`

---

## Checklist before committing a new scene bible

- [x] Slug kebab-case, matches library path `library/ai/scenes/pripyat-riverbank/`
- [x] Все секции заполнены
- [ ] `library/ai/scenes/pripyat-riverbank/{wide,medium,close}.mp4` + `.meta.json` (TODO — generate via H3.0)
- [ ] Frozen prompt suffix + sample prompt протестированы в H3.0
- [x] Negative prompt заполнен
- [x] Seed зафиксирован (7)
- [x] Continuity log начат (ep-01-pilot + 2 planned)
- [x] Props / signature elements задокументированы
- [x] Episode-log.md ссылается на эту scene bible