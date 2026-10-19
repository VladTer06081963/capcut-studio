# Задачи: health-check followups (fixation 021)

## Статус: 📝 Documented (2026-10-19) — 3 follow-ups открыты, код не менялся

| ID | Задача | Статус |
|---|---|---|
| 1 | Создать аудит `summary/audit/021_health_check_followups.md` (3 follow-up'а + verification) | ✅ Done |
| 2 | Создать tasks-файл `summary/tasks/021_health_check_followups.md` (этот файл) | ✅ Done |
| 3 | Подтвердить 129/129 pytest + 4/4 node smoke-тестов после установки `.venv` | ✅ Done |
| 4 | Добавить запись в `CHANGELOG.md` о fixation 021 | ✅ Done |
| 5 | **Follow-up 5.1:** Устранить shadowing `py/` ↔ `py` пакет | ⏸ Открыт (нужна отдельная fixation 022 — переименование `py/` → `capcut/`) |
| 6 | **Follow-up 5.2:** Реализовать `final.mp4` writer (CLI или MCP-tool) | ⏸ Открыт (нужна OpenSpec proposal + отдельная fixation 023) |
| 7 | **Follow-up 5.3:** Сгенерировать `final.mp4` для cyber-heist ep-01-infiltration | ⏸ Блокирован Follow-up'ом 5.2 (или ручной Concat GUI export) |
| 8 | **Bonus:** Решить, что делать с 2 незаархивированными OpenSpec'ами (`hybrid-media-workflow`, `pi-project-agent`) | ⏸ Не моя зона — это чужие proposed changes |
| 9 | Git commit + push | ✅ Done |

## Основание

`summary/audit/021_health_check_followups.md` — полный аудит с
верификацией, root cause анализом для каждой проблемы, и таблицей
вариантов решения (A/B/C) с оценкой effort/risk.

## Подробный разбор

### Follow-up 5.1: shadowing `py/` ↔ `py` пакет

**Корень проблемы:** Локальная директория `~/Projects/capcut-studio/py/`
содержит исходники pipeline (`ingest/`, `episode/`, `render/`, `index/`,
`search/`, `assemble/`, `lib/`, `requirements.txt`). У пакета `py` есть
свой `__init__.py` (см. `~/Projects/capcut-studio/py/__init__.py`).
Когда pytest запускается с CWD внутри проекта, `import py` подхватывает
**локальный** `py/__init__.py`, а не установленный пакет `py` (нужен для
`LEGACY_PATH = py.path.local` в pytest 7.x).

**Симптом:**
```python
$ cd ~/Projects/capcut-studio
$ python -c "import py; print(py.__file__)"
/Users/vladteresena/Projects/capcut-studio/py/__init__.py   # ← local!
$ python -m pytest
AttributeError: module 'py' has no attribute 'path'
```

**Workaround (использован в этом health-check):**
```bash
cd /tmp
source ~/Projects/capcut-studio/.venv/bin/activate
python -m pytest /Users/vladteresena/Projects/capcut-studio/tests/ \
  --rootdir=/Users/vladteresena/Projects/capcut-studio
# → 129/129 passed
```

**Реальные фиксы (любой ОДИН решает проблему):**

| Опция | Effort | Risk | Когда выбирать |
|---|---|---|---|
| (A) `py/` → `capcut/` | ~30 мин: bulk import-path rewrite (все `from py.X import`, `import py.X`, ~30 файлов), обновить README/AGENTS.md/summary/ | Medium (нужно поймать все импорты, включая `py.lib.config` в .env скриптах) | Если хочется чистоты на годы вперёд; matches comic-studio если там тоже `capcut/` |
| (B) `conftest.py` фикс sys.path | ~10 мин | Low (прячет footgun) | Если фикс (A) слишком рискованный |
| (C) Документировать workaround в AGENTS.md | ~5 мин | None | Если быстрый фикс приемлем |

**Рекомендация:** (A) — самое чистое. Но это отдельная fixation 022 с
OpenSpec proposal (трогает публичный import path, contract change).

### Follow-up 5.2: нет `final.mp4` writer

**Состояние:** Pipeline останавливается на `rendered/preview.mp4`
(Concat draft export). Нет CLI для production `rendered/final.mp4`.
AGENTS.md: «no final-render CLI confirmed», «immutable from creation»,
«rendered state transitions to remix, not re-render» — но **создание**
самой `final.mp4` не автоматизировано.

**Два пути:**

1. **Concat GUI вручную** — открыть `rendered/concat.json` в
   Concat.app, polish, экспортировать `final.mp4` руками. Уже
   работает, просто не автоматизировано.
2. **Concat MCP-tool** — добавить `render_final` tool в
   `mcp-server/index.js`, который через AppleScript/shell управляет
   Concat и экспортирует `final.mp4`. Не реализовано.

**Рекомендация:** для R&D фазы — путь (1) приемлем. Когда Concat MCP
export подтверждён, добавить `render_final` tool (отдельная fixation
023, требует OpenSpec).

### Follow-up 5.3: cyber-heist ep-01 approved, но без final

**Состояние:**
```
serials/cyber-heist/ep-01-infiltration/
  .approved       (sentinel, есть)
  brief.md
  spec.json
  matched.json
  rendered/
    concat.json
    draft.json
    ffmpeg_list.txt
    preview.mp4   (108 MB, Concat draft export)
```

**Импликация:** эпизод одобрен, preview готов, но `final.mp4` шаг не
сделан. Это та же проблема, что 5.2 — фикс 5.2 закроет 5.3.

**Рекомендация:** оставить как есть до 5.2, или Concat GUI export
вручную если `final.mp4` нужен до этого. `preview.mp4` достаточен для
review и re-encoding.

## Что в этой fixation 021

- Только документация: `audit/021_*.md`, `tasks/021_*.md`, CHANGELOG
- Никаких правок кода
- venv создан (`.venv/`) и runtime deps установлены — это сайд-эффект
  health-check, не самоцель

## Что НЕ в этой fixation 021

- 5.1 fix (rename / conftest / doc) — отдельная fixation 022
- 5.2 fix (`render_final` tool) — отдельная fixation 023
- 5.3 fix (сгенерировать `final.mp4` для cyber-heist) — блокирован 5.2
- Архивирование чужих OpenSpec'ов — не моя зона

## Чеклист закрытия 021

- [x] Аудит создан (`summary/audit/021_health_check_followups.md`)
- [x] Таски созданы (`summary/tasks/021_health_check_followups.md` — этот)
- [x] CHANGELOG.md обновлён
- [x] Git clean
- [x] Push на GitHub
- [x] Health-check verified (129/129 + 4/4)
