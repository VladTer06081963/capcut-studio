# Аудит: Scene bible template (F9)

**Дата:** 2026-10-09
**Change ID:** `scene-template`
**OpenSpec:** deferred (template, no code)
**Компаньон:** `summary/tasks/008_scene_template.md`
**Предшественник:** `summary/audit/007_matcher_assembler.md`

## 1. Контекст

Scene — переиспользуемая локация, появляющаяся в нескольких эпизодах
(например, "костёр у моста" — в 5 разных эпизодах). Нужен шаблон bible
для сцен, чтобы зафиксировать что **не меняется** между эпизодами.

**Цель**: frozen template для `bible/scene-<slug>.md`, mirror character/show
template pattern.

## 2. Архитектурные решения

| Секция | Что фиксирует |
|---|---|
| Setting | location, time of day, weather, era |
| Visual | composition, lighting, lens, color temp, atmospheric particles |
| Props | items expected to be visible |
| Signature elements | MUST be present (or absent) для continuity |
| Sound | ambience, foley, music slot |
| Frozen prompt suffix | copy-paste verbatim для H3.0 |
| Sample prompt | полный пример для первого прогона |
| Seed | фиксированный int, bump ±1 при drift |
| **Continuity log** | per-episode вариации — drift detector |
| Camera moves | default motion + transitions |

## 3. Что добавлено

- `bible/_TEMPLATE_scene.md` (~150 строк) с чеклистом из 11 пунктов
- `bible/README.md` обновлён (секция "Scene bible (F9)")

## 4. Проверка

- [x] Все секции заполняемы
- [x] Frozen prompt + sample prompt (verbatim)
- [x] Negative prompt
- [x] Seed pattern (mirror character bible)
- [x] Continuity log для drift detection
- [x] Props / signature elements documented
- [x] bible/README.md обновлён

## 5. Связанные

- `bible/_TEMPLATE_show.md` — show-level template
- `bible/_TEMPLATE_character.md` — character-level template
- Scene bible = location-level template (третий уровень иерархии)