# Аудит: Foundation (F1 — config + lifecycle)

**Дата:** 2026-10-09
**Change ID:** `foundation`
**OpenSpec:** deferred (small change, ~430 lines)
**Компаньон:** `summary/tasks/002_foundation.md`
**Предшественник:** `summary/audit/001_initial-scaffold.md`

## 1. Контекст

Первый функциональный код в проекте. Foundation для всех последующих модулей
(ingest, episode, render, search, assemble, MCP). Без `py/lib/config.py` каждый
скрипт парсил бы `.env` заново; без `py/lib/lifecycle.py` state machine эпизода
размазался бы по вызовам.

**Цель**: дать проекту два фундаментальных модуля, на которых строится всё
остальное, и закрыть lifecycle invariant из AGENTS.md («lifecycle as files on
disk, не in-memory flags»).

## 2. Что добавлено

- `py/lib/config.py` (~180 строк): грузит `.env` через `python-dotenv`,
  типизированные константы для всех путей/провайдеров/API-ключей. Helpers:
  `has_minimax()`, `has_openrouter()`, `has_youtube()`, `has_coverr()`,
  `is_test_env()`, `ensure_dirs()`.
- `py/lib/lifecycle.py` (~250 строк): `State` enum (DRAFT/APPROVED/MATCHED/
  RENDERED/PUBLISHED), `Episode` dataclass, sentinel-based state detection,
  atomic transitions (`approve`/`revise`/`mark_matched`/`mark_rendered`/
  `publish`), sha256-based idempotency для re-render.
- `tests/test_config.py` (4 теста), `tests/test_lifecycle.py` (14 тестов):
  18/18 OK.

## 3. Архитектурные решения

| Вопрос | Решение | Обоснование |
|---|---|---|
| Env loading | python-dotenv, override=False | CI может override; .env как fallback |
| State representation | Sentinel files (.draft, .approved) + path-based detection для matched.json/rendered/final.mp4 | Соответствует AGENTS.md invariant |
| Idempotency | sha256(spec.json) → spec.sha256 рядом с final.mp4 | Re-render без изменений = no-op |
| State enum value | str Enum (`State.DRAFT == "draft"`) | JSON-friendly, readable в логах |
| Test isolation | tempfile.mkdtemp + unittest.mock.patch | Никаких live-вызовов в тестах |

## 4. Файлы

### Created
- `py/lib/config.py`
- `py/lib/lifecycle.py`
- `tests/test_config.py`
- `tests/test_lifecycle.py`

### Modified
- (нет)

## 5. Что НЕ входит

- OpenSpec proposal — defer (single-file change)
- Provider routing / fallback chain — отдельный change (image gen, F5+)
- Multi-state approval (e.g. auto-approved) — out of scope, добавляется по необходимости

## 6. Связанные

- `summary/audit/001_initial-scaffold.md` — что было до
- `AGENTS.md` → "Project invariants" — formalизация через эти модули
- Все последующие fixations используют `py.lib.config` + `py.lib.lifecycle`