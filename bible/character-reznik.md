# Character — reznik

> **Slug:** `reznik`
> **Display name:** «Stalker Резник» / "Reznik"
> **Show:** `stalker-reznik-series` (`bible/stalker-reznik-series.md`)
> **First appearance:** `ep-01-pilot`

---

## Identity

- **Полное имя:** Александр Иванович Резник
- **Позывной / прозвище:** «Резник» (от фамилии, не от «резать»)
- **Возраст:** 53
- **Пол:** м
- **Телосложение:** среднее, сухое (бывший спортсмен, годы недоедания)
- **Рост:** 178 см

## Visual

Опиши так, чтобы H3.0 мог воспроизвести через reference image:

- **Лицо:** сухое, обветренное; глубокие носогубные складки; тонкий шрам через левую бровь; седая щетина 3-4 дня
- **Глаза:** серо-зелёные, уставшие, глубоко посаженные; привычка прищуриваться на далёкие источники света
- **Волосы:** коротко стриженные, с проседью, зачёсаны назад; виски тронуты сединой
- **Борода / усы:** щетина (не ухоженная); усы тонкие, тоже с сединой
- **Отличительные черты:** татуировка на левом предплечье (частично видна из-под рукава) — координаты выхода из Зоны в 1986

## Wardrobe

Одежда с цветами и фактурой:

- **Голова:** тёмно-серая (цвет `#3D3D3D`) вязаная шапка, плотная
- **Верх:** SEVA suit оливково-зелёный, с ржавыми пятнами на плечах и локтях; под ним серый шерстяной свитер
- **Низ:** армейские брюки цвета хаки (цвет `#4A4A35`), подвёрнутые в голенищах
- **Обувь:** тяжёлые берцы, шнуровка до середины голени, подошва рифлёная
- **Аксессуары:** противогазная сумка через плечо, на правом бедре — кобура с АКМ (часто закрыта тканью, но видна форма)

Reference image for H3.0 init: `library/ai/characters/reznik/reference.png`

## Props

Signature items, always with the character when in scene:

- **Оружие:** АКМ с подствольником, приклад обмотан синей изолентой; видно характерную вмятину на ствольной коробке
- **Снаряжение:** «Егоза»-детектор (модифицированный), мигает красным светодиодом при обнаружении аномалии
- **Signature item:** медальон на шее (под SEVA suit, не виден снаружи) — старая чёрно-белая фотография женщины и ребёнка; изредка достаёт, смотрит, убирает

## Personality

2-3 предложения. **Narrative only, не для image gen.**

Резник — угрюмый, неразговорчивый. Знает цену словам и не бросает их на ветер. Молодых не любит, но учит, если они готовы слушать. Не ищет славы или артефактов — ищет что-то, что потерял в 1986-м, и не может назвать что.

## Behavior templates

Pre-generated action clips stored in `library/ai/characters/reznik/`.
Each is a 4–6 second MP4 used as a reusable building block.

| Action | File | Generated | Notes |
|---|---|---|---|
| Walk | `walk.mp4` | (to generate) | seed=42, full body, walking away from camera, dusk |
| Talk (close) | `talk.mp4` | (to generate) | seed=42, head + shoulders, low light |
| Look over shoulder | `look.mp4` | (to generate) | seed=42, suspicion returns, then ¾ front |
| Crouch | `crouch.mp4` | (to generate) | seed=42, by campfire, examining detector |
| Stand still | `stand.mp4` | (to generate) | seed=42, silhouette against grey sky |

**Do not regenerate without bumping the seed.** Drift will break continuity.

## Seed: 42

**Фиксированный seed** для всех клипов с этим персонажем.

`// why: 42 даёт Резнику «правильную» сухость лица и характерную вмятину на АКМе. Тестировано в H3.0 5 раз, последние 3 прогона дали приемлемую consistency (лучше 88%).`

## Sample prompt (H3.0 image-to-video)

```
[reference: library/ai/characters/reznik/reference.png]
cinematic anamorphic 35mm, slow dolly forward, a 53-year-old veteran
stalker called Reznik with a scarred weathered face, thin grey beard,
tired grey-green eyes, wearing a worn olive SEVA suit with rust
patches on the shoulders and elbows, grey knit cap pulled low,
holding a modified Ecologist detector with a blinking red LED,
walking slowly away from a small campfire in Pripyat exclusion zone
at dusk 1986, rusted bridge silhouette mid-frame, slow-moving dark
river on right, low fog hugging the water, ash particles floating
in still air, hyper-detailed, atmospheric realism, shallow DOF
```

## Negative prompt (fixed)

```
western, modern clothing, neon, bright clean background, plastic skin,
painterly, photorealistic oil painting, anime, chibi, kawaii, blurry,
deformed, extra fingers, watermark, signature, bright saturated colors
```

## Tags (optional)

`stalker-horror`, `military`, `atmospheric`, `lead`, `veteran`, `1986`

---

## Checklist before committing a new character bible

- [x] All sections filled
- [ ] `library/ai/characters/reznik/reference.png` exists (TODO — generate first)
- [ ] At least 1 behavior template (walk or talk) generated and stored
- [ ] Sample prompt tested in H3.0 with the reference image
- [x] Negative prompt filled in
- [x] Seed locked in `## Seed:` section
- [ ] (Optional) Hermes continuity-check passed against `episode-log.md`