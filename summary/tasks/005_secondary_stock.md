# Задачи: Secondary stock ingest (F3)

**Change ID:** `secondary-stock`
**Компаньон:** `summary/audit/005_secondary_stock.md`

## Статус: ✅ Done

| ID | Задача | Оценка | Статус |
|---|---|---|---|
| 1 | `py/ingest/coverr.py` | 45m | ✅ Done |
| 2 | `py/ingest/mixkit.py` (HTML scrape + polite delay) | 1h | ✅ Done |
| 3 | `py/ingest/archive.py` (Lucene quoting + H.264 preference) | 1h | ✅ Done |
| 4 | 3 CLI scripts | 30m | ✅ Done |
| 5 | `tests/test_secondary_ingest.py` (12 тестов) | 45m | ✅ Done |
| 6 | Git commit `016e582` | 2m | ✅ Done |

**Tests:** 52/52 cumulative OK (40 prev + 12 new)

## Файлы

### Created
- `py/ingest/coverr.py` (~220 lines)
- `py/ingest/mixkit.py` (~280 lines)
- `py/ingest/archive.py` (~250 lines)
- `scripts/ingest_coverr.py`, `scripts/ingest_mixkit.py`, `scripts/ingest_archive.py`
- `tests/test_secondary_ingest.py` (12 tests)