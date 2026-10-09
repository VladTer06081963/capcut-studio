# Задачи: Foundation (F1 — config + lifecycle)

**Change ID:** `foundation`
**OpenSpec:** deferred
**Компаньон:** `summary/audit/002_foundation.md`

## Статус: ✅ Done

| ID | Задача | Оценка | Статус |
|---|---|---|---|
| 1 | `py/lib/config.py` (env loading, constants, helpers) | 30m | ✅ Done |
| 2 | `py/lib/lifecycle.py` (state machine, sentinels, sha256 idempotency) | 45m | ✅ Done |
| 3 | `tests/test_config.py` (defaults, helpers, paths, ensure_dirs) | 20m | ✅ Done |
| 4 | `tests/test_lifecycle.py` (transitions, sha256, publish, list_episodes) | 30m | ✅ Done |
| 5 | Verification: 18/18 tests passing | 5m | ✅ Done |
| 6 | Git commit `63e687d` | 2m | ✅ Done |

**Tests:** 18/18 OK

## Файлы

### Created
- `py/lib/config.py` (~180 lines)
- `py/lib/lifecycle.py` (~250 lines)
- `tests/test_config.py` (4 tests)
- `tests/test_lifecycle.py` (14 tests)

## Связанные

- `summary/audit/002_foundation.md`
- Используется всеми последующими fixations (F2-F9)