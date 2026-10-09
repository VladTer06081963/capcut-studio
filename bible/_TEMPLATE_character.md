# Character — <slug>

> **Slug:** `<kebab-case>` (e.g. `reznik`, `denis`)
> **Display name:** `<full name>` (e.g. «Stalker Резник»)
> **Show:** `<link to bible/<show>.md>`
> **First appearance:** `<ep-id>`

---

## Identity

- **Полное имя:** `<имя>`
- **Позывной / прозвище:** `<если есть>`
- **Возраст:** `<число>`
- **Пол:** `<м / ж>`
- **Телосложение:** `<хрупкое / среднее / атлетическое / крупное>`
- **Рост:** `<в см, приблизительно>`

## Visual

Опиши так, чтобы H3.0 мог воспроизвести через reference image:

- **Лицо:** `<форма, шрамы, асимметрия, морщины>`
- **Глаза:** `<цвет, выражение>`
- **Волосы:** `<цвет, длина, стиль>`
- **Борода / усы:** `<если есть>`
- **Отличительные черты:** `<татуировки, шрамы, импланты>`

## Wardrobe

Одежда с цветами и фактурой:

- **Голова:** `<например: тёмно-зелёная вязаная шапка>`
- **Верх:** `<SEVA suit с ржавыми пятнами, под ним серый свитер>`
- **Низ:** `<армейские брюки, подвёрнутые>`
- **Обувь:** `<берцы, шнуровка>`
- **Аксессуары:** `<рация, нож, фляжка>`

Reference image for H3.0 init: `library/ai/characters/<slug>/reference.png`

## Props

Signature items, always with the character when in scene:

- **Оружие:** `<АКМ с подствольником, приклад обмотан изолентой>`
- **Снаряжение:** `<Егоза-детектор, мигает красным>`
- **Signature item:** `<например: медальон на шее с фотографией>`

## Personality

2-3 предложения. **Narrative only, не для image gen.**

`<Например: «Резник — угрюмый, неразговорчивый. Знает цену словам и не бросает их на ветер. Молодых не любит, но учит, если они готовы слушать.»>`

## Behavior templates

Pre-generated action clips stored in `library/ai/characters/<slug>/`.
Each is a 4–6 second MP4 used as a reusable building block.

| Action | File | Generated | Notes |
|---|---|---|---|
| Walk | `walk.mp4` | 2026-10-09 | seed=42, front view, evening |
| Talk (close) | `talk.mp4` | 2026-10-09 | seed=42, head + shoulders |
| Sit | `sit.mp4` | 2026-10-09 | by campfire, looking at fire |
| Look over shoulder | `look.mp4` | — | TBD |
| Fight | `fight.mp4` | — | TBD |

**Do not regenerate without bumping the seed.** Drift will break continuity.
See `bible/README.md` → "Seed strategy".

## Seed: <int>

**Фиксированный seed** для всех клипов с этим персонажем.

`// why: <объясни почему этот seed — что в нём хорошо выглядит>`

## Sample prompt (H3.0 image-to-video)

```
<Полный промпт для H3.0. Включает: поза, одежда, props, локация,
настроение, освещение. Frozen — copy paste verbatim.>
```

**Пример** (Stalker Резник идёт у костра):

```
[reference: library/ai/characters/reznik/reference.png]
cinematic anamorphic, slow dolly forward,
a 50-year-old stalker veteran called Reznik with a scarred weathered face,
short grey beard, tired grey eyes,
wearing a worn olive SEVA suit with rust patches on the shoulders,
grey knit cap pulled low,
holding a modified Ecologist detector in his weathered hands,
walking slowly away from a small campfire in Pripyat evening 1986,
mutant red light through broken windows, fog and ash in the air,
atmospheric realism, hyper-detailed, 8k
```

## Negative prompt (fixed)

```
<western, modern clothing, neon, bright clean background, plastic skin,
painterly, photorealistic oil painting, anime, chibi, kawaii, blurry,
deformed, extra fingers, watermark, signature>
```

## Tags (optional)

`<genre tags for search/filtering, например: stalker-horror, military, atmospheric>`

---

## Checklist before committing a new character bible

- [ ] All sections filled
- [ ] `library/ai/characters/<slug>/reference.png` exists
- [ ] At least 1 behavior template (walk or talk) generated and stored
- [ ] Sample prompt tested in H3.0 with the reference image (paste verbatim)
- [ ] Negative prompt filled in
- [ ] Seed locked in `## Seed:` section
- [ ] (Optional) Hermes continuity-check passed against `episode-log.md`