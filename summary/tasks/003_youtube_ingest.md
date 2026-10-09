# Задачи: YouTube stock ingest (F2)

**Change ID:** `youtube-ingest`
**Компаньон:** `summary/audit/003_youtube_ingest.md`

## Статус: ✅ Done

| ID | Задача | Оценка | Статус |
|---|---|---|---|
| 1 | `pip install --break-system-packages yt-dlp python-dotenv` | 1m | ✅ Done |
| 2 | `py/ingest/youtube.py` (search + download + probe + metadata) | 1h | ✅ Done |
| 3 | ISO 8601 duration parser (без isodape dep) | 5m | ✅ Done |
| 4 | `scripts/ingest_youtube.py` CLI | 20m | ✅ Done |
| 5 | `tests/test_youtube_ingest.py` (7 тестов, mocked) | 30m | ✅ Done |
| 6 | `py/requirements.txt` с зависимостями | 5m | ✅ Done |
| 7 | Git commit `96b96ff` | 2m | ✅ Done |

**Tests:** 25/25 cumulative OK (18 prev + 7 new)

## Файлы

### Created
- `py/ingest/youtube.py` (~290 lines)
- `scripts/ingest_youtube.py` (~80 lines)
- `tests/test_youtube_ingest.py` (7 tests)
- `py/requirements.txt`