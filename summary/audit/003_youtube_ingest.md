# Аудит: YouTube stock ingest (F2)

**Дата:** 2026-10-09
**Change ID:** `youtube-ingest`
**OpenSpec:** deferred (single-source, ~290 lines)
**Компаньон:** `summary/tasks/003_youtube_ingest.md`
**Предшественник:** `summary/audit/002_foundation.md`

## 1. Контекст

После foundation нужен первый **реальный stock ingest**. YouTube — primary
UA-friendly stock (verified 200 из UA, curl 2026-10-09T18:13Z). Data API v3 +
yt-dlp дают максимальную coverage (миллиарды видео) без scraping.

**Цель**: первый end-to-end pipeline — пользователь запускает
`scripts/ingest_youtube.py --query "fog forest"` и получает `.mp4` клипы +
metadata в `library/stock/youtube/`.

## 2. Архитектурные решения

| Вопрос | Решение |
|---|---|
| Search | Data API v3 (2 запроса: `/search?type=video` + `/videos?part=snippet,contentDetails,status`) |
| Duration parser | Свой regex `_parse_iso_duration_seconds` (убрали `isodate` dep) |
| Download | yt-dlp, 720p MP4, 500MB hard cap |
| Probe | ffprobe JSON → duration/width/height/fps |
| License | `LICENSE_CC` или `LICENSE_ANY` (default) |
| Error handling | Per-video errors не валят весь batch; `IngestResult{errors[]}` |

## 3. Что добавлено

- `py/ingest/youtube.py` (~290 строк)
- `scripts/ingest_youtube.py` (~80 строк, CLI)
- `tests/test_youtube_ingest.py` (7 тестов)

## 4. Файлы

### Created
- `py/ingest/youtube.py`
- `scripts/ingest_youtube.py`
- `tests/test_youtube_ingest.py`
- `py/requirements.txt` (yt-dlp + python-dotenv + requests)

### Modified
- (нет)

## 5. Что НЕ входит

- Other stock sources (Coverr, Mixkit, Archive) → `summary/audit/005_secondary_stock.md`
- Indexer / embeddings → `summary/audit/006_library_indexer.md`

## 6. Проверка

- [x] YouTube Data API v3 search (2 запроса, обогащение через `/videos`)
- [x] yt-dlp download с 720p cap
- [x] ffprobe probe (duration/width/height/fps)
- [x] metadata.json рядом с .mp4
- [x] Per-video error handling (partial success)
- [x] CLI с --query, --count, --license, --output-dir, --duration
- [x] 7/7 tests passing

## 7. Связанные

- `summary/audit/005_secondary_stock.md` — Coverr + Mixkit + Archive (parallel)
- `summary/audit/006_library_indexer.md` — использует эти метадаты
- `AGENTS.md` → "Fallback chain" — YouTube = primary