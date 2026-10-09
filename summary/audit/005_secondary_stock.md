# Аудит: Secondary stock ingest (F3 — Coverr + Mixkit + Archive)

**Дата:** 2026-10-09
**Change ID:** `secondary-stock`
**OpenSpec:** deferred
**Компаньон:** `summary/tasks/005_secondary_stock.md`
**Предшественник:** `summary/audit/003_youtube_ingest.md`

## 1. Контекст

YouTube — primary, но для покрытия нужно больше источников. Все три (Coverr,
Mixkit, Archive.org) verified UA-friendly (curl 2026-10-09T18:13Z).

**Цель**: завершить UA-friendly stock coverage одним change'ом — три
параллельных ingest-модуля с одинаковым dataclass shape (для future unified
matcher).

## 2. Архитектурные решения

| Источник | API | Стратегия | Особенности |
|---|---|---|---|
| **Coverr** | REST | Bearer auth + JSON response | Streaming download |
| **Mixkit** | None (scrape) | Regex `_find_video_cards()` + page-level MP4 resolution | Polite delay (default 2.0s), HTML layout изолирован в одной функции |
| **Archive.org** | advancedsearch + metadata | Lucene query quoted, identifier → H.264 derivative | Public domain, anonymous access |

**Общий dataclass shape** (`VideoMeta`/`ProbeResult`/`IngestResult`) — облегчает
будущий unified matcher.

## 3. Что добавлено

- `py/ingest/coverr.py` (~220 строк)
- `py/ingest/mixkit.py` (~280 строк)
- `py/ingest/archive.py` (~250 строк)
- `scripts/ingest_{coverr,mixkit,archive}.py` (3 CLI)
- `tests/test_secondary_ingest.py` (12 тестов)

## 4. Проверка

- [x] Coverr: Bearer auth, streaming, ffprobe, metadata
- [x] Mixkit: HTML scrape, polite delay, page-level MP4 resolution
- [x] Archive: Lucene quoting, H.264 preference, fallback derivation
- [x] Per-video error handling во всех трёх
- [x] 12/12 tests passing

## 5. Связанные

- `summary/audit/003_youtube_ingest.md` — YouTube (primary, sibling)
- `AGENTS.md` → "Fallback chain" — порядок YouTube → Coverr → Mixkit → Archive