# Задачи: final-render writer с approval gate (fixation 023)

## Статус: ✅ Done (2026-10-19)

| ID | Задача | Статус |
|---|---|---|
| 1 | `capcut/assemble/final_renderer.py` — пакетный модуль | ✅ Done |
| 2 | `build_ffmpeg_command` (copy + re-encode пути) | ✅ Done |
| 3 | `build_concat_list` | ✅ Done |
| 4 | `render_final` — tmp-файл + `os.replace()` | ✅ Done |
| 5 | `probe_duration` | ✅ Done |
| 6 | `scripts/render_final.py` — CLI-обёртка | ✅ Done |
| 7 | **Approval gate** (без `.approved` → exit 1) | ✅ Done |
| 8 | **Идемпотентность** (2-й прогон = no-op, mtime не меняется) | ✅ Done |
| 9 | **Immutability** (hash mismatch → отказ, файл цел) | ✅ Done |
| 10 | `write_spec_sha()` + `mark_rendered()` после рендера | ✅ Done |
| 11 | MCP-инструмент `render_final` (list + handler) | ✅ Done |
| 12 | `tests/test_final_renderer.py` — 16 тестов | ✅ 16 passed |
| 13 | Весь набор pytest | ✅ **145 passed** (было 129) |
| 14 | Node smoke-тесты | ✅ 4/4 |
| 15 | MCP `tools/list` probe (stdio) | ✅ 3 tool'а, `render_final` есть |
| 16 | **Живой рендер** cyber-heist ep-01 → `final.mp4` | ✅ 108 МБ, 35.29 с, h264 1920×1080 |
| 17 | Живая проверка no-op на 2-м прогоне | ✅ |
| 18 | Живая проверка gate на stalker-reznik ep-01 | ✅ exit 1, файл не создан |
| 19 | `README.md` — секция «Final render», MCP 2→3 | ✅ Done |
| 20 | `README_RU.md` — секция «Финальный рендер», MCP 2→3 | ✅ Done |
| 21 | `summary/PRD/PRD.md` — Stage 5 переписан | ✅ Done |
| 22 | `AGENTS.md` — gate/idempotency «policy» → «enforced» | ✅ Done (после подтверждения) |
| 23 | Audit `summary/audit/023_final_render_writer.md` | ✅ |
| 24 | Tasks (этот файл) | ✅ |
| 25 | CHANGELOG.md | ✅ |
| 26 | OpenSpec архивирован | ✅ `archive/2026-10-19-final-render-writer/` |
| 27 | Git commit | ✅ |
| 28 | Merge в `main` + push | ⏸ Требует подтверждения |

## Подробности

### Как это работает

```
serials/<show>/<ep>/
├── brief.md
├── spec.json              ← sha256 считается отсюда
├── .approved              ← approval gate: без него writer отказывает
├── matched.json
└── rendered/
    ├── draft.json         ← вход: Concat timeline
    ├── preview.mp4        ← draft-превью (render_draft.py, не наш scope)
    ├── final.mp4          ← выход: immutable
    └── spec.sha256        ← идемпотентность
```

`scripts/render_final.py --serial <slug> --ep <id>`:

1. Проверяет, что episode существует, есть `spec.json` и `rendered/draft.json`
2. **Gate:** нет `.approved` → exit 1, «approval gate: … has no `.approved` sentinel»
3. **Idempotency:** есть `final.mp4` + совпадает `spec.sha256` → no-op, exit 0
4. **Immutability:** есть `final.mp4` + не совпадает hash → exit 1, «immutable … create a remix»
5. Рендерит: ffmpeg concat (copy), при отказе — повтор с re-encode
6. Пишет `spec.sha256`, вызывает `mark_rendered()`
7. Печатает: путь, размер, длительность (ffprobe), sha256, новое состояние

### Живой результат

```bash
$ python scripts/render_final.py --serial cyber-heist --ep ep-01-infiltration
[render_final] rendering serials/cyber-heist/ep-01-infiltration/rendered/final.mp4
[render_final] wrote .../final.mp4 (108064297 bytes)
[render_final] duration: 35.29s
[render_final] spec sha256: 07b9a1aa29ef4a3157d8497c3c3434a1885663ba05ffcfcd281adaf5350ead42
[render_final] state: rendered
```

```
codec_name=h264  width=1920  height=1080  duration=35.291667  size=108064297
```

### Что НЕ входит в scope

- **Burn-in субтитров** — остаётся Concat/CapCut
- **Переходы (transitions)** из timeline — декларативные, не применяются как ffmpeg-фильтры
- **Микширование аудио и TTS** — вне scope
- **`publish()`** (episode-log append) — не автоматизировано этим изменением
- **`preview.mp4`** (`render_draft.py`) — не тронут, по-прежнему перезаписывается in-place и без gate. Это намеренно: draft-превью создаётся до одобрения. Но теперь `preview.mp4` — единственный маркер, отличающий draft-выход от final

## Что осталось

- Merge ветки `feature/rename-py-to-capcut` в `main` + push (требует
  подтверждения — `main` защищён по AGENTS.md «Branch workflow»).
