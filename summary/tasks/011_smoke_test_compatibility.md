# Задачи: F-11 — Smoke test compatibility fixes

**Change ID:** `smoke-test-compatibility`
**Компаньон:** `summary/audit/011_smoke_test_compatibility.md`

## Статус: ✅ Done

| ID | Задача | Оценка | Статус |
|---|---|---|---|
| 1 | LM Studio `response_format=json_object` retry (fallback без него) | 15m | ✅ Done |
| 2 | Markdown ```json fence strip в `_extract_json_content` | 10m | ✅ Done |
| 3 | `VALID_SCENE_TYPES` whitelist + `_normalize_scene_type` (slash/underscore) | 15m | ✅ Done |
| 4 | LM Studio bearer token: `lm_studio_alive`, `embed_text`, `caption_image` | 20m | ✅ Done |
| 5 | Archive.org `sort[]="downloads desc"` (space, не plus) | 5m | ✅ Done |
| 6 | yt-dlp format selector (progressive + merge fallback) | 20m | ✅ Done |
| 7 | yt-dlp `js_runtimes={"node": {}}` для полного format listing | 5m | ✅ Done |
| 8 | `sys.path` shim в `scripts/ingest_*.py` (4 файла) | 5m | ✅ Done |
| 9 | `.env` → Ollama URL + `nomic-embed-text` | 5m | ✅ Done |
| 10 | YouTube API key через `gcloud services api-keys create` | 10m | ✅ Done |
| 11 | `.gitignore`: `serials/*/rendered/` + `serials/*/matched.json` | 2m | ✅ Done |
| 12 | Audit + tasks + CHANGELOG + git commit | 15m | ✅ Done |

**Итого:** ~2ч, 12 задач, 11 файлов изменено

## Файлы

### Created
- `summary/audit/011_smoke_test_compatibility.md`
- `summary/tasks/011_smoke_test_compatibility.md`

### Modified
- `py/episode/spec_writer.py`
- `py/index/embedder.py`
- `py/ingest/archive.py`
- `py/ingest/youtube.py`
- `scripts/ingest_youtube.py`
- `scripts/ingest_coverr.py`
- `scripts/ingest_mixkit.py`
- `scripts/ingest_archive.py`
- `serials/stalker-reznik/ep-01-pilot/spec.json`
- `.env` (не коммитится — в .gitignore)
- `.gitignore`

## Тесты
77/79 OK (2 fail — pre-existing test isolation issue, F-12 candidate)

## End-to-end
```
brief.md → spec.json → matched.json → draft.json → open -a Concat.app
   ✅         ✅          ✅            ✅              ✅
```